"""Evidence storage abstraction (spec: 'Supabase Storage or S3-compatible storage').

Two implementations behind one interface so the immutable-evidence guarantee (spec
section 3/5 Layer A) doesn't depend on which backend is configured. Local filesystem
storage is the default because no object-storage credentials are reachable from this
environment; the S3-compatible backend (works unmodified against Supabase Storage,
which speaks the S3 API) is a drop-in swap via STORAGE_BACKEND=s3.

Keys are content-addressed under the audit, so re-uploading identical bytes for the
same audit is idempotent and nothing already written is ever overwritten in place.
"""

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


def sha256_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_storage_key(audit_id: str, checksum: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"audits/{audit_id}/{checksum}/{safe_name}"


class StorageBackend(ABC):
    @abstractmethod
    def write(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, key: str, content: bytes) -> None:
        path = self._path(key)
        if not path.exists():
            path.write_bytes(content)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3StorageBackend(StorageBackend):
    def __init__(self, bucket: str, endpoint_url: str | None = None, region: str | None = None) -> None:
        import boto3  # imported lazily so the local backend never requires boto3 at import time

        self.bucket = bucket
        self._client = boto3.client("s3", endpoint_url=endpoint_url, region_name=region)

    def write(self, key: str, content: bytes) -> None:
        if self.exists(key):
            return
        self._client.put_object(Bucket=self.bucket, Key=key, Body=content)

    def read(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set")
        return S3StorageBackend(settings.s3_bucket, settings.s3_endpoint_url, settings.s3_region)
    return LocalStorageBackend(settings.storage_local_root)
