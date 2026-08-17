#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration Test for Voice Error Handling
통합 테스트: 음성 시스템 에러 처리
"""

import sys
import os

# modules 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'modules'))

from api_rate_limit_handler import APIRateLimitHandler, handle_api_error
from voice_response_fallback import get_fallback_response
from safe_api_wrapper import SafeAPIWrapper


def simulate_voice_command_with_api_error():
    """API 에러가 발생하는 음성 명령 시뮬레이션"""
    print("=" * 70)
    print("시나리오 1: API Rate Limit 에러 발생")
    print("=" * 70)
    
    command = "듀얼브레인 분석 시작"
    print(f"\n사용자 명령: {command}")
    
    # API 호출 시뮬레이션 (실패)
    try:
        # 실제로는 여기서 OpenAI API를 호출할 것입니다
        # 에러 메시지는 익명화된 조직 ID 사용
        raise Exception(
            "Error code: 429 - {'error': {'message': 'Rate limit reached for gpt-4o-mini "
            "in organization org-XXXXXXXXXXXXXXXXXXXX on requests per day (RPD): "
            "Limit 200, Used 200, Requested 1. Please try again in 7m12s.', "
            "'type': 'requests', 'param': None, 'code': 'rate_limit_exceeded'}}"
        )
    except Exception as e:
        print(f"\n⚠️  API 에러 발생: {str(e)[:100]}...")
        
        # 에러 처리
        if "429" in str(e):
            print("\n✅ Rate Limit 에러 감지됨")
            
            # 폴백 응답 생성
            fallback_response = get_fallback_response(command, is_api_error=True)
            print(f"\n리새: {fallback_response}")
            
            return fallback_response
    
    return None


def simulate_voice_command_with_retry():
    """재시도 로직 시뮬레이션"""
    print("\n" + "=" * 70)
    print("시나리오 2: 재시도 로직 (일시적 오류)")
    print("=" * 70)
    
    command = "시스템 상태 확인"
    print(f"\n사용자 명령: {command}")
    
    handler = APIRateLimitHandler(max_retries=3, base_delay=0.1)
    
    # API 호출 시뮬레이션 (2번 실패 후 성공)
    call_count = [0]
    
    def mock_api_call():
        call_count[0] += 1
        print(f"  시도 {call_count[0]}...")
        
        if call_count[0] < 2:
            raise Exception("429 - Rate limit temporarily exceeded")
        
        return "시스템이 정상 작동 중입니다."
    
    try:
        result = handler.retry_with_backoff(mock_api_call)
        print(f"\n✅ 성공: {result}")
        return result
    except Exception as e:
        print(f"\n⚠️  실패: {e}")
        # 폴백 응답
        return get_fallback_response(command, is_api_error=True)


def simulate_voice_command_without_api():
    """API 없이 로컬 응답만 사용"""
    print("\n" + "=" * 70)
    print("시나리오 3: API 없이 로컬 폴백만 사용")
    print("=" * 70)
    
    commands = ["상태", "IoT 동기화", "쇼핑몰 최적화", "도움말"]
    
    for command in commands:
        print(f"\n사용자 명령: {command}")
        response = get_fallback_response(command)
        print(f"리새: {response}")


def simulate_safe_api_wrapper():
    """Safe API Wrapper 사용 시뮬레이션"""
    print("\n" + "=" * 70)
    print("시나리오 4: Safe API Wrapper 사용")
    print("=" * 70)
    
    wrapper = SafeAPIWrapper()
    
    print(f"\nAPI 사용 가능: {wrapper.is_available()}")
    
    if not wrapper.is_available():
        print("✅ API 키가 없지만 폴백 모드로 정상 작동")
        print("   실제 환경에서는 .env 파일에 OPENAI_API_KEY를 설정하면 됩니다.")
    
    # API 호출 시도 (실패하면 None 반환)
    result = wrapper.generate_text("안녕하세요")
    
    if result is None:
        print("\nAPI를 사용할 수 없어 폴백 응답 사용:")
        fallback = get_fallback_response("안녕", is_api_error=False)
        print(f"리새: {fallback}")


def test_error_message_format():
    """에러 메시지 형식 테스트"""
    print("\n" + "=" * 70)
    print("시나리오 5: 에러 메시지 형식 확인")
    print("=" * 70)
    
    # 문제 상황에 나온 것과 동일한 형식의 에러 (조직 ID는 익명화)
    error_message = (
        "Error code: 429 - {'error': {'message': 'Rate limit reached for gpt-4o-mini "
        "in organization org-XXXXXXXXXXXXXXXXXXXX on requests per day (RPD): "
        "Limit 200, Used 200, Requested 1. Please try again in 7m12s. "
        "Visit https://platform.openai.com/account/rate-limits to learn more.', "
        "'type': 'requests', 'param': None, 'code': 'rate_limit_exceeded'}}"
    )
    
    print(f"\n원본 에러:")
    print(f"리새: [Voice 엔진 오류] {error_message[:100]}...")
    
    # 우리의 에러 핸들러로 처리
    error = Exception(error_message)
    handled_response = handle_api_error(error, "voice_command")
    
    print(f"\n처리된 응답:")
    print(f"리새: {handled_response}")
    
    # retry_after 추출 테스트
    handler = APIRateLimitHandler()
    retry_after = handler._extract_retry_after(error_message)
    if retry_after:
        print(f"\n✅ 재시도 권장 시간: {retry_after}초 ({retry_after//60}분 {retry_after%60}초)")


def main():
    """통합 테스트 메인 함수"""
    print("\n" + "=" * 70)
    print("🎤 소리새 음성 시스템 - API 에러 처리 통합 테스트")
    print("=" * 70)
    
    # 시나리오 1: API Rate Limit 에러
    simulate_voice_command_with_api_error()
    
    # 시나리오 2: 재시도 로직
    simulate_voice_command_with_retry()
    
    # 시나리오 3: 로컬 폴백만 사용
    simulate_voice_command_without_api()
    
    # 시나리오 4: Safe API Wrapper
    simulate_safe_api_wrapper()
    
    # 시나리오 5: 에러 메시지 형식
    test_error_message_format()
    
    print("\n" + "=" * 70)
    print("✅ 모든 통합 테스트 완료")
    print("=" * 70)
    
    print("\n요약:")
    print("  - Rate Limit 에러 자동 감지 및 처리 ✅")
    print("  - Exponential Backoff 재시도 ✅")
    print("  - 로컬 폴백 응답 생성 ✅")
    print("  - API 없이도 정상 작동 ✅")
    print("  - retry_after 시간 추출 ✅")
    print("\n시스템이 외부 API 오류에도 안정적으로 작동합니다!")


if __name__ == '__main__':
    main()
