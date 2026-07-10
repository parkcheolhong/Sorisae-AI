import {
    disableConversationAudio,
    enableConversationCaptureAudio,
    enableConversationPlaybackAudio,
} from '../shared/audioRouteKernel';

export async function enableFaceConversationAudio(): Promise<void> {
    // Capture 시작 시 speakerphone=true 를 강제하면 일부 삼성/OEM 단말에서
    // far-field 성향 라우팅이 잡혀 가까운 큰 목소리를 오히려 덜 잘 듣는 경향이 있다.
    // 소리새/대면통역 capture 는 통신 모드만 유지하고, 입력 라우팅은 수화기 쪽(false)으로 둔다.
    await enableConversationCaptureAudio();
}

export async function enableFaceConversationPlaybackAudio(): Promise<void> {
    // 통역 발화는 통신 캡처용 저음량 경로(false,false)에 남아 있으면
    // 사용자가 '소리가 죽었다'고 느낄 만큼 작아질 수 있다.
    // 재생 직전에는 스피커폰 + 통화 볼륨 최대를 강제해 체감 음량을 회복한다.
    await enableConversationPlaybackAudio();
}

export async function disableFaceConversationAudio(): Promise<void> {
    await disableConversationAudio();
}
