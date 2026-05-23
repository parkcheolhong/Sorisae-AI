#!/usr/bin/env python3
"""
🎤 소리새 통합 대시보드 (Sorisae Integrated Dashboard)
로컬에서 소리새 AI 시스템의 모든 기능을 한눈에 볼 수 있는 통합 웹 대시보드

실행 방법:
    python sorisae_integrated_dashboard.py

웹 브라우저에서 http://localhost:5050 접속
"""

import json
import logging
import os
import random
import sys
import threading
import webbrowser
from datetime import datetime

import urllib.request as _ureq
import urllib.error as _uerr

from flask import Flask, jsonify, render_template_string, request
from flask_socketio import SocketIO, emit

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# modules 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

# 폴백 시스템 import (실패해도 계속 진행)
try:
    from voice_response_fallback import get_fallback_response
    from api_rate_limit_handler import handle_api_error
    FALLBACK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"폴백 시스템을 로드할 수 없습니다: {e}. 기본 응답만 사용합니다.")
    FALLBACK_AVAILABLE = False

app = Flask(__name__)
# SECRET_KEY는 환경 변수에서 가져오거나 기본값 사용 (로컬 개발용)
app.config["SECRET_KEY"] = os.environ.get("SORISAE_SECRET_KEY", os.urandom(24).hex())
# CORS 허용 origin을 환경 변수에서 읽거나 기본값 사용 (보안 강화)
allowed_origins = os.environ.get("SORISAE_DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:5050")
socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode="threading",
    ping_timeout=60,  # 소켓 타임아웃 설정
    ping_interval=25,  # 주기적 연결 확인
    logger=False,  # 로거 비활성화 (WinError 10038 관련 로그 감소)
    engineio_logger=False  # 엔진IO 로거 비활성화
)


# === 시스템 상태 관리 ===
class SorisaeSystemState:
    """소리새 통합 시스템 상태 관리"""

    def __init__(self):
        self.voice_commands = []
        self.system_status = "대기 중"
        self.active_modules = []
        self.last_command = None
        self.command_count = 0
        self.is_listening = False
        self.error_count = 0
        self.current_persona = "friendly"
        self.ai_collaborations = 0
        self.memory_count = 0
        self.generated_plugins = 0

        # 쇼핑몰 데이터
        self.mall_stats = {
            "total_revenue": 2847650,
            "total_sales": 127,
            "active_products": 45,
            "customer_satisfaction": 94.2,
            "market_position": "상위 5%",
        }

        # 듀얼브레인 데이터
        self.dual_brain_stats = {
            "brain_a_status": "활성",
            "brain_b_status": "진화 중",
            "prediction_accuracy": 92.5,
            "evolution_cycle": 42,
            "analyzed_stocks": 15,
        }

        # IoT 데이터
        self.iot_stats = {
            "connected_devices": 12,
            "active_automations": 8,
            "energy_saved": 23.5,
            "temperature": 24.0,
            "humidity": 45,
        }

        # 창작 경제 데이터
        self.creative_stats = {
            "contents_created": 23,
            "monthly_revenue": 225,
            "ai_contributions": 45,
            "quality_score": 8.5,
        }

    def add_voice_command(self, command, status="성공", module_name=None):
        """음성 명령 추가"""
        command_data = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "command": command,
            "status": status,
            "module": module_name or "시스템",
        }
        self.voice_commands.append(command_data)
        self.last_command = command
        self.command_count += 1

        if status == "실패":
            self.error_count += 1

        if len(self.voice_commands) > 50:
            self.voice_commands.pop(0)

        return command_data

    def get_all_stats(self):
        """모든 통계 반환"""
        return {
            "system": {
                "total_commands": self.command_count,
                "recent_commands": len(self.voice_commands),
                "last_command": self.last_command,
                "system_status": self.system_status,
                "is_listening": self.is_listening,
                "error_count": self.error_count,
                "success_rate": ((self.command_count - self.error_count) / max(1, self.command_count)) * 100,
                "current_persona": self.current_persona,
                "ai_collaborations": self.ai_collaborations,
            },
            "mall": self.mall_stats,
            "dual_brain": self.dual_brain_stats,
            "iot": self.iot_stats,
            "creative": self.creative_stats,
            "active_modules": self.active_modules,
        }


state = SorisaeSystemState()

