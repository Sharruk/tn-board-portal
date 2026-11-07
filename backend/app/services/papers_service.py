"""
Papers service — business logic for the papers domain.

This layer sits between routes and the repository.
All business rules live here so they are testable independently
of HTTP and Supabase.

Business rules implemented:
  - Only published papers are returned to public endpoints
  - Search term expansion: aliases like 'maths' → 'mathematics'
    (mirrors expandTerms() in frontend/src/services/search.js exactly)
  - De-duplication of search results when multiple expanded terms match
  - download tracking delegates to the repository's RPC call
  - limit capped at MAX_LIMIT to prevent abuse
"""

import logging
from typing import Any, Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.admin_activity_repository import AdminActivityRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.papers_repository import PapersRepository
from app.schemas.paper import (
    PaperCreate,
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    PaperSearchResult,
    PaperSummary,
    PaperUpdate,
    SearchResponse,
)
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Maximum rows any list endpoint will return
MAX_LIMIT = 100
DEFAULT_LIMIT = 10

# ── Term expansion ────────────────────────────────────────────────────────────
# Mirrors SUBJECT_ALIASES + EXAM_PATTERNS from frontend/src/services/search.js
# exactly so API search results match what the frontend produces.

_SUBJECT_ALIASES: dict[str, str] = {
    "maths": "mathematics", "math": "mathematics", "mathematics": "mathematics",
    "phy": "physics", "physics": "physics",
    "chem": "chemistry", "chemistry": "chemistry",
    "bio": "biology", "biology": "biology",
    "eng": "english", "english": "english",
    "tamil": "tamil",
    "cs": "computer science", "computer": "computer science",
    "history": "history",
    "geo": "geography", "geography": "geography",
    "civics": "civics",
    "economics": "economics",
    "commerce": "commerce",
    "accounts": "accountancy", "accountancy": "accountancy",
    "social": "social science", "science": "science",
}

_EXAM_PATTERNS: list[str] = [
    "monthly test",
    "first mid term test", "first mid term",
    "unit test 1", "unit test 2", "unit test 3",
    "quarterly exam", "quarterly",
    "half yearly exam", "half yearly",
    "annual exam", "annual",
    "public exam",
    "practical exam",
    "model exam",
]


def _expand_terms(q: str) -> list[str]:
    """
    Expand a search query into a list of related terms.

    Mirrors expandTerms() in frontend/src/services/search.js.
    The original term is always included. Subject aliases and exam
    patterns are added when they match the query.
    """
    normalized = q.strip().lower()
    terms: set[str] = {normalized}

    for alias, full in _SUBJECT_ALIASES.items():
        if alias in normalized and full != normalized:
            terms.add(full)

    for pattern in _EXAM_PATTERNS:
        if pattern in normalized and pattern != normalized:
            terms.add(pattern)

    return list(terms)


_expand_search_terms = _expand_terms

# ── Service ───────────────────────────────────────────────────────────────────



