#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤🎬 소리새 4D 영화 제작 웹 서버 (음성 명령 기능 포함)
소리새와 같은 음성 인식 및 TTS 기능이 통합된 웹 기반 영화 제작 시스템
"""

import os
import socket
import threading
from datetime import datetime

# 음성 인식 및 TTS 라이브러리
try:
    import pyttsx3
    import speech_recognition as sr
    from gtts import gTTS  # type: ignore
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

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


class SorisaeVoiceMovieServer:
    """소리새 음성 명령 4D 영화 제작 웹 서버"""

    def __init__(self, host='0.0.0.0', port=5050):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.secret_key = 'sorisae_voice_movie_studio_2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # 음성 시스템 초기화
        self.init_voice_system()

        # 애니메이션 스튜디오 초기화
        if STUDIO_AVAILABLE:
            self.studio = SorisaeAnimationStudio()
        else:
            self.studio = None

        self.current_projects = {}
        self.voice_recognition_active = False

        self.setup_routes()
        self.setup_socketio()

        # 출력 디렉토리 생성
        os.makedirs('static/movies', exist_ok=True)
        os.makedirs('static/downloads', exist_ok=True)
        os.makedirs('static/audio', exist_ok=True)
        os.makedirs('templates', exist_ok=True)

        self.create_voice_web_templates()

    def init_voice_system(self):
        """음성 시스템 초기화"""
        if VOICE_AVAILABLE:
            try:
                # 음성 인식기 초기화
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()

                # TTS 엔진 초기화
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)

                # 한국어 음성 설정 시도
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if 'korean' in voice.name.lower() or 'ko' in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break

                print("✅ 소리새 음성 시스템 초기화 완료!")

            except Exception as e:
                print(f"⚠️ 음성 시스템 초기화 실패: {e}")
        else:
            print("⚠️ 음성 라이브러리가 설치되지 않았습니다.")

    def setup_routes(self):
        """웹 라우트 설정"""

        @self.app.route('/')
        def index():
            """메인 페이지 (음성 기능 포함)"""
            return render_template('voice_index.html')

        @self.app.route('/mobile')
        def mobile():
            """모바일 전용 페이지 (음성 기능 포함)"""
            return render_template('voice_mobile.html')

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

                # 음성 확인
                self.speak_text(f"영화 {title} 제작을 시작합니다.")

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

        @self.app.route('/voice_command', methods=['POST'])
        def voice_command():
            """음성 명령 처리"""
            try:
                if not VOICE_AVAILABLE:
                    return jsonify({'error': '음성 기능을 사용할 수 없습니다.'}), 400

                # 음성 인식 시작
                command = self.listen_for_command()

                if command:
                    response = self.process_voice_command(command)
                    return jsonify({
                        'success': True,
                        'command': command,
                        'response': response
                    })
                else:
                    return jsonify({'error': '음성을 인식할 수 없습니다.'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/speak', methods=['POST'])
        def speak():
            """텍스트 음성 변환"""
            try:
                data = request.get_json()
                text = data.get('text', '')

                if text:
                    self.speak_text(text)
                    return jsonify({'success': True})
                else:
                    return jsonify({'error': '텍스트가 없습니다.'}), 400

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
            emit('status', {'message': '소리새 음성 4D 영화 제작 시스템에 연결되었습니다.'})

            # 음성으로 환영 인사
            if VOICE_AVAILABLE:
                self.speak_text("소리새 4D 영화 제작 시스템에 오신 것을 환영합니다!")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"클라이언트 연결 해제됨: {request.sid}")

        @self.socketio.on('start_voice_recognition')
        def handle_voice_recognition():
            """음성 인식 시작"""
            if VOICE_AVAILABLE and not self.voice_recognition_active:
                threading.Thread(target=self.continuous_voice_recognition).start()
                emit('voice_status', {'status': 'listening', 'message': '음성 명령을 기다리고 있습니다...'})

        @self.socketio.on('stop_voice_recognition')
        def handle_stop_voice():
            """음성 인식 중지"""
            self.voice_recognition_active = False
            emit('voice_status', {'status': 'stopped', 'message': '음성 인식을 중지했습니다.'})

    def listen_for_command(self, timeout=5):
        """음성 명령 듣기"""
        if not VOICE_AVAILABLE:
            return None

        try:
            with self.microphone as source:
                print("🎤 음성 명령을 기다리고 있습니다...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=timeout)

            # 한국어 음성 인식
            command = self.recognizer.recognize_google(audio, language='ko-KR')
            print(f"🎤 인식된 명령: {command}")
            return command

        except sr.WaitTimeoutError:
            print("⏰ 음성 인식 타임아웃")
            return None
        except sr.UnknownValueError:
            print("❓ 음성을 인식할 수 없습니다")
            return None
        except sr.RequestError as e:
            print(f"❌ 음성 인식 서비스 오류: {e}")
            return None

    def process_voice_command(self, command):
        """음성 명령 처리"""
        command_lower = command.lower()

        # 영화 제작 관련 명령
        if '영화' in command_lower and ('만들' in command_lower or '제작' in command_lower):
            response = "영화 제작을 시작하겠습니다. 제목과 시나리오를 입력해주세요."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'start_movie_creation',
                'response': response
            })

        elif '시나리오' in command_lower:
            response = "시나리오 입력 창을 활성화합니다."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'focus_scenario',
                'response': response
            })

        elif '4D' in command_lower or '4d' in command_lower:
            response = "4D 품질로 설정합니다. 바람, 물, 진동, 향기, 온도 효과가 포함됩니다."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'set_4d_quality',
                'response': response
            })

        elif '주제곡' in command_lower:
            response = "주제곡 포함 옵션을 활성화합니다."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'enable_theme_song',
                'response': response
            })

        elif '도움' in command_lower or '명령' in command_lower:
            response = """사용 가능한 음성 명령:
