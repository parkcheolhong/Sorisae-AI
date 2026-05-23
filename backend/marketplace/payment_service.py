"""
결제 시스템 서비스
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models, schemas
import requests
import os
from backend.secret_store import read_secret_env


class PaymentService:
    """결제 시스템 관리 서비스"""
    
    def __init__(self):
        self.payment_gateway_url = os.getenv("PAYMENT_GATEWAY_URL", "http://localhost:8080/api/pay")
        self.api_key = read_secret_env("PAYMENT_API_KEY")
    
    def create_purchase(
        self,
        db: Session,
        project_id: int,
        buyer_id: int,
        amount: float,
        payment_method: str = "card"
    ) -> models.Purchase:
        """구매 기록 생성
        
        Args:
            db: DB 세션
            project_id: 프로젝트 ID
            buyer_id: 구매자 ID
            amount: 금액
            payment_method: 결제 방법
            
        Returns:
            Purchase 객체
        """
        purchase = models.Purchase(
            project_id=project_id,
            buyer_id=buyer_id,
            amount=amount,
            payment_method=payment_method,
            status="pending"
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)
        return purchase
    
    def initiate_payment(
        self,
        purchase_id: int,
        purchase: models.Purchase,
        return_url: str = "http://localhost:8000/api/marketplace/payment/callback"
    ) -> dict:
        """결제 초기화 (PG사 연동)
        
        Args:
            purchase_id: 구매 ID
            purchase: Purchase 객체
            return_url: 콜백 URL
            
        Returns:
            {'payment_url': str, 'order_id': str}
        """
        transaction_id = f"TXN_{uuid.uuid4().hex[:12]}"
        
        payload = {
            "order_id": str(purchase_id),
            "transaction_id": transaction_id,
            "amount": purchase.amount,
            "currency": "KRW",
            "customer_id": purchase.buyer_id,
            "return_url": return_url
        }
        
        # 실제 결제 게이트웨이 연동 (현재는 시뮬레이션)
        # response = requests.post(
        #     self.payment_gateway_url,
        #     json=payload,
        #     headers={"Authorization": f"Bearer {self.api_key}"}
        # )
        
        # 시뮬레이션: 결제 URL 반환
        payment_url = f"https://payment.example.com/pay?order_id={purchase_id}&transaction_id={transaction_id}"
        
        return {
            "payment_url": payment_url,
            "order_id": str(purchase_id),
            "transaction_id": transaction_id
        }
    
    def confirm_payment(
        self,
        db: Session,
        purchase_id: int,
        transaction_id: str,
        status: str = "completed"
    ) -> models.Purchase:
        """결제 확인 (콜백 처리)
        
        Args:
            db: DB 세션
            purchase_id: 구매 ID
            transaction_id: 거래 ID
            status: 결제 상태
            
        Returns:
            Purchase 객체
        """
        purchase = db.query(models.Purchase).filter(
            models.Purchase.id == purchase_id
        ).first()
        
        if not purchase:
            raise ValueError(f"구매 기록 없음: {purchase_id}")
        
        purchase.status = status
        purchase.transaction_id = transaction_id
        purchase.receipt_url = f"https://receipt.example.com/{transaction_id}"
        purchase.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(purchase)
        
        return purchase
    
    def get_purchase_by_id(self, db: Session, purchase_id: int) -> models.Purchase:
        """구매 기록 조회
        
        Args:
            db: DB 세션
            purchase_id: 구매 ID
            
        Returns:
            Purchase 객체
        """
        return db.query(models.Purchase).filter(
            models.Purchase.id == purchase_id
        ).first()
    
    def get_user_purchases(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list, int]:
        """사용자 구매 내역 조회
        
        Args:
            db: DB 세션
            user_id: 사용자 ID
            skip: 스킵
            limit: 제한
            
        Returns:
            (Purchase 리스트, 총 개수)
        """
        query = db.query(models.Purchase).filter(
            models.Purchase.buyer_id == user_id
        )
        total = query.count()
        purchases = query.offset(skip).limit(limit).all()
        return purchases, total
    
    def refund_purchase(
        self,
        db: Session,
        purchase_id: int,
        reason: str = "User request"
    ) -> models.Purchase:
        """구매 환불 처리
        
        Args:
            db: DB 세션
            purchase_id: 구매 ID
            reason: 환불 사유
            
        Returns:
            Purchase 객체
        """
        purchase = db.query(models.Purchase).filter(
            models.Purchase.id == purchase_id
        ).first()
        
        if not purchase:
            raise ValueError(f"구매 기록 없음: {purchase_id}")
        
        if purchase.status != "completed":
            raise ValueError(f"환불 불가: 상태={purchase.status}")
        
        purchase.status = "refunded"
        purchase.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(purchase)
        
        return purchase


class DownloadTokenService:
    """다운로드 토큰 서비스"""
    
    @staticmethod
    def create_token(
        db: Session,
        project_id: int,
        user_id: int,
        expires_in: int = 3600  # 1시간
    ) -> models.DownloadToken:
        """다운로드 토큰 생성
        
        Args:
            db: DB 세션
            project_id: 프로젝트 ID
            user_id: 사용자 ID
            expires_in: 만료 시간 (초)
            
        Returns:
            DownloadToken 객체
        """
        token = uuid.uuid4().hex
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        download_token = models.DownloadToken(
            token=token,
            project_id=project_id,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(download_token)
        db.commit()
        db.refresh(download_token)
        
        return download_token
    
    @staticmethod
    def validate_token(db: Session, token: str) -> models.DownloadToken:
        """토큰 유효성 검증
        
        Args:
            db: DB 세션
            token: 토큰
            
        Returns:
            DownloadToken 객체
        """
        download_token = db.query(models.DownloadToken).filter(
            models.DownloadToken.token == token
        ).first()
        
        if not download_token:
            raise ValueError("Invalid token")
        
        if download_token.is_used:
            raise ValueError("Token already used")
        
        if download_token.expires_at < datetime.utcnow():
            raise ValueError("Token expired")
        
        return download_token
    
    @staticmethod
    def use_token(db: Session, token: str) -> models.DownloadToken:
        """토큰 사용 표시
        
        Args:
            db: DB 세션
            token: 토큰
            
        Returns:
            DownloadToken 객체
        """
        download_token = DownloadTokenService.validate_token(db, token)
        download_token.is_used = True
        db.commit()
        db.refresh(download_token)
        return download_token


# 글로벌 인스턴스
payment_service = PaymentService()
download_token_service = DownloadTokenService()
