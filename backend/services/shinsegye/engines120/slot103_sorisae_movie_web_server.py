#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 소리새 4D 영화 제작 웹 서버
모바일과 데스크톱에서 모두 접근 가능한 웹 기반 영화 제작 시스템
"""

import os
import threading
from datetime import datetime

try:
    from flask import Flask, jsonify, render_template, request, send_file
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    import qrcode  # type: ignore
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# 소리새 애니메이션 스튜디오 import
try:
    from sorisae_animation_studio_ultra import SorisaeAnimationStudio
    STUDIO_AVAILABLE = True
except ImportError:
    STUDIO_AVAILABLE = False


class SorisaeMovieWebServer:
    """소리새 4D 영화 제작 웹 서버"""

    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.secret_key = 'sorisae_movie_studio_2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # 애니메이션 스튜디오 초기화
        if STUDIO_AVAILABLE:
            self.studio = SorisaeAnimationStudio()
        else:
            self.studio = None

        self.current_projects = {}
        self.setup_routes()
        self.setup_socketio()

        # 출력 디렉토리 생성
        os.makedirs('static/movies', exist_ok=True)
        os.makedirs('static/downloads', exist_ok=True)
        os.makedirs('templates', exist_ok=True)

        self.create_web_templates()

    def setup_routes(self):
        """웹 라우트 설정"""

        @self.app.route('/')
        def index():
            """메인 페이지"""
            return render_template('index.html')

        @self.app.route('/mobile')
        def mobile():
            """모바일 전용 페이지"""
            return render_template('mobile.html')

        @self.app.route('/create_movie', methods=['POST'])
        def create_movie():
            """영화 제작 API"""
            try:
                data = request.get_json()
                scenario = data.get('scenario', '')
                title = data.get('title', 'Untitled Movie')
                quality = data.get('quality', '4D')
                include_theme_song = data.get('include_theme_song', True)

                if not scenario:
                    return jsonify({'error': '시나리오를 입력해주세요.'}), 400

                # 프로젝트 ID 생성
                project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # 백그라운드에서 영화 제작
                threading.Thread(
                    target=self.create_movie_background,
                    args=(project_id, scenario, title, quality, include_theme_song)
                ).start()

                return jsonify({
                    'success': True,
                    'project_id': project_id,
                    'message': '영화 제작이 시작되었습니다.'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/project_status/<project_id>')
        def project_status(project_id):
            """프로젝트 상태 확인"""
            project = self.current_projects.get(project_id, {})
            return jsonify(project)

        @self.app.route('/download/<project_id>')
        def download_movie(project_id):
            """영화 다운로드"""
            project = self.current_projects.get(project_id, {})
            if project.get('status') == 'completed' and project.get('movie_file'):
                return send_file(project['movie_file'], as_attachment=True)
            else:
                return jsonify({'error': '영화가 아직 완성되지 않았습니다.'}), 404

        @self.app.route('/qr_code')
        def generate_qr():
            """모바일 접속용 QR 코드 생성"""
            if not QR_AVAILABLE:
                return "QR 코드 라이브러리가 없습니다."

            # 서버 URL
            server_url = f"http://{self.get_local_ip()}:{self.port}/mobile"

            # QR 코드 생성
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(server_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            qr_path = "static/qr_code.png"
            img.save(qr_path)

            return send_file(qr_path)

    def setup_socketio(self):
        """WebSocket 설정"""

        @self.socketio.on('connect')
        def handle_connect():
            print(f"클라이언트 연결됨: {request.sid}")
            emit('status', {'message': '서버에 연결되었습니다.'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"클라이언트 연결 해제됨: {request.sid}")

    def create_movie_background(self, project_id, scenario, title, quality, include_theme_song):
        """백그라운드에서 영화 제작"""
        try:
            # 프로젝트 상태 초기화
            self.current_projects[project_id] = {
                'status': 'in_progress',
                'progress': 0,
                'message': '영화 제작 시작...',
                'title': title,
                'quality': quality
            }

            # 진행 상황 업데이트

            def update_progress(progress, message):
                self.current_projects[project_id].update({
                    'progress': progress,
                    'message': message
                })
                self.socketio.emit('progress_update', {
                    'project_id': project_id,
                    'progress': progress,
                    'message': message
                })

            update_progress(10, '시나리오 분석 중...')

            if not self.studio:
                raise Exception("애니메이션 스튜디오를 초기화할 수 없습니다.")

            update_progress(20, '캐릭터 생성 중...')

            # 영화 제작
            project = self.studio.create_movie_from_scenario(
                scenario_text=scenario,
                movie_title=title,
                quality=quality,
                include_theme_song=include_theme_song
            )

            update_progress(80, '최종 편집 중...')

            # 결과 파일 경로
            movie_file = f"static/movies/{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

            # 프로젝트 완료
            self.current_projects[project_id].update({
                'status': 'completed',
                'progress': 100,
                'message': '영화 제작 완료!',
                'movie_file': movie_file,
                'project_data': {
                    'title': project.title,
                    'duration': f"{project.total_duration // 3600}시간 {(project.total_duration % 3600) // 60}분",
                    'scenes': len(project.scenes),
                    'characters': len(project.characters),
                    'quality': project.visual_quality
                }
            })

            update_progress(100, f'✅ 4D 영화 "{title}" 제작 완료!')

        except Exception as e:
            self.current_projects[project_id].update({
                'status': 'error',
                'progress': 0,
                'message': f'오류 발생: {str(e)}'
            })
            self.socketio.emit('error', {
                'project_id': project_id,
                'error': str(e)
            })

    def create_web_templates(self):
        """웹 템플릿 생성"""

        # 메인 페이지 템플릿
        index_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 소리새 4D 영화 제작 스튜디오</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            background: rgba(255,255,255,0.9);
            color: #333;
        }
        textarea {
            height: 200px;
            resize: vertical;
        }
        button {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 25px;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .progress-container {
            display: none;
            margin-top: 20px;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: rgba(255,255,255,0.2);
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4ECDC4, #44A08D);
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .qr-section {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .result-section {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: rgba(0,255,0,0.1);
            border-radius: 10px;
            border: 2px solid rgba(0,255,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬✨ 소리새 4D 영화 제작 스튜디오</h1>

        <div class="features">
            <div class="feature">
                <h3>🌪️ 4D 체감효과</h3>
                <p>바람, 물, 진동, 향기, 온도를 모두 느낄 수 있는 영화</p>
            </div>
            <div class="feature">
                <h3>🎭 AI 자동 제작</h3>
                <p>시나리오만 입력하면 1시간 50분 영화 자동 완성</p>
            </div>
            <div class="feature">
                <h3>🎵 전용 주제곡</h3>
                <p>영화에 맞는 오리지널 주제곡과 변주곡 생성</p>
            </div>
            <div class="feature">
                <h3>📱 모바일 지원</h3>
                <p>PC와 모바일에서 모두 사용 가능</p>
            </div>
        </div>

        <form id="movieForm">
            <div class="form-group">
                <label for="title">🎬 영화 제목:</label>
                <input type="text" id="title" name="title" placeholder="예: 신비한 모험" required>
            </div>

            <div class="form-group">
                <label for="quality">🎨 품질 선택:</label>
                <select id="quality" name="quality">
                    <option value="4D">🌪️ 4D (Ultra HD + 체감효과)</option>
                    <option value="Ultra">⭐ Ultra HD</option>
                    <option value="8K">📺 8K</option>
                    <option value="4K">🎥 4K</option>
                </select>
            </div>

            <div class="form-group">
                <label for="scenario">📝 시나리오:</label>
                <textarea id="scenario" name="scenario" placeholder="시나리오를 입력하세요...

예시:
장면 1: 아침의 시작
주인공이 침실에서 일어난다.
주인공: 좋은 아침이야!

장면 2: 모험의 시작
정원에서 신비한 보물을 발견한다.
주인공: 이게 뭐지? 신기해!" required></textarea>
            </div>

            <button type="submit">🎬 4D 영화 제작 시작!</button>
        </form>

        <div class="progress-container" id="progressContainer">
            <h3>🎬 영화 제작 진행 상황</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <p id="progressMessage">제작 대기 중...</p>
        </div>

        <div class="result-section" id="resultSection">
            <h3>🎊 영화 제작 완료!</h3>
            <div id="movieInfo"></div>
            <button id="downloadBtn" onclick="downloadMovie()">📥 영화 다운로드</button>
        </div>

        <div class="qr-section">
            <h3>📱 모바일에서 접속하기</h3>
            <p>모바일 기기로 QR 코드를 스캔하세요</p>
            <img src="/qr_code" alt="QR Code" style="max-width: 200px;">
        </div>
    </div>

    <script>
        const socket = io();
        let currentProjectId = null;

        // 폼 제출 처리
        document.getElementById('movieForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                title: document.getElementById('title').value,
                quality: document.getElementById('quality').value,
                scenario: document.getElementById('scenario').value,
                include_theme_song: true
            };

            try {
                const response = await fetch('/create_movie', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    currentProjectId = result.project_id;
                    document.getElementById('progressContainer').style.display = 'block';
                    document.getElementById('resultSection').style.display = 'none';
                } else {
                    alert('오류: ' + result.error);
                }
            } catch (error) {
                alert('영화 제작 요청 실패: ' + error.message);
            }
        });

        // 진행 상황 업데이트
        socket.on('progress_update', (data) => {
            if (data.project_id === currentProjectId) {
                const progressFill = document.getElementById('progressFill');
                const progressMessage = document.getElementById('progressMessage');

                progressFill.style.width = data.progress + '%';
                progressFill.textContent = data.progress + '%';
                progressMessage.textContent = data.message;

                if (data.progress === 100) {
                    setTimeout(checkProjectCompletion, 1000);
                }
            }
        });

        // 프로젝트 완료 확인
        async function checkProjectCompletion() {
            if (!currentProjectId) return;

            try {
                const response = await fetch(`/project_status/${currentProjectId}`);
                const project = await response.json();

                if (project.status === 'completed') {
                    const movieInfo = document.getElementById('movieInfo');
                    movieInfo.innerHTML = `
                        <p><strong>제목:</strong> ${project.project_data.title}</p>
                        <p><strong>길이:</strong> ${project.project_data.duration}</p>
                        <p><strong>장면 수:</strong> ${project.project_data.scenes}개</p>
                        <p><strong>캐릭터 수:</strong> ${project.project_data.characters}명</p>
                        <p><strong>품질:</strong> ${project.project_data.quality}</p>
                    `;
                    document.getElementById('resultSection').style.display = 'block';
                }
            } catch (error) {
                console.error('프로젝트 상태 확인 실패:', error);
            }
        }

        // 영화 다운로드
        function downloadMovie() {
            if (currentProjectId) {
                window.location.href = `/download/${currentProjectId}`;
            }
        }

        // 소켓 이벤트 처리
        socket.on('status', (data) => {
            console.log('서버 상태:', data.message);
        });

        socket.on('error', (data) => {
            alert('오류 발생: ' + data.error);
            document.getElementById('progressContainer').style.display = 'none';
        });
    </script>
</body>
</html>
        """

        # 모바일 페이지 템플릿
        mobile_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📱 소리새 4D 영화 제작 (모바일)</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            font-size: 16px;
        }
        .container {
            max-width: 100%;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            font-size: 14px;
        }
        input, textarea, select {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            background: rgba(255,255,255,0.9);
            color: #333;
            box-sizing: border-box;
            -webkit-appearance: none;
        }
        textarea {
            height: 150px;
            resize: vertical;
        }
        button {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            border: none;
            padding: 18px;
            font-size: 16px;
            border-radius: 25px;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            font-weight: bold;
        }
        .features {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 20px 0;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-size: 12px;
        }
        .progress-container {
            display: none;
            margin-top: 20px;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 25px;
            background: rgba(255,255,255,0.2);
            border-radius: 12px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4ECDC4, #44A08D);
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }
        .result-section {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: rgba(0,255,0,0.1);
            border-radius: 10px;
            border: 2px solid rgba(0,255,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱🎬 소리새 4D 영화 제작</h1>

        <div class="features">
            <div class="feature">
                <h4>🌪️ 4D 효과</h4>
                <small>체감형 영화</small>
            </div>
            <div class="feature">
                <h4>🤖 AI 제작</h4>
                <small>자동 완성</small>
            </div>
            <div class="feature">
                <h4>🎵 주제곡</h4>
                <small>오리지널 음악</small>
            </div>
            <div class="feature">
                <h4>⏱️ 1시간50분</h4>
                <small>장편 영화</small>
            </div>
        </div>

        <form id="mobileMovieForm">
            <div class="form-group">
                <label for="mobileTitle">🎬 영화 제목:</label>
                <input type="text" id="mobileTitle" placeholder="제목 입력" required>
            </div>

            <div class="form-group">
                <label for="mobileQuality">🎨 품질:</label>
                <select id="mobileQuality">
                    <option value="4D">🌪️ 4D</option>
                    <option value="Ultra">⭐ Ultra</option>
                    <option value="4K">🎥 4K</option>
                </select>
            </div>

            <div class="form-group">
                <label for="mobileScenario">📝 시나리오:</label>
                <textarea id="mobileScenario" placeholder="간단한 시나리오를 입력하세요..." required></textarea>
            </div>

            <button type="submit">🎬 영화 만들기!</button>
        </form>

        <div class="progress-container" id="mobileProgressContainer">
            <h4>🎬 제작 중...</h4>
            <div class="progress-bar">
                <div class="progress-fill" id="mobileProgressFill">0%</div>
            </div>
            <p id="mobileProgressMessage" style="font-size:14px;">대기 중...</p>
        </div>

        <div class="result-section" id="mobileResultSection">
            <h4>🎊 완성!</h4>
            <div id="mobileMovieInfo"></div>
            <button onclick="downloadMobileMovie()">📥 다운로드</button>
        </div>
    </div>

    <script>
        const socket = io();
        let currentProjectId = null;

        document.getElementById('mobileMovieForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                title: document.getElementById('mobileTitle').value,
                quality: document.getElementById('mobileQuality').value,
                scenario: document.getElementById('mobileScenario').value,
                include_theme_song: true
            };

            try {
                const response = await fetch('/create_movie', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    currentProjectId = result.project_id;
                    document.getElementById('mobileProgressContainer').style.display = 'block';
                } else {
                    alert('오류: ' + result.error);
                }
            } catch (error) {
                alert('요청 실패: ' + error.message);
            }
        });

        socket.on('progress_update', (data) => {
            if (data.project_id === currentProjectId) {
                const progressFill = document.getElementById('mobileProgressFill');
                const progressMessage = document.getElementById('mobileProgressMessage');

                progressFill.style.width = data.progress + '%';
                progressFill.textContent = data.progress + '%';
                progressMessage.textContent = data.message;

                if (data.progress === 100) {
                    setTimeout(checkMobileCompletion, 1000);
                }
            }
        });

        async function checkMobileCompletion() {
            try {
                const response = await fetch(`/project_status/${currentProjectId}`);
                const project = await response.json();

                if (project.status === 'completed') {
                    document.getElementById('mobileMovieInfo').innerHTML = `
                        <p><strong>${project.project_data.title}</strong></p>
                        <p>길이: ${project.project_data.duration}</p>
                        <p>품질: ${project.project_data.quality}</p>
                    `;
                    document.getElementById('mobileResultSection').style.display = 'block';
                }
            } catch (error) {
                console.error('확인 실패:', error);
            }
        }

        function downloadMobileMovie() {
            if (currentProjectId) {
                window.location.href = `/download/${currentProjectId}`;
            }
        }
    </script>
