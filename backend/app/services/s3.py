import boto3
import os
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile
import logging

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'eu-central-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    async def upload_fileobj(self, file: UploadFile, s3_key: str) -> str:
        try:
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': file.content_type}
            )
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")

s3_service = S3Service()
