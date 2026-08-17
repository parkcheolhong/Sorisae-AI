#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 소리새 4D 영화 제작 시스템 설치 및 실행 도구
자동으로 필요한 패키지를 설치하고 웹서버를 실행합니다
"""

import os
import platform
import socket
import subprocess
import sys


class SorisaeMovieInstaller:
    """소리새 4D 영화 제작 시스템 설치 관리자"""

    def __init__(self):
        self.system = platform.system()
        self.required_packages = [
            'flask',
            'flask-socketio',
            'qrcode[pil]',
            'pillow',
            'numpy',
            'opencv-python',
            'matplotlib'
        ]

    def check_python_version(self):
        """Python 버전 확인"""
        version = sys.version_info
        print(f"🐍 Python 버전: {version.major}.{version.minor}.{version.micro}")

        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Python 3.8 이상이 필요합니다.")
            return False

        print("✅ Python 버전 적합")
        return True

    def install_packages(self):
        """필요한 패키지 설치"""
        print("\n📦 필요한 패키지 설치 중...")

        for package in self.required_packages:
            try:
                print(f"   설치 중: {package}")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", package
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    print(f"   ✅ {package} 설치 완료")
                else:
                    print(f"   ⚠️ {package} 설치 실패")

            except Exception as e:
                print(f"   ❌ {package} 설치 오류: {e}")

    def check_port_availability(self, port=5050):
        """포트 사용 가능 여부 확인"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except Exception:
            return False

    def get_available_port(self, start_port=5050):
        """사용 가능한 포트 찾기"""
        for port in range(start_port, start_port + 100):
            if self.check_port_availability(port):
                return port
        return None

    def create_launch_script(self):
        """실행 스크립트 생성"""
        if self.system == "Windows":
            script_content = """@echo off
echo 🎬 소리새 4D 영화 제작 시스템 시작!
echo.
python sorisae_movie_web_server.py
pause
"""
            with open("start_movie_studio.bat", "w", encoding="utf-8") as f:
                f.write(script_content)
            print("✅ Windows 실행 스크립트 생성: start_movie_studio.bat")

        else:  # Linux/Mac
            script_content = """#!/bin/bash
echo "🎬 소리새 4D 영화 제작 시스템 시작!"
echo
python3 sorisae_movie_web_server.py
"""
            with open("start_movie_studio.sh", "w") as f:
                f.write(script_content)
            os.chmod("start_movie_studio.sh", 0o755)
            print("✅ Linux/Mac 실행 스크립트 생성: start_movie_studio.sh")

    def create_desktop_shortcut(self):
        """바탕화면 바로가기 생성 (Windows)"""
        if self.system == "Windows":
            try:
                import winshell  # type: ignore
                from win32com.client import Dispatch  # type: ignore

                desktop = winshell.desktop()
                shortcut_path = os.path.join(desktop, "소리새 4D 영화 제작.lnk")

                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = os.path.join(os.getcwd(), "start_movie_studio.bat")
                shortcut.WorkingDirectory = os.getcwd()
                shortcut.IconLocation = os.path.join(os.getcwd(), "start_movie_studio.bat")
                shortcut.save()

                print("✅ 바탕화면 바로가기 생성 완료")
            except ImportError:
                print("⚠️ 바탕화면 바로가기 생성을 위해 pywin32 설치가 필요합니다")
            except Exception as e:
                print(f"⚠️ 바탕화면 바로가기 생성 실패: {e}")

    def get_local_ip(self):
        """로컬 IP 주소 가져오기"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def create_download_info(self):
        """다운로드 및 설치 정보 파일 생성"""
        local_ip = self.get_local_ip()

        info_content = f"""
🎬✨ 소리새 4D 영화 제작 시스템
========================================

📋 시스템 정보:
- 개발: 소리새 (Sorisae)
- 버전: 1.0.0
- 날짜: 2025-10-31
- 플랫폼: {self.system}

🌐 접속 방법:

1. 데스크톱 (PC):
   - http://localhost:5050
   - http://{local_ip}:5050

2. 모바일:
   - http://{local_ip}:5050/mobile
   - QR 코드: http://{local_ip}:5050/qr_code

🚀 실행 방법:

Windows:
  - start_movie_studio.bat 실행

Linux/Mac:
  - ./start_movie_studio.sh 실행

Python 직접 실행:
  - python sorisae_movie_web_server.py

📦 설치된 기능:
✅ 4D 영화 제작 (바람, 물, 진동, 향기, 온도)
✅ AI 자동 시나리오 분석
✅ 1시간 50분 장편 영화 자동 생성
✅ 오리지널 주제곡 및 변주곡 생성
✅ Ultra HD / 4K / 8K / 4D 품질 지원
✅ 웹 브라우저 인터페이스
✅ 모바일 반응형 디자인
✅ 실시간 진행 상황 표시
✅ 영화 다운로드 기능

