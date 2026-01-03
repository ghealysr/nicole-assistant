import logging
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

logger = logging.getLogger(__name__)

def get_s3_client():
    """Get S3 client with proper configuration."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )

async def upload_file_to_s3(
    file_path: str,
    object_name: str,
    content_type: str = 'application/octet-stream'
) -> bool:
    """
    Upload a file to an S3 bucket.

    :param file_path: File to upload
    :param object_name: S3 object name. If not specified then file_name is used
    :param content_type: MIME type of the file
    :return: True if file was uploaded, else False
    """
    bucket_name = os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3_BUCKET_NAME not set")
        return False

    s3_client = get_s3_client()
    try:
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            object_name,
            ExtraArgs={'ContentType': content_type}
        )
        logger.info(f"Uploaded {file_path} to s3://{bucket_name}/{object_name}")
        return True
    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        return False

def generate_presigned_url(object_name: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL to share an S3 object.

    :param object_name: key of the object in S3
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    bucket_name = os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3_BUCKET_NAME not set")
        return None

    s3_client = get_s3_client()
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_name
            },
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None

