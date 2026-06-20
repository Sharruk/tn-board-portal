import os
import uuid
from fastapi import UploadFile, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB


def validate_file(file: UploadFile) -> None:
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")


async def save_file_locally(file: UploadFile) -> tuple[str, str]:
    """
    Save uploaded file to local /uploads/ directory.
    Returns (stored_filename, public_url).
    Phase 4: replace this with Supabase Storage upload.
    """
    validate_file(file)

    content = await file.read()

    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_FILE_SIZE_MB}MB")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    public_url = f"/uploads/{stored_filename}"
    return stored_filename, public_url


def delete_file_locally(file_path: str) -> None:
    """
    Delete a file from local /uploads/ directory.
    Phase 4: replace with Supabase Storage delete.
    """
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
