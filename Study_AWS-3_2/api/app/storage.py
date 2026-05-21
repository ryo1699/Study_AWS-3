from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .config import settings


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
        config=Config(signature_version="s3v4"),
    )


def build_image_key(task_id: int, filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower() or ".jpg"
    return f"private-images/tasks/{task_id}/{uuid4().hex}{suffix}"


def create_upload_url(task_id: int, filename: str, content_type: str) -> tuple[str, str]:
    if not settings.image_bucket_name:
        raise RuntimeError("IMAGE_BUCKET_NAME is not configured")

    key = build_image_key(task_id, filename)
    url = _s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.image_bucket_name,
            "Key": key,
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        },
        ExpiresIn=settings.upload_url_expires_seconds,
    )
    return url, key


def image_object_exists(s3_key: str) -> bool:
    if not settings.image_bucket_name:
        raise RuntimeError("IMAGE_BUCKET_NAME is not configured")

    try:
        _s3_client().head_object(Bucket=settings.image_bucket_name, Key=s3_key)
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code in (403, 404):
            return False
        raise RuntimeError(f"Failed to check image object: {exc}") from exc
    return True


def _rsa_signer(message: bytes) -> bytes:
    private_key_text = settings.cloudfront_private_key_pem.replace("\\n", "\n")
    private_key = serialization.load_pem_private_key(private_key_text.encode("utf-8"), password=None)
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def create_cloudfront_signed_url(s3_key: str) -> str:
    if not settings.cloudfront_domain_name or not settings.cloudfront_key_pair_id:
        raise RuntimeError("CloudFront signed URL settings are not configured")

    expire_at = datetime.now(timezone.utc) + timedelta(seconds=settings.view_url_expires_seconds)
    signer = CloudFrontSigner(settings.cloudfront_key_pair_id, _rsa_signer)
    resource_url = f"https://{settings.cloudfront_domain_name}/{s3_key}"
    return signer.generate_presigned_url(resource_url, date_less_than=expire_at)
