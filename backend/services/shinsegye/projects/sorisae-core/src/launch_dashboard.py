#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 쇼핑몰 시각화 대시보드 실행기
HTML 대시보드를 자동으로 브라우저에서 열어줍니다
"""

import os
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler


def start_web_server():
    """간단한 웹 서버 시작"""
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print("🌐 웹 서버가 포트 8080에서 시작되었습니다...")
    httpd.serve_forever()


def main():
    """메인 실행 함수"""
    print("🛒 쇼핑몰 시각화 대시보드 시작!")
    print("=" * 50)

    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    html_file = os.path.join(current_dir, "shopping_mall_visual.html")

    if not os.path.exists(html_file):
        print("❌ shopping_mall_visual.html 파일을 찾을 수 없습니다.")
        return

    print("✅ 대시보드 파일 확인 완료")

    # 백그라운드에서 웹 서버 시작
    server_thread = threading.Thread(target=start_web_server, daemon=True)
    server_thread.start()

    # 잠시 대기 후 브라우저 열기
    print("⏳ 웹 서버 준비 중...")
    time.sleep(2)

    dashboard_url = "http://localhost:8080/shopping_mall_visual.html"

    print("🚀 브라우저에서 대시보드를 여는 중...")
    print(f"🔗 URL: {dashboard_url}")

    try:
        webbrowser.open(dashboard_url)
        print("✅ 브라우저에서 대시보드가 열렸습니다!")
    except Exception as e:
        print(f"❌ 브라우저 실행 실패: {e}")
        print(f"수동으로 다음 URL을 브라우저에서 열어주세요: {dashboard_url}")

    print("\n" + "=" * 50)
    print("📊 대시보드 기능:")
    print("• 🛒 실시간 자율 쇼핑몰 현황")
    print("• 🎯 마케팅 캠페인 상태")
    print("• 🤖 멀티 AI 에이전트 협업")
    print("• 📈 수익 및 성과 분석")
    print("• 🎁 AI 생성 상품 쇼케이스")
    print("=" * 50)

    print("\n💡 대시보드에서 버튼을 클릭하여 AI 시스템을 테스트해보세요!")
    print("🔄 데이터는 3초마다 자동으로 업데이트됩니다.")

    # 서버 계속 실행
    try:
        print("\n⏹️  서버를 중지하려면 Ctrl+C를 누르세요...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 대시보드 서버가 종료되었습니다.")


if __name__ == "__main__":
    main()
