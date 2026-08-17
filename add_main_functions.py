"""8개 엔진 파일 main() 함수 추가 (main() 없는 파일들)"""
import os

ENGINES_DIR = r"C:\Users\WORK\source\repos\parkcheolhong\codeAI\backend\services\shinsegye\engines120"

additions = {
    'slot019_music_chat_friend_system.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 음악 채팅 친구 시스템"""
    context = context or {}
    user_id = str(context.get('user_id', 'user001'))
    target_id = str(context.get('target_id', 'user002'))
    try:
        system = get_friend_system()
        request = system.send_friend_request(user_id, target_id)
        friends = list(system.friend_connections.get(user_id, {}).keys())
        return {
            'status': 'ok',
            'user_id': user_id,
            'friend_request_sent': target_id,
            'request_id': request.request_id if hasattr(request, 'request_id') else str(request),
            'current_friends': friends[:5],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot104_future_prediction_engine.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 미래 예측 엔진"""
    context = context or {}
    focus_area = str(context.get('focus_area', '기술'))
    timeframe = str(context.get('timeframe', '5년'))
    try:
        engine = FuturePredictionEngine()
        analysis = engine.analyze_future_trends(focus_area=focus_area, timeframe=timeframe)
        return {
            'status': 'ok',
            'focus_area': focus_area,
            'timeframe': timeframe,
            'key_insights': analysis.get('key_insights', [])[:3],
            'confidence': analysis.get('confidence', 0),
            'trend_count': len(analysis.get('trends', [])),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot010_dream_interpreter.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 꿈 해석"""
    context = context or {}
    dream_text = str(context.get('dream_text', '하늘을 나는 꿈을 꿨다. 빛나는 별들 사이를 자유롭게 날아다녔다.'))
    try:
        interpreter = DreamInterpreter()
        analysis = interpreter.analyze_dream(dream_text)
        return {
            'status': 'ok',
            'dream_text': dream_text[:100],
            'analysis': analysis if isinstance(analysis, dict) else {'result': str(analysis)},
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot093_emotion_color_therapist.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 감정 색채 치료"""
    context = context or {}
    emotion_text = str(context.get('emotion_text', '요즘 많이 지치고 힘들어요'))
    try:
        therapist = EmotionColorTherapist()
        emotion_analysis = therapist.analyze_emotion(emotion_text)
        colors = therapist.recommend_colors(emotion_analysis)
        return {
            'status': 'ok',
            'input_text': emotion_text,
            'emotion_detected': emotion_analysis.get('primary_emotion', '알 수 없음') if isinstance(emotion_analysis, dict) else str(emotion_analysis),
            'recommended_colors': [
                {'name': c.name, 'hex': c.hex_code, 'effect': c.therapeutic_effect}
                for c in (colors[:3] if hasattr(colors, '__iter__') else [])
            ],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot044_sorisae_iot_smarthome.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 스마트홈 IoT"""
    context = context or {}
    try:
        result = test_iot_system()
        if isinstance(result, dict):
            return {'status': 'ok', **result}
        return {'status': 'ok', 'result': str(result)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot081_realtime_game_generator.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 실시간 게임 생성"""
    context = context or {}
    command = str(context.get('command', '새 게임을 시작해줘'))
    try:
        result = create_game_response(command)
        if isinstance(result, dict):
            return {'status': 'ok', **result}
        return {'status': 'ok', 'response': str(result)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot050_cyber_detective_ai.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 사이버 탐정 AI"""
    context = context or {}
    try:
        result = demo_cyber_detective()
        if isinstance(result, dict):
            return {'status': 'ok', **result}
        return {'status': 'ok', 'demo_result': str(result) if result else '탐정 AI 초기화 완료'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
    'slot061_spatiotemporal_learning_system_new.py': '''

def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 시공간 학습 시스템"""
    context = context or {}
    try:
        result = test_spatiotemporal_system()
        if isinstance(result, dict):
            return {'status': 'ok', **result}
        return {'status': 'ok', 'result': str(result) if result else '시공간 학습 시스템 실행 완료'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
''',
}

os.chdir(ENGINES_DIR)

for filename, new_main in additions.items():
    filepath = os.path.join(ENGINES_DIR, filename)
    with open(filepath) as f:
        content = f.read()

    # Check if main already exists
    if 'def main(' in content:
        print(f'SKIP {filename}: main() already exists')
        continue

    # Append before if __name__ == '__main__' or at end
    if 'if __name__' in content:
        idx = content.rfind('\nif __name__')
        new_content = content[:idx] + new_main + content[idx:]
    else:
        new_content = content + new_main

    with open(filepath, 'w') as f:
        f.write(new_content)

    print(f'OK {filename}: main() appended')

print('Done')