- '영화 만들어줘': 영화 제작 시작
- '시나리오': 시나리오 입력 창 활성화
- '4D로 설정해줘': 4D 품질 선택
- '주제곡 포함해줘': 주제곡 옵션 활성화
- '상태 확인해줘': 현재 진행 상황 확인"""
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'show_help',
                'response': response
            })

        elif '상태' in command_lower:
            active_projects = len([p for p in self.current_projects.values() if p.get('status') == 'in_progress'])
            response = f"현재 {active_projects}개의 영화가 제작 중입니다."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'show_status',
                'response': response
            })

        else:
            response = f"'{command}' 명령을 이해할 수 없습니다. '도움말'이라고 말해보세요."
            self.socketio.emit('voice_command_result', {
                'command': command,
                'action': 'unknown',
                'response': response
            })

        # 음성으로 응답
        self.speak_text(response)
        return response

    def speak_text(self, text):
        """텍스트를 음성으로 변환"""
        if not VOICE_AVAILABLE:
            return

        try:
            # pyttsx3로 한국어 TTS 시도
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

        except Exception as e:
            print(f"⚠️ TTS 오류: {e}")
            try:
                # gTTS로 대체 시도
                tts = gTTS(text=text, lang='ko')
                audio_file = f"static/audio/tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                tts.save(audio_file)

                # 클라이언트에 오디오 파일 전송
                self.socketio.emit('play_audio', {'audio_url': f"/{audio_file}"})

            except Exception as e2:
                print(f"⚠️ gTTS 오류: {e2}")

    def continuous_voice_recognition(self):
        """지속적인 음성 인식"""
        self.voice_recognition_active = True

        while self.voice_recognition_active:
            try:
                command = self.listen_for_command(timeout=3)
                if command:
                    self.process_voice_command(command)

            except Exception as e:
                print(f"⚠️ 지속적 음성 인식 오류: {e}")
                break

        self.voice_recognition_active = False

    def create_movie_background(self, project_id, scenario, title, quality, include_theme_song):
        """백그라운드에서 영화 제작 (음성 피드백 포함)"""
        try:
            # 프로젝트 상태 초기화
            self.current_projects[project_id] = {
                'status': 'in_progress',
                'progress': 0,
                'message': '영화 제작 시작...',
                'title': title,
                'quality': quality
            }

            # 진행 상황 업데이트 (음성 포함)

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

                # 주요 단계에서 음성 피드백
                if progress in [20, 50, 80]:
                    self.speak_text(message)

            update_progress(10, '시나리오 분석 중...')

            if not self.studio:
                raise Exception("애니메이션 스튜디오를 초기화할 수 없습니다.")

            update_progress(20, '캐릭터 생성 중...')
            update_progress(40, '4D 효과 분석 중...')
            update_progress(60, '렌더링 진행 중...')

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

            update_progress(100, f'4D 영화 {title} 제작이 완료되었습니다!')

            # 완료 음성 알림
            self.speak_text(f"영화 {title} 제작이 성공적으로 완료되었습니다. 다운로드할 수 있습니다.")

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

            # 오류 음성 알림
            self.speak_text(f"영화 제작 중 오류가 발생했습니다: {str(e)}")

    def create_voice_web_templates(self):
        """음성 기능이 포함된 웹 템플릿 생성"""

        # 메인 페이지 템플릿 (음성 기능 포함)
        voice_index_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤🎬 소리새 음성 4D 영화 제작 스튜디오</title>
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
        .voice-controls {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            border: 2px solid rgba(255,255,255,0.2);
        }
        .voice-button {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 25px;
            cursor: pointer;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .voice-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .voice-button.active {
            background: linear-gradient(45deg, #4ECDC4, #44A08D);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(76, 205, 196, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(76, 205, 196, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 205, 196, 0); }
        }
        .voice-status {
            margin-top: 15px;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            font-size: 14px;
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
            box-sizing: border-box;
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
        .result-section {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: rgba(0,255,0,0.1);
            border-radius: 10px;
            border: 2px solid rgba(0,255,0,0.3);
        }
        .qr-section {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        .voice-command-help {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤🎬 소리새 음성 4D 영화 제작 스튜디오</h1>

        <!-- 음성 제어 패널 -->
        <div class="voice-controls">
            <h3>🎤 소리새 음성 명령</h3>
            <button id="voiceBtn" class="voice-button" onclick="toggleVoiceRecognition()">
                🎤 음성 명령 시작
            </button>
            <button class="voice-button" onclick="speakHelp()">
                📢 도움말 듣기
            </button>
            <div class="voice-status" id="voiceStatus">
                음성 명령 기능이 준비되었습니다. 버튼을 클릭하여 시작하세요.
            </div>

            <div class="voice-command-help">
                <strong>🎤 음성 명령어:</strong><br>
                • "영화 만들어줘" - 영화 제작 시작<br>
                • "시나리오" - 시나리오 입력창 활성화<br>
                • "4D로 설정해줘" - 4D 품질 선택<br>
                • "주제곡 포함해줘" - 주제곡 옵션 활성화<br>
                • "상태 확인해줘" - 진행 상황 확인<br>
                • "도움말" - 사용 가능한 명령어 안내
            </div>
        </div>

        <div class="features">
            <div class="feature">
                <h3>🎤 음성 명령</h3>
                <p>소리새와 같은 음성 인식 및 TTS 기능</p>
            </div>
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
                <textarea id="scenario" name="scenario" placeholder="시나리오를 입력하거나 음성으로 말해주세요..." required></textarea>
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
        let voiceRecognitionActive = false;

        // 소켓 이벤트 처리
        socket.on('connect', () => {
            console.log('소리새 음성 시스템에 연결됨');
        });

        socket.on('status', (data) => {
            console.log('서버 상태:', data.message);
        });

        socket.on('voice_status', (data) => {
            document.getElementById('voiceStatus').textContent = data.message;

            const voiceBtn = document.getElementById('voiceBtn');
            if (data.status === 'listening') {
                voiceBtn.classList.add('active');
                voiceBtn.textContent = '🎤 음성 명령 중지';
                voiceRecognitionActive = true;
            } else {
                voiceBtn.classList.remove('active');
                voiceBtn.textContent = '🎤 음성 명령 시작';
                voiceRecognitionActive = false;
            }
        });

        socket.on('voice_command_result', (data) => {
            console.log('음성 명령 결과:', data);

            // 명령에 따른 UI 업데이트
            switch(data.action) {
                case 'start_movie_creation':
                    // 영화 제작 섹션으로 스크롤
                    document.getElementById('movieForm').scrollIntoView({behavior: 'smooth'});
                    break;
                case 'focus_scenario':
                    document.getElementById('scenario').focus();
                    break;
                case 'set_4d_quality':
                    document.getElementById('quality').value = '4D';
                    break;
                case 'show_help':
                    alert(data.response);
                    break;
            }

            document.getElementById('voiceStatus').textContent = `명령: "${data.command}" - ${data.response}`;
        });

        socket.on('play_audio', (data) => {
            const audio = new Audio(data.audio_url);
            audio.play().catch(e => console.log('오디오 재생 실패:', e));
        });

        // 음성 인식 토글
        function toggleVoiceRecognition() {
            if (voiceRecognitionActive) {
                socket.emit('stop_voice_recognition');
            } else {
                socket.emit('start_voice_recognition');
            }
        }

        // 도움말 음성 출력
        function speakHelp() {
            fetch('/speak', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    text: '소리새 음성 4D 영화 제작 시스템입니다. 영화 만들어줘, 시나리오, 4D로 설정해줘, 주제곡 포함해줘, 상태 확인해줘, 도움말 등의 명령을 사용할 수 있습니다.'
                })
            });
        }

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
                    headers: {'Content-Type': 'application/json'},
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

        // 오류 처리
        socket.on('error', (data) => {
            alert('오류 발생: ' + data.error);
            document.getElementById('progressContainer').style.display = 'none';
        });
    </script>
</body>
</html>"""

        # 모바일 페이지 템플릿 (음성 기능 포함)
        voice_mobile_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤📱 소리새 음성 4D 영화 제작</title>
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
        .voice-controls {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }
        .voice-button {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            border: none;
            padding: 15px;
            font-size: 14px;
            border-radius: 25px;
            cursor: pointer;
            margin: 5px;
            width: calc(50% - 10px);
            font-weight: bold;
        }
        .voice-button.active {
            background: linear-gradient(45deg, #4ECDC4, #44A08D);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(76, 205, 196, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(76, 205, 196, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 205, 196, 0); }
        }
        .voice-status {
            margin-top: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            font-size: 12px;
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
            height: 120px;
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
            margin-top: 15px;
            font-weight: bold;
        }
        .features {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            font-size: 11px;
        }
        .progress-container {
            display: none;
            margin-top: 15px;
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
        .voice-commands {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 10px;
            margin-top: 15px;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤📱 소리새 음성 4D 영화</h1>

        <!-- 모바일 음성 제어 -->
        <div class="voice-controls">
            <h4>🎤 음성 명령</h4>
            <button id="mobileVoiceBtn" class="voice-button" onclick="toggleMobileVoice()">
                🎤 음성 시작
            </button>
            <button class="voice-button" onclick="speakMobileHelp()">
                📢 도움말
            </button>
            <div class="voice-status" id="mobileVoiceStatus">
                음성 명령 준비됨
            </div>

            <div class="voice-commands">
                <strong>음성 명령어:</strong><br>
                "영화 만들어줘" / "4D로 설정" / "상태 확인" / "도움말"
            </div>
        </div>

        <div class="features">
            <div class="feature">
                <h4>🎤 음성인식</h4>
                <small>소리새 음성기능</small>
            </div>
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
        </div>

        <form id="mobileMovieForm">
            <div class="form-group">
                <label for="mobileTitle">🎬 영화 제목:</label>
                <input type="text" id="mobileTitle" placeholder="제목 입력 또는 음성으로" required>
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
                <textarea id="mobileScenario" placeholder="시나리오 입력 또는 음성으로 말하기..." required></textarea>
            </div>

            <button type="submit">🎬 음성 4D 영화 만들기!</button>
        </form>

        <div class="progress-container" id="mobileProgressContainer">
            <h4>🎬 제작 중...</h4>
            <div class="progress-bar">
                <div class="progress-fill" id="mobileProgressFill">0%</div>
            </div>
            <p id="mobileProgressMessage" style="font-size:12px;">대기 중...</p>
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
        let mobileVoiceActive = false;

        socket.on('connect', () => {
            console.log('모바일 음성 시스템 연결됨');
        });

        socket.on('voice_status', (data) => {
            document.getElementById('mobileVoiceStatus').textContent = data.message;

            const voiceBtn = document.getElementById('mobileVoiceBtn');
            if (data.status === 'listening') {
                voiceBtn.classList.add('active');
                voiceBtn.textContent = '🎤 중지';
                mobileVoiceActive = true;
            } else {
                voiceBtn.classList.remove('active');
                voiceBtn.textContent = '🎤 음성 시작';
                mobileVoiceActive = false;
            }
        });

        socket.on('voice_command_result', (data) => {
            switch(data.action) {
                case 'focus_scenario':
                    document.getElementById('mobileScenario').focus();
                    break;
                case 'set_4d_quality':
                    document.getElementById('mobileQuality').value = '4D';
                    break;
            }
            document.getElementById('mobileVoiceStatus').textContent = `"${data.command}" → ${data.response}`;
        });

        function toggleMobileVoice() {
            if (mobileVoiceActive) {
                socket.emit('stop_voice_recognition');
            } else {
                socket.emit('start_voice_recognition');
            }
        }

        function speakMobileHelp() {
            fetch('/speak', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    text: '모바일 소리새 음성 4D 영화 제작 시스템입니다. 영화 만들어줘, 4D로 설정해줘 등의 명령을 사용하세요.'
                })
            });
        }

        // 모바일 폼 제출
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

        socket.on('play_audio', (data) => {
            const audio = new Audio(data.audio_url);
            audio.play().catch(e => console.log('오디오 재생 실패:', e));
        });
    </script>
