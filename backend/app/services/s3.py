import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status

from ..config import settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self) -> None:
        self.storage_backend = settings.STORAGE_BACKEND.lower()
        if self.storage_backend == "s3":
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            # Use backend root for local storage
            self.local_path = Path("tmp/uploads")
            self.local_path.mkdir(parents=True, exist_ok=True)
            logger.info("Using local storage at %s", self.local_path.absolute())

    def _get_s3_client(self) -> "Any":
        """Return the boto3 S3 client, or None for local-storage backends.

        Exposed as a method (not a plain attribute) so tests can patch it.
        The S3 branches in `upload_fileobj` / `get_fileobj` call through
        this method instead of touching `self.s3_client` directly.
        """
        if self.storage_backend == "s3":
            return self.s3_client
        return None

    def _validate_local_path(self, s3_key: str) -> Path:
        """Validate s3_key to prevent path traversal attacks (CWE-22)."""
        dest_path = (self.local_path / s3_key).resolve()
        if not dest_path.is_relative_to(self.local_path.resolve()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path: traversal attempt detected",
            )
        return dest_path

    async def upload_fileobj(self, file: UploadFile, s3_key: str) -> str:
        if self.storage_backend == "local":
            try:
                dest_path = self._validate_local_path(s3_key)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with dest_path.open("wb") as buffer:
                    # shutil.copyfileobj is blocking; run in a worker thread.
                    await asyncio.to_thread(shutil.copyfileobj, file.file, buffer)
                return s3_key
            except HTTPException:
                raise
            except Exception as exc:
                logger.error("Failed to save locally: %s", exc)
                raise HTTPException(
                    status_code=500, detail="Failed to save file to local storage"
                ) from exc

        # S3 branch: boto3 is blocking, so dispatch to a thread.
        def _upload() -> None:
            client = self._get_s3_client()
            if client is None:
                raise RuntimeError("S3 client required for S3 backend")
            client.upload_fileobj(
                file.file,
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": file.content_type},
            )

        try:
            await asyncio.to_thread(_upload)
            return s3_key
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to upload to S3: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to upload file to storage") from exc

    async def get_fileobj(self, s3_key: str) -> bytes:
        if self.storage_backend == "local":
            try:
                dest_path = self._validate_local_path(s3_key)
                # Path.read_bytes() is blocking.
                return await asyncio.to_thread(dest_path.read_bytes)
            except HTTPException:
                raise
            except Exception as exc:
                logger.error("Failed to read locally: %s", exc)
                raise HTTPException(
                    status_code=500, detail="Failed to read file from local storage"
                ) from exc

        # S3 branch: boto3 is blocking, so dispatch to a thread.
        def _download() -> bytes:
            client = self._get_s3_client()
            if client is None:
                raise RuntimeError("S3 client required for S3 backend")
            response = client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            return response["Body"].read()

        try:
            return await asyncio.to_thread(_download)
        except (ClientError, BotoCoreError) as exc:
            logger.error("Failed to download from S3: %s", exc)
            raise HTTPException(
                status_code=500, detail="Failed to download file from storage"
            ) from exc


s3_service = S3Service()
