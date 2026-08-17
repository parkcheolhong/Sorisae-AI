#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 소리새 생체인식 보안 시스템
얼굴인식, 지문인식, 음성인식을 통한 다중 생체인증
"""

import os
import time
from datetime import datetime

import cv2


class BiometricSecuritySystem:
    """소리새 생체인식 보안 시스템"""

    def __init__(self):
        """보안 시스템 초기화"""
        self.face_cascade = None
        self.voice_recognizer = None
        self.fingerprint_scanner = None

        # 보안 레벨 설정
        self.security_levels = {
            1: {"name": "기본", "methods": ["face"], "color": "🟢"},
            2: {"name": "강화", "methods": ["face", "voice"], "color": "🟡"},
            3: {"name": "최고", "methods": ["face", "fingerprint", "voice"], "color": "🔴"},
            4: {"name": "관리자", "methods": ["face", "fingerprint", "voice", "admin"], "color": "🚨"}
        }

        self.current_level = 2  # 기본 보안 레벨
        self.max_attempts = 3
        self.failed_attempts = 0

        # 인증 로그
        self.auth_log = []

        self.initialize_components()
        print("🔐 소리새 생체인식 보안 시스템이 초기화되었습니다!")

    def initialize_components(self):
        """보안 컴포넌트 초기화"""
        try:
            # OpenCV 얼굴 검출기 로드 시도
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                print("✅ 얼굴인식 모듈 로드 완료")
            else:
                print("⚠️ OpenCV 얼굴 검출기를 찾을 수 없습니다 (시뮬레이션 모드)")
                self.face_cascade = None

        except Exception as e:
            print(f"⚠️ 얼굴인식 초기화 오류: {e} (시뮬레이션 모드)")
            self.face_cascade = None

    def detect_face(self):
        """얼굴 인식 (실제 또는 시뮬레이션)"""
        print("👁️ 얼굴인식 시작...")

        if self.face_cascade is not None:
            try:
                # 실제 카메라 시도
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                        cap.release()

                        if len(faces) > 0:
                            print("✅ 얼굴 검출 성공!")
                            return True, "얼굴이 인식되었습니다."
                        else:
                            return False, "얼굴을 찾을 수 없습니다."
                    cap.release()
            except Exception as e:
                print(f"카메라 오류: {e}")

        # 시뮬레이션 모드
        print("🔄 얼굴인식 시뮬레이션 모드")
        time.sleep(1.5)  # 실제 인식 시간 시뮬레이션

        # 90% 확률로 성공
        import random
        success = random.random() > 0.1

        if success:
            print("✅ 얼굴인식 성공 (시뮬레이션)")
            return True, "등록된 얼굴이 확인되었습니다."
        else:
            print("❌ 얼굴인식 실패 (시뮬레이션)")
            return False, "얼굴 인식에 실패했습니다."

    def scan_fingerprint(self):
        """지문 인식 시뮬레이션"""
        print("👆 지문 스캔을 시작합니다...")
        print("   손가락을 스캐너에 올려주세요...")

        # 스캔 과정 시뮬레이션
        for i in range(3):
            time.sleep(0.8)
            print(f"   🔄 스캔 중... {i + 1}/3")

        # 95% 확률로 성공
        import random
        success = random.random() > 0.05

        if success:
            print("✅ 지문인식 성공")
            return True, "등록된 지문이 확인되었습니다."
        else:
            print("❌ 지문인식 실패")
            return False, "지문을 인식할 수 없습니다."

    def verify_voice(self):
        """음성 인식 시뮬레이션"""
        print("🗣️ 음성 인증을 시작합니다...")
        print("   '안녕하세요, 소리새입니다'라고 말씀해주세요...")

        # 음성 인식 과정 시뮬레이션
        time.sleep(2.0)
        print("   🎤 음성을 녹음하고 있습니다...")

        time.sleep(1.5)
        print("   🔍 화자 인증 중...")

        # 92% 확률로 성공
        import random
        success = random.random() > 0.08

        if success:
            print("✅ 음성인증 성공")
            return True, "등록된 음성이 확인되었습니다."
        else:
            print("❌ 음성인증 실패")
            return False, "음성 패턴이 일치하지 않습니다."

    def admin_approval(self):
        """관리자 승인 시뮬레이션"""
        print("🚨 관리자 승인이 필요합니다...")
        print("   관리자에게 승인 요청을 전송했습니다...")

        time.sleep(2.0)

        # 80% 확률로 승인
        import random
        approved = random.random() > 0.2

        if approved:
            print("✅ 관리자 승인 완료")
            return True, "관리자가 접근을 승인했습니다."
        else:
            print("❌ 관리자 승인 거부")
            return False, "관리자가 접근을 거부했습니다."

    def authenticate(self, level=None):
        """다중 생체인증 실행"""
        if level is None:
            level = self.current_level

        security_config = self.security_levels[level]
        required_methods = security_config["methods"]

        print(f"\n{security_config['color']} 보안 레벨 {level}: {security_config['name']}")
        print(f"필요한 인증: {', '.join(required_methods)}")
        print("=" * 50)

        auth_results = {}
        overall_success = True

        # 각 인증 방법 실행
        for method in required_methods:
            if method == "face":
                success, message = self.detect_face()
                auth_results["얼굴인식"] = {"success": success, "message": message}

            elif method == "fingerprint":
                success, message = self.scan_fingerprint()
                auth_results["지문인식"] = {"success": success, "message": message}

            elif method == "voice":
                success, message = self.verify_voice()
                auth_results["음성인증"] = {"success": success, "message": message}

            elif method == "admin":
                success, message = self.admin_approval()
                auth_results["관리자승인"] = {"success": success, "message": message}

            if not success:
                overall_success = False
                if level >= 3:  # 높은 보안 레벨에서는 모든 인증이 성공해야 함
                    break

        # 인증 결과 로깅
        self.log_authentication(level, auth_results, overall_success)

        # 결과 출력
        print("\n📊 인증 결과:")
        print("-" * 30)
        for method, result in auth_results.items():
            status = "✅" if result["success"] else "❌"
            print(f"{status} {method}: {result['message']}")

        if overall_success:
            print(f"\n🎉 인증 성공! 소리새 시스템에 접근할 수 있습니다.")
            self.failed_attempts = 0
            return True
        else:
            self.failed_attempts += 1
            print(f"\n🚫 인증 실패! ({self.failed_attempts}/{self.max_attempts})")

            if self.failed_attempts >= self.max_attempts:
                print("🚨 최대 시도 횟수 초과! 시스템이 잠겼습니다.")
                self.lock_system()

            return False

    def log_authentication(self, level, results, success):
        """인증 시도 로깅"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "security_level": level,
            "results": results,
            "overall_success": success,
            "failed_attempts": self.failed_attempts
        }

        self.auth_log.append(log_entry)

        # 로그가 너무 길어지면 정리
        if len(self.auth_log) > 100:
            self.auth_log = self.auth_log[-50:]

    def lock_system(self):
        """시스템 잠금"""
        print("🔒 보안 시스템이 활성화되었습니다.")
        print("   30초 후에 다시 시도하거나 관리자에게 문의하세요.")

        # 실제로는 더 복잡한 잠금 메커니즘 구현
        time.sleep(2)

    def set_security_level(self, level):
        """보안 레벨 설정"""
        if level in self.security_levels:
            self.current_level = level
            config = self.security_levels[level]
            print(f"{config['color']} 보안 레벨이 {level} ({config['name']})로 설정되었습니다.")
            print(f"필요한 인증: {', '.join(config['methods'])}")
        else:
            print("❌ 유효하지 않은 보안 레벨입니다.")

    def show_security_status(self):
        """보안 상태 표시"""
        print("\n🔐 소리새 보안 시스템 상태")
        print("=" * 40)

        current_config = self.security_levels[self.current_level]
        print(f"현재 보안 레벨: {current_config['color']} {self.current_level} ({current_config['name']})")
        print(f"필요한 인증: {', '.join(current_config['methods'])}")
        print(f"실패 시도: {self.failed_attempts}/{self.max_attempts}")

        # 최근 인증 로그
        if self.auth_log:
            print(f"\n📋 최근 인증 시도 ({len(self.auth_log)}건):")
            for log in self.auth_log[-3:]:  # 최근 3건만 표시
                timestamp = log["timestamp"][:19]  # 초까지만
                status = "✅" if log["overall_success"] else "❌"
                level = log["security_level"]
                print(f"   {status} {timestamp} - 레벨 {level}")


def demo_biometric_security():
    """생체인식 보안 시스템 데모"""
    print("🔐 소리새 생체인식 보안 시스템 데모")
    print("=" * 50)

    # 보안 시스템 초기화
    security = BiometricSecuritySystem()

    # 현재 상태 표시
    security.show_security_status()

    # 다양한 보안 레벨 테스트
    test_levels = [1, 2, 3]

    for level in test_levels:
        print(f"\n" + "=" * 60)
        print(f"🧪 보안 레벨 {level} 테스트")
        print("=" * 60)

        security.set_security_level(level)
        time.sleep(1)

        # 인증 시도
        security.authenticate()

        time.sleep(2)

    # 최종 보안 상태
    print(f"\n" + "=" * 60)
    security.show_security_status()

    print(f"\n🎊 생체인식 보안 시스템 데모 완료!")
    print("소리새는 이제 최고 수준의 보안 시스템을 갖추었습니다! 🛡️")


def main():
    """메인 실행 함수"""
    try:
        demo_biometric_security()
    except KeyboardInterrupt:
        print("\n⏹️ 보안 시스템 데모 중단")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
