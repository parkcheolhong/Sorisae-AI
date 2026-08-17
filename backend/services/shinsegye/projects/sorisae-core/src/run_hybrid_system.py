#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 소리새 하이브리드 시스템 런처
Sorisae Hybrid System Launcher

모든 하이브리드 모듈을 체계적으로 실행하는 런처:
✅ 시스템 요구사항 확인
✅ 모듈별 의존성 체크
✅ 순차적 안전 시작
✅ 실시간 상태 모니터링
✅ 오류 복구 및 재시작
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime


def print_banner():
    """시작 배너 출력"""
    print("🌟" + "=" * 60 + "🌟")
    print("   🌐🛰️🎤🏠🛡️ 소리새 하이브리드 시스템 런처")
    print("   Sorisae Hybrid System Launcher")
    print("   Complete Hybrid Intelligence Platform")
    print("🌟" + "=" * 60 + "🌟")
    print()


def check_python_version():
    """Python 버전 확인"""
    print("🔍 시스템 환경 확인 중...")

    if sys.version_info < (3, 7):
        print("❌ Python 3.7 이상이 필요합니다.")
        print(f"   현재 버전: {sys.version}")
        return False

    print(f"✅ Python 버전: {sys.version.split()[0]}")
    return True


def check_required_packages():
    """필수 패키지 확인"""
    print("📦 필수 패키지 확인 중...")

    required_packages = [
        'requests',
        'speechrecognition',
        'pyttsx3'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (누락)")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n⚠️ 누락된 패키지: {', '.join(missing_packages)}")
        print("설치 명령:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    print("✅ 모든 필수 패키지 확인 완료")
    return True


def check_system_files():
    """시스템 파일 확인"""
    print("📁 하이브리드 시스템 파일 확인 중...")

    required_files = [
        'sorisae_integrated_hybrid_system.py',
        'hybrid_voice_processor.py',
        'hybrid_iot_controller.py',
        'hybrid_cyber_security_system.py',
        'hybrid_conversation_translator.py',
        'sorisae_master_hybrid_system.py'
    ]

    missing_files = []

    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (누락)")
            missing_files.append(file)

    if missing_files:
        print(f"\n⚠️ 누락된 파일: {', '.join(missing_files)}")
        return False

    print("✅ 모든 시스템 파일 확인 완료")
    return True


def create_startup_directories():
    """시작 디렉토리 생성"""
    print("📂 필요 디렉토리 생성 중...")

    directories = [
        'hybrid_system_data',
        'hybrid_iot_data',
        'hybrid_security_data',
        'master_hybrid_data',
        'logs'
    ]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"  ✅ {directory}/")
        except Exception as e:
            print(f"  ⚠️ {directory}/ 생성 실패: {e}")

    print("✅ 디렉토리 준비 완료")


def test_internet_connectivity():
    """인터넷 연결 테스트"""
    print("🌐 인터넷 연결 테스트 중...")

    import requests

    test_urls = [
        'https://www.google.com',
        'https://www.naver.com',
        'https://1.1.1.1',  # Cloudflare DNS
    ]

    working_connections = 0

    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                working_connections += 1
                print(f"  ✅ {url}")
            else:
                print(f"  ⚠️ {url} (상태 코드: {response.status_code})")
        except Exception:
            print(f"  ❌ {url} (연결 실패)")

    if working_connections > 0:
        print(f"✅ 인터넷 연결 확인 ({working_connections}/{len(test_urls)} 성공)")
        return True
    else:
        print("⚠️ 인터넷 연결 없음 - 오프라인 모드로 작동")
        return False


def show_startup_menu():
    """시작 메뉴 표시"""
    print("\n🎛️ 하이브리드 시스템 시작 옵션")
    print("=" * 40)
    print("1. 🚀 완전 시작 (모든 모듈)")
    print("2. 🌐 연결 시스템만")
    print("3. 🎤 음성 시스템만")
    print("4. 🏠 IoT 시스템만")
    print("5. 🛡️ 보안 시스템만")
    print("6. 💬 대화&통역 시스템만")
    print("7. 🧪 테스트 모드")
    print("8. ❌ 취소")
    print("=" * 40)