# === HTML 템플릿 ===
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 소리새 통합 대시보드</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #eee;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .live-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(76, 175, 80, 0.9);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            animation: pulse 2s infinite;
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .live-dot {
            width: 10px;
            height: 10px;
            background: #fff;
            border-radius: 50%;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.3; }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }

        .header {
            text-align: center;
            padding: 40px 20px 30px;
            background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, transparent 100%);
        }

        .header h1 {
            font-size: 2.8em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00bcd4, #4caf50, #ff9800);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: none;
        }

        .header .subtitle {
            color: #aaa;
            font-size: 1.2em;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px 40px;
        }

        .status-bar {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px 25px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }

        .status-active { background: linear-gradient(45deg, #4caf50, #8bc34a); }
        .status-waiting { background: linear-gradient(45deg, #ff9800, #ffc107); color: #333; }
        .status-error { background: linear-gradient(45deg, #f44336, #e91e63); }

        .section-title {
            font-size: 1.5em;
            margin: 30px 0 20px;
            padding-left: 15px;
            border-left: 4px solid #00bcd4;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }

        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            border-color: rgba(0,188,212,0.3);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .card-icon {
            font-size: 2em;
        }

        .card-title {
            font-size: 1.3em;
            font-weight: bold;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            transition: background 0.3s;
        }

        .stat-item:hover {
            background: rgba(0,188,212,0.1);
        }

        .stat-number {
            font-size: 1.8em;
            font-weight: bold;
            background: linear-gradient(45deg, #4caf50, #00bcd4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .command-log {
            height: 250px;
            overflow-y: auto;
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 15px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .command-item {
            padding: 10px 15px;
            margin: 5px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            border-left: 4px solid #4caf50;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .command-item.error { border-left-color: #f44336; }

        .command-time {
            color: #888;
            font-size: 0.85em;
        }

        .control-panel {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .control-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            justify-content: center;
        }

        .btn {
            background: linear-gradient(45deg, #00bcd4, #0097a7);
            border: none;
            color: white;
            padding: 14px 28px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,188,212,0.4);
        }

        .btn-secondary {
            background: linear-gradient(45deg, #607d8b, #546e7a);
        }

        .btn-secondary:hover {
            box-shadow: 0 8px 25px rgba(96,125,139,0.4);
        }

        .btn-success {
            background: linear-gradient(45deg, #4caf50, #43a047);
        }

        .btn-success:hover {
            box-shadow: 0 8px 25px rgba(76,175,80,0.4);
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00bcd4, #4caf50);
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        .module-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }

        .module-item {
            text-align: center;
            padding: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            transition: all 0.3s;
            cursor: pointer;
        }

        .module-item:hover {
            background: rgba(0,188,212,0.1);
            transform: scale(1.05);
        }

        .module-icon {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .module-name {
            font-weight: bold;
            margin-bottom: 5px;
        }

        .module-status {
            font-size: 0.85em;
            color: #4caf50;
        }

        .footer {
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }

        /* 음성 인식 관련 스타일 */
        .btn-recording {
            background: linear-gradient(45deg, #f44336, #e91e63) !important;
            animation: pulse-recording 1s infinite;
        }

        @keyframes pulse-recording {
            0%, 100% { transform: scale(1); box-shadow: 0 0 10px rgba(244, 67, 54, 0.5); }
            50% { transform: scale(1.05); box-shadow: 0 0 20px rgba(244, 67, 54, 0.8); }
        }

        .voice-indicator {
            display: none;
            position: fixed;
            bottom: 100px;
            right: 20px;
            background: rgba(244, 67, 54, 0.95);
            color: white;
            padding: 15px 25px;
            border-radius: 25px;
            font-weight: bold;
            z-index: 1000;
            animation: pulse-recording 1s infinite;
        }

        .voice-indicator.active {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .voice-wave {
            display: flex;
            gap: 3px;
            align-items: center;
        }

        .voice-wave span {
            width: 4px;
            background: white;
            border-radius: 2px;
            animation: wave 0.5s ease-in-out infinite;
        }

        .voice-wave span:nth-child(1) { height: 10px; animation-delay: 0s; }
        .voice-wave span:nth-child(2) { height: 15px; animation-delay: 0.1s; }
        .voice-wave span:nth-child(3) { height: 20px; animation-delay: 0.2s; }
        .voice-wave span:nth-child(4) { height: 15px; animation-delay: 0.3s; }
        .voice-wave span:nth-child(5) { height: 10px; animation-delay: 0.4s; }

        @keyframes wave {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(1.5); }
        }

        @media (max-width: 768px) {
            .header h1 { font-size: 2em; }
            .stats-grid { grid-template-columns: 1fr; }
            .dashboard-grid { grid-template-columns: 1fr; }
            .status-bar { flex-direction: column; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="live-indicator">
        <span class="live-dot"></span>
        <span>실시간 • LIVE</span>
    </div>

    <!-- 음성 인식 표시기 -->
    <div id="voice-indicator" class="voice-indicator">
        <div class="voice-wave">
            <span></span><span></span><span></span><span></span><span></span>
        </div>
        <span id="voice-status-text">음성 인식 중...</span>
    </div>

    <div class="header">
        <h1>🎤 소리새 통합 대시보드</h1>
        <p class="subtitle">Sorisae Integrated AI System Dashboard</p>
    </div>

    <div class="container">
        <!-- 상태 바 -->
        <div class="status-bar">
            <div class="status-item">
                <span>시스템 상태:</span>
                <span id="system-status" class="status-badge status-active">실행 중</span>
            </div>
            <div class="status-item">
                <span>마지막 명령:</span>
                <span id="last-command">없음</span>
            </div>
            <div class="status-item">
                <span>성공률:</span>
                <span id="success-rate">100%</span>
            </div>
            <div class="status-item">
                <span>업타임:</span>
                <span id="uptime">00:00:00</span>
            </div>
        </div>

        <!-- 핵심 모듈 섹션 -->
        <h2 class="section-title">🎯 핵심 AI 모듈</h2>
        <div class="module-grid" id="module-grid">
            <div class="module-item" onclick="activateModule('voice')">
                <div class="module-icon">🎤</div>
                <div class="module-name">음성 인식</div>
                <div class="module-status">● 활성</div>
            </div>
            <div class="module-item" onclick="activateModule('dual_brain')">
                <div class="module-icon">🧠</div>
                <div class="module-name">듀얼브레인</div>
                <div class="module-status">● 활성</div>
            </div>
            <div class="module-item" onclick="activateModule('iot')">
                <div class="module-icon">🏠</div>
                <div class="module-name">IoT 제어</div>
                <div class="module-status">● 활성</div>
            </div>
            <div class="module-item" onclick="activateModule('shopping')">
                <div class="module-icon">🛒</div>
                <div class="module-name">자율 쇼핑몰</div>
                <div class="module-status">● 활성</div>
            </div>
            <div class="module-item" onclick="activateModule('creative')">
                <div class="module-icon">🎨</div>
                <div class="module-name">창작 경제</div>
                <div class="module-status">● 활성</div>
            </div>
            <div class="module-item" onclick="activateModule('investment')">
                <div class="module-icon">📈</div>
                <div class="module-name">투자 조언</div>
                <div class="module-status">● 활성</div>
            </div>
        </div>

        <!-- 대시보드 그리드 -->
        <h2 class="section-title">📊 실시간 통계</h2>
        <div class="dashboard-grid">
            <!-- 음성 명령 카드 -->
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🎙️</span>
                    <span class="card-title">음성 명령 시스템</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="total-commands">0</div>
                        <div class="stat-label">총 명령 수</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="ai-collaborations">0</div>
                        <div class="stat-label">AI 협업</div>
                    </div>
                </div>
                <div class="command-log" id="command-log">
                    <div style="text-align: center; color: #666; padding: 50px 0;">
                        음성 명령 대기 중...
                    </div>
                </div>
            </div>

            <!-- 듀얼브레인 카드 -->
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🧠</span>
                    <span class="card-title">듀얼브레인 시스템</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="prediction-accuracy">92.5%</div>
                        <div class="stat-label">예측 정확도</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="evolution-cycle">42</div>
                        <div class="stat-label">진화 사이클</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="brain-a-status">활성</div>
                        <div class="stat-label">Brain A (실시간)</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="brain-b-status">진화중</div>
                        <div class="stat-label">Brain B (학습)</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="evolution-progress" style="width: 75%;"></div>
                </div>
            </div>

            <!-- 자율 쇼핑몰 카드 -->
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🛒</span>
                    <span class="card-title">자율 쇼핑몰</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="total-revenue">₩2,847,650</div>
                        <div class="stat-label">총 수익</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="total-sales">127</div>
                        <div class="stat-label">판매 건수</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="active-products">45</div>
                        <div class="stat-label">활성 상품</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="satisfaction">94.2%</div>
                        <div class="stat-label">고객 만족도</div>
                    </div>
                </div>
            </div>

            <!-- IoT 스마트홈 카드 -->
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🏠</span>
                    <span class="card-title">IoT 스마트홈</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="connected-devices">12</div>
                        <div class="stat-label">연결된 기기</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="active-automations">8</div>
                        <div class="stat-label">자동화 규칙</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="temperature">24°C</div>
                        <div class="stat-label">실내 온도</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="energy-saved">23.5%</div>
                        <div class="stat-label">에너지 절감</div>
                    </div>
                </div>
            </div>

            <!-- 창작 경제 카드 -->
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🎨</span>
                    <span class="card-title">창작 경제 시스템</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="contents-created">23</div>
                        <div class="stat-label">생성된 콘텐츠</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="monthly-revenue">$225</div>
                        <div class="stat-label">월 수익</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="ai-contributions">45</div>
                        <div class="stat-label">AI 기여도</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="quality-score">8.5</div>
                        <div class="stat-label">품질 점수</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 제어 패널 -->
        <h2 class="section-title">🎮 제어 패널</h2>
        <div class="control-panel">
            <div class="control-buttons">
                <button class="btn" onclick="sendCommand('상태 확인')">
                    📋 상태 확인
                </button>
                <button class="btn btn-success" id="voice-btn" onclick="toggleVoiceRecognition()">
                    🎤 음성 시작
                </button>
                <button class="btn" onclick="sendCommand('듀얼브레인 분석')">
                    🧠 분석 실행
                </button>
                <button class="btn" onclick="sendCommand('IoT 동기화')">
                    🏠 IoT 동기화
                </button>
                <button class="btn" onclick="sendCommand('쇼핑몰 최적화')">
                    🛒 최적화
                </button>
                <button class="btn btn-secondary" onclick="sendCommand('시스템 테스트')">
                    🧪 테스트
                </button>
                <button class="btn btn-secondary" onclick="sendCommand('도움말')">
                    ❓ 도움말
                </button>
            </div>
        </div>

        <!-- 푸터 -->
        <div class="footer">
            <p>🎤 소리새 통합 AI 시스템 v2.0 | © 2024 Sorisae Project</p>
            <p>로컬에서 실행 중 • http://localhost:5050</p>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let startTime = Date.now();

        // 소켓 연결 이벤트
        socket.on('connect', function() {
            console.log('🔗 서버 연결됨');
            updateSystemStatus('실행 중');
        });

        socket.on('disconnect', function() {
            console.log('❌ 서버 연결 끊김');
            updateSystemStatus('연결 끊김');
        });

        // 명령 업데이트
        socket.on('command_update', function(data) {
            addCommandToLog(data.command, data.status);
        });

        // 통계 업데이트
        socket.on('stats_update', function(data) {
            updateAllStats(data);
        });

        // 시스템 상태 업데이트
        function updateSystemStatus(status) {
            const statusEl = document.getElementById('system-status');
            statusEl.textContent = status;
            statusEl.className = 'status-badge ' +
                (status.includes('실행') ? 'status-active' :
                 status.includes('끊김') || status.includes('오류') ? 'status-error' : 'status-waiting');
        }

        // 명령 로그에 추가
        function addCommandToLog(command, status) {
            const log = document.getElementById('command-log');
            const item = document.createElement('div');
            item.className = 'command-item' + (status === '실패' ? ' error' : '');

            const now = new Date();
            const time = now.toLocaleTimeString('ko-KR');
            const icon = status === '실패' ? '❌' : '✅';

            item.innerHTML = '<span>' + icon + ' ' + command + '</span><span class="command-time">' + time + '</span>';

            // 초기 메시지 제거
            const emptyMsg = log.querySelector('div[style]');
            if (emptyMsg) emptyMsg.remove();

            log.appendChild(item);
            log.scrollTop = log.scrollHeight;
        }

        // 모든 통계 업데이트
        function updateAllStats(data) {
            if (data.system) {
                document.getElementById('total-commands').textContent = data.system.total_commands;
                document.getElementById('ai-collaborations').textContent = data.system.ai_collaborations;
                document.getElementById('last-command').textContent = data.system.last_command || '없음';
                document.getElementById('success-rate').textContent = data.system.success_rate.toFixed(1) + '%';
            }

            if (data.dual_brain) {
                document.getElementById('prediction-accuracy').textContent = data.dual_brain.prediction_accuracy + '%';
                document.getElementById('evolution-cycle').textContent = data.dual_brain.evolution_cycle;
                document.getElementById('brain-a-status').textContent = data.dual_brain.brain_a_status;
                document.getElementById('brain-b-status').textContent = data.dual_brain.brain_b_status;
            }

            if (data.mall) {
                document.getElementById('total-revenue').textContent = '₩' + data.mall.total_revenue.toLocaleString();
                document.getElementById('total-sales').textContent = data.mall.total_sales;
                document.getElementById('active-products').textContent = data.mall.active_products;
                document.getElementById('satisfaction').textContent = data.mall.customer_satisfaction + '%';
            }

            if (data.iot) {
                document.getElementById('connected-devices').textContent = data.iot.connected_devices;
                document.getElementById('active-automations').textContent = data.iot.active_automations;
                document.getElementById('temperature').textContent = data.iot.temperature + '°C';
                document.getElementById('energy-saved').textContent = data.iot.energy_saved + '%';
            }

            if (data.creative) {
                document.getElementById('contents-created').textContent = data.creative.contents_created;
                document.getElementById('monthly-revenue').textContent = '$' + data.creative.monthly_revenue;
                document.getElementById('ai-contributions').textContent = data.creative.ai_contributions;
                document.getElementById('quality-score').textContent = data.creative.quality_score;
            }
        }

        // 명령 전송
        function sendCommand(command) {
            socket.emit('remote_command', {command: command});
            addCommandToLog('[원격] ' + command, '성공');
        }

        // 모듈 활성화
        function activateModule(moduleName) {
            const moduleNames = {
                'voice': '음성 인식',
                'dual_brain': '듀얼브레인',
                'iot': 'IoT 제어',
                'shopping': '자율 쇼핑몰',
                'creative': '창작 경제',
                'investment': '투자 조언'
            };
            sendCommand(moduleNames[moduleName] + ' 활성화');
        }

        // 업타임 업데이트
        function updateUptime() {
            const uptime = Math.floor((Date.now() - startTime) / 1000);
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = uptime % 60;
            document.getElementById('uptime').textContent =
                hours.toString().padStart(2, '0') + ':' +
                minutes.toString().padStart(2, '0') + ':' +
                seconds.toString().padStart(2, '0');
        }

        // 통계 요청
        function requestStats() {
            socket.emit('get_stats');
        }

        // === Web Speech API 음성 인식/합성 ===
        let recognition = null;
        let isRecording = false;
        let isSpeaking = false;  // TTS 발화 중 플래그 (음성 루프 방지)

        // 음성 인식 초기화
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                console.warn('브라우저가 음성 인식을 지원하지 않습니다.');
                return false;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'ko-KR';
            recognition.continuous = true;  // 연속 인식 모드 (한 번의 발화가 끝날 때까지 계속 듣기, 명령 처리 후 자동 중지)
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;

            recognition.onstart = function() {
                isRecording = true;
                const btn = document.getElementById('voice-btn');
                btn.textContent = '🔴 녹음 중...';
                btn.classList.add('btn-recording');
                document.getElementById('voice-indicator').classList.add('active');
                document.getElementById('voice-status-text').textContent = '음성 인식 중...';
                addCommandToLog('음성 인식 시작', '성공');
            };

            recognition.onresult = function(event) {
                // TTS 발화 중에는 음성 인식 결과 무시 (루프 방지)
                if (isSpeaking) {
                    console.log('TTS 발화 중 - 음성 인식 결과 무시');
                    return;
                }

                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                document.getElementById('voice-status-text').textContent = transcript || '듣는 중...';

                if (event.results[event.results.length - 1].isFinal) {
                    // 최종 결과 처리
                    processVoiceCommand(transcript);
                    // continuous 모드에서는 명령 처리 후 인식 중지
                    recognition.stop();
                }
            };

            recognition.onerror = function(event) {
                console.error('음성 인식 오류:', event.error);
                stopVoiceRecognition();

                let errorMsg = '음성 인식 오류';
                if (event.error === 'no-speech') {
                    errorMsg = '음성이 감지되지 않았습니다';
                } else if (event.error === 'not-allowed') {
                    errorMsg = '마이크 권한이 필요합니다';
                }
                addCommandToLog(errorMsg, '실패');
                speak('죄송합니다. ' + errorMsg);
            };

            recognition.onend = function() {
                stopVoiceRecognition();
            };

            return true;
        }

        // 음성 인식 시작/중지 토글
        function toggleVoiceRecognition() {
            if (!recognition) {
                if (!initSpeechRecognition()) {
                    addCommandToLog('브라우저가 음성 인식을 지원하지 않습니다', '실패');
                    speak('죄송합니다. 이 브라우저는 음성 인식을 지원하지 않습니다.');
                    return;
                }
            }

            if (isRecording) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                } catch (e) {
                    console.error('음성 인식 시작 오류:', e);
                    addCommandToLog('음성 인식을 시작할 수 없습니다', '실패');
                }
            }
        }

        // 음성 인식 중지
        function stopVoiceRecognition() {
            isRecording = false;
            const btn = document.getElementById('voice-btn');
            btn.textContent = '🎤 음성 시작';
            btn.classList.remove('btn-recording');
            document.getElementById('voice-indicator').classList.remove('active');
        }

        // 음성 명령 처리
        function processVoiceCommand(command) {
            if (!command || command.trim() === '') return;

            addCommandToLog('[음성] ' + command, '성공');
            socket.emit('remote_command', {command: command});

            // 서버 응답만 사용 (기본 응답 제거하여 중복 방지)
            socket.once('voice_response', function(data) {
                if (data && data.response) {
                    speak(data.response);
                }
            });
        }

        // 음성 합성 (TTS)
        function speak(text) {
            if (!('speechSynthesis' in window)) {
                console.warn('브라우저가 음성 합성을 지원하지 않습니다.');
                return;
            }

            // 무한 루프 방지: 이미 발화 중이면 무시
            if (isSpeaking) {
                console.log('이미 TTS 발화 중 - 새 요청 무시');
                return;
            }

            // 발화 플래그를 즉시 설정 (레이스 컨디션 방지)
            isSpeaking = true;

            // TTS 시작 전 음성 인식 중지 (루프 방지)
            if (isRecording && recognition) {
                recognition.stop();
            }

            // 이전 음성 중지
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'ko-KR';
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            // 한국어 음성 찾기
            const voices = window.speechSynthesis.getVoices();
            const koreanVoice = voices.find(function(voice) {
                return voice.lang.includes('ko');
            });
            if (koreanVoice) {
                utterance.voice = koreanVoice;
            }

            utterance.onstart = function() {
                addCommandToLog('[TTS] ' + text.substring(0, 30) + '...', '성공');
            };

            utterance.onend = function() {
                isSpeaking = false;  // 발화 종료
                console.log('TTS 발화 완료');
            };

            utterance.onerror = function(event) {
                isSpeaking = false;  // 오류 시에도 플래그 해제
                console.error('TTS 오류:', event);
            };

            // utterance가 실패하면 플래그를 해제해야 하므로 try-catch로 보호
            try {
                window.speechSynthesis.speak(utterance);
            } catch (error) {
                isSpeaking = false;  // 예외 발생 시 플래그 해제
                console.error('TTS 시작 실패:', error);
            }
        }

        // 음성 목록 로드 대기
        if ('speechSynthesis' in window) {
            window.speechSynthesis.onvoiceschanged = function() {
                console.log('음성 목록 로드됨:', window.speechSynthesis.getVoices().length);
            };
        }

        // 초기화 및 주기적 업데이트
        setInterval(updateUptime, 1000);
        setInterval(requestStats, 3000);
        requestStats();
    </script>
</body>
</html>"""


# === 라우트 정의 ===
@app.route("/")
def index():
    """메인 대시보드 페이지"""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/stats")
def api_stats():
    """API: 전체 통계 반환"""
    return jsonify(state.get_all_stats())


@app.route("/api/health")
def api_health():
    """API: 서버 상태 확인"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


def _extract_openai_user_message(messages):
    """OpenAI-compatible messages payload에서 최근 user message를 추출한다."""
    if not isinstance(messages, list):
        return ""
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").strip().lower() != "user":
            continue
        return str(item.get("content") or "").strip()
    return ""


def _build_openai_compatible_response(content, model):
    """OpenAI chat/completions 응답 규격으로 래핑한다."""
    now_ts = int(datetime.now().timestamp())
    response_model = str(model or "sorisae-compat")
    return {
        "id": f"chatcmpl-sorisae-{now_ts}",
        "object": "chat.completion",
        "created": now_ts,
        "model": response_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": str(content or "")},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


@app.route("/chat/completions", methods=["POST"])
@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions_adapter():
    """OpenAI-compatible chat/completions 어댑터.

    SORISAE_UPSTREAM_URL 이 설정된 경우 해당 vLLM 엔드포인트로 요청을 프록시한다.
    미설정 시 키워드 매핑 fallback 응답을 사용한다.
    """
    payload = request.get_json(silent=True) or {}
    model = str(payload.get("model") or "sorisae-compat")
    messages = payload.get("messages")
    user_message = _extract_openai_user_message(messages)

    upstream_base = str(
        os.environ.get("SORISAE_UPSTREAM_URL", "http://host.docker.internal:8008")
    ).rstrip("/")
    logger.info(
        "[SORISAE_COMPAT] chat/completions hit model=%s user_len=%s upstream=%s",
        model,
        len(user_message or ""),
        upstream_base or "none",
    )

    # --- upstream vLLM 프록시 경로 ---
    if upstream_base:
        upstream_url = upstream_base + "/v1/chat/completions"
        try:
            proxy_body = json.dumps(payload).encode("utf-8")
            req = _ureq.Request(
                upstream_url,
                data=proxy_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _ureq.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            result = json.loads(raw)
            # 응답이 올바른 choices 구조인지 확인
            if isinstance(result, dict) and result.get("choices"):
                logger.info("[SORISAE_COMPAT] upstream OK")
                return jsonify(result)
            logger.warning("[SORISAE_COMPAT] upstream 응답 형식 불일치 — fallback 사용")
        except _uerr.URLError as e:
            logger.warning("[SORISAE_COMPAT] upstream 연결 실패 (%s) — fallback 사용", e)
        except Exception as e:
            logger.warning("[SORISAE_COMPAT] upstream 오류 (%s) — fallback 사용", e)

    # --- fallback: 키워드 매핑 응답 ---
    fallback_message = "안녕하세요. 소리새 중앙 컨트롤 타워가 연결되었습니다."
    content = generate_voice_response(user_message or fallback_message)
    return jsonify(_build_openai_compatible_response(content, model))


# === 소켓 이벤트 핸들러 ===
@socketio.on("connect")
def handle_connect():
    """클라이언트 연결"""
    print("🔗 클라이언트 연결됨")
    emit("stats_update", state.get_all_stats())


@socketio.on("disconnect")
def handle_disconnect():
    """클라이언트 연결 해제"""
    print("👋 클라이언트 연결 해제됨")


@socketio.on("remote_command")
def handle_remote_command(data):
    """원격 명령 처리"""
    try:
        command = data.get("command", "")
        print(f"📡 원격 명령 수신: {command}")

        # 명령 처리 및 상태 업데이트
        command_data = state.add_voice_command(f"[원격] {command}")

        # 시뮬레이션: 명령에 따른 데이터 업데이트
        simulate_command_effect(command)

        # 음성 응답 생성
        response = generate_voice_response(command)

        emit("command_update", command_data, broadcast=True)
        emit("stats_update", state.get_all_stats(), broadcast=True)
        emit("voice_response", {"response": response})
    except Exception as e:
        print(f"❌ 명령 처리 오류: {e}")
        # 오류 발생 시에도 클라이언트에 응답 전송
        try:
            emit("voice_response", {"response": "명령 처리 중 오류가 발생했습니다."})
        except Exception as emit_error:
            # 소켓이 이미 닫혀있을 수 있음
            print(f"⚠️ 응답 전송 실패 (소켓 닫힘): {emit_error}")


@socketio.on("get_stats")
def handle_get_stats():
    """통계 요청 처리"""
    try:
        emit("stats_update", state.get_all_stats())
    except Exception as e:
        print(f"❌ 통계 전송 오류: {e}")


def simulate_command_effect(command):
    """명령 효과 시뮬레이션"""
    if "쇼핑몰" in command or "최적화" in command:
        state.mall_stats["total_revenue"] += random.randint(10000, 50000)
        state.mall_stats["total_sales"] += random.randint(1, 5)

    if "듀얼브레인" in command or "분석" in command:
        state.dual_brain_stats["evolution_cycle"] += 1
        new_accuracy = state.dual_brain_stats["prediction_accuracy"] + random.uniform(0.1, 0.5)
        state.dual_brain_stats["prediction_accuracy"] = min(99.9, new_accuracy)

    if "IoT" in command or "동기화" in command:
        state.iot_stats["energy_saved"] = min(50, state.iot_stats["energy_saved"] + random.uniform(0.5, 2))

    if "창작" in command or "콘텐츠" in command:
        state.creative_stats["contents_created"] += 1
        state.creative_stats["monthly_revenue"] += random.randint(5, 20)

    state.ai_collaborations += 1


def generate_voice_response(command):
    """
    음성 명령에 대한 응답 생성
    
    Rate limit 에러 등 외부 API 오류 시 폴백 응답 사용
    """
    try:
        command_lower = command.lower()

        # 명령어에 따른 응답 매핑
        responses = {
            "상태": f"시스템이 정상 작동 중입니다. 현재 {state.command_count}개의 명령을 처리했습니다.",
            "듀얼브레인": f"듀얼브레인 분석을 시작합니다. 현재 예측 정확도는 {state.dual_brain_stats['prediction_accuracy']:.1f}퍼센트입니다.",
            "분석": f"듀얼브레인 분석을 실행합니다. 진화 사이클 {state.dual_brain_stats['evolution_cycle']}번째입니다.",
            "iot": f"IoT 기기를 동기화합니다. 현재 {state.iot_stats['connected_devices']}개의 기기가 연결되어 있습니다.",
            "동기화": f"IoT 동기화가 완료되었습니다. 에너지 절감률은 {state.iot_stats['energy_saved']:.1f}퍼센트입니다.",
            "쇼핑몰": f"쇼핑몰 최적화를 실행합니다. 현재 총 수익은 {state.mall_stats['total_revenue']:,}원입니다.",
            "최적화": f"쇼핑몰 최적화가 완료되었습니다. 판매 건수는 {state.mall_stats['total_sales']}건입니다.",
            "테스트": "시스템 테스트를 시작합니다. 모든 모듈이 정상 작동 중입니다.",
            "도움말": "음성 명령을 통해 시스템을 제어할 수 있습니다. 상태 확인, 듀얼브레인 분석, IoT 동기화, 쇼핑몰 최적화 등의 명령을 사용해보세요.",
            "안녕": "안녕하세요! 소리새 통합 대시보드입니다. 무엇을 도와드릴까요?",
            "창작": f"창작 경제 시스템이 활성화되었습니다. 현재 {state.creative_stats['contents_created']}개의 콘텐츠가 생성되었습니다.",
            "투자": "투자 조언 모듈을 활성화합니다.",
            "음성": "음성 인식 시스템이 활성화되었습니다. 말씀해주세요.",
        }

        # 명령어 매칭
        for keyword, response in responses.items():
            if keyword in command_lower:
                return response

        # 기본 응답
        return f"명령을 처리했습니다: {command}"
        
    except Exception as e:
        # 에러 발생 시 처리
        error_message = str(e)
        logger.error(f"음성 응답 생성 중 오류: {error_message}")
        
        # Rate limit 에러 감지
        if "429" in error_message or "rate_limit" in error_message.lower():
            logger.warning("API Rate Limit 에러 감지")
            if FALLBACK_AVAILABLE:
                return get_fallback_response(command, 
                                            context={"command_count": state.command_count},
                                            is_api_error=True)
            else:
                return "죄송합니다. 현재 AI 서비스가 일시적으로 제한되어 있습니다. 나중에 다시 시도해주세요."
        
        # 일반 오류 처리
        if FALLBACK_AVAILABLE:
            return get_fallback_response(command, 
                                        context={"command_count": state.command_count})
        else:
            return f"명령을 처리했습니다: {command}"


def load_mall_data():
    """쇼핑몰 데이터 로드"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    data_path = os.path.join(data_dir, "autonomous_mall_data.json")

    # 경로 검증: data 디렉토리 내부 파일인지 확인
    if not os.path.isdir(data_dir):
        print("⚠️ 데이터 디렉토리가 존재하지 않습니다")
        return

    # 실제 경로가 data 디렉토리 내부인지 확인 (경로 탐색 방지)
    real_data_path = os.path.realpath(data_path)
    real_data_dir = os.path.realpath(data_dir)
    if not real_data_path.startswith(real_data_dir):
        print("⚠️ 잘못된 데이터 파일 경로")
        return

    if os.path.exists(data_path):
        try:
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)
                if "mall_stats" in data:
                    state.mall_stats.update(data["mall_stats"])
                print("✅ 쇼핑몰 데이터 로드 완료")
        except Exception as e:
            print(f"⚠️ 쇼핑몰 데이터 로드 실패: {e}")


def run_dashboard(host="127.0.0.1", port=5050, open_browser=True):
    """대시보드 서버 실행

    Args:
        host: 호스트 주소 (기본: 127.0.0.1 - 로컬 전용, 외부 접근 필요시 0.0.0.0)
        port: 포트 번호 (기본: 5050)
        open_browser: 브라우저 자동 열기 여부 (기본: True)
    """
    print("=" * 60)
    print("🎤 소리새 통합 대시보드 시작")
    print("=" * 60)
    print(f"🌐 서버 주소: http://localhost:{port}")
    print("📊 실시간 통계 및 제어 기능 제공")
    print("🔌 WebSocket 연결 지원")
    print("=" * 60)

    # 쇼핑몰 데이터 로드
    load_mall_data()

    # 자동으로 브라우저 열기
    if open_browser:
        def open_browser_delayed():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")

        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()
        print("🚀 브라우저에서 대시보드를 여는 중...")

    print("\n⏹️  종료하려면 Ctrl+C를 누르세요\n")

    # 서버 실행 (개발용 서버 - 프로덕션에서는 gunicorn 등 사용 권장)
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="소리새 통합 대시보드")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 주소 (기본: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5050, help="포트 번호 (기본: 5050)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 열기 비활성화")

    args = parser.parse_args()

    try:
        run_dashboard(host=args.host, port=args.port, open_browser=not args.no_browser)
    except KeyboardInterrupt:
        print("\n👋 소리새 통합 대시보드가 종료되었습니다.")


if __name__ == "__main__":
    main()
