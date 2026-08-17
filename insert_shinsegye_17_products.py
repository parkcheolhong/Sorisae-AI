#!/usr/bin/env python3
"""
신세계 17개 프로젝트 DB INSERT 스크립트
(sorisae-interpreter 는 id=10 으로 이미 등록됨 — 제외)

실행: python3 insert_shinsegye_17_products.py
"""
import sqlite3
from datetime import datetime

DB_PATH = "app.db"

PRODUCTS = [
    # key, title, description, price, category_id, file_key
    (
        "voice-processing",
        "소리새 음성 처리 시스템 – AI 자연어 음성 제어",
        "자연어 처리 기반 음성 명령 처리 시스템. 다중 음성 프로파일과 컨텍스트 인식 명령 처리를 지원합니다.",
        39000.0, 3, "voice-processing-v1.zip",
    ),
    (
        "music-composer",
        "AI 음악 작곡가 & 가사 스튜디오",
        "AI가 멜로디, 화음, 리듬을 자동 생성하고 분위기별 가사까지 작성하는 음악 창작 스튜디오입니다.",
        59000.0, 6, "music-composer-v1.zip",
    ),
    (
        "animation-studio",
        "소리새 애니메이션 스튜디오 Ultra",
        "씬·캐릭터·애니메이션 프로젝트를 AI가 자동 생성하는 차세대 애니메이션 제작 시스템.",
        79000.0, 6, "animation-studio-v1.zip",
    ),
    (
        "cyber-detective",
        "사이버 탐정 AI 대시보드",
        "네트워크 위협 탐지, 사이버 수사 시뮬레이션, 글로벌 서버 분석을 실시간으로 수행하는 AI 사이버 탐정 시스템.",
        69000.0, 3, "cyber-detective-v1.zip",
    ),
    (
        "iot-smarthome",
        "소리새 IoT 스마트홈 제어 시스템",
        "음성 명령과 AI로 스마트홈 기기를 통합 제어하는 IoT 플랫폼. 자동화 규칙과 센서 데이터 실시간 모니터링을 지원합니다.",
        49000.0, 3, "iot-smarthome-v1.zip",
    ),
    (
        "security",
        "하이브리드 사이버 보안 시스템",
        "보안 위협 탐지, 정책 관리, 생체인식 보안을 통합한 AI 사이버 보안 플랫폼.",
        89000.0, 3, "security-v1.zip",
    ),
    (
        "vr-games",
        "소리새 판타지 VR 무한우주 게임",
        "AI가 무한히 생성하는 VR 우주를 탐험하는 판타지 게임. 현실 조작과 신성 대화 시스템을 포함합니다.",
        99000.0, 5, "vr-games-v1.zip",
    ),
    (
        "game-economy",
        "소리새 게임 경제 시스템",
        "AI 파트너와 함께 게임 내 경제를 운영하고 수익을 분석하는 게임 경제 엔진.",
        59000.0, 5, "game-economy-v1.zip",
    ),
    (
        "investment-advisor",
        "AI 투자 자문 시스템 200% (지능형 시장 분석)",
        "200% 수익률 목표 AI 투자 자문 시스템. 주식 예측, 시장 분석, 지능형 투자 결정 지원.",
        119000.0, 4, "investment-advisor-v1.zip",
    ),
    (
        "satellite",
        "소리새 위성 WiFi 시스템",
        "위성 통신 기반 WiFi 연결 관리 시스템. 연결 상태 모니터링, 자동 전환, 위성 정보 조회를 지원합니다.",
        69000.0, 3, "satellite-v1.zip",
    ),
    (
        "movie-studio",
        "소리새 영화 웹 서버 & 제작 스튜디오",
        "AI 기반 영화 콘텐츠 생성, 스트리밍, 관리를 위한 영화 웹 서버 플랫폼.",
        89000.0, 6, "movie-studio-v1.zip",
    ),
    (
        "gps-police",
        "윤리적 GPS 시스템 – 공공안전 AI",
        "윤리적 기준을 준수하는 GPS 기반 공공안전 모니터링 시스템. 실시간 위치 추적과 이상 탐지를 지원합니다.",
        79000.0, 3, "gps-police-v1.zip",
    ),
    (
        "shopping-mall",
        "소리새 쇼핑몰 대시보드 – 지능형 e커머스 운영",
        "AI 기반 쇼핑몰 운영 대시보드. 상품 관리, 주문 처리, 고객 분석, 매출 예측을 통합 제공합니다.",
        99000.0, 1, "shopping-mall-v1.zip",
    ),
    (
        "sorisae-core",
        "소리새 코어 – AI 의식 엔진 & 통합 제어 시스템",
        "소리새 AI의 핵심 의식 엔진. 자기인식, 감정 처리, 윤리적 의사결정, 통합 시스템 제어를 담당합니다.",
        149000.0, 3, "sorisae-core-v1.zip",
    ),
    (
        "civil-bidding",
        "소리새 건설 입찰 시스템 – AI 자동 입찰",
        "AI 기반 건설 공사 입찰 자동화 시스템. 입찰 분석, 견적 계산, 경쟁사 분석을 자동으로 처리합니다.",
        129000.0, 4, "civil-bidding-v1.zip",
    ),
    (
        "dev-tools",
        "가상 AI 개발팀 시스템 – 자동 코드 생성",
        "가상 AI 개발팀이 협업하여 코드를 자동 생성하고 리뷰하는 개발 도구 플랫폼.",
        89000.0, 1, "dev-tools-v1.zip",
    ),
    (
        "testing",
        "종합 프로젝트 분석기 – AI 코드 품질 검사",
        "AI가 전체 프로젝트를 분석하고 코드 품질, 성능, 보안 취약점을 자동으로 검사·보고합니다.",
        59000.0, 4, "testing-v1.zip",
    ),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # 이미 등록된 file_key 목록 확인
    cur.execute("SELECT file_key FROM projects WHERE file_key IS NOT NULL")
    existing_keys = {row[0] for row in cur.fetchall()}
    print(f"기존 등록된 file_key: {existing_keys}")

    inserted = 0
    skipped = 0
    for file_key, title, description, price, category_id, fk in [
        (p[0], p[1], p[2], p[3], p[4], p[5]) for p in PRODUCTS
    ]:
        if fk in existing_keys:
            print(f"  SKIP (이미 존재): {title}")
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO projects
              (title, description, price, category_id, author_id,
               image_url, demo_url, github_url, file_key,
               downloads, rating, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title, description, price, category_id,
                1,  # author_id = ops-admin
                None,
                f"/api/marketplace/shinsegye/products/{file_key.replace('-v1.zip','')}/demo",
                None,
                fk,
                0, 5.0, 1, now, now,
            ),
        )
        print(f"  INSERT: {title} (file_key={fk})")
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\n완료 — 신규 삽입: {inserted}, 스킵: {skipped}")


if __name__ == "__main__":
    main()