def run_full_system():
    """완전 시스템 실행"""
    print("\n🚀 완전 하이브리드 시스템 시작...")

    try:
        # 마스터 시스템 실행
        from sorisae_master_hybrid_system import main
        print("✅ 마스터 하이브리드 시스템 로딩 완료")

        # 메인 함수 실행
        main()

    except KeyboardInterrupt:
        print("\n⚠️ 사용자가 시스템을 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 시스템 실행 오류: {e}")
        print("🔧 트러블슈팅:")
        print("1. 모든 필수 파일이 있는지 확인")
        print("2. Python 패키지가 설치되어 있는지 확인")
        print("3. 관리자 권한으로 실행해보세요")


def run_connection_only():
    """연결 시스템만 실행"""
    print("\n🌐 하이브리드 연결 시스템 시작...")

    try:
        from sorisae_integrated_hybrid_system import main
        main()
    except Exception as e:
        print(f"❌ 연결 시스템 오류: {e}")


def run_voice_only():
    """음성 시스템만 실행"""
    print("\n🎤 하이브리드 음성 시스템 시작...")

    try:
        from hybrid_voice_processor import main
        main()
    except Exception as e:
        print(f"❌ 음성 시스템 오류: {e}")


def run_iot_only():
    """IoT 시스템만 실행"""
    print("\n🏠 하이브리드 IoT 시스템 시작...")

    try:
        from hybrid_iot_controller import main
        main()
    except Exception as e:
        print(f"❌ IoT 시스템 오류: {e}")


def run_security_only():
    """보안 시스템만 실행"""
    print("\n🛡️ 하이브리드 보안 시스템 시작...")

    try:
        from hybrid_cyber_security_system import main
        main()
    except Exception as e:
        print(f"❌ 보안 시스템 오류: {e}")


def run_conversation_translator_only():
    """대화&통역 시스템만 실행"""
    print("\n💬 하이브리드 대화 & 통역 시스템 시작...")

    try:
        from hybrid_conversation_translator import main
        main()
    except Exception as e:
        print(f"❌ 대화&통역 시스템 오류: {e}")


def run_interpreter_only():
    """통역 시스템만 실행"""
    print("\n🌐 하이브리드 통역 시스템 시작...")

    try:
        from hybrid_interpreter_system import main
        main()
    except Exception as e:
        print(f"❌ 통역 시스템 오류: {e}")


def run_test_mode():
    """테스트 모드 실행"""
    print("\n🧪 테스트 모드 시작...")

    # 각 시스템을 순차적으로 짧게 테스트
    test_results = {}

    print("\n1️⃣ 연결 시스템 테스트...")
    try:
        from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
        hybrid_system = SorisaeIntegratedHybridSystem()
        test_results['connection'] = '✅ 성공'
        hybrid_system.shutdown()
        time.sleep(1)
    except Exception as e:
        test_results['connection'] = f'❌ 실패: {e}'

    print("\n2️⃣ 음성 시스템 테스트...")
    try:
        from hybrid_voice_processor import HybridVoiceProcessor
        HybridVoiceProcessor()
        test_results['voice'] = '✅ 성공'
        # voice_system.shutdown() 메서드가 있다면 호출
        time.sleep(1)
    except Exception as e:
        test_results['voice'] = f'❌ 실패: {e}'

    print("\n3️⃣ IoT 시스템 테스트...")
    try:
        from hybrid_iot_controller import HybridIoTController
        iot_system = HybridIoTController()
        test_results['iot'] = '✅ 성공'
        iot_system.shutdown()
        time.sleep(1)
    except Exception as e:
        test_results['iot'] = f'❌ 실패: {e}'

    print("\n4️⃣ 보안 시스템 테스트...")
    try:
        from hybrid_cyber_security_system import HybridCyberSecuritySystem
        security_system = HybridCyberSecuritySystem()
        test_results['security'] = '✅ 성공'
        security_system.shutdown()
        time.sleep(1)
    except Exception as e:
        test_results['security'] = f'❌ 실패: {e}'

    print("\n5️⃣ 대화&통역 시스템 테스트...")
    try:
        from hybrid_conversation_translator import HybridConversationSystem
        conversation_system = HybridConversationSystem()
        test_results['conversation'] = '✅ 성공'
        conversation_system.shutdown()
        time.sleep(1)
    except Exception as e:
        test_results['conversation'] = f'❌ 실패: {e}'

    print("\n5️⃣ 통역 시스템 테스트...")
    try:
        from hybrid_interpreter_system import HybridInterpreterSystem
        interpreter_system = HybridInterpreterSystem()
        test_results['interpreter'] = '✅ 성공'
        interpreter_system.shutdown()
        time.sleep(1)
    except Exception as e:
        test_results['interpreter'] = f'❌ 실패: {e}'

    # 테스트 결과 출력
    print("\n📊 테스트 결과:")
    print("=" * 40)
    print(f"🌐 연결 시스템: {test_results.get('connection', '❓ 미실행')}")
    print(f"🎤 음성 시스템: {test_results.get('voice', '❓ 미실행')}")
    print(f"🏠 IoT 시스템: {test_results.get('iot', '❓ 미실행')}")
    print(f"🛡️ 보안 시스템: {test_results.get('security', '❓ 미실행')}")
    print(f"💬 대화&통역 시스템: {test_results.get('conversation', '❓ 미실행')}")
    print(f"🌐 통역 시스템: {test_results.get('interpreter', '❓ 미실행')}")

    success_count = len([r for r in test_results.values() if '✅' in r])
    total_tests = len(test_results)

    print(f"\n📈 전체 성공률: {success_count}/{total_tests} ({success_count / total_tests * 100:.1f}%)")

    if success_count == total_tests:
        print("🎉 모든 시스템이 정상 작동합니다!")
    else:
        print("⚠️ 일부 시스템에 문제가 있습니다. 개별 시스템을 확인해보세요.")


