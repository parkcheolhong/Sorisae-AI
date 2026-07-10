"""Regression tests for Whisper near-silence hallucination signature filtering.

실통화(call-624f6b60ac75) 로그에서 한국어 근접무음 환각 "통역 문장"→"翻訳文" 이 seq 4·6·9
로 반복 생성·relay 되어 상대에게 같은 문구가 중복 발화되던 문제를 차단하는 시그니처를 검증한다.
"""

from __future__ import annotations

import pytest

from backend.llm.router import _is_whisper_hallucination_phrase


@pytest.mark.parametrize(
    "transcript",
    [
        "통역 문장",
        "통역문장",
        " 통역  문장 .",
        "한국어 자막 by 한효주",
        "자막 제공",
        "자막을 사용하였습니다",
        # 기존 유튜브 아웃트로 계열(회귀 보존)
        "시청해 주셔서 감사합니다",
        "ご視聴ありがとうございました",
        "thank you for watching",
        "请不吝点赞 订阅 转发 打赏 支持明镜与点点栏目",
        "좋아요, 구독, 공유, 후원을 부탁드립니다",
        "词曲 李宗盛",
        "작사 작곡 김종성",
        "多谢您收睇時局新聞,再會!",
        "多谢您收睇時局新聞",
        "시국 뉴스를 보시고 감사합니다, 다음에 또 만나요!",
        "자막 · 좋아요, 구독, 공유, 후원을 부탁드립니다",
    ],
)
def test_blocks_near_silence_hallucinations(transcript: str) -> None:
    assert _is_whisper_hallucination_phrase(transcript) is True


@pytest.mark.parametrize(
    "transcript",
    [
        "지금 어디쯤 오고 계세요",
        "통역 부탁드립니다 문장이 좀 길어요",  # '통역'·'문장'이 섞여도 메타 단어 단독이 아니면 통과
        "식사하시죠 형님",
        "오늘 날씨가 참 좋네요",
    ],
)
def test_allows_real_conversation(transcript: str) -> None:
    assert _is_whisper_hallucination_phrase(transcript) is False
