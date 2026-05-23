import json
import logging
from datetime import datetime
from functools import wraps
from threading import Lock

from flask import Flask, jsonify, render_template_string, request
from flask_socketio import SocketIO, emit

# 로깅 설정 import
try:
    from modules.logging_config import setup_logger
    logger = setup_logger('sorisae_dashboard_web', level='INFO')
except ImportError:
    # 백업: 기본 로깅 설정
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('sorisae_dashboard_web')

# 🎵 음악 채팅 시스템 통합
try:
    from ai_code_manager.music_chat_system import MusicChatSystem
    music_chat_available = True
except ImportError:
    music_chat_available = False

# 🔒 보안 설정 로드


def load_security_config():
    try:
        with open("config/security_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info("보안 설정 파일 로드 완료")
            return config
    except FileNotFoundError:
        logger.warning("보안 설정 파일이 없습니다. 기본 설정을 사용합니다.")
        print("⚠️ 보안 설정 파일이 없습니다. 기본 설정을 사용합니다.")
        return {
            "security": {
                "allowed_commands": ["리팩터링", "동기화", "상태", "테스트", "정리", "도움말"],
                "max_failed_attempts": 5
            }
        }
    except json.JSONDecodeError as e:
        logger.error(f"보안 설정 파일 JSON 파싱 오류: {e}", exc_info=True)
        print(f"⚠️ 보안 설정 파일 형식 오류: {e}")
        return {
            "security": {
                "allowed_commands": ["리팩터링", "동기화", "상태", "테스트", "정리", "도움말"],
                "max_failed_attempts": 5
            }
        }
    except Exception as e:
        logger.error(f"보안 설정 로드 중 예상치 못한 오류: {e}", exc_info=True)
        print(f"⚠️ 보안 설정 로드 실패: {e}")
        return {
            "security": {
                "allowed_commands": ["리팩터링", "동기화", "상태", "테스트", "정리", "도움말"],
                "max_failed_attempts": 5
            }
        }


security_config = load_security_config()
failed_attempts = {}  # IP별 실패 횟수 추적
active_sessions = {}  # 활성 세션 관리

# 🔑 인증 관련 함수들


def verify_api_key(api_key):
    """API 키 검증"""
    api_keys = security_config.get("security", {}).get("api_keys", {})
    return api_key in api_keys.values()


def verify_token(token):
    """액세스 토큰 검증"""
    tokens = security_config.get("security", {}).get("access_tokens", {})
    return token in tokens.values()


def get_permission_level(credential):
    """자격 증명에 따른 권한 레벨 반환"""
    permissions = security_config.get("security", {}).get("permissions", {})

    # API 키로 검색
    api_keys = security_config.get("security", {}).get("api_keys", {})
    for key_name, key_value in api_keys.items():
        if credential == key_value:
            return permissions.get(key_name, [])

    # 토큰으로 검색
    tokens = security_config.get("security", {}).get("access_tokens", {})
    for token_name, token_value in tokens.items():
        if credential == token_value:
            return permissions.get(token_name, [])

    return []


def require_auth(permission=None):
    """인증 데코레이터"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # API 키 또는 토큰 확인
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            token = request.headers.get('Authorization') or request.args.get('token')

            if not api_key and not token:
                return jsonify({"error": "인증이 필요합니다", "code": "AUTH_REQUIRED"}), 401

            credential = api_key or token
            if not verify_api_key(credential) and not verify_token(credential):
                return jsonify({"error": "유효하지 않은 인증 정보", "code": "INVALID_CREDENTIALS"}), 401

            # 권한 확인
            if permission:
                user_permissions = get_permission_level(credential)
                if permission not in user_permissions and "all" not in user_permissions:
                    return jsonify({"error": "권한이 부족합니다", "code": "INSUFFICIENT_PERMISSIONS"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


app = Flask(__name__)
app.secret_key = "sorisae_secure_key_2025"  # 보안키 추가
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5050", "http://127.0.0.1:5050"])  # CORS 제한

# 🎵 음악 채팅 시스템 초기화
if music_chat_available:
    music_chat_system = MusicChatSystem()
else:
    music_chat_system = None

# 실시간 상태 관리


class DashboardState:
    def __init__(self):
        self.lock = Lock()
        self.voice_commands = []
        self.system_status = "대기 중"
        self.active_plugins = []
        self.last_command = None
        self.command_count = 0
        self.is_listening = False
        self.error_count = 0
        # 🎨 새로운 창의적 기능 상태
        self.current_persona = "friendly"
        self.creative_activities = []
        self.ai_collaborations = 0
        self.memory_count = 0
        self.generated_plugins = 0
        # 🎵 음악 채팅 상태
        self.music_chat_rooms = []
        self.active_chat_users = 0
        self.total_chat_messages = 0

    def add_voice_command(self, command, status="성공", plugin_name=None):
        with self.lock:
            command_data = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "command": command,
                "status": status,
                "plugin": plugin_name or "시스템"
            }
            self.voice_commands.append(command_data)
            self.last_command = command
            self.command_count += 1

            if status == "실패":
                self.error_count += 1

            # 최근 20개만 유지
            if len(self.voice_commands) > 20:
                self.voice_commands.pop(0)

        # 클라이언트에 실시간 업데이트 전송
        socketio.emit('command_update', command_data)
        socketio.emit('stats_update', self.get_stats())

    def set_system_status(self, status):
        with self.lock:
            self.system_status = status
        socketio.emit('status_update', {"status": status})

    def set_listening_status(self, is_listening):
        with self.lock:
            self.is_listening = is_listening
        socketio.emit('listening_update', {"is_listening": is_listening})

    def get_stats(self):
        with self.lock:
            return {
                "total_commands": self.command_count,
                "recent_commands": len(self.voice_commands),
                "last_command": self.last_command,
                "system_status": self.system_status,
                "active_plugins": self.active_plugins,
                "is_listening": self.is_listening,
                "error_count": self.error_count,
                "success_rate": ((self.command_count - self.error_count) / max(1, self.command_count)) * 100,
                # 🎨 창의적 기능 통계
                "current_persona": self.current_persona,
                "ai_collaborations": self.ai_collaborations,
                "memory_count": self.memory_count,
                "generated_plugins": self.generated_plugins,
                "creative_activities": len(self.creative_activities),
                # 🎵 음악 채팅 통계
                "chat_rooms": len(music_chat_system.list_rooms()) if music_chat_system else 0,
                "chat_users": sum(len(room.current_users) for room in music_chat_system.list_rooms().values()) if music_chat_system else 0,
                "total_chat_messages": self.total_chat_messages
            }

    def update_persona(self, persona):
        """🎭 페르소나 업데이트"""
        with self.lock:
            self.current_persona = persona
        socketio.emit('persona_update', {"current_persona": persona})

    def add_creative_activity(self, activity_type, description):
        """🎨 창의적 활동 추가"""
        with self.lock:
            activity = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": activity_type,
                "description": description
            }
            self.creative_activities.append(activity)

            # 활동 유형별 카운터 증가
            if activity_type == "collaboration":
                self.ai_collaborations += 1
            elif activity_type == "plugin_generation":
                self.generated_plugins += 1
            elif activity_type == "memory_save":
                self.memory_count += 1

            # 최근 10개만 유지
            if len(self.creative_activities) > 10:
                self.creative_activities.pop(0)

        socketio.emit('creative_update', activity)
        socketio.emit('stats_update', self.get_stats())


dashboard_state = DashboardState()

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌐 소리새 대시보드</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: linear-gradient(135deg, #1e3c72, #2a5298);
    color: #eee;
    font-family: 'Malgun Gothic', sans-serif;
    min-height: 100vh;
}
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.header { text-align: center; margin-bottom: 30px; }
.header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
.status-bar {
    background: rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    backdrop-filter: blur(10px);
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.card {
    background: rgba(255,255,255,0.1);
    border-radius: 15px;
    padding: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
}
.card h3 { margin-bottom: 15px; color: #00bcd4; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
.stat-item { text-align: center; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px; }
.stat-number { font-size: 2em; font-weight: bold; color: #4caf50; }
.command-log {
    height: 300px;
    overflow-y: auto;
    background: rgba(0,0,0,0.3);
    border-radius: 10px;
    padding: 15px;
    border: 1px solid rgba(255,255,255,0.1);
}
.command-item {
    padding: 8px 12px;
    margin: 5px 0;
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
    border-left: 4px solid #4caf50;
}
.command-item.failed { border-left-color: #f44336; }
.controls { text-align: center; margin-top: 20px; }
button {
    background: linear-gradient(45deg, #00bcd4, #0097a7);
    border: none;
    color: white;
    padding: 12px 24px;
    margin: 8px;
    border-radius: 25px;
    cursor: pointer;
    font-size: 16px;
    font-weight: bold;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0,188,212,0.3);
}
button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,188,212,0.4);
}
.system-status {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 15px;
    font-weight: bold;
}
.status-active { background: #4caf50; }
.status-waiting { background: #ff9800; }
.status-error { background: #f44336; }
@media (max-width: 768px) {
    .grid { grid-template-columns: 1fr; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎤 소리새 AI 대시보드</h1>
        <div class="status-bar">
            <span>시스템 상태: </span>
            <span id="system-status" class="system-status status-waiting">대기 중</span>
            <span style="margin-left: 20px;">마지막 명령: </span>
            <span id="last-command">없음</span>
            <div style="margin-left: auto; display: flex; align-items: center;">
                <div id="auth-status" style="padding: 5px 12px; border-radius: 10px; background: #f44336; color: white; margin-right: 10px;">🔒 미인증</div>
                <button onclick="showAuthModal()" style="padding: 5px 10px; background: #2196f3; border: none; border-radius: 5px; color: white;">🔑 인증</button>
            </div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>📊 실시간 통계</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number" id="total-commands">0</div>
                    <div>총 명령 수</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="recent-commands">0</div>
                    <div>최근 명령</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="active-plugins">0</div>
                    <div>활성 플러그인</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="uptime">00:00</div>
                    <div>가동 시간</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>🎭 창의적 AI 상태</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number" id="current-persona">😊</div>
                    <div>현재 페르소나</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="ai-collaborations">0</div>
                    <div>AI 협업 횟수</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="memory-count">0</div>
                    <div>저장된 기억</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="generated-plugins">0</div>
                    <div>생성된 플러그인</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="chat-rooms">0</div>
                    <div>채팅방 수</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="chat-users">0</div>
                    <div>채팅 사용자</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>🎙️ 음성 명령 로그</h3>
            <div id="command-log" class="command-log">
                <div style="text-align: center; color: #888; margin-top: 50px;">
                    음성 명령을 기다리는 중...
                </div>
            </div>
        </div>

        <div class="card">
            <h3>🎨 창의적 활동 로그</h3>
            <div id="creative-log" class="command-log">
                <div style="text-align: center; color: #888; margin-top: 50px;">
                    창의적 활동을 기다리는 중...
                </div>
            </div>
        </div>
    </div>

        <div class="card">
        <h3>🎮 원격 제어</h3>
        <div class="controls">
            <button onclick="sendCommand('리팩터링')">🔧 리팩터링</button>
            <button onclick="sendCommand('동기화')">🔄 동기화</button>
            <button onclick="sendCommand('상태')">📋 상태 확인</button>
            <button onclick="sendCommand('테스트')">🧪 테스트 실행</button>
            <button onclick="sendCommand('정리')">🧹 프로젝트 정리</button>
            <button onclick="sendCommand('도움말')">❓ 도움말</button>
        </div>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
            <h4>🎵 음악 & 채팅</h4>
            <div class="controls">
                <button onclick="window.open('/music-chat', '_blank')">🎵 음악 채팅방</button>
                <button onclick="sendCommand('작곡 시작')">🎼 작곡하기</button>
                <button onclick="sendCommand('작사 시작')">📝 작사하기</button>
                <button onclick="sendCommand('채팅방 목록')">💬 채팅 목록</button>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
const socket = io();
let startTime = Date.now();

// 소켓 이벤트 리스너
socket.on('voice_command', function(data) {
    addCommandToLog(data.command, data.status);
    updateStats();
});

socket.on('system_status', function(data) {
    updateSystemStatus(data.status);
});

socket.on('stats_update', function(data) {
    document.getElementById('total-commands').textContent = data.total_commands;
    document.getElementById('recent-commands').textContent = data.recent_commands;
    document.getElementById('active-plugins').textContent = data.active_plugins.length;
    document.getElementById('last-command').textContent = data.last_command || '없음';

    // 🎨 창의적 기능 통계 업데이트
    if (data.current_persona) {
        const personaEmoji = {
            'friendly': '😊', 'genius': '🤓', 'creative': '🎨',
            'coach': '💪', 'philosopher': '🧐'
        };
        document.getElementById('current-persona').textContent =
            personaEmoji[data.current_persona] || '🤖';
    }
    if (data.ai_collaborations !== undefined) {
        document.getElementById('ai-collaborations').textContent = data.ai_collaborations;
    }
    if (data.memory_count !== undefined) {
        document.getElementById('memory-count').textContent = data.memory_count;
    }
    if (data.generated_plugins !== undefined) {
        document.getElementById('generated-plugins').textContent = data.generated_plugins;
    }
    // 🎵 음악 채팅 통계 업데이트
    if (data.chat_rooms !== undefined) {
        document.getElementById('chat-rooms').textContent = data.chat_rooms;
    }
    if (data.chat_users !== undefined) {
        document.getElementById('chat-users').textContent = data.chat_users;
    }
});

// 🎭 페르소나 업데이트 이벤트
socket.on('persona_update', function(data) {
    console.log('페르소나 변경:', data.current_persona);
});

// 🎨 창의적 활동 업데이트 이벤트
socket.on('creative_update', function(data) {
    addCreativeActivityToLog(data);
});

// 명령어 로그에 추가
function addCommandToLog(command, status = 'success') {
    const log = document.getElementById('command-log');
    const item = document.createElement('div');
    item.className = `command-item ${status === 'failed' ? 'failed' : ''}`;

    const now = new Date();
    const time = now.toLocaleTimeString();
    const statusIcon = status === 'failed' ? '❌' : '✅';

    item.innerHTML = `
        <span style="color: #888;">[${time}]</span>
        <span>${statusIcon} ${command}</span>
    `;

    log.appendChild(item);
    log.scrollTop = log.scrollHeight;

    // 빈 메시지 제거
    const emptyMsg = log.querySelector('div[style*="text-align: center"]');
    if (emptyMsg) emptyMsg.remove();
}

// 시스템 상태 업데이트
function updateSystemStatus(status) {
    const statusEl = document.getElementById('system-status');
    statusEl.textContent = status;
    statusEl.className = 'system-status ' +
        (status.includes('실행') ? 'status-active' :
         status.includes('오류') ? 'status-error' : 'status-waiting');
}

// 원격 명령 전송
function sendCommand(command) {
    socket.emit('remote_command', {command: command});
    addCommandToLog(`[원격] ${command}`, 'success');
}

// 🎨 창의적 활동 로그에 추가
function addCreativeActivityToLog(activity) {
    const log = document.getElementById('creative-log');
    const item = document.createElement('div');
    item.className = 'command-item';

    const activityIcons = {
        'collaboration': '🤝',
        'plugin_generation': '🧩',
        'memory_save': '🧠',
        'persona_switch': '🎭',
        'code_analysis': '🎨'
    };

    const icon = activityIcons[activity.type] || '✨';

    item.innerHTML = `
        <span style="color: #888;">[${activity.timestamp}]</span>
        <span>${icon} ${activity.description}</span>
    `;

    log.appendChild(item);
    log.scrollTop = log.scrollHeight;

    // 빈 메시지 제거
    const emptyMsg = log.querySelector('div[style*="text-align: center"]');
    if (emptyMsg) emptyMsg.remove();
}

// 🔑 인증 관련 함수들
let currentAuth = null;

// 인증 모달 표시
function showAuthModal() {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); display: flex; align-items: center;
        justify-content: center; z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 15px; max-width: 400px; width: 90%;">
            <h3 style="margin-bottom: 20px; color: #333;">🔑 인증하기</h3>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">API 키:</label>
                <input type="text" id="auth-api-key" placeholder="API 키 입력" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">액세스 토큰:</label>
                <input type="text" id="auth-token" placeholder="액세스 토큰 입력" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="authenticate()" style="flex: 1; padding: 10px; background: #4caf50; border: none; border-radius: 5px; color: white; font-weight: bold;">✅ 인증</button>
                <button onclick="closeAuthModal()" style="flex: 1; padding: 10px; background: #f44336; border: none; border-radius: 5px; color: white; font-weight: bold;">❌ 취소</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.onclick = (e) => { if (e.target === modal) closeAuthModal(); };
}

// 인증 모달 닫기
function closeAuthModal() {
    const modal = document.querySelector('div[style*="z-index: 1000"]');
    if (modal) modal.remove();
}

// 인증 실행
async function authenticate() {
    const apiKey = document.getElementById('auth-api-key').value;
    const token = document.getElementById('auth-token').value;

    if (!apiKey && !token) {
        alert('API 키 또는 액세스 토큰 중 하나를 입력해주세요.');
        return;
    }

    const credential = apiKey || token;

    try {
        const response = await fetch('/api/auth/verify', {
            method: 'GET',
            headers: {
                'X-API-Key': apiKey || '',
                'Authorization': token || ''
            }
        });

        const result = await response.json();

        if (result.valid) {
            currentAuth = credential;
            updateAuthStatus(true, result.permissions);
            closeAuthModal();
            alert(`✅ 인증 성공! 권한: ${result.permissions.join(', ')}`);
        } else {
            alert('❌ 인증 실패: ' + (result.error || '유효하지 않은 인증 정보'));
        }
    } catch (error) {
        console.error('인증 오류:', error);
        alert('❌ 인증 중 오류가 발생했습니다.');
    }
}

// 인증 상태 업데이트
function updateAuthStatus(authenticated, permissions = []) {
    const authStatus = document.getElementById('auth-status');

    if (authenticated) {
        authStatus.textContent = `🔓 인증됨 (${permissions.join(', ')})`;
        authStatus.style.background = '#4caf50';
    } else {
        authStatus.textContent = '🔒 미인증';
        authStatus.style.background = '#f44336';
    }
}

// 로그아웃
function logout() {
    currentAuth = null;
    updateAuthStatus(false);
    alert('🔒 로그아웃되었습니다.');
}

// 인증된 요청 전송
function sendAuthenticatedCommand(command) {
    if (!currentAuth) {
        alert('⚠️ 명령 실행을 위해 먼저 인증이 필요합니다.');
        showAuthModal();
        return;
    }

    socket.emit('remote_command', {
        command: command,
        auth: currentAuth
    });
}

// 기존 명령 전송 함수 수정
function sendRemoteCommand() {
    const command = document.getElementById('remote-command').value.trim();
    if (command) {
        sendAuthenticatedCommand(command);
        document.getElementById('remote-command').value = '';
    }
}

// 통계 업데이트 요청
function updateStats() {
    socket.emit('get_stats');
}

// 가동 시간 업데이트
function updateUptime() {
    const uptime = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(uptime / 60);
    const seconds = uptime % 60;
    document.getElementById('uptime').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 초기화 및 주기적 업데이트
setInterval(updateUptime, 1000);
setInterval(updateStats, 5000);
updateStats();
</script>
</body>
</html>"""


@app.route("/")
def index():
    # 🔑 기본 인증 확인 (선택적)
    api_key = request.args.get('api_key')
    token = request.args.get('token')

    if security_config.get("security", {}).get("require_auth", False):
        if not api_key and not token:
            return """
            <h1>🔒 소리새 AI 대시보드 - 인증 필요</h1>
            <p>접근하려면 올바른 API 키 또는 토큰이 필요합니다.</p>
            <form method="GET">
                <label>API 키: <input type="text" name="api_key" placeholder="API 키 입력"></label><br><br>
                <label>또는 토큰: <input type="text" name="token" placeholder="액세스 토큰 입력"></label><br><br>
                <button type="submit">🔓 접근</button>
            </form>
            """

        credential = api_key or token
        if not verify_api_key(credential) and not verify_token(credential):
            return "<h1>❌ 인증 실패</h1><p>유효하지 않은 인증 정보입니다.</p>"

    return render_template_string(HTML)


@app.route("/api/stats")
@require_auth("dashboard")
def api_stats():
    return jsonify(dashboard_state.get_stats())


@app.route("/api/auth/verify")
def verify_auth():
    """🔑 인증 정보 검증 API"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    token = request.headers.get('Authorization') or request.args.get('token')

    if not api_key and not token:
        return jsonify({"valid": False, "error": "인증 정보 없음"}), 401

    credential = api_key or token
    is_valid = verify_api_key(credential) or verify_token(credential)

    if is_valid:
        permissions = get_permission_level(credential)
        return jsonify({
            "valid": True,
            "permissions": permissions,
            "credential_type": "api_key" if verify_api_key(credential) else "token"
        })
    else:
        return jsonify({"valid": False, "error": "유효하지 않은 인증 정보"}), 401


@app.route("/api/auth/keys")
@require_auth("all")
def list_keys():
    """🔐 API 키 목록 (마스터 키만 접근 가능)"""
    return jsonify({
        "api_keys": list(security_config.get("security", {}).get("api_keys", {}).keys()),
        "tokens": list(security_config.get("security", {}).get("access_tokens", {}).keys())
    })


@socketio.on("remote_command")
def handle_remote_command(data):
    command = data.get('command', '')
    auth_credential = data.get('auth', '')  # 소켓에서 인증 정보 받기

    # 🔑 소켓 인증 검증
    if security_config.get("security", {}).get("require_auth", False):
        if not auth_credential:
            emit("auth_error", {"message": "인증이 필요합니다"})
            return

        if not verify_api_key(auth_credential) and not verify_token(auth_credential):
            emit("auth_error", {"message": "유효하지 않은 인증 정보"})
            return

        # 명령어 실행 권한 확인
        permissions = get_permission_level(auth_credential)
        if "commands" not in permissions and "all" not in permissions:
            emit("auth_error", {"message": "명령어 실행 권한이 없습니다"})
            return

    # 🔒 명령어 보안 검증
    allowed_commands = security_config.get("security", {}).get("allowed_commands", [])
    if command not in allowed_commands:
        print(f"🚫 허용되지 않은 명령어: {command}")
        emit("security_warning", {"message": f"허용되지 않은 명령어: {command}"})
        return

    print(f"📡 웹에서 원격 명령 수신: {command}")
    dashboard_state.add_voice_command(f"[원격] {command}")
    emit("voice_command", {"command": f"[원격] {command}", "status": "success"}, broadcast=True)


@socketio.on("get_stats")
def handle_get_stats():
    stats = dashboard_state.get_stats()
    emit("stats_update", stats)

# 🎵 음악 채팅 라우트


@app.route("/music-chat")
def music_chat():
    """음악 채팅 페이지"""
    if not music_chat_available:
        return jsonify({"error": "음악 채팅 시스템을 사용할 수 없습니다"}), 503

    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>🎵 음악 채팅방</title>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    </head>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: Arial, sans-serif;">
        <div id="chatContainer" style="max-width: 800px; margin: 20px auto; padding: 20px;">
            <h1>🎵 소리새 음악 채팅방</h1>
            <div id="roomList" style="margin: 20px 0;"></div>
            <div id="chatArea" style="display: none;">
                <div id="messages" style="height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin: 10px 0; background: rgba(255,255,255,0.1);"></div>
                <input type="text" id="messageInput" placeholder="메시지를 입력하세요..." style="width: 70%; padding: 10px;">
                <button onclick="sendMessage()">전송</button>
                <button onclick="leaveRoom()">나가기</button>
            </div>
        </div>

        <script>
            const socket = io();
            let currentRoom = null;
            let currentUser = null;

            // 방 목록 로드
            function loadRooms() {
                fetch('/api/music-chat/rooms')
                    .then(r => r.json())
                    .then(rooms => {
                        const roomList = document.getElementById('roomList');
                        roomList.innerHTML = '<h3>채팅방 목록</h3>';
                        rooms.forEach(room => {
                            roomList.innerHTML += `
                                <div style="margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.2); border-radius: 5px;">
                                    <strong>${room.name}</strong> (${room.user_count}명)
                                    <button onclick="joinRoom('${room.id}', '${room.name}')">참여</button>
                                </div>
                            `;
                        });
                        roomList.innerHTML += `
                            <div style="margin: 20px 0;">
                                <input type="text" id="newRoomName" placeholder="새 방 이름">
                                <button onclick="createRoom()">방 만들기</button>
                            </div>
                        `;
                    });
            }

            function createRoom() {
                const name = document.getElementById('newRoomName').value;
                if (!name) return;

                fetch('/api/music-chat/create-room', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                }).then(() => loadRooms());
            }

            function joinRoom(roomId, roomName) {
                const username = prompt('사용자 이름을 입력하세요:');
                if (!username) return;

                currentRoom = roomId;
                currentUser = username;

                fetch('/api/music-chat/join-room', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_id: roomId, username: username})
                }).then(() => {
                    document.getElementById('roomList').style.display = 'none';
                    document.getElementById('chatArea').style.display = 'block';
                    socket.emit('join_room', {room_id: roomId, username: username});
                });
            }

            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (!input.value || !currentRoom) return;

                socket.emit('send_message', {
                    room_id: currentRoom,
                    message: input.value
                });
                input.value = '';
            }

            function leaveRoom() {
                if (currentRoom) {
                    socket.emit('leave_room', {room_id: currentRoom});
                    currentRoom = null;
                    currentUser = null;
                    document.getElementById('roomList').style.display = 'block';
                    document.getElementById('chatArea').style.display = 'none';
                    loadRooms();
                }
            }

            // 소켓 이벤트
            socket.on('new_message', (data) => {
                const messages = document.getElementById('messages');
                messages.innerHTML += `<div><strong>${data.username}:</strong> ${data.message}</div>`;
                messages.scrollTop = messages.scrollHeight;
            });

            // 페이지 로드 시 방 목록 로드
            loadRooms();
        </script>
    </body>
    </html>
    """


@app.route("/api/music-chat/rooms")
def get_chat_rooms():
    """채팅방 목록 API"""
    if not music_chat_system:
        return jsonify([])

    rooms = music_chat_system.list_rooms()
    return jsonify([{
        "id": room_id,
        "name": room.name,
        "user_count": len(room.current_users),
        "created_at": room.created_at.strftime("%Y-%m-%d %H:%M")
    } for room_id, room in rooms.items()])


@app.route("/api/music-chat/create-room", methods=["POST"])
def create_chat_room():
    """채팅방 생성 API"""
    if not music_chat_system:
        return jsonify({"error": "채팅 시스템 사용 불가"}), 503

    data = request.json
    room_name = data.get("name", "새 방")
    room_id = music_chat_system.create_room(room_name)
    return jsonify({"room_id": room_id, "status": "created"})


@app.route("/api/music-chat/join-room", methods=["POST"])
def join_chat_room():
    """채팅방 참여 API"""
    if not music_chat_system:
        return jsonify({"error": "채팅 시스템 사용 불가"}), 503

    data = request.json
    room_id = data.get("room_id")
    username = data.get("username")

    success = music_chat_system.join_room(room_id, username)
    return jsonify({"success": success})

# 🎵 음악 채팅 소켓 이벤트


@socketio.on("join_room")
def handle_join_room(data):
    """채팅방 입장"""
    if music_chat_system:
        room_id = data.get("room_id")
        username = data.get("username")
        music_chat_system.join_room(room_id, username)
        emit("room_joined", {"room_id": room_id}, room=room_id)


@socketio.on("leave_room")
def handle_leave_room(data):
    """채팅방 나가기"""
    if music_chat_system:
        room_id = data.get("room_id")
        emit("room_left", {"room_id": room_id}, room=room_id)


@socketio.on("send_message")
def handle_send_message(data):
    """메시지 전송"""
    if music_chat_system:
        room_id = data.get("room_id")
        message = data.get("message")
        username = data.get("username", "익명")

        # 메시지 저장 및 브로드캐스트
        music_chat_system.send_message(room_id, username, message)
        emit("new_message", {
            "username": username,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M")
        }, room=room_id)


def broadcast_voice_command(command, status="success"):
    """음성 명령을 대시보드에 브로드캐스트"""
    dashboard_state.add_voice_command(command, status)
    socketio.emit("voice_command", {"command": command, "status": status})


def broadcast_system_status(status):
    """시스템 상태를 대시보드에 브로드캐스트"""
    dashboard_state.set_system_status(status)
    socketio.emit("system_status", {"status": status})


def broadcast_persona_change(persona):
    """🎭 페르소나 변경을 대시보드에 브로드캐스트"""
    dashboard_state.update_persona(persona)


def broadcast_creative_activity(activity_type, description):
    """🎨 창의적 활동을 대시보드에 브로드캐스트"""
    dashboard_state.add_creative_activity(activity_type, description)


def run_dashboard():
    print("🌍 웹 대시보드 실행 중... (http://localhost:5050)")
    print("🔒 보안 모드: 로컬호스트만 접근 허용")
    socketio.run(app, host="127.0.0.1", port=5050, debug=False)  # 보안: 로컬호스트만 허용
