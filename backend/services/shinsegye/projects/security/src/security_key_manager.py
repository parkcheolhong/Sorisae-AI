#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔑 소리새 AI 보안 키 관리 도구
API 키와 액세스 토큰을 생성, 관리, 검증하는 도구
"""

import argparse
import json
import secrets
import string
from datetime import datetime


class SecurityKeyManager:
    def __init__(self, config_path="config/security_config.json"):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        """보안 설정 로드"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print("❌ 보안 설정 파일이 없습니다.")
            self.config = {"security": {"api_keys": {}, "access_tokens": {}, "permissions": {}}}

    def save_config(self):
        """보안 설정 저장"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"✅ 설정이 {self.config_path}에 저장되었습니다.")

    def generate_api_key(self, key_type="user"):
        """API 키 생성"""
        # 32자리 랜덤 키 생성
        random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        timestamp = datetime.now().strftime("%Y%m")
        api_key = f"sorisae_{key_type}_{timestamp}_key_{random_part}"
        return api_key

    def generate_token(self, token_type="user"):
        """액세스 토큰 생성"""
        # JWT 스타일 토큰 생성
        prefix_map = {
            "admin": "ADM",
            "user": "USR",
            "readonly": "RO"
        }
        prefix = prefix_map.get(token_type, "USR")
        random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
        timestamp = datetime.now().strftime("%Y")
        token = f"{prefix}_tok_{timestamp}_{random_part}"
        return token

    def add_api_key(self, key_name, key_type="user", permissions=None):
        """새 API 키 추가"""
        if permissions is None:
            permission_defaults = {
                "master": ["all"],
                "admin": ["dashboard", "commands", "config", "logs"],
                "user": ["dashboard", "commands"],
                "guest": ["dashboard"]
            }
            permissions = permission_defaults.get(key_type, ["dashboard"])

        api_key = self.generate_api_key(key_type)

        self.config["security"]["api_keys"][f"{key_name}_key"] = api_key
        self.config["security"]["permissions"][f"{key_name}_key"] = permissions

        print(f"🔑 새 API 키 생성:")
        print(f"   이름: {key_name}_key")
        print(f"   키: {api_key}")
        print(f"   권한: {permissions}")

        return api_key

    def add_token(self, token_name, token_type="user", permissions=None):
        """새 액세스 토큰 추가"""
        if permissions is None:
            permission_defaults = {
                "admin": ["dashboard", "commands", "logs"],
                "user": ["dashboard", "commands"],
                "readonly": ["dashboard"]
            }
            permissions = permission_defaults.get(token_type, ["dashboard"])

        token = self.generate_token(token_type)

        self.config["security"]["access_tokens"][f"{token_name}_token"] = token
        self.config["security"]["permissions"][f"{token_name}_token"] = permissions

        print(f"🎫 새 액세스 토큰 생성:")
        print(f"   이름: {token_name}_token")
        print(f"   토큰: {token}")
        print(f"   권한: {permissions}")

        return token

    def revoke_key(self, key_name):
        """API 키 또는 토큰 폐기"""
        removed = False

        # API 키에서 제거
        if key_name in self.config["security"]["api_keys"]:
            del self.config["security"]["api_keys"][key_name]
            removed = True

        # 토큰에서 제거
        if key_name in self.config["security"]["access_tokens"]:
            del self.config["security"]["access_tokens"][key_name]
            removed = True

        # 권한에서 제거
        if key_name in self.config["security"]["permissions"]:
            del self.config["security"]["permissions"][key_name]

        if removed:
            print(f"🗑️ {key_name} 폐기 완료")
        else:
            print(f"❌ {key_name}을 찾을 수 없습니다")

    def list_credentials(self):
        """모든 인증 정보 목록"""
        print("🔐 현재 등록된 인증 정보:")
        print("\n📋 API 키:")
        for key_name, key_value in self.config["security"]["api_keys"].items():
            permissions = self.config["security"]["permissions"].get(key_name, [])
            print(f"   • {key_name}: {key_value[:20]}... (권한: {permissions})")

        print("\n🎫 액세스 토큰:")
        for token_name, token_value in self.config["security"]["access_tokens"].items():
            permissions = self.config["security"]["permissions"].get(token_name, [])
            print(f"   • {token_name}: {token_value[:20]}... (권한: {permissions})")

    def verify_credential(self, credential):
        """인증 정보 검증"""
        # API 키 확인
        for key_name, key_value in self.config["security"]["api_keys"].items():
            if credential == key_value:
                permissions = self.config["security"]["permissions"].get(key_name, [])
                print(f"✅ 유효한 API 키: {key_name} (권한: {permissions})")
                return True

        # 토큰 확인
        for token_name, token_value in self.config["security"]["access_tokens"].items():
            if credential == token_value:
                permissions = self.config["security"]["permissions"].get(token_name, [])
                print(f"✅ 유효한 토큰: {token_name} (권한: {permissions})")
                return True

        print("❌ 유효하지 않은 인증 정보")
        return False


def main():
    parser = argparse.ArgumentParser(description="소리새 AI 보안 키 관리 도구")
    parser.add_argument("action", choices=["add-key", "add-token", "revoke", "list", "verify"],
                        help="수행할 작업")
    parser.add_argument("--name", help="키/토큰 이름")
    parser.add_argument("--type", choices=["master", "admin", "user", "guest", "readonly"],
                        default="user", help="키/토큰 유형")
    parser.add_argument("--credential", help="검증할 인증 정보")

    args = parser.parse_args()

    manager = SecurityKeyManager()

    if args.action == "add-key":
        if not args.name:
            print("❌ --name 옵션이 필요합니다")
            return
        manager.add_api_key(args.name, args.type)
        manager.save_config()

    elif args.action == "add-token":
        if not args.name:
            print("❌ --name 옵션이 필요합니다")
            return
        manager.add_token(args.name, args.type)
        manager.save_config()

    elif args.action == "revoke":
        if not args.name:
            print("❌ --name 옵션이 필요합니다")
            return
        manager.revoke_key(args.name)
        manager.save_config()

    elif args.action == "list":
        manager.list_credentials()

    elif args.action == "verify":
        if not args.credential:
            print("❌ --credential 옵션이 필요합니다")
            return
        manager.verify_credential(args.credential)


if __name__ == "__main__":
    print("🔐 소리새 AI 보안 키 관리 도구")
    print("=" * 40)
    main()