</body>
</html>
        """

        # 템플릿 파일 저장
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write(index_html)

        with open('templates/mobile.html', 'w', encoding='utf-8') as f:
            f.write(mobile_html)

    def get_local_ip(self):
        """로컬 IP 주소 가져오기"""
        import socket
        try:
            # 임시 소켓을 만들어 IP 확인
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def run(self):
        """웹 서버 실행"""
        if not FLASK_AVAILABLE:
            print("❌ Flask가 설치되지 않았습니다.")
            print("다음 명령어로 설치하세요: pip install flask flask-socketio")
            return

        local_ip = self.get_local_ip()

        print("🌐 소리새 4D 영화 제작 웹 서버 시작!")
        print("=" * 60)
        print(f"🖥️  데스크톱 접속: http://localhost:{self.port}")
        print(f"🖥️  데스크톱 접속: http://{local_ip}:{self.port}")
        print(f"📱 모바일 접속: http://{local_ip}:{self.port}/mobile")
        print(f"📱 QR 코드: http://{local_ip}:{self.port}/qr_code")
        print("=" * 60)
        print("🎬 브라우저에서 위 주소로 접속하여 4D 영화를 제작하세요!")
        print("📱 모바일에서는 QR 코드를 스캔하여 접속하세요!")

        try:
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 서버를 종료합니다.")


def main():
    """메인 실행 함수"""
    server = SorisaeMovieWebServer()
    server.run()


if __name__ == "__main__":
    main()
