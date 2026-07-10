"""PII 저장용 AES-256-GCM 암호화 유틸 (법·윤리·품질 체크리스트: 개인정보 보호).

용도
- 위치·검색 로그 등 개인정보를 **부득이 영속 저장**해야 할 때 평문 저장을 금지하고
  AES-256-GCM(AEAD: 기밀성+무결성)으로 암호화한다.
- 현재 파이프라인은 위치/검색을 저장하지 않는 '비저장' 원칙이므로 통상 호출되지 않으나,
  검색이력·분석 등 저장 기능 도입 시 SSOT 암호화 계층으로 사용한다.

설계
- 키: `PII_ENCRYPTION_KEY`(권장, 32B 이상 권장) → 없으면 `SECRET_KEY` 를 HKDF-SHA256 으로
  32바이트(AES-256)로 유도. `backend/secret_store.read_secret_env` 로 시크릿 소싱.
- 봉투(envelope): magic(b"PII1") + 12B nonce + ciphertext(+16B GCM tag) 를 base64url 로 인코딩.
- `cryptography` 미설치 시 명확히 예외 — **평문 폴백 금지**(개인정보 평문 저장 방지).
"""

from __future__ import annotations

import base64
import os
from typing import Optional

_MAGIC = b"PII1"
_NONCE_LEN = 12  # GCM 권장 96-bit


class PiiCryptoUnavailable(RuntimeError):
    """cryptography 미설치 등으로 암호화를 수행할 수 없음(평문 저장 금지)."""


def _derive_key() -> bytes:
    try:
        from backend.secret_store import read_secret_env

        secret = read_secret_env("PII_ENCRYPTION_KEY") or read_secret_env("SECRET_KEY")
    except Exception:
        secret = os.getenv("PII_ENCRYPTION_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        # 개발 편의용 폴백(운영에서는 PII_ENCRYPTION_KEY/SECRET_KEY 필수).
        secret = "dev-pii-key-not-for-production"
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"codeai-pii-aes256")
        return hkdf.derive(secret.encode("utf-8"))
    except ImportError as exc:  # cryptography 없음
        raise PiiCryptoUnavailable("cryptography 미설치 — PII 암호화 불가") from exc


def is_available() -> bool:
    try:
        import cryptography  # noqa: F401

        return True
    except Exception:
        return False


def encrypt_pii(plaintext: Optional[str]) -> Optional[str]:
    """평문 → base64url 암호문 토큰. None/빈문자는 그대로 통과."""
    if plaintext is None or plaintext == "":
        return plaintext
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise PiiCryptoUnavailable("cryptography 미설치 — PII 암호화 불가") from exc

    key = _derive_key()
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(_MAGIC + nonce + ct).decode("ascii")


def decrypt_pii(token: Optional[str]) -> Optional[str]:
    """암호문 토큰 → 평문. None/빈문자는 그대로. 형식 불일치 시 ValueError."""
    if token is None or token == "":
        return token
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise PiiCryptoUnavailable("cryptography 미설치 — PII 복호화 불가") from exc

    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if not raw.startswith(_MAGIC):
        raise ValueError("PII 봉투 매직 불일치")
    body = raw[len(_MAGIC):]
    nonce, ct = body[:_NONCE_LEN], body[_NONCE_LEN:]
    key = _derive_key()
    pt = AESGCM(key).decrypt(nonce, ct, None)
    return pt.decode("utf-8")