class PapersService:
    """Business logic for the papers domain."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._repo = PapersRepository(db, storage=storage)
        self._activity_repo = AdminActivityRepository(db)
        self._outbox_repo = OutboxRepository(db)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/{id}
    # ------------------------------------------------------------------ #

    def get_paper(self, paper_id: int) -> PaperResponse:
        """
        Return one published paper with full subject + class detail.
        Raises NotFoundError if not found or not published.
        """
        logger.info("PapersService.get_paper(paper_id=%s)", paper_id)
        row = self._repo.get_by_id(paper_id, published_only=True)
        if row is None:
            raise NotFoundError(resource="Paper", identifier=paper_id)
        return PaperResponse(**row)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers — list (recent or popular)
    # ------------------------------------------------------------------ #

    def list_papers(
        self,
        sort: Literal["recent", "popular"] = "recent",
        limit: int = DEFAULT_LIMIT,
    ) -> PaperListResponse:
        """
        Return recent or popular published papers.

        Args:
            sort:  'recent'  → ordered by created_at DESC (default)
                   'popular' → ordered by download_count DESC
            limit: Number of papers to return (capped at MAX_LIMIT).
        """
        logger.info("PapersService.list_papers(sort=%s, limit=%s)", sort, limit)
        limit = min(max(1, limit), MAX_LIMIT)

        if sort == "popular":
            rows = self._repo.list_popular(limit)
        else:
            rows = self._repo.list_recent(limit)

        items = [PaperSummary(**row) for row in rows]
        return PaperListResponse(data=items, count=len(items), limit=limit)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/by-subject/{subject_id}
    # ------------------------------------------------------------------ #

    def list_by_subject(
        self,
        subject_id: int,
        exam_type: str | None = None,
        paper_type: str | None = None,
    ) -> PaperListResponse:
        """
        Return all published papers for a subject, ordered by year DESC.
        Mirrors getPapersForSubject() in frontend/src/services/subjects.js.
        """
        logger.info(
            "PapersService.list_by_subject(subject_id=%s, exam_type=%s, paper_type=%s)",
            subject_id, exam_type, paper_type,
        )
        rows = self._repo.list_by_subject(
            subject_id=subject_id,
            exam_type=exam_type,
            paper_type=paper_type,
        )
        items = [PaperSummary(**row) for row in rows]
        return PaperListResponse(data=items, count=len(items), limit=len(items))

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/search
    # ------------------------------------------------------------------ #

    def search_papers(
        self,
        q: str,
        class_id: int | None = None,
        exam_type: str | None = None,
        paper_type: str | None = None,
        month: str | None = None,
        district: str | None = None,
    ) -> SearchResponse:
        """
        Full-text paper search using direct SQL joining papers, subjects, and classes.

        Mirrors the frontend searchPapers() function in search.js:
          1. Normalise the raw query
          2. Expand into multiple terms (aliases + exam patterns)
          3. Call search query for each term
          4. De-duplicate results by paper id (last-write-wins)
          5. Return wrapped SearchResponse

        Only searches visible / published papers.
        """
        logger.info(
            "PapersService.search_papers(q=%r, class_id=%s, exam_type=%s, "
            "paper_type=%s, month=%s, district=%s)",
            q, class_id, exam_type, paper_type, month, district,
        )

        raw_query = q.strip()
        if not raw_query:
            return SearchResponse(query="", total=0, results=[])

        terms = _expand_terms(raw_query)
        seen: dict[int, dict] = {}

        for term in terms:
            rows = self._repo.search(
                q=term,
                class_id=class_id,
                exam_type=exam_type,
                paper_type=paper_type,
                month=month,
                district=district,
            )
            for row in rows:
                seen[row["id"]] = row

        results = [PaperSearchResult(**row) for row in seen.values()]
        return SearchResponse(query=raw_query, total=len(results), results=results)

    # ------------------------------------------------------------------ #
    # POST /api/v1/papers/{id}/download
    # ------------------------------------------------------------------ #

    def record_download(
        self,
        paper_id: int,
        user_id: str | None = None,
        user_email: str | None = None,
    ) -> None:
        """
        Increment the download counter for a published paper.
        Raises NotFoundError if the paper doesn't exist or isn't published.
        """
        logger.info("PapersService.record_download(paper_id=%s)", paper_id)
        try:
            self._repo.record_download(paper_id, user_id=user_id, user_email=user_email)
        except Exception as exc:
            logger.warning("record_download failed for paper_id=%s: %s", paper_id, exc)
            raise NotFoundError(resource="Paper", identifier=paper_id) from exc

    # ------------------------------------------------------------------ #
    # POST /api/v1/papers (Admin)
    # ------------------------------------------------------------------ #

    def create_paper(
        self,
        req: PaperCreate,
        current_user: dict,
        ip_address: Optional[str] = None,
    ) -> PaperResponse:
        """Create a paper and log PAPER_CREATED admin activity."""
        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        try:
            created = self._repo.create_paper(
                subject_id=req.subject_id,
                exam_type=req.exam_type,
                year=req.year,
                month=req.month,
                district=req.district,
                title=req.title,
                description=req.description,
                paper_type=req.paper_type,
                file_path=req.file_path,
                public_url=req.public_url,
                youtube_url=req.youtube_url,
                original_filename=req.original_filename,
                is_visible=req.is_visible,
                status=req.status,
                contributor_name=req.contributor_name,
                auto_commit=False,
            )
            paper_id = created["id"]

            paper = self._repo.get_by_id(paper_id, published_only=False)
            if not paper:
                paper = created

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="PAPER_CREATED",
                target_type="paper",
                target_id=str(paper_id),
                target_title=paper.get("title") or f"Paper {paper_id}",
                reason=None,
                metadata={
                    "paper_id": paper_id,
                    "title": paper.get("title"),
                    "subject_id": req.subject_id,
                    "exam_type": req.exam_type,
                    "year": req.year,
                    "file_path": req.file_path,
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return PaperResponse(**paper)
        except Exception:
            self._db.rollback()
            raise

    # ------------------------------------------------------------------ #
    # PATCH /api/v1/papers/{id} (Admin)
    # ------------------------------------------------------------------ #

    def update_paper(
        self,
        paper_id: int,
        req: PaperUpdate,
        current_user: dict,
        ip_address: Optional[str] = None,
    ) -> PaperResponse:
        """Update a paper, enqueue storage outbox if file replaced, and log PAPER_UPDATED admin activity."""
        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        existing = self._repo.get_by_id(paper_id, published_only=False)
        if not existing:
            raise NotFoundError(resource="Paper", identifier=paper_id)

        updates = req.model_dump(exclude_unset=True)

        try:
            # If file_path is being replaced, enqueue deletion of old file_path to outbox
            new_file_path = updates.get("file_path")
            old_file_path = existing.get("file_path")
            if new_file_path and old_file_path and new_file_path != old_file_path:
                self._outbox_repo.enqueue(
                    bucket_name="papers",
                    object_path=old_file_path,
                    operation="DELETE",
                    idempotency_key=f"replace:papers:{paper_id}:{old_file_path}",
                )

            self._repo.update_paper(paper_id=paper_id, updates=updates, auto_commit=False)
            updated = self._repo.get_by_id(paper_id, published_only=False)
            if not updated:
                raise NotFoundError(resource="Paper", identifier=paper_id)

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="PAPER_UPDATED",
                target_type="paper",
                target_id=str(paper_id),
                target_title=updated.get("title") or f"Paper {paper_id}",
                reason=None,
                metadata={
                    "paper_id": paper_id,
                    "updated_fields": list(updates.keys()),
                    "title": updated.get("title"),
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return PaperResponse(**updated)
        except Exception:
            self._db.rollback()
            raise

    # ------------------------------------------------------------------ #
    # DELETE /api/v1/papers/{id} (Admin)
    # ------------------------------------------------------------------ #

    def delete_paper(
        self,
        paper_id: int,
        current_user: dict | None = None,
        ip_address: Optional[str] = None,
    ) -> PaperDeleteResponse:
        """
        Permanently delete a paper and its associated storage file in the 'papers' bucket.

        Args:
            paper_id: Primary key of the paper.
            current_user: Admin user dict from require_admin dependency.
            ip_address: Client IP address.

        Raises:
            NotFoundError if the paper does not exist.
        """
        logger.info("PapersService.delete_paper(paper_id=%s)", paper_id)
        admin_id = ((current_user.get("user_id") or current_user.get("firebase_uid")) if current_user else None)
        admin_email = current_user.get("email") if current_user else None

        # Fetch paper details first for audit logging
        paper = self._repo.get_by_id(paper_id, published_only=False)
        if not paper:
            raise NotFoundError(resource="Paper", identifier=paper_id)

        try:
            # Enqueue storage deletion into transactional outbox
            file_path = paper.get("file_path")
            if not file_path and paper.get("public_url"):
                pub_url = paper["public_url"]
                if "/papers/" in pub_url:
                    file_path = pub_url.split("/papers/")[-1].split("?")[0]
            if file_path:
                self._outbox_repo.enqueue(
                    bucket_name="papers",
                    object_path=file_path,
                    operation="DELETE",
                    idempotency_key=f"delete:papers:{paper_id}:{file_path}",
                )

            db_deleted, storage_deleted = self._repo.delete_paper(
                paper_id=paper_id,
                admin_id=admin_id,
                admin_email=admin_email,
                auto_commit=False,
            )
            if not db_deleted:
                raise NotFoundError(resource="Paper", identifier=paper_id)

            if current_user:
                actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
                actor_email = current_user.get("email") or "system@hungrylearner.internal"
                actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
                actor_role = current_user.get("role") or "ADMIN"
                self._activity_repo.log_activity(
                    actor_uid=actor_id,
                    actor_email=actor_email,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    action="PAPER_DELETED",
                    target_type="paper",
                    target_id=str(paper_id),
                    target_title=paper.get("title") or f"Paper {paper_id}",
                    reason=None,
                    metadata={
                        "paper_id": paper_id,
                        "title": paper.get("title"),
                        "exam_type": paper.get("exam_type"),
                        "year": paper.get("year"),
                        "file_path": paper.get("file_path"),
                        "original_filename": paper.get("original_filename"),
                        "storage_deleted": storage_deleted,
                    },
                    ip_address=ip_address,
                )

            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        msg = (
            "Paper and its uploaded file deleted successfully."
            if storage_deleted
            else "Paper deleted successfully (storage file was not found)."
        )
        return PaperDeleteResponse(
            paper_id=paper_id,
            deleted=True,
            storage_deleted=storage_deleted,
            message=msg,
        )

    # ------------------------------------------------------------------ #
    # Likes & Comments
    # ------------------------------------------------------------------ #

    def toggle_like(self, paper_id: int, firebase_uid: str) -> dict:
        """Toggle like for user on paper."""
        # Ensure paper exists
        self.get_paper(paper_id)
        return self._repo.toggle_like(paper_id, firebase_uid)

    def get_likes_info(self, paper_id: int, firebase_uid: str | None = None) -> dict:
        """Get like count and has_liked status."""
        self.get_paper(paper_id)
        return self._repo.get_likes_info(paper_id, firebase_uid)

    def get_comments(self, paper_id: int) -> list:
        """Get threaded comments for paper."""
        self.get_paper(paper_id)
        flat_rows = self._repo.get_comments_for_paper(paper_id)

        from app.schemas.paper import PaperCommentOut

        comment_map: dict[str, PaperCommentOut] = {}
        root_comments: list[PaperCommentOut] = []

        for c in flat_rows:
            c_out = PaperCommentOut(
                id=str(c["id"]),
                paper_id=c["paper_id"],
                firebase_uid=c["firebase_uid"],
                author_name=c["author_name"],
                author_avatar=c.get("author_avatar"),
                parent_id=str(c["parent_id"]) if c.get("parent_id") else None,
                content=c["content"],
                is_deleted=c.get("is_deleted", False),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                replies=[],
            )
            comment_map[str(c["id"])] = c_out

        for c in flat_rows:
            c_id = str(c["id"])
            p_id = str(c["parent_id"]) if c.get("parent_id") else None
            if p_id and p_id in comment_map:
                comment_map[p_id].replies.append(comment_map[c_id])
            else:
                root_comments.append(comment_map[c_id])

        return root_comments

    def add_comment(
        self,
        paper_id: int,
        content: str,
        firebase_uid: str,
        author_name: str,
        parent_id: str | None = None,
        author_avatar: str | None = None,
    ) -> dict:
        """Add comment to paper."""
        self.get_paper(paper_id)
        return self._repo.add_paper_comment(
            paper_id=paper_id,
            firebase_uid=firebase_uid,
            author_name=author_name,
            content=content.strip(),
            parent_id=parent_id,
            author_avatar=author_avatar,
        )

    def delete_comment(
        self,
        comment_id: str,
        current_user: dict,
        ip_address: Optional[str] = None,
    ) -> dict:
        """Delete a comment (owner or admin)."""
        is_admin = current_user.get("role") in ("ADMIN", "SUPER_ADMIN")

        chk_stmt = text("SELECT id, paper_id, firebase_uid, content FROM paper_comments WHERE id::text = :cid")
        row = self._db.execute(chk_stmt, {"cid": str(comment_id)}).fetchone()
        if not row:
            raise NotFoundError(resource="Comment", identifier=comment_id)

        comment_dict = dict(row._mapping)
        user_uid = current_user.get("firebase_uid") or current_user.get("user_id")
        if not is_admin and comment_dict.get("firebase_uid") != user_uid:
            from app.utils.exceptions import ForbiddenError
            raise ForbiddenError(message="You do not have permission to delete this comment.")

        try:
            self._repo.delete_paper_comment(comment_id, hard_delete=is_admin, auto_commit=False)
            if is_admin:
                actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
                actor_email = current_user.get("email") or "system@hungrylearner.internal"
                actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
                actor_role = current_user.get("role") or "ADMIN"
                self._activity_repo.log_activity(
                    actor_uid=actor_id,
                    actor_email=actor_email,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    action="PAPER_COMMENT_DELETED",
                    target_type="paper_comment",
                    target_id=str(comment_id),
                    target_title=f"Comment {comment_id}",
                    reason=None,
                    metadata={
                        "comment_id": str(comment_id),
                        "paper_id": comment_dict.get("paper_id"),
                        "comment_author_uid": comment_dict.get("firebase_uid"),
                        "hard_delete": is_admin,
                    },
                    ip_address=ip_address,
                )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        return {"success": True, "message": "Comment deleted"}
