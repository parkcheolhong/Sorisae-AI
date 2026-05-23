"""
MinIO 파일 스토리지 서비스 — Lazy Connection (시작 시 연결 안 함)
"""
import os
import io
import time
import logging
from typing import Optional
from backend.secret_store import read_secret_env

logger = logging.getLogger(__name__)
class MinIOService:
    def __init__(self):
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "host.docker.internal:9000")
        self.minio_access_key = read_secret_env("MINIO_ACCESS_KEY")
        self.minio_secret_key = read_secret_env("MINIO_SECRET_KEY")
        self.bucket_name = os.getenv("MINIO_BUCKET", "marketplace-projects")
        self._client = None  # Lazy — 첫 사용 시 연결
        self._disabled_until_epoch = 0.0
        self._retry_cooldown_sec = 30.0
        logger.info(f"[MinIO] endpoint={self.minio_endpoint}, bucket={self.bucket_name}")

    @property
    def client(self):
        """첫 호출 시에만 MinIO 연결"""
        if self._client is None and time.time() < self._disabled_until_epoch:
            return None
        if not self.minio_access_key or not self.minio_secret_key:
            logger.warning("[MinIO] MINIO_ACCESS_KEY/MINIO_SECRET_KEY 미설정으로 기능을 비활성화합니다")
            return None
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    self.minio_endpoint,
                    access_key=self.minio_access_key,
                    secret_key=self.minio_secret_key,
                    secure=False,
                )
                # 버킷 생성 (없으면)
                if not self._client.bucket_exists(self.bucket_name):
                    self._client.make_bucket(self.bucket_name)
                    logger.info(f"[MinIO] 버킷 생성: {self.bucket_name}")
                else:
                    logger.info(f"[MinIO] 버킷 확인: {self.bucket_name}")
                self._disabled_until_epoch = 0.0
            except Exception as e:
                logger.warning(f"[MinIO] 연결 실패 (기능 비활성화): {e}")
                self._client = None
                self._disabled_until_epoch = time.time() + self._retry_cooldown_sec
        return self._client

    def upload_file(self, file_data: bytes, filename: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """파일 업로드 — MinIO 없으면 None 반환"""
        if self.client is None:
            logger.warning("[MinIO] 클라이언트 없음 — 업로드 건너뜀")
            return None
        try:
            self.client.put_object(
                self.bucket_name,
                filename,
                io.BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )
            return f"http://{self.minio_endpoint}/{self.bucket_name}/{filename}"
        except Exception as e:
            logger.error(f"[MinIO] 업로드 실패: {e}")
            return None

    def download_file(self, filename: str) -> Optional[bytes]:
        """파일 다운로드"""
        if self.client is None:
            return None
        try:
            response = self.client.get_object(self.bucket_name, filename)
            return response.read()
        except Exception as e:
            logger.error(f"[MinIO] 다운로드 실패: {e}")
            return None

    def delete_file(self, filename: str) -> bool:
        """파일 삭제"""
        if self.client is None:
            return False
        try:
            self.client.remove_object(self.bucket_name, filename)
            return True
        except Exception as e:
            logger.error(f"[MinIO] 삭제 실패: {e}")
            return False

    def get_presigned_url(self, filename: str, expires_seconds: int = 3600) -> Optional[str]:
        """Pre-signed 다운로드 URL 생성"""
        if self.client is None:
            return None
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name, filename, expires=timedelta(seconds=expires_seconds)
            )
            return url
        except Exception as e:
            logger.error(f"[MinIO] presigned URL 실패: {e}")
            return None

    @property
    def is_available(self) -> bool:
        """MinIO 사용 가능 여부"""
        return self.client is not None


# 싱글턴 인스턴스 (연결은 첫 사용 시)
minio_service = MinIOService()