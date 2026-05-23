#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Security System v2.0
Environment variables, encryption, key management, security settings integrated management
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from collections.abc import Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# 선택적 임포트
try:
    from cryptography.fernet import Fernet  # type: ignore
    from cryptography.hazmat.primitives import hashes  # type: ignore
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # type: ignore
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography package not available - advanced encryption features limited")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """보안 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityConfig:
    """보안 설정 데이터클래스"""
    encryption_enabled: bool = True
    key_rotation_interval: int = 86400  # 24시간
    max_login_attempts: int = 5
    session_timeout: int = 3600  # 1시간
    require_2fa: bool = False
    audit_logging: bool = True
    security_level: SecurityLevel = SecurityLevel.MEDIUM


class EnvironmentManager:
    """환경 변수 관리자"""

    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.variables: Dict[str, str] = {}
        self.sensitive_vars: Set[str] = {
            'API_KEY', 'SECRET_KEY', 'DATABASE_PASSWORD',
            'JWT_SECRET', 'ENCRYPTION_KEY', 'PRIVATE_KEY'
        }
        self._load_env_file()

    def _load_env_file(self) -> None:
        """환경 파일 로드"""
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            self.variables[key.strip()] = value.strip().strip('"\'')
                logger.info(f"환경 파일 로드 완료: {len(self.variables)}개 변수")
            except Exception as e:
                logger.error(f"환경 파일 로드 오류: {e}")
        else:
            logger.info("환경 파일이 없습니다. 새로 생성합니다.")
            self._create_default_env()

    def _create_default_env(self) -> None:
        """기본 환경 파일 생성"""
        default_vars = {
            'SORISAE_SECRET_KEY': self._generate_secure_key(),
            'SORISAE_API_KEY': self._generate_api_key(),
            'SORISAE_ENVIRONMENT': 'development',
            'SORISAE_DEBUG': 'false',
            'SORISAE_LOG_LEVEL': 'INFO',
            'SORISAE_SESSION_TIMEOUT': '3600',
            'SORISAE_MAX_LOGIN_ATTEMPTS': '5',
            'SORISAE_ENCRYPTION_ENABLED': 'true'
        }

        self.variables.update(default_vars)
        self._save_env_file()

    def _generate_secure_key(self, length: int = 32) -> str:
        """보안 키 생성"""
        return secrets.token_urlsafe(length)

    def _generate_api_key(self) -> str:
        """API 키 생성"""
        return f"sk-{secrets.token_urlsafe(32)}"

    def _save_env_file(self) -> None:
        """환경 파일 저장"""
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# 소리새 보안 환경 설정\n")
                f.write(f"# 생성일: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for key, value in self.variables.items():
                    f.write(f"{key}={value}\n")

            # 파일 권한 설정 (Unix/Linux)
            if os.name != 'nt':
                os.chmod(self.env_file, 0o600)

            logger.info("환경 파일 저장 완료")

        except Exception as e:
            logger.error(f"환경 파일 저장 오류: {e}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """환경 변수 조회"""
        # 시스템 환경 변수 우선
        value = os.getenv(key)
        if value is not None:
            return value

        # .env 파일에서 조회
        return self.variables.get(key, default)

    def set(self, key: str, value: str, save: bool = True) -> None:
        """환경 변수 설정"""
        self.variables[key] = value
        os.environ[key] = value

        if save:
            self._save_env_file()

        # 민감한 변수는 로그에 출력하지 않음
        if any(sensitive in key.upper() for sensitive in self.sensitive_vars):
            logger.info(f"민감한 환경 변수 설정: {key}=***")
        else:
            logger.info(f"환경 변수 설정: {key}={value}")

    def rotate_keys(self) -> None:
        """키 순환"""
        logger.info("보안 키 순환 시작")

        # 새 키 생성
        self.set('SORISAE_SECRET_KEY', self._generate_secure_key(), save=False)
        self.set('SORISAE_API_KEY', self._generate_api_key(), save=False)

        # 순환 시간 기록
        self.set('SORISAE_LAST_KEY_ROTATION', str(int(time.time())), save=False)

        self._save_env_file()
        logger.info("보안 키 순환 완료")


class AdvancedEncryption:
    """고급 암호화 관리자"""

    def __init__(self, password: Optional[str] = None):
        self.password = password or self._get_default_password()
        self.fernet = None

        if CRYPTO_AVAILABLE:
            self._initialize_encryption()
        else:
            logger.warning("암호화 라이브러리 없음 - 기본 인코딩 사용")

    def _get_default_password(self) -> str:
        """기본 암호화 패스워드 조회"""
        env_manager = EnvironmentManager()
        password = env_manager.get('SORISAE_SECRET_KEY')
        if not password:
            password = secrets.token_urlsafe(32)
            env_manager.set('SORISAE_SECRET_KEY', password)
        return password

    def _initialize_encryption(self) -> None:
        """암호화 초기화"""
        try:
            # 패스워드에서 키 파생
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'sorisae_salt_2024',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
            self.fernet = Fernet(key)
            logger.info("고급 암호화 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"암호화 초기화 오류: {e}")
            self.fernet = None

    def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        if not data:
            return ""

        try:
            if self.fernet and CRYPTO_AVAILABLE:
                # 고급 암호화
                encrypted = self.fernet.encrypt(data.encode('utf-8'))
                return base64.urlsafe_b64encode(encrypted).decode('utf-8')
            else:
                # 기본 인코딩
                return base64.b64encode(data.encode('utf-8')).decode('utf-8')

        except Exception as e:
            logger.error(f"암호화 오류: {e}")
            return data

    def decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        if not encrypted_data:
            return ""

        try:
            if self.fernet and CRYPTO_AVAILABLE:
                # 고급 복호화
                decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
                decrypted = self.fernet.decrypt(decoded)
                return decrypted.decode('utf-8')
            else:
                # 기본 디코딩
                return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')

        except Exception as e:
            logger.error(f"복호화 오류: {e}")
            return encrypted_data

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """패스워드 해시"""
        if salt is None:
            salt = secrets.token_hex(16)

        # SHA-256 해시
        hash_obj = hashlib.sha256()
        hash_obj.update((password + salt).encode('utf-8'))
        hashed = hash_obj.hexdigest()

        return hashed, salt

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """패스워드 검증"""
        test_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(test_hash, hashed)


class SecurityConfigManager:
    """보안 설정 관리자"""

    def __init__(self, config_file: str = "config/security_config.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.encryption = AdvancedEncryption()
        self.config = self._load_config()

    def _load_config(self) -> SecurityConfig:
        """보안 설정 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                return SecurityConfig(
                    encryption_enabled=data.get('encryption_enabled', True),
                    key_rotation_interval=data.get('key_rotation_interval', 86400),
                    max_login_attempts=data.get('max_login_attempts', 5),
                    session_timeout=data.get('session_timeout', 3600),
                    require_2fa=data.get('require_2fa', False),
                    audit_logging=data.get('audit_logging', True),
                    security_level=SecurityLevel(data.get('security_level', 'medium'))
                )
            except Exception as e:
                logger.error(f"보안 설정 로드 오류: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self) -> SecurityConfig:
        """기본 보안 설정 생성"""
        config = SecurityConfig()
        self._save_config(config)
        logger.info("기본 보안 설정 생성")
        return config

    def _save_config(self, config: SecurityConfig) -> None:
        """보안 설정 저장"""
        try:
            data = {
                'encryption_enabled': config.encryption_enabled,
                'key_rotation_interval': config.key_rotation_interval,
                'max_login_attempts': config.max_login_attempts,
                'session_timeout': config.session_timeout,
                'require_2fa': config.require_2fa,
                'audit_logging': config.audit_logging,
                'security_level': config.security_level.value,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info("보안 설정 저장 완료")

        except Exception as e:
            logger.error(f"보안 설정 저장 오류: {e}")

    def update_security_level(self, level: SecurityLevel) -> None:
        """보안 수준 업데이트"""
        self.config.security_level = level

        # 보안 수준에 따른 설정 조정
        if level == SecurityLevel.CRITICAL:
            self.config.require_2fa = True
            self.config.session_timeout = 1800  # 30분
            self.config.max_login_attempts = 3
            self.config.key_rotation_interval = 3600  # 1시간
        elif level == SecurityLevel.HIGH:
            self.config.require_2fa = True
            self.config.session_timeout = 3600  # 1시간
            self.config.max_login_attempts = 3
        elif level == SecurityLevel.MEDIUM:
            self.config.session_timeout = 7200  # 2시간
            self.config.max_login_attempts = 5
        else:  # LOW
            self.config.session_timeout = 14400  # 4시간
            self.config.max_login_attempts = 10

        self._save_config(self.config)
        logger.info(f"보안 수준 업데이트: {level.value}")

    def get_config(self) -> SecurityConfig:
        """보안 설정 조회"""
        return self.config


class SecurityAuditor:
    """보안 감사 시스템"""

    def __init__(self, log_file: str = "logs/security_audit.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 보안 감사 로거 설정
        self.audit_logger = logging.getLogger('security_audit')
        self.audit_logger.setLevel(logging.INFO)

        # 파일 핸들러
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - AUDIT - %(message)s')
        )
        self.audit_logger.addHandler(file_handler)

    def log_event(self, event_type: str, user: str, details: Dict[str, Any]) -> None:
        """보안 이벤트 로그"""
        event_data = {
            'timestamp': time.time(),
            'event_type': event_type,
            'user': user,
            'ip_address': details.get('ip', 'unknown'),
            'user_agent': details.get('user_agent', 'unknown'),
            'success': details.get('success', True),
            'details': details
        }

        self.audit_logger.info(json.dumps(event_data, ensure_ascii=False))

    def log_login_attempt(self, user: str, success: bool, ip: str = "unknown") -> None:
        """로그인 시도 로그"""
        self.log_event('LOGIN_ATTEMPT', user, {
            'success': success,
            'ip': ip,
            'timestamp': time.time()
        })

    def log_key_rotation(self, user: str = "system") -> None:
        """키 순환 로그"""
        self.log_event('KEY_ROTATION', user, {
            'success': True,
            'timestamp': time.time()
        })

    def log_config_change(self, user: str, changes: Dict[str, Any]) -> None:
        """설정 변경 로그"""
        self.log_event('CONFIG_CHANGE', user, {
            'success': True,
            'changes': changes,
            'timestamp': time.time()
        })


class IntegratedSecuritySystem:
    """통합 보안 시스템"""

    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.encryption = AdvancedEncryption()
        self.config_manager = SecurityConfigManager()
        self.auditor = SecurityAuditor()

        logger.info("통합 보안 시스템 초기화 완료")

    def initialize_security(self) -> Dict[str, Any]:
        """보안 시스템 초기화"""
        logger.info("보안 시스템 전체 초기화 시작")

        result = {
            'status': 'success',
            'components': {},
            'recommendations': []
        }

        try:
            # 1. 환경 변수 검증
            env_status = self._validate_environment()
            result['components']['environment'] = env_status

            # 2. 암호화 시스템 검증
            crypto_status = self._validate_encryption()
            result['components']['encryption'] = crypto_status

            # 3. 보안 설정 검증
            config_status = self._validate_security_config()
            result['components']['config'] = config_status

            # 4. 감사 시스템 검증
            audit_status = self._validate_audit_system()
            result['components']['audit'] = audit_status

            # 5. 권장사항 생성
            result['recommendations'] = self._generate_security_recommendations()

            # 감사 로그
            self.auditor.log_event('SECURITY_INITIALIZATION', 'system', result)

            logger.info("보안 시스템 초기화 완료")

        except Exception as e:
            logger.error(f"보안 시스템 초기화 오류: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def _validate_environment(self) -> Dict[str, Any]:
        """환경 변수 검증"""
        required_vars = [
            'SORISAE_SECRET_KEY', 'SORISAE_API_KEY', 'SORISAE_ENVIRONMENT'
        ]

        missing_vars = []
        weak_keys = []

        for var in required_vars:
            value = self.env_manager.get(var)
            if not value:
                missing_vars.append(var)
            elif 'KEY' in var and len(value) < 32:
                weak_keys.append(var)

        return {
            'status': 'healthy' if not missing_vars and not weak_keys else 'warning',
            'missing_variables': missing_vars,
            'weak_keys': weak_keys,
            'total_variables': len(self.env_manager.variables)
        }

    def _validate_encryption(self) -> Dict[str, Any]:
        """암호화 시스템 검증"""
        try:
            # 테스트 암호화/복호화
            test_data = "보안 테스트 데이터"
            encrypted = self.encryption.encrypt(test_data)
            decrypted = self.encryption.decrypt(encrypted)

            return {
                'status': 'healthy' if decrypted == test_data else 'error',
                'crypto_available': CRYPTO_AVAILABLE,
                'test_passed': decrypted == test_data
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _validate_security_config(self) -> Dict[str, Any]:
        """보안 설정 검증"""
        config = self.config_manager.get_config()

        issues = []
        if config.session_timeout > 14400:  # 4시간
            issues.append("세션 타임아웃이 너무 깁니다")

        if config.max_login_attempts > 10:
            issues.append("최대 로그인 시도 횟수가 너무 많습니다")

        return {
            'status': 'healthy' if not issues else 'warning',
            'security_level': config.security_level.value,
            'issues': issues,
            'config': {
                'encryption_enabled': config.encryption_enabled,
                'session_timeout': config.session_timeout,
                'max_login_attempts': config.max_login_attempts,
                'require_2fa': config.require_2fa
            }
        }

    def _validate_audit_system(self) -> Dict[str, Any]:
        """감사 시스템 검증"""
        try:
            # 테스트 로그 작성
            self.auditor.log_event('SYSTEM_TEST', 'system', {'test': True})

            return {
                'status': 'healthy',
                'log_file': str(self.auditor.log_file),
                'log_exists': self.auditor.log_file.exists()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def _generate_security_recommendations(self) -> List[str]:
        """보안 권장사항 생성"""
        recommendations = []

        # 암호화 권장사항
        if not CRYPTO_AVAILABLE:
            recommendations.append("고급 암호화를 위해 cryptography 패키지를 설치하세요")

        # 환경 변수 권장사항
        if not self.env_manager.get('SORISAE_SECRET_KEY'):
            recommendations.append("SECRET_KEY 환경 변수를 설정하세요")

        # 보안 수준 권장사항
        config = self.config_manager.get_config()
        if config.security_level == SecurityLevel.LOW:
            recommendations.append("보안 수준을 MEDIUM 이상으로 설정하세요")

        if not config.require_2fa and config.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            recommendations.append("높은 보안 수준에서는 2FA를 활성화하세요")

        return recommendations

    def enhance_security(self) -> Dict[str, Any]:
        """보안 강화 실행"""
        logger.info("보안 강화 작업 시작")

        enhancements = []

        try:
            # 1. 키 순환
            self.env_manager.rotate_keys()
            enhancements.append("보안 키 순환 완료")

            # 2. 보안 수준 업그레이드
            current_level = self.config_manager.get_config().security_level
            if current_level == SecurityLevel.LOW:
                self.config_manager.update_security_level(SecurityLevel.MEDIUM)
                enhancements.append("보안 수준을 MEDIUM으로 업그레이드")
            elif current_level == SecurityLevel.MEDIUM:
                self.config_manager.update_security_level(SecurityLevel.HIGH)
                enhancements.append("보안 수준을 HIGH로 업그레이드")

            # 3. 감사 로그
            self.auditor.log_event('SECURITY_ENHANCEMENT', 'system', {
                'enhancements': enhancements,
                'timestamp': time.time()
            })

            logger.info("보안 강화 완료")

            return {
                'status': 'success',
                'enhancements': enhancements,
                'new_security_level': self.config_manager.get_config().security_level.value
            }

        except Exception as e:
            logger.error(f"보안 강화 오류: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


def main():
    """메인 실행 함수"""
    print("Advanced Security System v2.0")
    print("=" * 50)

    try:
        # 통합 보안 시스템 초기화
        security_system = IntegratedSecuritySystem()

        # 보안 시스템 초기화
        print("🔍 보안 시스템 검증 중...")
        init_result = security_system.initialize_security()

        print(f"✅ 초기화 상태: {init_result['status']}")

        # 컴포넌트 상태 출력
        for component, status in init_result['components'].items():
            status_icon = "[OK]" if status['status'] == 'healthy' else "[WARN]" if status['status'] == 'warning' else "[ERROR]"
            print(f"  {status_icon} {component}: {status['status']}")

        # 권장사항 출력
        if init_result['recommendations']:
            print(f"\n📋 보안 권장사항:")
            for rec in init_result['recommendations']:
                print(f"  • {rec}")

        # 보안 강화 실행
        print(f"\n🔧 보안 강화 실행 중...")
        enhance_result = security_system.enhance_security()

        if enhance_result['status'] == 'success':
            print(f"✅ 보안 강화 완료!")
            print(f"  • 새로운 보안 수준: {enhance_result['new_security_level']}")
            for enhancement in enhance_result['enhancements']:
                print(f"  • {enhancement}")
        else:
            print(f"❌ 보안 강화 실패: {enhance_result.get('error')}")

        # 최종 보안 상태
        config = security_system.config_manager.get_config()
        print(f"\n🛡️ 현재 보안 상태:")
        print(f"  • 보안 수준: {config.security_level.value}")
        print(f"  • 암호화 활성화: {config.encryption_enabled}")
        print(f"  • 2FA 필요: {config.require_2fa}")
        print(f"  • 세션 타임아웃: {config.session_timeout}초")
        print(f"  • 최대 로그인 시도: {config.max_login_attempts}회")
        print(f"  • 감사 로깅: {config.audit_logging}")

        print(f"\n🎉 고급 보안 시스템 구축 완료!")

    except Exception as e:
        logger.error(f"보안 시스템 실행 오류: {e}")
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
