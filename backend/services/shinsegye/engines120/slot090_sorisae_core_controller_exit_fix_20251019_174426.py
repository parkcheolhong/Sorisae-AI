import speech_recognition as sr
import pyttsx3
import time
import json
import os
import random
import sys
import os

# 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
sys.path.append(root_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)

from modules.plugins.plugin_manager import PluginManager
from modules.sorisae_dashboard_web import broadcast_voice_command, broadcast_system_status, broadcast_persona_change, broadcast_creative_activity
from nlp_processor import NLPProcessor
from self_learning_engine import SelfLearningEngine
from auto_feature_expansion import AutoFeatureExpansion
from creative_sorisae_engine import CreativeSorisaeEngine
from persona_system import PersonaSystem
from memory_palace import MemoryPalace
from ai_collaboration_network import AICollaborationNetwork
from creative_coding_assistant import CreativeCodingAssistant
from smart_plugin_generator import SmartPluginGenerator
from ai_music_composer import AIMusicComposer
from dream_interpreter import DreamInterpreter
from virtual_dev_team import VirtualDevelopmentTeam
from future_prediction_engine import FuturePredictionEngine
from emotion_color_therapist import EmotionColorTherapist

class SorisaeCore:
    def __init__(self, config_path="config/settings.json"):
        # 설정 로드
        self.config = self.load_config(config_path)
        
        # 음성 인식 설정
        self.recognizer = sr.Recognizer()
        voice_config = self.config.get("voice_recognition", {})
        self.recognizer.energy_threshold = voice_config.get("energy_threshold", 300)
        self.recognizer.dynamic_energy_threshold = voice_config.get("dynamic_energy_threshold", True)
        self.recognizer.pause_threshold = voice_config.get("pause_threshold", 0.8)
        self.recognizer.phrase_threshold = voice_config.get("phrase_threshold", 0.3)
        
        # TTS 설정
        self.engine = pyttsx3.init()
        tts_config = self.config.get("tts", {})
        self.setup_tts_voice(tts_config)
        
        # 플러그인 매니저 초기화
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()
        
        # 자연어 처리기 초기화
        self.nlp_processor = NLPProcessor()
        
        # 자가 학습 엔진 초기화
        self.learning_engine = SelfLearningEngine()
        
        # 자동 기능 확장 시스템 초기화
        self.auto_expansion = AutoFeatureExpansion()
        
        # 🎨 창조형 소리새 엔진 초기화
        self.creative_engine = CreativeSorisaeEngine()
        
        # 🎭 페르소나 시스템 초기화
        self.persona_system = PersonaSystem()
        
        # 🧠 기억의 궁전 초기화
        self.memory_palace = MemoryPalace()
        
        # 🤝 AI 협업 네트워크 초기화
        self.ai_network = AICollaborationNetwork()
        
        # 🎨 창조적 코딩 어시스턴트 초기화
        self.coding_assistant = CreativeCodingAssistant()
        
        # 🧩 스마트 플러그인 생성기 초기화
        self.plugin_generator = SmartPluginGenerator()
        
        # 🎵 AI 음악 작곡가 초기화
        self.music_composer = AIMusicComposer()
        
        # 🌙 꿈 해석 시스템 초기화
        self.dream_interpreter = DreamInterpreter()
        
        # 🤖 가상 개발팀 시스템 초기화
        self.virtual_dev_team = VirtualDevelopmentTeam()
        
        # 🔮 미래 예측 엔진 초기화
        self.prediction_engine = FuturePredictionEngine()
        
        # 🎨 감정 색채 치료사 초기화
        self.color_therapist = EmotionColorTherapist()
        
        # 진화 카운터
        self.interaction_count = 0
        self.last_evolution_check = 0
        
        # 🚀 창조 모드 설정 (70% 확률로 창조적 아이디어 제안)
        self.creative_mode = True
        self.creative_probability = 0.75  # 75% 확률로 창조적 아이디어
        
        self.running = True
        
        # 대시보드에 시스템 시작 알림
        broadcast_system_status("소리새 시스템 시작됨")

    def load_config(self, config_path):
        """설정 파일 로드"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠ 설정 파일을 찾을 수 없습니다: {config_path}")
                return self.get_default_config()
        except Exception as e:
            print(f"⚠ 설정 파일 로드 실패: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """기본 설정 반환"""
        return {
            "voice_recognition": {
                "energy_threshold": 300,
                "dynamic_energy_threshold": True,
                "pause_threshold": 0.8,
                "phrase_threshold": 0.3,
                "timeout": 5,
                "phrase_time_limit": 3
            },
            "tts": {
                "rate": 120,  # 더 느리게 (기존 150에서 120으로)
                "voice_index": 0,
                "volume": 0.9,
                "voice_gender": "female",
                "language": "ko",
                "emotion": "friendly",
                "pitch": 0,
                "voice_effects": {
                    "enable_emotion": False,  # 감정 표현 비활성화
                    "enable_speed_variation": False,  # 속도 변화 비활성화
                    "enable_pause_insertion": False  # 일시정지 비활성화
                }
            }
        }

    def setup_tts_voice(self, tts_config):
        """TTS 음성 설정"""
        try:
            # 기본 TTS 속성 설정
            rate = tts_config.get("rate", 150)
            volume = tts_config.get("volume", 0.9)
            voice_index = tts_config.get("voice_index", 0)
            
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            # 사용 가능한 음성 목록 가져오기
            voices = self.engine.getProperty('voices')
            
            if voices:
                # 한국어 음성 찾기 (선호도 순)
                korean_voices = []
                female_voices = []
                
                for i, voice in enumerate(voices):
                    voice_name = voice.name.lower()
                    voice_id = voice.id.lower()
                    
                    # 한국어 음성 우선 선택
                    if any(keyword in voice_name or keyword in voice_id 
                          for keyword in ['korean', 'ko-kr', 'korea', '한국']):
                        korean_voices.append((i, voice))
                    
                    # 여성 음성 우선 선택  
                    if any(keyword in voice_name or keyword in voice_id
                          for keyword in ['female', 'woman', 'zira', 'hazel']):
                        female_voices.append((i, voice))
                
                # 음성 선택 우선순위: 한국어 > 여성 > 인덱스
                selected_voice = None
                if korean_voices:
                    selected_voice = korean_voices[0]
                    print(f"🎤 한국어 음성 선택: {selected_voice[1].name}")
                elif female_voices:
                    selected_voice = female_voices[0]
                    print(f"🎤 여성 음성 선택: {selected_voice[1].name}")
                elif voice_index < len(voices):
                    selected_voice = (voice_index, voices[voice_index])
                    print(f"🎤 음성 선택: {selected_voice[1].name}")
                
                if selected_voice:
                    self.engine.setProperty('voice', selected_voice[1].id)
                
            print(f"🔊 TTS 설정 완료 - 속도: {rate}, 볼륨: {volume}")
            
        except Exception as e:
            print(f"⚠ TTS 설정 중 오류: {e}")

    def speak_with_emotion(self, text, emotion="neutral", speed_modifier=1.0):
        """감정과 속도 조절이 가능한 음성 출력"""
        try:
            tts_config = self.config.get("tts", {})
            effects = tts_config.get("voice_effects", {})
            
            # 원래 속도 저장
            original_rate = self.engine.getProperty('rate')
            
            # 감정에 따른 속도 조절 - 더 자연스럽게
            if effects.get("enable_speed_variation", True):
                emotion_rates = {
                    "excited": original_rate * 1.05,  # 살짝만 빠르게
                    "happy": original_rate * 1.02,   # 아주 살짝 빠르게
                    "neutral": original_rate,
                    "sad": original_rate * 0.95,     # 살짝 느리게
                    "error": original_rate * 0.98,   # 조금 느리게
                    "success": original_rate * 1.02, # 살짝 빠르게
                    "casual": original_rate * 0.98   # 편안하게 느리게
                }
                new_rate = int(emotion_rates.get(emotion, original_rate) * speed_modifier)
                self.engine.setProperty('rate', new_rate)
            else:
                # 대화 모드에서는 속도 변화 최소화
                new_rate = int(original_rate * speed_modifier)
                self.engine.setProperty('rate', new_rate)
            
            # 감정에 따른 텍스트 수정
            if effects.get("enable_emotion", True):
                text = self.add_emotional_markers(text, emotion)
            
            # 자연스러운 일시정지 추가
            if effects.get("enable_pause_insertion", True):
                text = self.add_natural_pauses(text)
            
            print(f"🗣 [{emotion}] {text}")
            self.engine.say(text)
            self.engine.runAndWait()
            
            # 원래 속도로 복원
            self.engine.setProperty('rate', original_rate)
            
        except Exception as e:
            print(f"⚠ 음성 출력 오류: {e}")
            # 기본 speak 메서드로 fallback
            self.speak(text)

    def add_emotional_markers(self, text, emotion):
        """감정에 따른 텍스트 마커 추가 - 자연스럽게"""
        emotion_prefixes = {
            "excited": "",      # 과도한 표현 제거
            "happy": "",        # 자연스럽게
            "success": "",      # 차분하게
            "error": "음, ",    # 조금만
            "sad": "",          # 담담하게
            "neutral": "",
            "casual": ""        # 편안하게
        }
        
        emotion_suffixes = {
            "excited": "",      # 느낌표 제거
            "happy": "",        # 자연스럽게
            "success": "",      # 차분하게
            "error": "",        # 간단하게
            "sad": "",          # 담담하게
            "neutral": "",
            "casual": ""        # 편안하게
        }
        
        prefix = emotion_prefixes.get(emotion, "")
        suffix = emotion_suffixes.get(emotion, "")
        
        return f"{prefix}{text}{suffix}"

    def add_natural_pauses(self, text):
        """자연스러운 일시정지 추가 - 간단하게"""
        # 기본 텍스트 그대로 반환 (일시정지 마커 제거)
        return text
        
        return text

    def speak(self, text, emotion="neutral"):
        """개선된 음성 출력 (감정 지원)"""
        self.speak_with_emotion(text, emotion)

    def listen(self):
        try:
            voice_config = self.config.get("voice_recognition", {})
            with sr.Microphone() as source:
                print("🎧 듣는 중...")
                self.recognizer.adjust_for_ambient_noise(
                    source, 
                    duration=voice_config.get("ambient_noise_duration", 0.5)
                )
                audio = self.recognizer.listen(
                    source, 
                    timeout=voice_config.get("timeout", 5), 
                    phrase_time_limit=voice_config.get("phrase_time_limit", 3)
                )
                
                cmd = self.recognizer.recognize_google(audio, language="ko-KR")
                print(f"🎙 인식된 명령: '{cmd}'")
                return cmd.strip()
                
        except sr.WaitTimeoutError:
            print("⏱ 음성 입력 대기 시간 초과")
            return None
        except sr.UnknownValueError:
            print("⚠ 음성을 인식하지 못했습니다")
            self.speak("다시 말씀해 주세요")
            return None
        except sr.RequestError as e:
            print(f"🚫 Google Speech Recognition 오류: {e}")
            self.speak("인터넷 연결을 확인해주세요")
            return None

    def run(self):
        self.speak("진화형 소리새가 준비되었습니다. 저는 스스로 학습하고 발전합니다.")
        
        # 학습 현황 출력
        learning_summary = self.learning_engine.get_learning_summary()
        print(f"📚 학습 현황: {learning_summary}")
        
        # 모든 플러그인의 도움말 출력
        help_text = self.plugin_manager.get_all_help()
        print(help_text)
        print("-" * 50)
        
        broadcast_system_status("진화형 AI 대기 중")
        
        while self.running:
            cmd = self.listen()
            if not cmd: 
                time.sleep(0.5)
                continue
            
            self.interaction_count += 1
            response_success = False
            final_response = ""
            
            # 🎭 페르소나 시스템으로 감정 감지 및 성격 전환
            user_mood = self.persona_system.detect_user_mood(cmd)
            old_persona = self.persona_system.current_persona
            self.persona_system.switch_persona(user_mood)
            if old_persona != self.persona_system.current_persona:
                print(f"🎭 페르소나 변경: {old_persona} → {self.persona_system.current_persona}")
                broadcast_persona_change(self.persona_system.current_persona)
                broadcast_creative_activity("persona_switch", f"{old_persona} → {self.persona_system.current_persona}")
            else:
                print(f"🎭 활성 페르소나: {self.persona_system.current_persona}")
            
            # 🛑 종료 명령 최우선 처리
            if any(keyword in cmd.lower() for keyword in ["종료", "끝", "그만", "정지", "멈춰", "닫아", "shutdown", "exit", "quit", "소리새 안녕"]):
                print("🛑 종료 명령 감지됨!")
                self.speak("소리새를 종료합니다. 안녕히 가세요!")
                self.running = False
                broadcast_system_status("시스템 종료 중")
                yield cmd
                break
            
            # 🧠 기억의 궁전에 대화 저장
            nlp_result = self.nlp_processor.process_natural_language(cmd)
            emotion = nlp_result.get("emotion", "neutral")
            
            # 🧠 자가 학습된 지식으로 먼저 응답 시도
            smart_response = self.learning_engine.smart_response(cmd)
            if smart_response:
                print(f"🎓 학습된 지식으로 응답: {smart_response[:50]}...")
                self.speak(smart_response)
                final_response = smart_response
                response_success = True
                broadcast_voice_command(cmd, "smart_success")
                
                # 학습 기록
                self.learning_engine.learn_from_interaction(cmd, smart_response, True)
                yield cmd
                
            else:
                # 기존 NLP 처리
                nlp_result = self.nlp_processor.process_natural_language(cmd)
                intent = nlp_result["intent"]
                confidence = nlp_result["confidence"]
                
                print(f"🧠 NLP 분석: 의도='{intent}', 신뢰도={confidence:.2f}")
                
                # 높은 신뢰도로 의도가 파악된 경우
                if intent and confidence > 0.5:
                    mapped_command = self.nlp_processor.get_command_mapping(intent)
                    emotion = nlp_result.get("emotion", "neutral")
                    
                    if mapped_command:
                        plugin_name, command, keyword = self.plugin_manager.find_command(mapped_command)
                        
                        if plugin_name and command:
                            print(f"✅ 자연어 명령 실행: '{cmd}' -> '{mapped_command}' (플러그인: {plugin_name})")
                            broadcast_voice_command(cmd, "success")
                            
                            nlp_response = nlp_result["response"]
                            self.speak(nlp_response, emotion)
                            
                            try:
                                response = self.plugin_manager.execute_command(plugin_name, command, cmd)
                                if response != nlp_response:
                                    self.speak(response, "success")
                                
                                final_response = f"{nlp_response} {response}"
                                response_success = True
                                
                                if command == "stop":
                                    self.running = False
                                    broadcast_system_status("시스템 종료 중")
                                    
                            except Exception as e:
                                error_msg = f"명령어 실행 중 오류가 발생했습니다: {str(e)}"
                                print(f"❌ {error_msg}")
                                self.speak(error_msg, "error")
                                final_response = error_msg
                                broadcast_voice_command(cmd, "failed")
                                
                            yield cmd
                        else:
                            print(f"✅ 자연어 응답: '{intent}'")
                            response_text = nlp_result["response"]
                            self.speak(response_text, emotion)
                            final_response = response_text
                            response_success = True
                            broadcast_voice_command(cmd, "success")
                            yield cmd
                    else:
                        print(f"⚠ 매핑되지 않은 의도: '{intent}'")
                        response_text = nlp_result["response"]
                        self.speak(response_text, emotion)
                        final_response = response_text
                        response_success = False
                        broadcast_voice_command(cmd, "warning")
                        yield cmd
                else:
                    # 🌐 웹 검색을 통한 새로운 지식 획득
                    print(f"🔍 웹 검색을 통한 지식 확장 시도...")
                    search_results = self.learning_engine.web_search(cmd)
                    
                    if search_results and search_results[0].get("content"):
                        web_response = f"웹에서 찾은 정보입니다: {search_results[0]['content'][:200]}..."
                        self.speak(web_response)
                        final_response = web_response
                        response_success = True
                        broadcast_voice_command(cmd, "web_search_success")
                        
                        # 새로운 지식으로 학습
                        self.learning_engine.learn_from_interaction(cmd, web_response, True)
                        yield cmd
                    else:
                        # 🎨 창의적 AI 기능들 처리
                        creative_response = self.handle_creative_commands(cmd)
                        if creative_response:
                            self.speak(creative_response, emotion)
                            final_response = creative_response
                            response_success = True
                            broadcast_voice_command(cmd, "creative_success")
                            yield cmd
                        else:
                            # 기존 방식으로 처리
                            plugin_name, command, keyword = self.plugin_manager.find_command(cmd)
                        
                        if plugin_name and command:
                            print(f"✅ '{keyword}' 명령어 실행 (플러그인: {plugin_name})")
                            broadcast_voice_command(cmd, "success")
                            
                            try:
                                response = self.plugin_manager.execute_command(plugin_name, command, cmd)
                                self.speak(response)
                                final_response = response
                                response_success = True
                                
                                if command == "stop":
                                    self.running = False
                                    broadcast_system_status("시스템 종료 중")
                                    
                            except Exception as e:
                                error_msg = f"명령어 실행 중 오류가 발생했습니다: {str(e)}"
                                print(f"❌ {error_msg}")
                                self.speak(error_msg)
                                final_response = error_msg
                                broadcast_voice_command(cmd, "failed")
                                
                            yield cmd
                        else:
                            # 완전히 이해하지 못한 경우
                            unknown_response = "죄송합니다. 아직 이해하지 못하는 요청입니다. 하지만 학습해서 다음엔 더 잘 도와드리겠습니다."
                            self.speak(unknown_response)
                            final_response = unknown_response
                            response_success = False
                            broadcast_voice_command(cmd, "learning_needed")
                            yield cmd
                
                # 모든 상호작용에서 학습
                if not smart_response:  # 이미 학습하지 않은 경우만
                    self.learning_engine.learn_from_interaction(cmd, final_response, response_success)
                
                # 🧠 모든 대화를 기억의 궁전에 저장
                self.memory_palace.remember_conversation(cmd, final_response, emotion)
            
            # 🚀 주기적 자가 진화 (50번 상호작용마다)
            if self.interaction_count - self.last_evolution_check >= 50:
                self.self_evolve()
                self.last_evolution_check = self.interaction_count
            
            if not self.running:
                break
            time.sleep(0.5)

    def generate_creative_idea(self, context: str = "") -> str:
        """🎨 창조적 아이디어 생성"""
        idea = self.creative_engine.generate_creative_idea(context)
        
        response = f"""