</body>
</html>"""

        # 템플릿 파일 저장
        with open('templates/voice_index.html', 'w', encoding='utf-8') as f:
            f.write(voice_index_html)

        with open('templates/voice_mobile.html', 'w', encoding='utf-8') as f:
            f.write(voice_mobile_html)

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

    def run(self):
        """웹 서버 실행"""
        if not FLASK_AVAILABLE:
            print("❌ Flask가 설치되지 않았습니다.")
            print("다음 명령어로 설치하세요: pip install flask flask-socketio")
            return

        local_ip = self.get_local_ip()

        print("🎤🌐 소리새 음성 4D 영화 제작 웹 서버 시작!")
        print("=" * 60)
        print(f"🖥️  데스크톱 접속: http://localhost:{self.port}")
        print(f"🖥️  데스크톱 접속: http://{local_ip}:{self.port}")
        print(f"📱 모바일 접속: http://{local_ip}:{self.port}/mobile")
        print(f"📱 QR 코드: http://{local_ip}:{self.port}/qr_code")
        print("=" * 60)
        print("🎤 소리새 음성 명령 기능:")
        print("  • '영화 만들어줘' - 영화 제작 시작")
        print("  • '시나리오' - 시나리오 입력창 활성화")
        print("  • '4D로 설정해줘' - 4D 품질 선택")
        print("  • '주제곡 포함해줘' - 주제곡 옵션 활성화")
        print("  • '상태 확인해줘' - 진행 상황 확인")
        print("  • '도움말' - 명령어 안내")
        print("=" * 60)
        print("🎬 브라우저에서 위 주소로 접속하여 음성으로 4D 영화를 제작하세요!")
        print("📱 모바일에서는 QR 코드를 스캔하여 접속하세요!")

        if VOICE_AVAILABLE:
            print("✅ 소리새 음성 시스템 활성화됨!")
        else:
            print("⚠️ 음성 라이브러리 설치 필요: pip install speechrecognition pyttsx3 pyaudio gtts")

        try:
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 서버를 종료합니다.")


def main():
    """메인 실행 함수"""
    server = SorisaeVoiceMovieServer()
    server.run()


if __name__ == "__main__":
    main()
