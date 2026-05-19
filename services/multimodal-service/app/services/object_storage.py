from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

_MINIO_CLIENT: Minio | None = None


def _normalize_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme:
        return parsed.netloc
    return endpoint


def get_object_storage_client() -> Minio:
    global _MINIO_CLIENT
    if _MINIO_CLIENT is None:
        settings = get_settings()
        _MINIO_CLIENT = Minio(
            _normalize_endpoint(settings["minio_endpoint"]),
            access_key=settings["minio_access_key"],
            secret_key=settings["minio_secret_key"],
            secure=settings["minio_secure"],
        )
    return _MINIO_CLIENT


def ensure_multimodal_bucket() -> None:
    settings = get_settings()
    client = get_object_storage_client()
    bucket_name = settings["multimodal_bucket"]
    if client.bucket_exists(bucket_name):
        return
    client.make_bucket(bucket_name)


def upload_audio_object(
    object_key: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    settings = get_settings()
    client = get_object_storage_client()
    client.put_object(
        settings["multimodal_bucket"],
        object_key,
        BytesIO(file_bytes),
        len(file_bytes),
        content_type=content_type,
    )
    return f"s3://{settings['multimodal_bucket']}/{object_key}"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError("invalid_s3_uri")
    return parsed.netloc, parsed.path.lstrip("/")


def download_object_bytes(uri: str) -> bytes:
    bucket_name, object_key = parse_s3_uri(uri)
    client = get_object_storage_client()
    response = client.get_object(bucket_name, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_object_to_bucket(
    *,
    bucket_name: str,
    object_key: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    client = get_object_storage_client()
    client.put_object(
        bucket_name,
        object_key,
        BytesIO(file_bytes),
        len(file_bytes),
        content_type=content_type,
    )
    return f"s3://{bucket_name}/{object_key}"


def is_storage_ready() -> bool:
    try:
        ensure_multimodal_bucket()
        return True
    except S3Error:
        return False
