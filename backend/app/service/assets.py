import asyncio
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


def build_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        config=Config(
            s3={"addressing_style": settings.S3_ADDRESSING_STYLE}, retries={"max_attempts": 2}
        ),
    )


_client = lru_cache(build_s3_client)


def _fetch(key: str) -> tuple[bytes, str] | None:
    try:
        obj = _client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
            return None
        raise
    return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")


async def get_asset(key: str) -> tuple[bytes, str] | None:
    return await asyncio.to_thread(_fetch, key)
