from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///./local.db"
    aws_region: str = "ap-northeast-1"
    image_bucket_name: str = ""
    csv_bucket_name: str = ""
    csv_export_queue_url: str = ""
    cloudfront_domain_name: str = ""
    cloudfront_key_pair_id: str = ""
    cloudfront_private_key_pem: str = ""
    upload_url_expires_seconds: int = 300
    view_url_expires_seconds: int = 300

    class Config:
        env_file = ".env"


settings = Settings()
