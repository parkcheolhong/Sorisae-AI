#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
감정 기반 음악 생성기
사용자의 감정 상태를 분석하여 맞춤형 음악을 생성하는 시스템입니다.
"""

import json
import random
from datetime import datetime
from typing import Any, Dict, List


class EmotionBasedMusicGenerator:
    def __init__(self):
        # 기본 음계 및 코드 정의
        self.notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.major_scale_intervals = [0, 2, 4, 5, 7, 9, 11]
        self.minor_scale_intervals = [0, 2, 3, 5, 7, 8, 10]

        # 감정별 음악 매개변수
        self.emotion_parameters = {
            'happy': {
                'tempo': (120, 140),
                'key_mode': 'major',
                'rhythm_complexity': 'medium',
                'chord_progression': ['I', 'V', 'vi', 'IV'],
                'dynamics': 'forte',
                'articulation': 'staccato'
            },
            'sad': {
                'tempo': (60, 80),
                'key_mode': 'minor',
                'rhythm_complexity': 'simple',
                'chord_progression': ['i', 'iv', 'V', 'i'],
                'dynamics': 'piano',
                'articulation': 'legato'
            },
            'energetic': {
                'tempo': (140, 180),
                'key_mode': 'major',
                'rhythm_complexity': 'complex',
                'chord_progression': ['I', 'bVII', 'IV', 'I'],
                'dynamics': 'fortissimo',
                'articulation': 'marcato'
            },
            'calm': {
                'tempo': (70, 90),
                'key_mode': 'major',
                'rhythm_complexity': 'simple',
                'chord_progression': ['I', 'vi', 'ii', 'V'],
                'dynamics': 'mezzo-piano',
                'articulation': 'cantabile'
            }
        }

    def analyze_emotion(self, emotion_input: str, intensity: float = 0.7) -> Dict[str, Any]:
        """감정 입력을 분석하여 음악 매개변수 결정"""
        emotion_input = emotion_input.lower()

        detected_emotion = 'calm'  # 기본값
        if any(word in emotion_input for word in ['happy', 'joy', 'cheerful']):
            detected_emotion = 'happy'
        elif any(word in emotion_input for word in ['sad', 'melancholy', 'blue']):
            detected_emotion = 'sad'
        elif any(word in emotion_input for word in ['energetic', 'excited', 'dynamic']):
            detected_emotion = 'energetic'
        elif any(word in emotion_input for word in ['calm', 'peaceful', 'serene']):
            detected_emotion = 'calm'

        base_params = self.emotion_parameters[detected_emotion].copy()
        tempo_range = base_params['tempo']
        adjusted_tempo = tempo_range[0] + (tempo_range[1] - tempo_range[0]) * intensity

        return {
            'emotion': detected_emotion,
            'intensity': intensity,
            'tempo': int(adjusted_tempo),
            'parameters': base_params
        }

    def generate_melody(self, emotion_analysis: Dict[str, Any], length: int = 16) -> List[str]:
        """감정 분석 결과를 바탕으로 멜로디 생성"""
        params = emotion_analysis['parameters']
        key_mode = params['key_mode']

        if key_mode == 'major':
            scale_intervals = self.major_scale_intervals
        else:
            scale_intervals = self.minor_scale_intervals

        root_index = self.notes.index('C')
        scale_notes = []
        for interval in scale_intervals:
            note_index = (root_index + interval) % 12
            scale_notes.append(self.notes[note_index])

        melody = []
        prev_note_index = 0

        for i in range(length):
            if emotion_analysis['emotion'] == 'happy':
                step_size = random.choice([-2, -1, 1, 2, 3])
            elif emotion_analysis['emotion'] == 'sad':
                step_size = random.choice([-3, -2, -1, 0, 1])
            elif emotion_analysis['emotion'] == 'energetic':
                step_size = random.choice([-4, -3, 2, 3, 4])
            else:
                step_size = random.choice([-2, -1, 0, 1, 2])

            next_note_index = (prev_note_index + step_size) % len(scale_notes)
            melody.append(scale_notes[next_note_index])
            prev_note_index = next_note_index

        return melody

    def create_musical_composition(self, emotion_input: str, intensity: float = 0.7) -> Dict[str, Any]:
        """완전한 음악 작품 생성"""
        print(f"🎵 감정 '{emotion_input}' (강도: {intensity})를 바탕으로 음악 생성 중...")

        emotion_analysis = self.analyze_emotion(emotion_input, intensity)
        print(f"🎭 감지된 감정: {emotion_analysis['emotion']}")

        melody = self.generate_melody(emotion_analysis, 32)
        print(f"🎼 멜로디 생성 완료: {len(melody)}개 음표")

        composition = {
            'title': f"{emotion_analysis['emotion'].title()} Composition",
            'created_at': datetime.now().isoformat(),
            'emotion_analysis': emotion_analysis,
            'musical_elements': {
                'melody': melody,
                'tempo': emotion_analysis['tempo'],
                'key': 'C',
                'mode': emotion_analysis['parameters']['key_mode']
            }
        }

        return composition


def main(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """메인 실행 함수 - dispatch API용"""
    context = context or {}
    generator = EmotionBasedMusicGenerator()
    
    # context에서 감정과 강도 추출
    emotion_input = context.get('emotion', 'calm')
    intensity = context.get('intensity', 0.7)
    
    try:
        # 단일 음악 작품 생성
        composition = generator.create_musical_composition(emotion_input, intensity)
        return {
            'status': 'ok',
            'composition': composition,
            'emotion': emotion_input,
            'intensity': intensity
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'emotion': emotion_input,
            'intensity': intensity
        }


if __name__ == "__main__":
    main()
