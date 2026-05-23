"""
Marketplace utilities
MinIO integration, rating calculation, etc.
"""
from fastapi import UploadFile
from sqlalchemy.orm import Session
from typing import Tuple
import boto3
from botocore.client import Config
import os

from .models import Review
from backend.secret_store import read_secret_env


# ==================== MinIO 설정 ====================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = read_secret_env("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = read_secret_env("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "marketplace-projects")


def get_minio_client():
    """MinIO S3 클라이언트 생성"""
    if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        raise RuntimeError("MINIO_ACCESS_KEY/MINIO_SECRET_KEY 가 설정되지 않았습니다")
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )


async def upload_to_minio(file: UploadFile, prefix: str) -> str:
    """
    MinIO에 파일 업로드
    
    Args:
        file: 업로드할 파일
        prefix: 파일 경로 prefix (예: "projects/123")
    
    Returns:
        MinIO 파일 경로
    """
    client = get_minio_client()
    
    # 파일명 생성
    filename = f"{prefix}/{file.filename}"
    
    # 업로드
    content = await file.read()
    client.put_object(
        Bucket=MINIO_BUCKET,
        Key=filename,
        Body=content,
        ContentType=file.content_type
    )
    
    return filename


def get_download_url(file_path: str, expires: int = 3600) -> str:
    """
    MinIO 파일 다운로드 URL 생성 (임시 URL)
    
    Args:
        file_path: MinIO 파일 경로
        expires: URL 만료 시간 (초)
    
    Returns:
        다운로드 URL
    """
    client = get_minio_client()
    
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": file_path},
        ExpiresIn=expires
    )
    
    return url


# ==================== 평점 계산 ====================

def calculate_rating(db: Session, project_id: int) -> Tuple[float, int]:
    """
    프로젝트 평점 계산
    
    Args:
        db: DB 세션
        project_id: 프로젝트 ID
    
    Returns:
        (평균 평점, 리뷰 수)
    """
    reviews = db.query(Review).filter(Review.project_id == project_id).all()
    
    if not reviews:
        return 0.0, 0
    
    total_rating = sum(r.rating for r in reviews)
    avg_rating = total_rating / len(reviews)
    
    return round(avg_rating, 2), len(reviews)
