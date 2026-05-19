import csv
import io
import json
import os
import time
from datetime import datetime, timezone

import boto3
import psycopg
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    aws_region: str = "ap-northeast-1"
    csv_bucket_name: str
    csv_export_queue_url: str
    poll_wait_seconds: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
sqs = boto3.client("sqs", region_name=settings.aws_region)
s3 = boto3.client("s3", region_name=settings.aws_region)


def update_job(conn: psycopg.Connection, job_id: int, status: str, s3_key: str | None = None, error: str | None = None) -> None:
    completed_at = datetime.now(timezone.utc) if status in {"complete", "failed"} else None
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE csv_export_jobs
               SET status = %s,
                   s3_key = COALESCE(%s, s3_key),
                   error_message = %s,
                   updated_at = CURRENT_TIMESTAMP,
                   completed_at = COALESCE(%s, completed_at)
             WHERE id = %s
            """,
            (status, s3_key, error, completed_at, job_id),
        )
    conn.commit()


def build_csv(conn: psycopg.Connection) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "description", "status", "picture_s3_key", "created_at", "updated_at"])
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, description, status, picture_s3_key, created_at, updated_at
              FROM tasks
             ORDER BY id
            """
        )
        for row in cur.fetchall():
            writer.writerow(row)
    return output.getvalue()


def process_job(job_id: int) -> None:
    with psycopg.connect(settings.database_url) as conn:
        try:
            update_job(conn, job_id, "processing")
            csv_body = build_csv(conn)
            s3_key = f"csv-exports/job-{job_id}.csv"
            s3.put_object(
                Bucket=settings.csv_bucket_name,
                Key=s3_key,
                Body=csv_body.encode("utf-8-sig"),
                ContentType="text/csv; charset=utf-8",
                ServerSideEncryption="AES256",
            )
            update_job(conn, job_id, "complete", s3_key=s3_key)
            print(json.dumps({"jobId": job_id, "status": "complete", "s3Key": s3_key}))
        except Exception as exc:
            update_job(conn, job_id, "failed", error=str(exc))
            raise


def poll_once() -> bool:
    response = sqs.receive_message(
        QueueUrl=settings.csv_export_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=settings.poll_wait_seconds,
    )
    messages = response.get("Messages", [])
    if not messages:
        return False

    message = messages[0]
    payload = json.loads(message["Body"])
    process_job(int(payload["jobId"]))
    sqs.delete_message(QueueUrl=settings.csv_export_queue_url, ReceiptHandle=message["ReceiptHandle"])
    return True


def main() -> None:
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"
    while True:
        poll_once()
        if run_once:
            break
        time.sleep(1)


if __name__ == "__main__":
    main()

