import logging
import uuid
from typing import Any, cast

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user, require_role
from ..limiter import limiter
from ..services.document_validation import UnsafeDocumentError, validate_docx_archive
from ..services.s3 import s3_service
from ..worker import process_company_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

# Magic-byte signature map — guards against extension spoofing (CWE-434)
# Validation is based EXCLUSIVELY on magic bytes, not file extensions
ALLOWED_SIGNATURES = {
    "pdf": [b"%PDF"],
    "docx": [b"PK"],  # DOCX is a ZIP archive starting with PK
}

# Content types for each extension (used after magic-byte validation)
CONTENT_TYPES = {
    "pdf": {"application/pdf", "application/x-pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    },
}


def _validate_file_by_magic_bytes(content: bytes) -> str | None:
    """Validate file by magic bytes only. Returns extension if valid, None otherwise.

    This is the primary validation method — extension-based validation is removed
    to prevent extension spoofing attacks (CWE-434).
    """
    for ext, signatures in ALLOWED_SIGNATURES.items():
        if any(content.startswith(sig) for sig in signatures):
            return ext
    return None


def _validate_mime_match(content_type: str, extension: str) -> bool:
    """Validate declared content_type is plausible for the file extension."""
    expected = CONTENT_TYPES.get(extension, set())
    if not expected:
        return True
    # content_type can be something like "application/pdf; charset=utf-8"
    base_type = content_type.split(";")[0].strip()
    if base_type not in expected:
        logger.warning(
            f"Content-Type '{base_type}' does not match detected extension '{extension}' — rejecting"
        )
        return False
    return True


@router.get("/documents", response_model=list[schemas.DocumentOut])
async def list_company_documents(
    db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)
):
    docs = (
        db.query(models.CompanyDocument)
        .filter(models.CompanyDocument.organization_id == current_user.organization_id)
        .order_by(models.CompanyDocument.created_at.desc())
        .all()
    )
    return docs


@router.post(
    "/company-document", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def upload_company_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.CompanyDocument:
    # SEC-3: Validate file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File too large. Maximum size is 25MB."
        )

    # Validate filename exists
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    # Validate file by magic bytes ONLY (not extension) — prevents extension spoofing
    file.file.seek(0)
    header = file.file.read(8)
    file.file.seek(0)
    extension = _validate_file_by_magic_bytes(header)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF and DOCX files are accepted.",
        )

    # Validate declared content-type is plausible for the detected extension
    if file.content_type and not _validate_mime_match(file.content_type, extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Declared content-type does not match file content",
        )

    # Additional DOCX validation
    if extension == "docx":
        file.file.seek(0)
        file_content = file.file.read()
        file.file.seek(0)
        try:
            validate_docx_archive(file_content)
        except UnsafeDocumentError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsafe archive: {exc}",
            ) from exc

    # Generate unique S3 key
    s3_key = f"org_{current_user.organization_id}/{uuid.uuid4()}.{extension}"

    # Upload to S3
    await s3_service.upload_fileobj(file, s3_key)

    # Save to DB
    new_doc = models.CompanyDocument(
        organization_id=current_user.organization_id,
        file_name=file.filename,
        s3_key=s3_key,
        content_type=file.content_type,
        status=models.DocumentStatus.PENDING,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Trigger background processing
    cast(Any, process_company_document).delay(new_doc.id)

    return new_doc
