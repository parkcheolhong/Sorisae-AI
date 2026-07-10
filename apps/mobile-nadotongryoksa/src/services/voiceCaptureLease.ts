// [기능 분리 Phase2] 마이크 단일 소유 lease (VoiceCaptureService 커널).
//
// 마스터 기술서 §2-1 단일-활성 계약(R1): "한 시점에 마이크 캡처를 가진 기능은 단 하나."
// 음성 캡처(startVoiceInput)를 쓰는 기능 — 대면통역(face) / 소리새(sorisae) / 일반전화(inter_call)
// / 노래(song) — 은 캡처를 시작하기 전에 이 lease 를 acquire 한다. 다른 기능이 acquire 하면
// 직전 소유자의 revoke 콜백(자기 캡처 정지)이 자동 호출되어, 두 기능이 동시에 마이크를 잡는
// 일이 원천 차단된다. (VoIP 통화는 WebRTC 자체 오디오 경로라 이 lease 와 무관 — 통화 종료
// 부작용을 막기 위해 의도적으로 포함하지 않는다.)
//
// 순수 모듈(React 비의존) — 테스트/재사용 용이. 콘솔 태그 [VOICE_LEASE] 로 소유권 전이를 관측.

export type VoiceCaptureFeatureId = 'face' | 'sorisae' | 'inter_call' | 'song';

import {
    clearActiveAudioEngine,
    transitionToAudioEngine,
} from './audioEngineKernel';

type RevokeFn = () => void;

let currentOwner: VoiceCaptureFeatureId | null = null;
let currentRevoke: RevokeFn | null = null;

/**
 * 마이크 캡처 소유권 획득. 직전 소유자가 다른 기능이면 그 기능의 revoke(정지)를 먼저 호출한다.
 * @param featureId 새 소유 기능
 * @param onRevoke  이후 다른 기능이 acquire 할 때 호출될 '이 기능 캡처 정지' 콜백
 */
export function acquireVoiceCapture(featureId: VoiceCaptureFeatureId, onRevoke: RevokeFn): void {
    if (currentOwner === featureId) {
        currentRevoke = onRevoke;
        return;
    }

    const prevOwner = currentOwner;
    const prevRevoke = currentRevoke;

    transitionToAudioEngine(featureId, 'voice_capture_acquire', {
        stopPrevious: () => {
            if (prevOwner && prevRevoke) {
                currentOwner = null;
                currentRevoke = null;
                try {
                    prevRevoke();
                } catch {
                    /* revoke 실패는 무시(새 소유자 진입을 막지 않는다) */
                }
                // eslint-disable-next-line no-console
                console.log('[VOICE_LEASE]', JSON.stringify({ event: 'revoke', prev: prevOwner, next: featureId }));
            }
        },
        startNext: () => {
            currentOwner = featureId;
            currentRevoke = onRevoke;
        },
    });

    // eslint-disable-next-line no-console
    console.log('[VOICE_LEASE]', JSON.stringify({ event: 'acquire', owner: featureId }));
}

/** 소유권 반납(자기 기능이 캡처를 끝냈을 때). 다른 기능이 소유 중이면 무시한다. */
export function releaseVoiceCapture(featureId: VoiceCaptureFeatureId): void {
    if (currentOwner === featureId) {
        currentOwner = null;
        currentRevoke = null;
        clearActiveAudioEngine(featureId, 'voice_capture_release');
        // eslint-disable-next-line no-console
        console.log('[VOICE_LEASE]', JSON.stringify({ event: 'release', owner: featureId }));
    }
}

/** 현재 마이크 소유 기능(없으면 null). */
export function currentVoiceCaptureOwner(): VoiceCaptureFeatureId | null {
    return currentOwner;
}

/**
 * [Phase4] 현재 소유자를 강제 정지(revoke)시킨다 — 단일-활성 라우터가 기능 전환(레일 변경) 시
 * 직전 음성 기능을 정지(quiesce)시킬 때 사용한다. 소유자가 없으면 무시.
 */
export function revokeCurrentVoiceCapture(reason: string = 'feature_switch'): void {
    if (currentOwner && currentRevoke) {
        const prevOwner = currentOwner;
        const prevRevoke = currentRevoke;
        currentOwner = null;
        currentRevoke = null;
        clearActiveAudioEngine(prevOwner, reason);
        try {
            prevRevoke();
        } catch {
            /* revoke 실패 무시 */
        }
        // eslint-disable-next-line no-console
        console.log('[VOICE_LEASE]', JSON.stringify({ event: 'revoke_current', prev: prevOwner, reason }));
    }
}
