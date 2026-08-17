#!/usr/bin/env python3
"""
마켓플레이스 구매/결제/다운로드 플로우 테스트
"""
import urllib.request
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode

BASE_URL = "http://127.0.0.1:8000"

def test_login():
    """로그인 테스트 (form-encoded)"""
    print("\n=== TEST 1: 로그인 ===")
    body = urlencode({
        "username": "testuser",
        "password": "testpass123"
    }).encode()
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            token = result.get("access_token", "")
            print(f"✓ 로그인 성공: token_len={len(token)}")
            return token
    except HTTPError as e:
        print(f"✗ 로그인 실패: {e.code}")
        print(f"  {e.read().decode()[:200]}")
        return None

def test_create_purchase(token):
    """구매 생성 테스트"""
    print("\n=== TEST 2: 구매 생성 (인증 필수) ===")
    data = json.dumps({
        "project_id": 1,
        "amount": 189000.0,
        "payment_method": "card"
    }).encode()
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/marketplace/purchase",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            purchase_id = result.get("id")
            print(f"✓ 구매 생성 성공: purchase_id={purchase_id}")
            return purchase_id
    except HTTPError as e:
        print(f"✗ 구매 생성 실패: {e.code}")
        print(f"  {e.read().decode()[:200]}")
        return None

def test_initiate_payment(token, purchase_id):
    """결제 초기화 테스트"""
    print(f"\n=== TEST 3: 결제 초기화 (purchase_id={purchase_id}) ===")
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/marketplace/purchase/{purchase_id}/pay",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            payment_url = result.get("payment_url", "")
            print(f"✓ 결제 초기화 성공: url_len={len(payment_url)}")
            return result
    except HTTPError as e:
        print(f"✗ 결제 초기화 실패: {e.code}")
        print(f"  {e.read().decode()[:200]}")
        return None

def test_create_download_token(token, project_id):
    """다운로드 토큰 생성 테스트"""
    print(f"\n=== TEST 4: 다운로드 토큰 생성 (project_id={project_id}) ===")
    data = json.dumps({
        "project_id": project_id
    }).encode()
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/marketplace/download-token",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            dl_token = result.get("token", "")
            expires_at = result.get("expires_at", "")
            print(f"✓ 토큰 생성 성공: token_len={len(dl_token)}")
            return dl_token
    except HTTPError as e:
        print(f"✗ 토큰 생성 실패: {e.code}")
        print(f"  {e.read().decode()[:200]}")
        return None

def test_download_apk(token, download_token):
    """APK 다운로드 테스트 (토큰 사용)"""
    print(f"\n=== TEST 5: APK 다운로드 (인증 토큰 사용) ===")
    
    # 인증 토큰으로 직접 다운로드 (토큰 없이)
    req = urllib.request.Request(
        f"{BASE_URL}/api/marketplace/apk/nadotongryoksa-v1.apk",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            size = len(resp.read())
            print(f"✓ APK 다운로드 성공 (인증토큰): size={size} bytes")
            return True
    except HTTPError as e:
        print(f"✗ APK 다운로드 실패 (인증토큰): {e.code}")
        
    # 다운로드 토큰으로 다운로드
    if download_token:
        print(f"\n=== TEST 5-2: APK 다운로드 (다운로드 토큰 사용) ===")
        req = urllib.request.Request(
            f"{BASE_URL}/api/marketplace/apk/nadotongryoksa-v1.apk?token={download_token}",
            headers={"Authorization": f"Bearer {token}"},
            method="GET"
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                size = len(resp.read())
                print(f"✓ APK 다운로드 성공 (다운로드토큰): size={size} bytes")
                return True
        except HTTPError as e:
            print(f"✗ APK 다운로드 실패 (다운로드토큰): {e.code}")
            print(f"  {e.read().decode()[:200]}")
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("마켓플레이스 구매/결제/다운로드 E2E 테스트")
    print("=" * 60)
    
    # 1. 로그인
    token = test_login()
    if not token:
        sys.exit(1)
    
    # 2. 구매 생성
    purchase_id = test_create_purchase(token)
    if not purchase_id:
        sys.exit(1)
    
    # 3. 결제 초기화
    payment_result = test_initiate_payment(token, purchase_id)
    if not payment_result:
        sys.exit(1)
    
    # 4. 다운로드 토큰 생성 (project_id=1 가정)
    download_token = test_create_download_token(token, 1)
    
    # 5. APK 다운로드
    success = test_download_apk(token, download_token)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 모든 테스트 통과!")
    else:
        print("✗ 일부 테스트 실패")
    print("=" * 60)
