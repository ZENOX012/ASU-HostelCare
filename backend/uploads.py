import os
import uuid
import io
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from backend.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}

def validate_and_save_upload(file: UploadFile, subfolder: str = "") -> str:
    """
    Validates file extension, MIME type, file size, and magic bytes using Pillow.
    Saves file with a random UUID to avoid collisions and execution attacks.
    Returns relative URL path for accessing the file.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # 1. Check extension
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not allowed. Supported formats: JPG, JPEG, PNG, WEBP."
        )

    # 2. Check declared content type
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type '{file.content_type}' is not an allowed image format."
        )

    # 3. Read file into memory to check size and magic bytes
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 4. Validate magic bytes / image structure with Pillow
    try:
        image_stream = io.BytesIO(content)
        with Image.open(image_stream) as img:
            img_format = img.format
            if img_format not in ALLOWED_PIL_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image structure or disguised executable file detected."
                )
            # Verify image integrity
            img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or invalid image file. Magic byte validation failed."
        )

    # 5. Generate secure random filename
    target_dir = os.path.join(settings.UPLOAD_DIR, subfolder) if subfolder else settings.UPLOAD_DIR
    os.makedirs(target_dir, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(target_dir, unique_filename)

    with open(target_path, "wb") as f:
        f.write(content)

    # Return public URL endpoint path
    if subfolder:
        return f"/api/uploads/{subfolder}/{unique_filename}"
    return f"/api/uploads/{unique_filename}"
