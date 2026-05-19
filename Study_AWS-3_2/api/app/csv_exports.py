import json

import boto3

from .config import settings


def sqs_client():
    return boto3.client("sqs", region_name=settings.aws_region)


def s3_client():
    return boto3.client("s3", region_name=settings.aws_region)


def enqueue_csv_export(job_id: int) -> None:
    if not settings.csv_export_queue_url:
        raise RuntimeError("CSV_EXPORT_QUEUE_URL is not configured")

    sqs_client().send_message(
        QueueUrl=settings.csv_export_queue_url,
        MessageBody=json.dumps({"jobId": job_id}),
    )


def create_csv_download_url(s3_key: str, expires_in: int = 300) -> str:
    if not settings.csv_bucket_name:
        raise RuntimeError("CSV_BUCKET_NAME is not configured")

    return s3_client().generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.csv_bucket_name, "Key": s3_key},
        ExpiresIn=expires_in,
    )
