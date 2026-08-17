#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voice Response Fallback System
음성 응답 폴백 시스템 - API 실패 시 로컬 응답 제공
"""

import logging
import random
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VoiceResponseFallback:
    """
    음성 응답 폴백 시스템
    
    외부 API (OpenAI 등) 실패 시 로컬에서 적절한 응답 생성
    """
    
    def __init__(self):
        """폴백 응답 패턴 초기화"""
        self.response_patterns = {
            # 시스템 상태 관련
            "상태": [
                "시스템이 정상 작동 중입니다.",
                "모든 모듈이 정상적으로 동작하고 있습니다.",
                "현재 시스템 상태는 양호합니다.",
            ],
            "듀얼브레인": [
                "듀얼브레인 시스템을 확인하겠습니다.",
                "듀얼브레인 분석을 시작합니다.",
                "Brain A와 Brain B가 협력하여 처리합니다.",
            ],
            "분석": [
                "데이터 분석을 시작합니다.",
                "분석을 진행하겠습니다.",
                "지금 바로 분석해드리겠습니다.",
            ],
            
            # IoT 관련
            "iot": [
                "IoT 기기를 확인하겠습니다.",
                "스마트홈 시스템을 동기화합니다.",
                "연결된 기기를 점검합니다.",
            ],
            "동기화": [
                "동기화를 시작합니다.",
                "시스템을 동기화하겠습니다.",
                "동기화 작업을 진행합니다.",
            ],
            
            # 쇼핑몰 관련
            "쇼핑몰": [
                "쇼핑몰 시스템을 확인합니다.",
                "쇼핑몰 현황을 분석하겠습니다.",
                "쇼핑몰 최적화를 진행합니다.",
            ],
            "최적화": [
                "최적화를 시작합니다.",
                "시스템을 최적화하겠습니다.",
                "성능 개선을 진행합니다.",
            ],
            
            # 기본 대화
            "안녕": [
                "안녕하세요! 소리새입니다.",
                "네, 안녕하세요! 무엇을 도와드릴까요?",
                "안녕하세요! 소리새 AI 시스템입니다.",
            ],
            "도움말": [
                "음성 명령으로 시스템을 제어할 수 있습니다.",
                "상태 확인, 분석, IoT 제어 등의 명령을 사용할 수 있습니다.",
                "듀얼브레인, 쇼핑몰, 창작 등의 기능을 음성으로 제어할 수 있습니다.",
            ],
            "테스트": [
                "시스템 테스트를 시작합니다.",
                "테스트 모드로 전환합니다.",
                "기능 테스트를 진행하겠습니다.",
            ],
            
            # 창작 관련
            "창작": [
                "창작 모드를 활성화합니다.",
                "창작 도구를 준비하겠습니다.",
                "창작 경제 시스템을 시작합니다.",
            ],
            "음악": [
                "음악 시스템을 준비합니다.",
                "음악 생성 모드로 전환합니다.",
                "음악 창작을 시작하겠습니다.",
            ],
            
            # 투자 관련
            "투자": [
                "투자 분석을 시작합니다.",
                "투자 조언 시스템을 활성화합니다.",
                "시장 분석을 진행하겠습니다.",
            ],
            "주식": [
                "주식 시장을 분석합니다.",
                "주식 정보를 확인하겠습니다.",
                "투자 조언을 준비합니다.",
            ],
            
            # 오류 관련
            "오류": [
                "오류를 확인하겠습니다.",
                "문제를 해결하겠습니다.",
                "시스템을 점검합니다.",
            ],
        }
        
        # 기본 응답 (매칭되는 키워드가 없을 때)
        self.default_responses = [
            "명령을 인식했습니다. 처리하겠습니다.",
            "네, 알겠습니다. 실행하겠습니다.",
            "명령을 수행하겠습니다.",
            "바로 처리해드리겠습니다.",
        ]
        
        # API 오류 시 응답
        self.api_error_responses = [
            "죄송합니다. 현재 AI 서비스가 일시적으로 제한되어 기본 모드로 처리합니다.",
            "AI 서비스 사용량이 일시적으로 제한되었습니다. 기본 기능으로 처리하겠습니다.",
            "외부 AI 서비스에 접근할 수 없습니다. 로컬 모드로 전환합니다.",
        ]
        
        logger.info("음성 응답 폴백 시스템 초기화 완료")
    
    def get_response(self, command: str, use_default: bool = False) -> str:
        """
        명령에 대한 폴백 응답 생성
        
        Args:
            command: 사용자 음성 명령
            use_default: True이면 키워드 매칭 없이 기본 응답 반환
            
        Returns:
            적절한 폴백 응답 문자열
        """
        if use_default:
            return random.choice(self.default_responses)
        
        command_lower = command.lower()
        
        # 키워드 매칭
        for keyword, responses in self.response_patterns.items():
            if keyword in command_lower:
                response = random.choice(responses)
                logger.debug(f"폴백 응답 생성: '{keyword}' -> '{response}'")
                return response
        
        # 매칭되는 키워드가 없으면 기본 응답
        response = random.choice(self.default_responses)
        logger.debug(f"기본 폴백 응답: '{response}'")
        return response
    
    def get_api_error_response(self) -> str:
        """
        API 오류 시 응답 반환
        
        Returns:
            API 오류 관련 응답 문자열
        """
        return random.choice(self.api_error_responses)
    
    def add_pattern(self, keyword: str, responses: List[str]):
        """
        새로운 응답 패턴 추가
        
        Args:
            keyword: 매칭할 키워드
            responses: 해당 키워드에 대한 응답 목록
        """
        if keyword in self.response_patterns:
            self.response_patterns[keyword].extend(responses)
        else:
            self.response_patterns[keyword] = responses
        logger.info(f"새로운 응답 패턴 추가: {keyword}")
    
    def get_contextual_response(self, command: str, context: Optional[Dict] = None) -> str:
        """
        컨텍스트를 고려한 응답 생성
        
        Args:
            command: 사용자 명령
            context: 추가 컨텍스트 정보 (상태, 통계 등)
            
        Returns:
            컨텍스트를 반영한 응답 문자열
        """
        base_response = self.get_response(command)
        
        # 컨텍스트가 있으면 추가 정보 포함
        if context:
            if "command_count" in context:
                base_response += f" 현재까지 {context['command_count']}개의 명령을 처리했습니다."
            
            if "system_status" in context:
                base_response += f" 시스템 상태: {context['system_status']}"
        
        return base_response


# 전역 폴백 시스템 인스턴스
global_fallback_system = VoiceResponseFallback()


def get_fallback_response(command: str, context: Optional[Dict] = None, 
                          is_api_error: bool = False) -> str:
    """
    폴백 응답을 가져오는 유틸리티 함수
    
    Args:
        command: 사용자 명령
        context: 추가 컨텍스트
        is_api_error: API 오류로 인한 폴백인 경우 True
        
    Returns:
        적절한 폴백 응답
    """
    if is_api_error:
        return global_fallback_system.get_api_error_response()
    
    if context:
        return global_fallback_system.get_contextual_response(command, context)
    
    return global_fallback_system.get_response(command)
