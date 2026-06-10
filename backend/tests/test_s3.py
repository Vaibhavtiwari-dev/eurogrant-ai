"""Tests for the S3 service layer.

The service has two paths:
  * `STORAGE_BACKEND=local` → writes to a local directory.
  * `STORAGE_BACKEND=s3`    → talks to AWS via boto3.

These tests exercise the local path with the real service object and the S3
path with boto3 mocked.  Both methods are async (Chunk 3 fix) — we await
them to confirm the async wrapper is in place.
"""

import io
import os
from unittest.mock import MagicMock, patch

import pytest

# Make sure tests run with local storage enabled, regardless of CI env.
os.environ.setdefault("STORAGE_BACKEND", "local")

from app.services.s3 import S3Service  # noqa: E402


@pytest.mark.asyncio
async def test_upload_fileobj_local(tmp_path, monkeypatch):
    from app.config import settings
    settings.STORAGE_BACKEND = "local"

    # Rebuild the service so it picks up the new env vars
    svc = S3Service()
    svc.local_path = tmp_path

    # Minimal UploadFile-like shim — S3Service only needs .file
    class FakeUpload:
        def __init__(
            self, data: bytes, filename: str = "x.pdf", content_type: str = "application/pdf"
        ):
            self.file = io.BytesIO(data)
            self.filename = filename
            self.content_type = content_type

    payload = b"hello-s3"
    await svc.upload_fileobj(FakeUpload(payload), "org_1/abc.pdf")  # type: ignore

    written = tmp_path / "org_1" / "abc.pdf"
    assert written.exists()
    assert written.read_bytes() == payload


@pytest.mark.asyncio
async def test_get_fileobj_local(tmp_path, monkeypatch):
    from app.config import settings
    settings.STORAGE_BACKEND = "local"

    target = tmp_path / "readme.txt"
    target.write_text("readme-content", encoding="utf-8")

    svc = S3Service()
    svc.local_path = tmp_path
    data = await svc.get_fileobj("readme.txt")
    assert data == b"readme-content"


@pytest.mark.asyncio
async def test_upload_fileobj_s3_path(monkeypatch):
    from app.config import settings
    settings.STORAGE_BACKEND = "s3"
    settings.S3_BUCKET_NAME = "test-bucket"

    svc = S3Service()

    mock_client = MagicMock()
    # upload_fileobj is blocking; ensure it was called with the fileobj
    with patch.object(svc, "_get_s3_client", return_value=mock_client):

        class FakeUpload:
            def __init__(self, data: bytes):
                self.file = io.BytesIO(data)
                self.filename = "x.pdf"
                self.content_type = "application/pdf"

        await svc.upload_fileobj(FakeUpload(b"abc"), "org_1/x.pdf")  # type: ignore
        assert mock_client.upload_fileobj.called
        call_args = mock_client.upload_fileobj.call_args
        # First positional arg is the fileobj, second is the bucket, third is the key
        assert call_args.args[1] == "test-bucket"
        assert call_args.args[2] == "org_1/x.pdf"


@pytest.mark.asyncio
async def test_get_fileobj_s3_path(monkeypatch):
    from app.config import settings
    settings.STORAGE_BACKEND = "s3"
    settings.S3_BUCKET_NAME = "test-bucket"

    svc = S3Service()

    mock_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b"object-bytes"
    mock_client.get_object.return_value = {"Body": mock_body}

    with patch.object(svc, "_get_s3_client", return_value=mock_client):
        data = await svc.get_fileobj("org_1/y.pdf")
        assert data == b"object-bytes"
        mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="org_1/y.pdf")


@pytest.mark.asyncio
async def test_upload_fileobj_boto3_error(monkeypatch):
    """A boto3 ClientError should be translated to a safe HTTP error."""
    from app.config import settings
    settings.STORAGE_BACKEND = "s3"
    settings.S3_BUCKET_NAME = "test-bucket"

    from botocore.exceptions import ClientError
    from fastapi import HTTPException

    svc = S3Service()
    mock_client = MagicMock()
    mock_client.upload_fileobj.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "nope"}}, "PutObject"
    )

    with patch.object(svc, "_get_s3_client", return_value=mock_client):

        class FakeUpload:
            def __init__(self):
                self.file = io.BytesIO(b"x")
                self.filename = "x.pdf"
                self.content_type = "application/pdf"

        with pytest.raises(HTTPException) as exc_info:
            await svc.upload_fileobj(FakeUpload(), "org_1/x.pdf")  # type: ignore
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to upload file to storage"