🎨 새로운 아이디어가 떠올랐습니다!

💡 {idea['name']}
📝 {idea['description']}
⭐ 창조성 점수: {idea['creativity_score']}/10

이 기능을 만들어볼까요?
        """.strip()
        
        return response
    
    def implement_creative_feature(self, idea_name: str) -> str:
        """🛠️ 창조적 기능 구현"""
        idea = self.creative_engine.generate_creative_idea()
        result = self.creative_engine.implement_feature(idea)
        evolution_msg = self.creative_engine.evolve_creativity()
        return f"{result}\n\n🧠 {evolution_msg}"
    
    def suggest_self_improvements(self) -> str:
        """🚀 자가 개선 제안"""
        suggestions = self.creative_engine.suggest_improvements()
        response = "🚀 스스로 생각해본 개선 아이디어:\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"
        response += "\n어떤 것부터 개선해볼까요?"
        return response
    
    def self_evolve(self):
        """🚀 자가 진화 시스템"""
        print("🧠 소리새가 스스로 진화하고 있습니다...")
        
        # 학습된 패턴 분석
        learning_data = self.learning_engine.get_learning_summary()
        
        evolution_messages = [
            "새로운 대화 패턴을 학습했습니다!",
            "사용자 선호도를 분석하여 개선했습니다!",
            "더 정확한 응답을 위해 알고리즘을 최적화했습니다!",
            "창조적 사고 능력이 향상되었습니다!"
        ]
        
        evolution_msg = random.choice(evolution_messages)
        self.speak(f"🧠 {evolution_msg}")
        
        # 창조적 확률 조정 (학습이 많이 될수록 더 창조적으로)
        if learning_data.get('total_interactions', 0) > 200:
            self.creative_probability = min(0.85, self.creative_probability + 0.01)  # 최대 85%까지
        
        return evolution_msg
    
    def handle_creative_commands(self, cmd: str) -> str:
        """🎨 창의적 AI 기능들 처리"""
        cmd_lower = cmd.lower()
        
        # 페르소나 관련 명령어
        if any(keyword in cmd_lower for keyword in ["페르소나", "성격", "모드", "감정"]):
            persona_response = self.persona_system.get_persona_response(cmd)
            # 기억에 저장
            self.memory_palace.remember_conversation(cmd, persona_response, self.persona_system.current_persona)
            return persona_response
        
        # AI 협업 요청
        elif any(keyword in cmd_lower for keyword in ["브레인스토밍", "아이디어", "협업", "팀워크"]):
            session = self.ai_network.brainstorm_session(cmd, 2)
            response = f"🤝 AI 팀 협업 결과:\n{session['final_solution']}\n\n📊 합의도: {session['consensus_score']:.1f}점"
            self.memory_palace.remember_conversation(cmd, response, "collaborative")
            broadcast_creative_activity("collaboration", f"AI 팀 브레인스토밍 (합의도: {session['consensus_score']:.0f}%)")
            return response
        
        # 코드 분석 및 개선 요청
        elif any(keyword in cmd_lower for keyword in ["코드", "프로그램", "개선", "리팩토링"]):
            if "분석" in cmd_lower or "개선" in cmd_lower:
                suggestions = self.coding_assistant.suggest_code_poetry("def example(): pass")
                response = "🎨 창조적 코딩 제안:\n" + "\n".join(suggestions)
                self.memory_palace.remember_conversation(cmd, response, "creative")
                return response
        
        # 플러그인 생성 요청
        elif any(keyword in cmd_lower for keyword in ["플러그인", "기능 추가", "만들어", "생성"]):
            analysis = self.plugin_generator.analyze_user_request(cmd)
            if analysis['confidence_score'] > 30:
                result = self.plugin_generator.generate_plugin(cmd)
                if result['success']:
                    response = f"🧩 플러그인 자동 생성 완료!\n📁 {result['plugin_info']['name']}\n💡 {result['plugin_info']['description'][:100]}..."
                    self.memory_palace.remember_conversation(cmd, response, "productive")
                    broadcast_creative_activity("plugin_generation", f"플러그인 '{result['plugin_info']['name']}' 생성")
                    return response
        
        # 기억 검색 요청
        elif any(keyword in cmd_lower for keyword in ["기억", "이전", "전에", "예전"]):
            memories = self.memory_palace.recall_memories(cmd, 3)
            if memories:
                response = "🧠 관련 기억을 찾았어요:\n"
                for i, memory in enumerate(memories[:2], 1):
                    response += f"{i}. {memory['user_input'][:30]}... ({memory['timestamp'][:10]})\n"
                return response
            else:
                return "🤔 관련된 기억을 찾지 못했어요. 더 구체적으로 말씀해 주시겠어요?"
        
        # 성격 인사이트 요청
        elif any(keyword in cmd_lower for keyword in ["분석", "성격", "인사이트", "특징"]):
            insights = self.memory_palace.get_personality_insights()
            self.memory_palace.remember_conversation(cmd, insights, "analytical")
            return insights
        
        # � 꿈 해석 요청
        elif any(keyword in cmd_lower for keyword in ["꿈", "해석", "꿈해석", "심리분석"]):
            if "꿈" in cmd_lower:
                # 꿈 내용 추출
                dream_text = cmd.replace("꿈", "").replace("해석", "").replace("분석", "").strip()
                if not dream_text:
                    dream_text = "물에 떨어져서 무서웠지만 날개가 생겨서 하늘을 날아다녔다"
                
                # 나이와 문화권 정보 (기본값 사용)
                dreamer_age = 25  # 기본 나이
                culture = "한국"  # 기본 문화권
                
                # 꿈 분석 실행
                analysis = self.dream_interpreter.analyze_dream(dream_text, dreamer_age, culture)
                
                # 간단한 응답 생성
                symbols = analysis.get("상징_분석", {}).get("발견된_상징", {})
                emotion = analysis.get("감정_분석", {}).get("지배적_감정", "중립")
                advice = analysis.get("조언", {}).get("우선순위_조언", [])
                
                response = f"🌙 꿈 해석 결과:\n"
                response += f"🔮 발견된 상징: {len(symbols)}개\n"
                response += f"💭 지배적 감정: {emotion}\n"
                
                if advice:
                    response += f"💡 조언: {advice[0]}\n"
                
                # 상세 보고서 생성
                detailed_report = self.dream_interpreter.create_dream_report(analysis)
                print(detailed_report)  # 콘솔에 상세 출력
                
                broadcast_creative_activity("dream_analysis", f"꿈 해석: {emotion} 감정, {len(symbols)}개 상징")
                self.memory_palace.remember_conversation(cmd, response, "analytical")
                return response
        
        # 🤖 가상 개발팀 요청
        elif any(keyword in cmd_lower for keyword in ["개발팀", "프로젝트", "팀관리", "스프린트", "개발진행"]):
            if "프로젝트" in cmd_lower and ("생성" in cmd_lower or "만들" in cmd_lower):
                # 새 프로젝트 생성
                project_name = "AI 기반 웹 서비스"  # 기본 프로젝트명
                project = self.virtual_dev_team.create_project(
                    project_name, 
                    "혁신적인 AI 기반 웹 서비스 개발 프로젝트",
                    duration_weeks=4
                )
                response = f"🤖 새 프로젝트 생성!\n"
                response += f"📋 프로젝트: {project['name']}\n"
                response += f"🆔 ID: {project['id']}\n"
                response += f"📅 기간: {project['duration_weeks']}주\n"
                response += f"💰 예산: ${project['budget']['total']:,.0f}\n"
                response += f"📝 작업 수: {len(project['tasks'])}개"
                
                broadcast_creative_activity("project_creation", f"프로젝트 생성: {project['name']}")
                
            elif "진행상황" in cmd_lower or "현황" in cmd_lower:
                # 프로젝트 진행 상황 체크
                if self.virtual_dev_team.current_projects:
                    project_id = list(self.virtual_dev_team.current_projects.keys())[0]
                    progress = self.virtual_dev_team.simulate_daily_progress(project_id)
                    
                    response = f"📊 프로젝트 진행 현황\n"
                    response += f"📈 전체 진행률: {progress['overall_progress']:.1f}%\n"
                    response += f"✅ 완료 작업: {len(progress['completed_tasks'])}개\n"
                    response += f"👥 팀 활동: {len(progress['team_activities'])}건\n"
                    
                    if progress['completed_tasks']:
                        latest_task = progress['completed_tasks'][0]
                        response += f"� 최근 완료: {latest_task['task_title']}"
                else:
                    response = "현재 진행 중인 프로젝트가 없습니다."
                
            elif "미팅" in cmd_lower or "회의" in cmd_lower:
                # 팀 미팅 진행
                meeting = self.virtual_dev_team.conduct_team_meeting("일일스탠드업")
                response = f"👥 {meeting['type']} 완료!\n"
                response += f"📅 시간: {meeting['date']}\n"
                response += f"👨‍💻 참석자: {len(meeting['attendees'])}명\n"
                response += f"📋 결정사항: {len(meeting['decisions'])}건\n"
                
                if meeting['decisions']:
                    response += f"💡 주요 결정: {meeting['decisions'][0]}"
                    
                broadcast_creative_activity("team_meeting", f"{meeting['type']} 미팅 진행")
                
            elif "스프린트" in cmd_lower:
                # 스프린트 계획
                sprint = self.virtual_dev_team.simulate_sprint_planning()
                response = f"🏃 스프린트 계획 수립!\n"
                response += f"🆔 스프린트: {sprint['sprint_id']}\n"
                response += f"📅 기간: {sprint['duration_weeks']}주\n"
                response += f"📝 선택 작업: {len(sprint['selected_tasks'])}개\n"
                response += f"🎯 목표: {sprint['goals'][0] if sprint['goals'] else 'N/A'}"
                
                broadcast_creative_activity("sprint_planning", f"스프린트 {sprint['sprint_id']} 계획")
                
            elif "분석" in cmd_lower or "리포트" in cmd_lower:
                # 팀 분석 리포트
                analytics = self.virtual_dev_team.get_team_analytics()
                response = f"📊 팀 분석 리포트\n"
                response += f"👥 팀원: {analytics['team_overview']['total_members']}명\n"
                response += f"⚡ 팀 효율성: {analytics['productivity_metrics']['team_efficiency']:.1f}%\n"
                response += f"💚 팀 만족도: {analytics['team_health']['satisfaction_index']:.1f}%\n"
                response += f"📈 완료율: {analytics['productivity_metrics']['completion_rate']:.1f}%"
                
                # 상세 리포트 콘솔 출력
                detailed_report = self.virtual_dev_team.generate_team_report()
                print(detailed_report)
                
                broadcast_creative_activity("team_analysis", "팀 성과 분석 완료")
            else:
                # 기본 팀 상태 정보
                analytics = self.virtual_dev_team.get_team_analytics()
                response = f"🤖 가상 개발팀 상태\n"
                response += f"👥 {analytics['team_overview']['total_members']}명의 전문가들이 대기 중\n"
                response += f"💪 평균 스킬: {analytics['team_overview']['avg_skill_level']:.1f}/10\n"
                response += f"🎯 현재 프로젝트: {analytics['project_status']['active_projects']}개"
                
            self.memory_palace.remember_conversation(cmd, response, "project_management")
            return response
        
        # 🔮 미래 예측 요청
        elif any(keyword in cmd_lower for keyword in ["미래", "예측", "전망", "트렌드", "예상", "분석"]):
            if "트렌드" in cmd_lower:
                # 트렌드 분석 요청
                category = "전체"
                if "기술" in cmd_lower:
                    category = "기술"
                elif "경제" in cmd_lower:
                    category = "경제"
                elif "사회" in cmd_lower:
                    category = "사회"
                
                analysis = self.prediction_engine.analyze_future_trends(category)
                response = f"📈 {category} 트렌드 분석 완료!\n"
                response += f"🎯 신뢰도: {analysis.get('confidence_score', 0):.1%}\n"
                
                # 신흥 트렌드 표시
                emerging = analysis.get('emerging_trends', [])[:2]
                if emerging:
                    response += f"🚀 주요 신흥 트렌드:\n"
                    for trend in emerging:
                        response += f"  • {trend['name']}: {trend['predicted_value']:.1%} 성장 예상\n"
                
                # 핵심 인사이트
                insights = analysis.get('key_insights', [])
                if insights:
                    response += f"💡 핵심 인사이트: {insights[0]}"
                
                broadcast_creative_activity("trend_analysis", f"{category} 트렌드 분석")
                
            elif "예측" in cmd_lower or "전망" in cmd_lower:
                # 미래 예측 생성
                focus = "전체"
                if "기술" in cmd_lower:
                    focus = "기술"
                elif "사회" in cmd_lower:
                    focus = "사회"
                elif "경제" in cmd_lower:
                    focus = "경제"
                
                predictions = self.prediction_engine.generate_predictions(focus, 3)
                response = f"🔮 {focus} 분야 미래 예측!\n\n"
                
                for i, pred in enumerate(predictions, 1):
                    response += f"{i}. {pred.title}\n"
                    response += f"   📊 확률: {pred.probability:.1%} | 신뢰도: {pred.confidence.value}\n"
                    response += f"   ⏰ 시기: {pred.timeframe.value} | 영향도: {pred.impact_score:.1f}/1.0\n\n"
                
                broadcast_creative_activity("future_prediction", f"{focus} 분야 예측 {len(predictions)}건")
                
            elif "시나리오" in cmd_lower:
                # 시나리오 시뮬레이션 (최신 예측 기준)
                predictions = self.prediction_engine.generate_predictions("기술", 1)
                if predictions:
                    scenario = self.prediction_engine.simulate_scenario(predictions[0].id)
                    response = f"🎭 시나리오 시뮬레이션: {predictions[0].title}\n\n"
                    
                    scenarios = scenario.get('scenarios', {})
                    if 'realistic' in scenarios:
                        real_scenario = scenarios['realistic']
                        response += f"📋 현실적 시나리오:\n{real_scenario['description']}\n\n"
                        response += f"⏱️ 예상 일정: {real_scenario['timeline']}\n"
                    
                    # 권장 행동
                    actions = scenario.get('recommended_actions', [])
                    if actions:
                        response += f"\n💡 권장 행동:\n"
                        for action in actions[:2]:
                            response += f"  • {action}\n"
                    
                    broadcast_creative_activity("scenario_simulation", predictions[0].title)
                else:
                    response = "시나리오 생성에 실패했습니다."
                    
            elif "보고서" in cmd_lower or "리포트" in cmd_lower:
                # 종합 미래 예측 보고서
                category = "전체"
                if "기술" in cmd_lower:
                    category = "기술"
                elif "경제" in cmd_lower:
                    category = "경제"
                elif "사회" in cmd_lower:
                    category = "사회"
                    
                report = self.prediction_engine.generate_future_report(category)
                response = f"📋 {category} 미래 예측 보고서가 생성되었습니다!\n"
                response += "상세 내용은 콘솔에서 확인하세요."
                
                # 콘솔에 상세 보고서 출력
                print(report)
                
                broadcast_creative_activity("prediction_report", f"{category} 미래 예측 보고서")
            else:
                # 기본 예측 엔진 소개
                accuracy = self.prediction_engine.get_prediction_accuracy()
                response = f"🔮 미래 예측 엔진 활성화!\n"
                response += f"🎯 예측 정확도: {accuracy.get('accuracy_rate', 75):.1f}%\n"
                response += f"📊 총 예측: {accuracy.get('total_predictions', 0)}건\n"
                response += f"💡 '미래 트렌드', '예측', '시나리오', '보고서' 등으로 요청하세요!"
            
            self.memory_palace.remember_conversation(cmd, response, "prediction")
            return response
        
        # � 감정 색채 치료 요청
        elif any(keyword in cmd_lower for keyword in ["색", "색깔", "컬러", "치료", "감정치료", "색채치료"]):
            if "분석" in cmd_lower or "진단" in cmd_lower:
                # 감정 분석 요청
                if "스트레스" in cmd_lower or "불안" in cmd_lower:
                    emotion_text = "스트레스받고 불안해요"
                    context = "일상 생활"
                elif "우울" in cmd_lower or "슬프" in cmd_lower:
                    emotion_text = "우울하고 기분이 안좋아요"
                    context = "개인적 상황"
                elif "화나" in cmd_lower or "짜증" in cmd_lower:
                    emotion_text = "화나고 짜증나요"
                    context = "대인 관계"
                else:
                    emotion_text = "감정이 복잡해요"
                    context = "일반적 상황"
                
                analysis = self.color_therapist.analyze_emotion(emotion_text, context)
                response = f"🎨 감정 분석 완료!\n"
                
                primary_emotion = analysis.get('primary_emotion')
                if primary_emotion and hasattr(primary_emotion, 'value'):
                    response += f"🎯 주감정: {primary_emotion.value}\n"
                
                response += f"📊 감정 강도: {analysis.get('emotion_intensity', 0):.1%}\n"
                response += f"🔍 복합성: {analysis.get('emotion_complexity', '미상')}\n"
                response += f"⚡ 긴급도: {analysis.get('urgency_level', '미상')}\n"
                response += f"💡 '색 추천', '치료 시작' 등으로 요청하세요!"
                
                broadcast_creative_activity("emotion_analysis", f"감정 분석: {primary_emotion.value if primary_emotion and hasattr(primary_emotion, 'value') else '미상'}")
                
            elif "추천" in cmd_lower or "제안" in cmd_lower or "색깔" in cmd_lower:
                # 색상 추천
                emotion_text = "전체적으로 마음이 복잡하고 힘들어요"
                context = "일상 스트레스"
                
                # 사용자 선호도 추출
                preference = "균형"
                if "따뜻" in cmd_lower:
                    preference = "따뜻함"
                elif "차가" in cmd_lower or "시원" in cmd_lower:
                    preference = "차가움"
                elif "강렬" in cmd_lower or "진한" in cmd_lower:
                    preference = "강렬함"
                elif "부드럽" in cmd_lower or "연한" in cmd_lower:
                    preference = "부드러움"
                
                analysis = self.color_therapist.analyze_emotion(emotion_text, context)
                colors = self.color_therapist.recommend_colors(analysis, preference)
                
                response = f"🎨 색채 치료 추천!\n"
                response += f"🎯 선호도: {preference}\n\n"
                
                for i, color in enumerate(colors[:3], 1):
                    response += f"{i}. {color.name} ({color.hex_code})\n"
                    response += f"   💫 효과: {', '.join(color.emotion_effects[:2])}\n"
                    response += f"   🌡️ 온도감: {'따뜻함' if color.warmth > 0.6 else '차가움' if color.warmth < 0.4 else '중성'}\n\n"
                
                response += "💡 '치료 시작'으로 정식 세션을 시작할 수 있어요!"
                
                broadcast_creative_activity("color_recommendation", f"{len(colors)}개 색상 추천")
                
            elif "시작" in cmd_lower or "세션" in cmd_lower or "치료시작" in cmd_lower:
                # 치료 세션 시작
                emotion_text = "요즘 감정이 복잡하고 힘들어요"
                context = "일상 생활의 스트레스"
                
                session = self.color_therapist.create_therapy_session(emotion_text, context, "균형", 15)
                if session:
                    response = f"🎨 색채 치료 세션 시작!\n"
                    response += f"📋 세션 ID: {session.session_id}\n"
                    response += f"🎯 치료 유형: {session.therapy_type.value}\n"
                    response += f"⏰ 예상 시간: {session.session_duration}분\n"
                    response += f"💪 예상 효과: {session.effectiveness_score:.1%}\n\n"
                    
                    response += f"🎨 추천 색상:\n"
                    for color in session.recommended_colors[:2]:
                        response += f"  • {color.name} ({color.hex_code})\n"
                    
                    response += f"\n💡 '보고서 {session.session_id}'로 상세 결과를 확인하세요!"
                    
                    broadcast_creative_activity("therapy_session", f"치료 세션 {session.session_id}")
                else:
                    response = "세션 생성에 실패했습니다. 다시 시도해주세요."
            
            elif "보고서" in cmd_lower:
                # 세션 보고서 (최신 세션)
                if self.color_therapist.therapy_history:
                    latest_session_id = list(self.color_therapist.therapy_history.keys())[-1]
                    report = self.color_therapist.get_session_report(latest_session_id)
                    response = f"📋 최신 치료 세션 보고서가 생성되었습니다!\n"
                    response += "상세 내용은 콘솔에서 확인하세요."
                    
                    # 콘솔에 상세 보고서 출력
                    print(report)
                    
                    broadcast_creative_activity("therapy_report", f"세션 보고서: {latest_session_id}")
                else:
                    response = "아직 치료 세션이 없습니다. '치료 시작'으로 세션을 만들어보세요!"
                    
            elif "통계" in cmd_lower or "상태" in cmd_lower:
                # 치료사 통계
                stats = self.color_therapist.get_therapist_stats()
                response = f"🎨 색채 치료사 통계\n"
                response += f"📊 총 세션: {stats['total_sessions']}건\n"
                response += f"🎯 평균 효과: {stats['average_effectiveness']:.1%}\n"
                response += f"😊 주요 감정: {stats['most_common_emotion']}\n"
                response += f"💊 주요 치료: {stats['most_used_therapy']}\n"
                response += f"🎨 색상 DB: {stats['color_database_size']}개\n"
                response += f"⭐ 경험치: {stats['therapist_experience']:.1f}"
                
                broadcast_creative_activity("therapist_stats", f"통계 조회: {stats['total_sessions']}건")
            else:
                # 기본 색채 치료 소개
                stats = self.color_therapist.get_therapist_stats()
                response = f"🎨 감정 색채 치료사 활성화!\n"
                response += f"💫 색상 데이터베이스: {stats['color_database_size']}개 색상\n"
                response += f"📊 총 세션: {stats['total_sessions']}건\n"
                response += f"💡 명령어:\n"
                response += f"  • '감정 분석' - 현재 감정 상태 분석\n"
                response += f"  • '색 추천' - 맞춤 색상 추천\n"
                response += f"  • '치료 시작' - 정식 치료 세션 시작\n"
                response += f"  • '보고서' - 세션 결과 확인\n"
                response += f"  • '통계' - 치료사 현황"
            
            self.memory_palace.remember_conversation(cmd, response, "color_therapy")
            return response
        
        # �🎵 음악 작곡 요청
        elif any(keyword in cmd_lower for keyword in ["음악", "작곡", "멜로디", "노래"]):
            if "코드" in cmd_lower and ("음악" in cmd_lower or "작곡" in cmd_lower):
                # 코드를 음악으로 변환
                sample_code = "def hello_world():\n    for i in range(10):\n        if i % 2 == 0:\n            print(f'Hello {i}')"
                emotion = self.persona_system.current_persona
                composition = self.music_composer.compose_from_code(sample_code, emotion)
                response = self.music_composer.play_composition_text(composition)
                broadcast_creative_activity("music_composition", f"코드 기반 작곡: {composition['title']}")
            else:
                # 감정 기반 작곡
                emotion = self.persona_system.current_persona
                composition = self.music_composer.compose_by_emotion(emotion, 8)
                response = self.music_composer.play_composition_text(composition)
                broadcast_creative_activity("music_composition", f"감정 기반 작곡: {composition['title']}")
            
            self.memory_palace.remember_conversation(cmd, response, "creative")
            return response
        
        return None  # 창의적 기능에 해당하지 않음
