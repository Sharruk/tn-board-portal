"""
Conversations service — business logic for Student-to-Admin Messaging & Support.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.conversations_repository import ConversationsRepository
from app.repositories.submissions_repository import SubmissionsRepository
from app.repositories.admin_users_repository import AdminUsersRepository
from app.services.leaderboard_service import LeaderboardService
from app.schemas.conversation import (
    AdminConversationStatsResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListItem,
    ConversationListResponse,
    LinkedSubmissionInfo,
    MessageCreateRequest,
    MessageResponse,
    StudentContext,
)
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "general_question",
    "material_request",
    "submission_status",
    "report_problem",
    "feedback",
    "other",
}

VALID_STATUSES = {
    "open",
    "awaiting_admin",
    "awaiting_user",
    "resolved",
}


class ConversationsService:
    """Service layer for support conversations and messaging."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ConversationsRepository(db)
        self._submissions_repo = SubmissionsRepository(db)
        self._admin_users_repo = AdminUsersRepository(db)

    # ── Student Endpoints ──────────────────────────────────────────────────────

    def create_conversation(
        self, current_user: dict[str, Any], req: ConversationCreateRequest
    ) -> ConversationDetailResponse:
        """Start a new support conversation."""
        category = req.category.strip().lower()
        if category not in VALID_CATEGORIES:
            raise ValidationError(
                f"Invalid category '{req.category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
            )

        subject = req.subject.strip()
        if len(subject) < 3 or len(subject) > 255:
            raise ValidationError("Subject must be between 3 and 255 characters.")

        message = req.message.strip()
        if not message:
            raise ValidationError("Message cannot be empty.")

        firebase_uid = current_user["firebase_uid"]
        user_email = current_user.get("email") or ""
        user_display_name = current_user.get("display_name") or user_email.split("@")[0] or "Student"

        # Verify submission_id ownership if provided
        submission_id = req.submission_id
        if submission_id:
            sub = self._submissions_repo.get_by_id(submission_id)
            if not sub:
                submission_id = None
            elif sub.get("firebase_uid") and sub.get("firebase_uid") != firebase_uid:
                submission_id = None

        conv_dict = self._repo.create_conversation(
            firebase_uid=firebase_uid,
            user_email=user_email,
            user_display_name=user_display_name,
            category=category,
            subject=subject,
            initial_message=message,
            submission_id=submission_id,
        )

        return self.get_user_conversation_detail(current_user, conv_dict["id"])

    def get_user_conversations(
        self, current_user: dict[str, Any], limit: int = 50, offset: int = 0
    ) -> ConversationListResponse:
        """List current user's conversations."""
        firebase_uid = current_user["firebase_uid"]
        rows, total = self._repo.get_user_conversations(firebase_uid, limit=limit, offset=offset)
        items = [ConversationListItem(**r) for r in rows]
        return ConversationListResponse(data=items, total=total)

    def get_user_conversation_detail(
        self, current_user: dict[str, Any], conversation_id: str
    ) -> ConversationDetailResponse:
        """Fetch full conversation thread for current user and mark admin messages as read."""
        conv = self._repo.get_conversation_by_id(conversation_id)
        if not conv:
            raise NotFoundError(resource="Conversation", identifier=conversation_id)

        # Enforce student isolation
        if conv["firebase_uid"] != current_user["firebase_uid"]:
            raise ForbiddenError("You do not have access to this conversation.")

        # Mark incoming messages as read
        self._repo.mark_messages_read(conversation_id, reader_role="user")

        messages = self._repo.get_messages(conversation_id)
        msg_items = [MessageResponse(**m) for m in messages]

        # Fetch linked submission context if present
        linked_submission = self._load_linked_submission(conv.get("submission_id"))

        return ConversationDetailResponse(
            id=conv["id"],
            firebase_uid=conv["firebase_uid"],
            user_email=conv["user_email"],
            user_display_name=conv["user_display_name"],
            user_photo_url=conv.get("user_photo_url") or current_user.get("photo_url"),
            category=conv["category"],
            subject=conv["subject"],
            status=conv["status"],
            submission_id=conv.get("submission_id"),
            created_at=conv["created_at"],
            updated_at=conv["updated_at"],
            messages=msg_items,
            linked_submission=linked_submission,
        )

    def add_user_message(
        self, current_user: dict[str, Any], conversation_id: str, req: MessageCreateRequest
    ) -> MessageResponse:
        """Post a reply to an existing conversation as a student."""
        conv = self._repo.get_conversation_by_id(conversation_id)
        if not conv:
            raise NotFoundError(resource="Conversation", identifier=conversation_id)

        if conv["firebase_uid"] != current_user["firebase_uid"]:
            raise ForbiddenError("You do not have access to this conversation.")

        message = req.message.strip()
        if not message:
            raise ValidationError("Message cannot be empty.")

        firebase_uid = current_user["firebase_uid"]
        user_name = current_user.get("display_name") or current_user.get("email") or "Student"

        # If conversation was resolved, sending a message re-opens it to awaiting_admin
        new_status = "awaiting_admin"

        msg_dict = self._repo.add_message(
            conversation_id=conversation_id,
            sender_role="user",
            sender_firebase_uid=firebase_uid,
            sender_name=user_name,
            message=message,
            new_status=new_status,
        )
        return MessageResponse(**msg_dict)

    def get_user_unread_count(self, current_user: dict[str, Any]) -> dict[str, int]:
        """Return count of unread admin messages for the student."""
        count = self._repo.get_user_unread_count(current_user["firebase_uid"])
        return {"unread_count": count}

    # ── Admin Endpoints ────────────────────────────────────────────────────────

    def get_admin_conversations(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationListResponse:
        """List conversations for Admin Inbox."""
        rows, total = self._repo.get_admin_conversations(
            status=status, category=category, search=search, limit=limit, offset=offset
        )
        items = [ConversationListItem(**r) for r in rows]
        return ConversationListResponse(data=items, total=total)

    def get_admin_conversation_detail(
        self, conversation_id: str
    ) -> ConversationDetailResponse:
        """Fetch conversation thread with full student context for the admin."""
        conv = self._repo.get_conversation_by_id(conversation_id)
        if not conv:
            raise NotFoundError(resource="Conversation", identifier=conversation_id)

        # Mark student messages as read by admin
        self._repo.mark_messages_read(conversation_id, reader_role="admin")

        messages = self._repo.get_messages(conversation_id)
        msg_items = [MessageResponse(**m) for m in messages]

        # Load contextual student profile
        student_context = self._load_student_context(conv["firebase_uid"], conv.get("user_email"))

        # Load linked submission
        linked_submission = self._load_linked_submission(conv.get("submission_id"))

        return ConversationDetailResponse(
            id=conv["id"],
            firebase_uid=conv["firebase_uid"],
            user_email=conv["user_email"],
            user_display_name=conv["user_display_name"],
            user_photo_url=conv.get("user_photo_url"),
            category=conv["category"],
            subject=conv["subject"],
            status=conv["status"],
            submission_id=conv.get("submission_id"),
            created_at=conv["created_at"],
            updated_at=conv["updated_at"],
            messages=msg_items,
            linked_submission=linked_submission,
            student_context=student_context,
        )

    def admin_reply(
        self, admin_user: dict[str, Any], conversation_id: str, req: MessageCreateRequest
    ) -> MessageResponse:
        """Post a reply as the TN Board Admin and set status to awaiting_user."""
        conv = self._repo.get_conversation_by_id(conversation_id)
        if not conv:
            raise NotFoundError(resource="Conversation", identifier=conversation_id)

        message = req.message.strip()
        if not message:
            raise ValidationError("Message cannot be empty.")

        admin_uid = admin_user.get("firebase_uid") or admin_user.get("id") or "admin"
        admin_name = "TN Board Admin"

        msg_dict = self._repo.add_message(
            conversation_id=conversation_id,
            sender_role="admin",
            sender_firebase_uid=admin_uid,
            sender_name=admin_name,
            message=message,
            new_status="awaiting_user",
        )
        return MessageResponse(**msg_dict)

    def update_conversation_status(
        self, conversation_id: str, new_status: str
    ) -> ConversationDetailResponse:
        """Update conversation status."""
        st = new_status.strip().lower()
        if st not in VALID_STATUSES:
            raise ValidationError(
                f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )
        conv = self._repo.update_status(conversation_id, st)
        if not conv:
            raise NotFoundError(resource="Conversation", identifier=conversation_id)
        return self.get_admin_conversation_detail(conversation_id)

    def get_admin_stats(self) -> AdminConversationStatsResponse:
        """Return inbox statistics for Admin Dashboard."""
        stats = self._repo.get_admin_conversation_stats()
        return AdminConversationStatsResponse(**stats)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _load_linked_submission(self, submission_id: Optional[str]) -> Optional[LinkedSubmissionInfo]:
        """Fetch linked submission details if present."""
        if not submission_id:
            return None
        try:
            sub = self._submissions_repo.get_by_id(submission_id)
            if not sub:
                return None
            files = self._submissions_repo.get_files(submission_id)
            published = self._submissions_repo.get_published_papers_for_submission(submission_id)

            return LinkedSubmissionInfo(
                id=str(sub["id"]),
                publisher_name=sub.get("publisher_name") or "",
                details=sub.get("details"),
                status=sub.get("status") or "pending",
                rejection_reason=sub.get("rejection_reason"),
                thank_you_message=sub.get("thank_you_message"),
                created_at=sub["created_at"],
                reviewed_at=sub.get("reviewed_at"),
                files_count=len(files),
                published_papers=published,
            )
        except Exception as exc:
            logger.warning("Failed to load linked submission %s: %s", submission_id, exc)
            return None

    def _load_student_context(
        self, firebase_uid: str, email: Optional[str] = None
    ) -> Optional[StudentContext]:
        """Build student summary context for the admin."""
        try:
            user_row = self._admin_users_repo.get_user_by_firebase_uid(firebase_uid)
            display_name = (user_row.get("display_name") if user_row else None) or email or "Student"
            photo_url = user_row.get("photo_url") if user_row else None

            # Get user submission stats
            stats = self._submissions_repo.get_user_submission_stats(firebase_uid, email=email)
            total_submissions = stats.get("total_submissions", 0)
            published_count = stats.get("published_count", 0)
            pending_count = stats.get("pending_count", 0)
            rejected_count = stats.get("rejected_count", 0)

            # Get leaderboard rank if any published contributions
            rank = None
            rate = None
            if published_count > 0:
                lb = LeaderboardService(self._db).get_leaderboard(limit=100)
                uname = display_name.strip().lower()
                for entry in lb.data:
                    if entry.contributor_name.strip().lower() == uname:
                        rank = entry.rank
                        rate = entry.acceptance_rate
                        break

            return StudentContext(
                firebase_uid=firebase_uid,
                display_name=display_name,
                email=email,
                photo_url=photo_url,
                total_submissions=total_submissions,
                published_count=published_count,
                pending_count=pending_count,
                rejected_count=rejected_count,
                leaderboard_rank=rank,
                acceptance_rate=rate,
                created_at=user_row.get("created_at") if user_row else None,
                last_active_at=user_row.get("last_active_at") if user_row else None,
            )
        except Exception as exc:
            logger.warning("Failed to load student context for uid %s: %s", firebase_uid, exc)
            return None