🎭 사용법:
1. 웹 브라우저에서 위 주소 접속
2. 영화 제목과 시나리오 입력
3. 품질 선택 (4D 권장)
4. '영화 제작 시작' 버튼 클릭
5. 제작 완료 후 다운로드

🌟 특징:
- 시나리오만 입력하면 완전한 4D 영화 자동 제작
- PC와 모바일에서 모두 사용 가능
- 실제 4D 영화관에서 상영 가능한 품질
- 105% 신적 지능 AI 시스템 적용

📱 모바일 사용:
- 모바일 브라우저에서 접속
- QR 코드 스캔으로 간편 접속
- 터치 최적화 인터페이스

💾 파일 저장 위치:
- 완성된 영화: static/movies/
- 프로젝트 정보: projects/
- 4D 효과 데이터: rendered_scenes/

🔧 문제 해결:
- 포트 충돌 시 자동으로 다른 포트 사용
- 패키지 오류 시 requirements.txt 참조
- 브라우저 호환성: Chrome, Firefox, Safari, Edge

📞 지원:
- GitHub: https://github.com/parkcheolhong
- 이메일: support@sorisae.com

========================================
🎊 소리새 4D 영화 제작 시스템으로 꿈의 영화를 만들어보세요!
        """

        with open("소리새_4D영화제작_사용법.txt", "w", encoding="utf-8") as f:
            f.write(info_content)

        print("✅ 사용법 가이드 생성: 소리새_4D영화제작_사용법.txt")

    def create_requirements_file(self):
        """requirements.txt 생성"""
        requirements_content = """# 소리새 4D 영화 제작 시스템 필수 패키지
flask>=2.3.0
flask-socketio>=5.3.0
qrcode[pil]>=7.4.2
pillow>=10.0.0
numpy>=1.24.0
opencv-python>=4.8.0
matplotlib>=3.7.0
python-socketio>=5.8.0
eventlet>=0.33.0
"""

        with open("requirements.txt", "w") as f:
            f.write(requirements_content)

        print("✅ requirements.txt 생성 완료")

    def run_installation(self):
        """전체 설치 프로세스 실행"""
        print("🎬✨ 소리새 4D 영화 제작 시스템 설치 시작!")
        print("=" * 60)

        # Python 버전 확인
        if not self.check_python_version():
            return False

        # 패키지 설치
        self.install_packages()

        # 실행 스크립트 생성
        self.create_launch_script()

        # 바탕화면 바로가기 (Windows만)
        if self.system == "Windows":
            self.create_desktop_shortcut()

        # 사용법 가이드 생성
        self.create_download_info()

        # requirements.txt 생성
        self.create_requirements_file()

        # 사용 가능한 포트 확인
        available_port = self.get_available_port()
        local_ip = self.get_local_ip()

        print("\n🎊 설치 완료!")
        print("=" * 60)
        print("🚀 실행 방법:")

        if self.system == "Windows":
            print("   1. start_movie_studio.bat 더블클릭")
            print("   2. 또는 바탕화면 '소리새 4D 영화 제작' 바로가기 실행")
        else:
            print("   1. ./start_movie_studio.sh 실행")

        print("   3. 또는 python sorisae_movie_web_server.py 실행")

        print(f"\n🌐 접속 주소:")
        print(f"   데스크톱: http://localhost:{available_port or 5050}")
        print(f"   데스크톱: http://{local_ip}:{available_port or 5050}")
        print(f"   모바일: http://{local_ip}:{available_port or 5050}/mobile")

        print(f"\n📱 모바일 접속:")
        print(f"   QR 코드: http://{local_ip}:{available_port or 5050}/qr_code")

        print(f"\n📄 자세한 사용법: 소리새_4D영화제작_사용법.txt 참조")

        return True

    def quick_start(self):
        """빠른 시작"""
        try:
            print("🚀 소리새 4D 영화 제작 시스템 빠른 시작!")

            # 웹서버 실행
            from sorisae_movie_web_server import main
            main()

        except ImportError:
            print("❌ 웹서버 모듈을 찾을 수 없습니다.")
            print("먼저 설치를 진행하세요: python sorisae_movie_installer.py install")
        except Exception as e:
            print(f"❌ 실행 오류: {e}")


def main():
    """메인 실행 함수"""
    installer = SorisaeMovieInstaller()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "install":
            installer.run_installation()
        elif command == "start":
            installer.quick_start()
        else:
            print("사용법:")
            print("  python sorisae_movie_installer.py install  # 설치")
            print("  python sorisae_movie_installer.py start    # 실행")
    else:
        # 기본 동작: 설치 후 실행
        if installer.run_installation():
            input("\n설치가 완료되었습니다. Enter를 눌러 웹서버를 시작하세요...")
            installer.quick_start()


if __name__ == "__main__":
    main()