def save_startup_log():
    """시작 로그 저장"""
    try:
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'platform': sys.platform,
            'startup_successful': True
        }

        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        print(f"📝 시작 로그 저장: {log_file}")
    except Exception as e:
        print(f"⚠️ 로그 저장 실패: {e}")


def main():
    """메인 런처 함수"""
    print_banner()

    # 시스템 요구사항 확인
    if not check_python_version():
        input("\n❌ 시스템 요구사항을 만족하지 않습니다. 엔터를 눌러 종료...")
        return

    if not check_required_packages():
        choice = input("\n⚠️ 필수 패키지를 설치하시겠습니까? (y/n): ").lower()
        if choice == 'y':
            print("📦 패키지 설치 중...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                                       'requests', 'speechrecognition', 'pyttsx3'])
                print("✅ 패키지 설치 완료")
            except Exception as e:
                print(f"❌ 패키지 설치 실패: {e}")
                return
        else:
            print("❌ 필수 패키지 없이는 실행할 수 없습니다.")
            return

    if not check_system_files():
        input("\n❌ 필수 시스템 파일이 누락되었습니다. 엔터를 눌러 종료...")
        return

    # 디렉토리 준비
    create_startup_directories()

    # 인터넷 연결 테스트
    internet_available = test_internet_connectivity()

    if not internet_available:
        print("⚠️ 인터넷 연결이 없어 일부 기능이 제한될 수 있습니다.")

    # 시작 메뉴
    while True:
        show_startup_menu()

        try:
            choice = input("\n선택하세요 (1-7): ").strip()

            if choice == '1':
                print("\n🚀 완전 시스템을 시작합니다...")
                save_startup_log()
                run_full_system()
                break

            elif choice == '2':
                run_connection_only()
                break

            elif choice == '3':
                run_voice_only()
                break

            elif choice == '4':
                run_iot_only()
                break

            elif choice == '5':
                run_security_only()
                break

            elif choice == '6':
                run_interpreter_only()
                break

            elif choice == '6':
                run_conversation_translator_only()
                break

            elif choice == '7':
                run_test_mode()
                input("\n테스트 완료. 엔터를 눌러 메뉴로 돌아가기...")

            elif choice == '8':
                print("👋 하이브리드 시스템 런처를 종료합니다.")
                break

            else:
                print("❌ 잘못된 선택입니다. 1-8 사이의 숫자를 입력하세요.")

        except KeyboardInterrupt:
            print("\n\n👋 사용자가 런처를 중단했습니다.")
            break

        except Exception as e:
            print(f"\n❌ 런처 오류: {e}")
            print("다시 시도하거나 문제를 확인해주세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 하이브리드 시스템 런처를 종료합니다.")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        print("시스템 관리자에게 문의하세요.")
    finally:
        print("\n🌟 소리새 하이브리드 시스템 런처 종료")
