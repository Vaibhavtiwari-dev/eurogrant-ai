"""Tests for the S3 service layer.

The service has two paths:
  * `USE_LOCAL_STORAGE=true` (test env)  → writes to a local directory.
  * `USE_LOCAL_STORAGE=false` (prod)     → talks to AWS via boto3.

These tests exercise the local path with the real service object and the S3
path with boto3 mocked.  Both methods are async (Chunk 3 fix) — we await
them to confirm the async wrapper is in place.
"""
import os
import io
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Make sure tests run with local storage enabled, regardless of CI env.
os.environ.setdefault("USE_LOCAL_STORAGE", "true")

from app.services.s3 import S3Service, s3_service  # noqa: E402


@pytest.mark.asyncio
async def test_upload_fileobj_local(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("USE_LOCAL_STORAGE", "true")

    # Rebuild the service so it picks up the new env vars
    svc = S3Service()

    # Minimal UploadFile-like shim — S3Service only needs .file
    class FakeUpload:
        def __init__(self, data: bytes, filename: str = "x.pdf", content_type: str = "application/pdf"):
            self.file = io.BytesIO(data)
            self.filename = filename
            self.content_type = content_type

    payload = b"hello-s3"
    await svc.upload_fileobj(FakeUpload(payload), "org_1/abc.pdf")

    written = tmp_path / "org_1" / "abc.pdf"
    assert written.exists()
    assert written.read_bytes() == payload


@pytest.mark.asyncio
async def test_get_fileobj_local(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("USE_LOCAL_STORAGE", "true")

    target = tmp_path / "readme.txt"
    target.write_text("readme-content", encoding="utf-8")

    svc = S3Service()
    data = await svc.get_fileobj(str(target))
    assert data == b"readme-content"


@pytest.mark.asyncio
async def test_upload_fileobj_s3_path(monkeypatch):
    monkeypatch.setenv("USE_LOCAL_STORAGE", "false")
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

    svc = S3Service()

    mock_client = MagicMock()
    # upload_fileobj is blocking; ensure it was called with the fileobj
    with patch.object(svc, "_get_s3_client", return_value=mock_client):
        class FakeUpload:
            def __init__(self, data: bytes):
                self.file = io.BytesIO(data)
                self.filename = "x.pdf"
                self.content_type = "application/pdf"

        await svc.upload_fileobj(FakeUpload(b"abc"), "org_1/x.pdf")
        assert mock_client.upload_fileobj.called
        call_args = mock_client.upload_fileobj.call_args
        # First positional arg is the fileobj, second is the bucket, third is the key
        assert call_args.args[1] == "test-bucket"
        assert call_args.args[2] == "org_1/x.pdf"


@pytest.mark.asyncio
async def test_get_fileobj_s3_path(monkeypatch):
    monkeypatch.setenv("USE_LOCAL_STORAGE", "false")
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

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
    """A boto3 ClientError should propagate (not be silently swallowed)."""
    monkeypatch.setenv("USE_LOCAL_STORAGE", "false")
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

    from botocore.exceptions import ClientError

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

        with pytest.raises(ClientError):
            await svc.upload_fileobj(FakeUpload(), "org_1/x.pdf")
