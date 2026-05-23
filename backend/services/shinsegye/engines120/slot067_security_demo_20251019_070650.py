#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔒 소리새 AI 보안 시스템 최적화 데모
빠른 보안 테스트와 API 키 관리
"""

import json
import secrets
import string
from datetime import datetime
import hashlib

class OptimizedSecurityDemo:
    def __init__(self):
        self.api_keys = {}
        self.permissions = {}
        self.session_tokens = {}
        
    def generate_secure_key(self, key_type="user", length=32):
        """최적화된 보안 키 생성"""
        # 암호학적으로 안전한 랜덤 생성
        random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # 해시 기반 체크섬 추가
        raw_key = f"sorisae_{key_type}_{timestamp}_{random_part}"
        checksum = hashlib.sha256(raw_key.encode()).hexdigest()[:8]
        
        return f"{raw_key}_{checksum}"
    
    def setup_optimized_security(self):
        """최적화된 보안 설정"""
        print("🚀 최적화된 보안 시스템 초기화...")
        
        # 강화된 API 키 생성
        self.api_keys = {
            "master": self.generate_secure_key("master", 40),
            "admin": self.generate_secure_key("admin", 32),
            "user": self.generate_secure_key("user", 24),
            "guest": self.generate_secure_key("guest", 16)
        }
        
        # 세분화된 권한 시스템
        self.permissions = {
            "master": ["all", "system", "security", "admin"],
            "admin": ["dashboard", "commands", "config", "logs", "users"],
            "user": ["dashboard", "commands", "basic"],
            "guest": ["dashboard", "readonly"]
        }
        
        # 세션 토큰 생성
        for role in self.api_keys.keys():
            token = secrets.token_urlsafe(32)
            self.session_tokens[f"{role}_session"] = token
    
    def validate_key(self, api_key):
        """최적화된 키 검증"""
        if not api_key or len(api_key) < 20:
            return False, "키 형식 오류"
        
        try:
            parts = api_key.split('_')
            if len(parts) < 5:
                return False, "키 구조 오류"
            
            key_without_checksum = '_'.join(parts[:-1])
            expected_checksum = hashlib.sha256(key_without_checksum.encode()).hexdigest()[:8]
            actual_checksum = parts[-1]
            
            if expected_checksum != actual_checksum:
                return False, "체크섬 불일치"
        except:
            return False, "키 검증 오류"
        
        for role, key in self.api_keys.items():
            if api_key == key:
                return True, f"유효한 {role} 키"
        
        return False, "등록되지 않은 키"
    
    def run_quick_test(self):
        """빠른 보안 테스트"""
        print("\n🧪 빠른 보안 테스트:")
        print("-" * 40)
        
        user_key = self.api_keys["user"]
        is_valid, message = self.validate_key(user_key)
        print(f"✅ 사용자 키 검증: {message}" if is_valid else f"❌ 실패: {message}")
        
        fake_key = "invalid_key_123"
        is_valid, message = self.validate_key(fake_key)
        print(f"✅ 잘못된 키 거부: {message}" if not is_valid else f"❌ 보안 취약: {message}")
        
        admin_perms = self.permissions["admin"]
        print(f"✅ 관리자 권한: {admin_perms}")
        
        return True

def main():
    """빠른 보안 데모 실행"""
    print("🔒 소리새 AI 최적화 보안 데모")
    print("=" * 45)
    
    demo = OptimizedSecurityDemo()
    demo.setup_optimized_security()
    demo.run_quick_test()
    
    print(f"\n🔑 생성된 API 키:")
    for role, key in demo.api_keys.items():
        perms = demo.permissions[role]
        print(f"   {role.upper()}: {key[:25]}...{key[-8:]}")
        print(f"   └─ 권한: {', '.join(perms)}")
    
    user_key = demo.api_keys['user']
    print(f"\n📋 사용 예제:")
    print(f"   대시보드: http://localhost:5000?api_key={user_key}")
    
    return demo

if __name__ == "__main__":
    demo = main()
    print("\n✅ 보안 시스템 데모 완료!")
    print("\n📚 더 자세한 사용법은 SECURITY_GUIDE.md를 참고하세요.")