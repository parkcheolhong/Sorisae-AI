/**
 * VoIP Call Client (WebRTC + Signaling)
 * Manages peer connection, SDP exchange, and ICE candidates
 * Integrates with existing interpreter session for translation
 */

import { Platform } from 'react-native';

import { WebRTCStatsReporter } from '../features/voip-voice-relay/webrtcStatsReporter';
import { setVoipServerBridgeActive } from './worldlincoTuningConfig';

// Declare navigator for TypeScript
declare const navigator: any;

/** Native VoIP requires this exact package name — do not typo (e.g. react-native-wert). */
const REACT_NATIVE_WEBRTC_MODULE = 'react-native-webrtc';

// React Native WebRTC (lazy-loaded; web has no native module)
let RTCPeerConnection: any;
let RTCSessionDescription: any;
let RTCIceCandidate: any;
let WebRTCMediaDevices: any;
let WebRTCMediaStream: any;

if (Platform.OS !== 'web') {
    try {
        const webrtc = require(REACT_NATIVE_WEBRTC_MODULE);
        RTCPeerConnection = webrtc.RTCPeerConnection;
        RTCSessionDescription = webrtc.RTCSessionDescription;
        RTCIceCandidate = webrtc.RTCIceCandidate;
        WebRTCMediaDevices = webrtc.mediaDevices;
        WebRTCMediaStream = webrtc.MediaStream;
        console.log('[VoIP] WebRTC module loaded', {
            module: REACT_NATIVE_WEBRTC_MODULE,
            hasPeerConnection: typeof RTCPeerConnection === 'function',
            hasMediaDevices: Boolean(WebRTCMediaDevices),
        });
    } catch (err) {
        console.warn('[VoIP] react-native-webrtc not available', err);
    }
}

export interface VoIPCallConfig {
    callId: string;
    signalingServerUrl: string;
    turnServers: TURNServer[];
    // 장거리 기준 고정: 백엔드가 'relay' 를 내려주면 릴레이 경로만 사용(VOIP_FORCE_RELAY).
    iceTransportPolicy?: 'all' | 'relay';
    // 재협상 주체 구분: 'caller'(offerer) 만 ICE 재시작 offer 를 만든다(글레어 방지). 'callee' 는 통화를 유지하며 대기.
    participantRole?: 'caller' | 'callee';
    mediaConstraints?: {
        audio: {
            echoCancellation: boolean;
            noiseSuppression: boolean;
            autoGainControl: boolean;
        };
        video: boolean;
    };
}

export interface TURNServer {
    urls: string[];
    username?: string;
    credential?: string;
}

export interface CallInitResponse {
    call_id: string;
    signaling_server: string;
    turn_servers: TURNServer[];
    ice_transport_policy?: 'all' | 'relay' | null;
    session_id?: string;
    call_route?: string;
    phone_dialer_required?: boolean;
    fallback_dial_url?: string;
    user_message?: string;
    callee_app_online?: boolean;
    caller_user_id?: number;
    caller_voice_id?: string;
    callee_voice_id?: string;
    callee_user_id?: number;
    participant_role?: 'caller' | 'callee';
    display_label?: string;
    display_language?: string;
    display_country_code?: string;
    status?: string;
    requested_mode?: string;
    resolved_mode?: string;
    auto_relay_requested?: boolean;
    auto_relay_applied?: boolean;
    error_code?: string;
}

export interface VoIPChatMessage {
    type: 'chat_message';
    call_id: string;
    text: string;
    sent_at?: string;
    client_sent_at?: string;
    from_role?: 'caller' | 'callee';
    translated_text?: string;
    source_lang?: string;
    target_lang?: string;
    translation_status?: string;
    message_id?: string;
    room_id?: string;
    sender_label?: string;
    sender_voice_id?: string;
}

export interface VoIPVoiceTranslationMessage {
    type: 'voice_translation';
    call_id: string;
    transcript: string;
    translated_text: string;
    source_lang: string;
    target_lang: string;
    audio_url?: string;
    audio_base64?: string;
    audio_format?: string;
    sent_at?: string;
    from_role?: 'caller' | 'callee';
    seq_id?: number;
    utterance_id?: string;
    chunk_index?: number;
    is_final?: boolean;
    detected_lang?: string;
    capture_trust?: string;
    correlation_id?: string;
}

// 장거리 ICE 복구 파라미터. 'disconnected' 는 일시적인 경우가 많아 잠깐 자가회복을 기다린 뒤 재시작한다.
const ICE_DISCONNECT_GRACE_MS = 2500;
const ICE_RESTART_MAX_ATTEMPTS = 4;
const ICE_RESTART_BACKOFF_BASE_MS = 2000;

export class VoIPCallClient {
    private peerConnection: any = null;
    private localStream: any = null;
    private localAudioSuspendedForRelay = false;
    private remoteStream: any = null;
    // 통역(풀오토) 통화에서 원음 WebRTC 트랙을 영구히 음소거하기 위한 상태.
    // ontrack 으로 트랙이 늦게 도착해도 이 값이 true 면 즉시 enabled=false 를 재적용한다.
    private remoteAudioSuppressed = false;
    private signalingSocket: WebSocket | null = null;
    private signalingKeepaliveTimer: ReturnType<typeof setInterval> | null = null;
    // opt-in: WebRTC QoS(RTT/jitter/loss) 표본 리포터. startStatsReporter() 호출 시에만 활성.
    private statsReporter: WebRTCStatsReporter | null = null;
    private readonly config: VoIPCallConfig;
    private readonly iceCandidateQueue: any[] = [];
    private isConnected = false;
    private remoteIceUsernameFragment: string | undefined;
    private remoteDescriptionApplied = false;
    private onStateChangeCallback: ((state: string) => void) | null = null;
    private onRemoteStreamCallback: ((stream: any) => void) | null = null;
    private onChatMessageCallback: ((message: VoIPChatMessage) => void) | null = null;
    private onChatMessageRejectedCallback: ((detail: string) => void) | null = null;
    private onVoiceTranslationCallback: ((message: VoIPVoiceTranslationMessage) => void) | null = null;
    // ICE 자동 재연결 상태(장거리 경로 변동·일시 손실 복구).
    private iceRestartAttempts = 0;
    private iceRestartInFlight = false;
    private reconnecting = false;
    private closed = false;
    private iceDisconnectGraceTimer: ReturnType<typeof setTimeout> | null = null;
    private iceRestartBackoffTimer: ReturnType<typeof setTimeout> | null = null;
    // 서버 미디어 브리지(MCU) 모드 여부 — 서버 answer(from_role='server_bridge') 수신 시 true.
    private serverBridgeMode = false;

    constructor(config: VoIPCallConfig) {
        this.config = config;
    }

    isServerBridgeMode(): boolean {
        return this.serverBridgeMode;
    }

    /**
     * Register a callback for connection state changes
     */
    onStateChange(callback: (state: string) => void): void {
        this.onStateChangeCallback = callback;
    }

    onRemoteStream(callback: (stream: any) => void): void {
        this.onRemoteStreamCallback = callback;
    }

    onChatMessage(callback: (message: VoIPChatMessage) => void): void {
        this.onChatMessageCallback = callback;
    }

    onChatMessageRejected(callback: (detail: string) => void): void {
        this.onChatMessageRejectedCallback = callback;
    }

    onVoiceTranslation(callback: (message: VoIPVoiceTranslationMessage) => void): void {
        this.onVoiceTranslationCallback = callback;
    }

    private getSocketReadyStateLabel(): string {
        if (!this.signalingSocket) {
            return 'null';
        }

        switch (this.signalingSocket.readyState) {
            case WebSocket.CONNECTING:
                return 'CONNECTING';
            case WebSocket.OPEN:
                return 'OPEN';
            case WebSocket.CLOSING:
                return 'CLOSING';
            case WebSocket.CLOSED:
                return 'CLOSED';
            default:
                return String(this.signalingSocket.readyState);
        }
    }

    private stopSignalingKeepalive(): void {
        if (this.signalingKeepaliveTimer) {
            clearInterval(this.signalingKeepaliveTimer);
            this.signalingKeepaliveTimer = null;
        }
    }

    private startSignalingKeepalive(socket: WebSocket): void {
        this.stopSignalingKeepalive();
        this.signalingKeepaliveTimer = setInterval(() => {
            if (this.signalingSocket !== socket || socket.readyState !== WebSocket.OPEN) {
                this.stopSignalingKeepalive();
                return;
            }
            try {
                socket.send(JSON.stringify({ type: 'ping', call_id: this.config.callId }));
            } catch (error) {
                console.warn('[VoIP] Keepalive ping failed', error);
                this.stopSignalingKeepalive();
            }
        }, 20000);
    }

    private summarizeSignalingMessage(message: any): Record<string, unknown> {
        return {
            type: message?.type ?? null,
            call_id: message?.call_id ?? this.config.callId,
            from_role: message?.from_role ?? null,
            has_sdp: typeof message?.sdp === 'string' && message.sdp.length > 0,
            sdp_length: typeof message?.sdp === 'string' ? message.sdp.length : 0,
            has_candidate: typeof message?.candidate === 'string' && message.candidate.length > 0,
            candidate_length: typeof message?.candidate === 'string' ? message.candidate.length : 0,
            sdp_mid: message?.sdpMid ?? null,
            sdp_Milne_index: message?.sdpMLineIndex ?? null,
            username_fragment: message?.usernameFragment ?? null,
        };
    }

    private normalizeConnectionState(rawState?: string): string {
        switch (rawState) {
            case 'completed':
                return 'connected';
            case 'new':
            case 'checking':
            case 'connecting':
            case 'have-local-offer':
            case 'have-remote-offer':
                return 'connecting';
            case 'connected':
            case 'failed':
            case 'disconnected':
                return rawState;
            case 'closed':
                return 'disconnected';
            default:
                return this.peerConnection || this.signalingSocket ? 'connecting' : 'disconnected';
        }
    }

    private getPeerConnectionState(): string {
        if (!this.peerConnection) {
            return 'disconnected';
        }

        const rawState =
            this.peerConnection.connectionState ||
            this.peerConnection.iceConnectionState ||
            this.peerConnection.signalingState;

        const normalizedState = this.normalizeConnectionState(rawState);
        if (normalizedState === 'connecting' && this.hasRemoteAudioTrack()) {
            return 'connected';
        }

        // Once remote SDP is applied, treat the call as accepted/connected phase.
        // Media may still be establishing, but ringing should stop immediately.
        if (normalizedState === 'connecting' && this.remoteDescriptionApplied) {
            return 'connected';
        }

        // 장거리 ICE 자동 재연결 중에는 통화를 끝내지 않고 'connecting'(재연결 중)으로 유지한다.
        // 재시도 예산이 소진되면 reconnecting=false 가 되어 실제 terminal 상태가 그대로 노출된다.
        if ((normalizedState === 'failed' || normalizedState === 'disconnected') && this.reconnecting) {
            return 'connecting';
        }

        return normalizedState;
    }

    private emitStateChange(): void {
        const state = this.getPeerConnectionState();
        console.log(`[VoIP] Connection state: ${state}`);
        this.isConnected = state === 'connected';
        if (this.onStateChangeCallback) {
            this.onStateChangeCallback(state);
        }
    }

    private clearIceReconnectTimers(): void {
        if (this.iceDisconnectGraceTimer) {
            clearTimeout(this.iceDisconnectGraceTimer);
            this.iceDisconnectGraceTimer = null;
        }
        if (this.iceRestartBackoffTimer) {
            clearTimeout(this.iceRestartBackoffTimer);
            this.iceRestartBackoffTimer = null;
        }
    }

    /**
     * ICE 연결 상태 변화 처리: 'disconnected'(일시적 다수)는 짧은 자가회복 유예 뒤,
     * 'failed'(영구)는 즉시 ICE 재시작을 시도한다. 통화가 한 번이라도 성립된 뒤에만 동작한다.
     */
    private handleIceConnectionStateChange(): void {
        this.emitStateChange();
        if (this.closed || !this.peerConnection) {
            return;
        }
        const ice = String(this.peerConnection.iceConnectionState || '');

        if (ice === 'connected' || ice === 'completed') {
            // 복구 완료 — 재시도 카운터/타이머 초기화.
            this.clearIceReconnectTimers();
            if (this.reconnecting || this.iceRestartAttempts > 0) {
                console.log('[VoIP] ICE recovered — connection restored');
            }
            this.iceRestartAttempts = 0;
            this.iceRestartInFlight = false;
            this.reconnecting = false;
            return;
        }

        // 통화가 성립되기 전(초기 협상 단계)에는 재시작하지 않는다(초기 실패는 상위에서 처리).
        if (!this.remoteDescriptionApplied) {
            return;
        }

        if (ice === 'disconnected') {
            if (!this.iceDisconnectGraceTimer && !this.iceRestartInFlight) {
                this.iceDisconnectGraceTimer = setTimeout(() => {
                    this.iceDisconnectGraceTimer = null;
                    const cur = String(this.peerConnection?.iceConnectionState || '');
                    if (cur === 'disconnected' || cur === 'failed') {
                        this.beginIceRestart('disconnected-grace-elapsed');
                    }
                }, ICE_DISCONNECT_GRACE_MS);
            }
            return;
        }

        if (ice === 'failed') {
            this.beginIceRestart('failed');
        }
    }

    /**
     * ICE 재시작 시작. 글레어 방지를 위해 offerer('caller')만 재협상 offer 를 만든다.
     * callee 는 통화를 유지(reconnecting)하며 caller 의 재시작 offer 를 기다린다.
     */
    private beginIceRestart(reason: string): void {
        if (this.closed || !this.peerConnection) {
            return;
        }
        if (this.iceRestartInFlight) {
            return;
        }
        if (this.iceRestartAttempts >= ICE_RESTART_MAX_ATTEMPTS) {
            // 재시도 예산 소진 — 실제 terminal 상태를 노출(통화 종료 허용).
            this.reconnecting = false;
            this.emitStateChange();
            return;
        }

        if (this.config.participantRole === 'callee') {
            // 콜리는 직접 재협상하지 않고 통화를 유지하며 대기(caller 의 재시작 offer 로 handleOffer 재협상).
            this.reconnecting = true;
            this.emitStateChange();
            return;
        }

        this.iceRestartInFlight = true;
        this.reconnecting = true;
        this.iceRestartAttempts += 1;
        const attempt = this.iceRestartAttempts;
        console.warn(`[VoIP] ICE restart attempt ${attempt}/${ICE_RESTART_MAX_ATTEMPTS} (reason=${reason})`);
        this.emitStateChange();

        this.performIceRestartOffer()
            .catch((err) => console.warn('[VoIP] ICE restart offer failed', err))
            .finally(() => {
                this.iceRestartInFlight = false;
                this.scheduleIceRestartRetry();
            });
    }

    private async performIceRestartOffer(): Promise<void> {
        if (!this.peerConnection) {
            return;
        }
        if (typeof this.peerConnection.restartIce === 'function') {
            try {
                this.peerConnection.restartIce();
            } catch {
                // restartIce 미지원/실패 시 iceRestart 옵션으로 대체.
            }
        }
        const offer = await this.peerConnection.createOffer({
            offerToReceiveAudio: true,
            offerToReceiveVideo: false,
            iceRestart: true,
        });
        await this.peerConnection.setLocalDescription(offer);
        this.sendSignalingMessage({
            type: 'offer',
            call_id: this.config.callId,
            sdp: offer.sdp,
            ice_restart: true,
        });
        console.log('[VoIP] ICE restart offer sent');
    }

    private scheduleIceRestartRetry(): void {
        if (this.closed || this.iceRestartBackoffTimer) {
            return;
        }
        const cur = String(this.peerConnection?.iceConnectionState || '');
        if (cur === 'connected' || cur === 'completed') {
            return;
        }
        if (this.iceRestartAttempts >= ICE_RESTART_MAX_ATTEMPTS) {
            // 예산 소진 — terminal 노출.
            this.reconnecting = false;
            this.emitStateChange();
            return;
        }
        const backoff = ICE_RESTART_BACKOFF_BASE_MS * this.iceRestartAttempts;
        this.iceRestartBackoffTimer = setTimeout(() => {
            this.iceRestartBackoffTimer = null;
            const c = String(this.peerConnection?.iceConnectionState || '');
            if (c !== 'connected' && c !== 'completed') {
                this.beginIceRestart('retry');
            }
        }, backoff);
    }

    /**
     * Initialize WebRTC peer connection with TURN servers
     */
    async initializePeerConnection(): Promise<void> {
        if (!RTCPeerConnection) {
            throw new Error('react-native-webrtc not available');
        }

        const iceServers = this.config.turnServers.map((turn) => {
            const server: { urls: string[]; username?: string; credential?: string } = { urls: turn.urls };
            if (turn.username != null) server.username = turn.username;
            if (turn.credential != null) server.credential = turn.credential;
            return server;
        });

        const peerConnectionConfig: {
            iceServers: typeof iceServers;
            bundlePolicy: string;
            rtcpMuxPolicy: string;
            iceTransportPolicy?: 'all' | 'relay';
        } = {
            iceServers,
            bundlePolicy: 'max-bundle',
            rtcpMuxPolicy: 'require',
        };
        // 장거리 기준 고정: 백엔드가 'relay' 를 지정하면 릴레이만 사용(같은 LAN 테스트도 동일 경로).
        if (this.config.iceTransportPolicy === 'relay') {
            peerConnectionConfig.iceTransportPolicy = 'relay';
        }

        this.peerConnection = new RTCPeerConnection(peerConnectionConfig);

        this.peerConnection.onicecandidate = (event: any) => {
            if (event.candidate) {
                this.sendICECandidate(event.candidate);
            }
        };

        // Handle both onaddstream (legacy) and ontrack (modern)
        this.peerConnection.onaddstream = (event: any) => {
            this.remoteStream = event.stream;
            console.log('[VoIP] Remote stream received (onaddstream)', event.stream);
            this.applyRemoteAudioSuppression('onaddstream');
            if (this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(event.stream);
            }
            this.emitStateChange();
        };

        this.peerConnection.ontrack = (event: any) => {
            console.log('[VoIP] Track received (ontrack)', event.track.kind);
            const incomingStream = event.streams?.[0];
            if (incomingStream) {
                this.remoteStream = incomingStream;
            } else {
                if (!this.remoteStream) {
                    this.remoteStream = WebRTCMediaStream ? new WebRTCMediaStream() : null;
                }

                if (this.remoteStream?.addTrack && event.track) {
                    const existingTrackIds = new Set(
                        (this.remoteStream.getTracks?.() ?? [])
                            .map((track: any) => track?.id)
                            .filter(Boolean),
                    );
                    if (!existingTrackIds.has(event.track.id)) {
                        this.remoteStream.addTrack(event.track);
                    }
                }
            }

            // 트랙이 늦게 도착해도(예: 연결 후 수 초 뒤 ontrack) 통역 모드면 즉시 원음을 음소거한다.
            // 과거에는 setRemoteAudioEnabled(false) 가 트랙 도착 전에 호출돼 무효화되고,
            // 이후 도착한 원격 오디오 트랙이 enabled=true 상태로 그대로 재생되는 버그가 있었다.
            this.applyRemoteAudioSuppression('ontrack');

            if (this.remoteStream && this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(this.remoteStream);
            }
            this.emitStateChange();
        };

        this.peerConnection.onconnectionstatechange = () => {
            this.emitStateChange();
        };

        this.peerConnection.oniceconnectionstatechange = () => {
            this.handleIceConnectionStateChange();
        };

        this.peerConnection.onsignalingstatechange = () => {
            this.emitStateChange();
        };
    }

    /**
     * Extract ICE username fragment from SDP.
     */
    private extractIceUsernameFragment(sdp?: string): string | undefined {
        if (!sdp) return undefined;
        const match = sdp.match(/a=ice-ufrag:([^\r\n]+)/);
        return match?.[1]?.trim();
    }

    /**
     * Extract ICE username fragment from candidate line when present.
     */
    private extractIceUfragFromCandidate(candidate?: string): string | undefined {
        if (!candidate) return undefined;
        const match = candidate.match(/\bufrag\s+([^\s]+)/);
        return match?.[1]?.trim();
    }

    /**
     * Acquire local audio stream (mic) with echo cancellation
     */
    async getLocalStream(): Promise<any> {
        const constraints = this.config.mediaConstraints || {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
            video: false,
        };

        try {
            console.log('[VoIP] Getting local stream with constraints:', constraints);
            const mediaDevices = WebRTCMediaDevices || (navigator as any).mediaDevices;
            console.log('[VoIP] mediaDevices available:', !!mediaDevices);

            if (!mediaDevices || typeof mediaDevices.getUserMedia !== 'function') {
                throw new Error('mediaDevices.getUserMedia not available');
            }

            console.log('[VoIP] Calling getUserMedia...');
            this.localStream = await mediaDevices.getUserMedia(constraints);
            console.log('[VoIP] Local stream acquired successfully', {
                tracks: this.localStream.getTracks(),
                audioTracks: this.localStream.getAudioTracks(),
                trackCount: this.localStream.getTracks().length,
            });

            // Add local tracks to peer connection
            if (this.peerConnection && this.localStream) {
                console.log('[VoIP] Adding local tracks to peer connection...');
                this.localStream.getTracks().forEach((track: any) => {
                    if (this.peerConnection && this.localStream) {
                        const sender = this.peerConnection.addTrack(track, this.localStream);
                        console.log('[VoIP] Track added:', { kind: track.kind, enabled: track.enabled, sender: !!sender });
                    }
                });
                console.log('[VoIP] All tracks added to peer connection');
            }

            return this.localStream;
        } catch (err) {
            console.error('[VoIP] Failed to acquire local stream', { error: String(err), errorMsg: (err as any).message });
            throw err;
        }
    }

    /**
     * Create offer (caller side) and send to signaling server
     */
    async createAndSendOffer(): Promise<void> {
        if (!this.peerConnection) {
            throw new Error('PeerConnection not initialized');
        }

        try {
            const offer = await this.peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: false,
            });

            await this.peerConnection.setLocalDescription(offer);

            this.sendSignalingMessage({
                type: 'offer',
                call_id: this.config.callId,
                sdp: offer.sdp,
            });

            console.log('[VoIP] Offer sent', offer);
        } catch (err) {
            console.error('[VoIP] Failed to create offer', err);
            throw err;
        }
    }

    /**
     * Handle answer from remote peer (signaling server relays from media relay)
     */
    async handleAnswer(answerSDP: string): Promise<void> {
        if (!this.peerConnection) {
            throw new Error('PeerConnection not initialized');
        }

        try {
            const answer = {
                type: 'answer',
                sdp: answerSDP,
            };

            await this.peerConnection.setRemoteDescription(answer);
            this.remoteIceUsernameFragment = this.extractIceUsernameFragment(answerSDP);
            this.remoteDescriptionApplied = true;
            console.log('[VoIP] Answer applied', answerSDP);
            this.emitStateChange();
        } catch (err) {
            console.error('[VoIP] Failed to handle answer', err);
            throw err;
        }
    }

    /**
     * Send ICE candidate to remote peer via signaling server
     */
    private sendICECandidate(candidate: any): void {
        if (this.signalingSocket && this.signalingSocket.readyState === WebSocket.OPEN) {
            this.sendSignalingMessage({
                type: 'candidate',
                call_id: this.config.callId,
                candidate: candidate.candidate,
                sdpMLineIndex: candidate.sdpMLineIndex,
                sdpMid: candidate.sdpMid,
            });
        } else {
            // Queue candidates until signaling channel is ready.
            this.iceCandidateQueue.push(candidate);
        }
    }

    /**
     * Handle incoming ICE candidate from remote peer
     */
    async handleICECandidate(candidateData: any): Promise<void> {
        if (!this.peerConnection) {
            throw new Error('PeerConnection not initialized');
        }

        try {
            const usernameFragment =
                candidateData.usernameFragment ||
                this.remoteIceUsernameFragment ||
                this.extractIceUfragFromCandidate(candidateData.candidate);

            const candidateInit = {
                candidate: candidateData.candidate,
                sdpMLineIndex: candidateData.sdpMLineIndex,
                sdpMid: candidateData.sdpMid,
                usernameFragment,
            };

            const candidate = RTCIceCandidate
                ? new RTCIceCandidate(candidateInit)
                : candidateInit;

            await this.peerConnection.addIceCandidate(candidate);
            console.log('[VoIP] ICE candidate added', candidateInit);
        } catch (err) {
            console.error('[VoIP] Failed to add ICE candidate', err, candidateData);
        }
    }

    /**
     * Flush queued ICE candidates after connection established
     */
    private flushICECandidateQueue(): void {
        console.log(`[VoIP] Flushing ${this.iceCandidateQueue.length} queued ICE candidates`);
        while (this.iceCandidateQueue.length > 0) {
            const candidate = this.iceCandidateQueue.shift();
            if (candidate) {
                this.sendICECandidate(candidate);
            }
        }
    }

    /**
     * Send message via signaling WebSocket
     */
    private sendSignalingMessage(message: any): void {
        if (this.signalingSocket && this.signalingSocket.readyState === WebSocket.OPEN) {
            this.signalingSocket.send(JSON.stringify(message));
            console.log('[VoIP] Signaling message sent', message);
            console.log('[VoIP][Diag] sendSignalingMessage:sent', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                summary: this.summarizeSignalingMessage(message),
            });
        } else {
            console.warn('[VoIP] Signaling socket not ready', message);
            console.warn('[VoIP][Diag] sendSignalingMessage:not-ready', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                summary: this.summarizeSignalingMessage(message),
            });
        }
    }

    sendChatMessage(text: string, sentAt: string = new Date().toISOString()): boolean {
        const normalized = text.trim();
        if (!normalized || !this.signalingSocket || this.signalingSocket.readyState !== WebSocket.OPEN) {
            return false;
        }

        this.sendSignalingMessage({
            type: 'chat_message',
            call_id: this.config.callId,
            text: normalized.slice(0, 280),
            sent_at: sentAt,
        });
        return true;
    }

    sendVoiceTranslation(payload: {
        transcript: string;
        translatedText: string;
        sourceLang: string;
        targetLang: string;
        audioUrl?: string;
        audioBase64?: string;
        audioFormat?: string;
        sentAt?: string;
        seqId?: number;
        utteranceId?: string;
        chunkIndex?: number;
        isFinal?: boolean;
        detectedLang?: string;
        captureTrust?: string;
        correlationId?: string;
    }): boolean {
        const transcript = payload.transcript.trim();
        const translatedText = payload.translatedText.trim();
        if (!transcript || !translatedText || !this.signalingSocket || this.signalingSocket.readyState !== WebSocket.OPEN) {
            console.warn('[VoIP][Diag] sendVoiceTranslation:blocked', {
                callId: this.config.callId,
                transcriptLength: transcript.length,
                translatedLength: translatedText.length,
                hasSocket: !!this.signalingSocket,
                socketState: this.getSocketReadyStateLabel(),
            });
            return false;
        }

        // Stenographer relay: text ledger over WS only (audio_base64 breaks WS size limits).
        const message: Record<string, unknown> = {
            type: 'voice_translation',
            call_id: this.config.callId,
            transcript: transcript.slice(0, 280),
            translated_text: translatedText.slice(0, 280),
            source_lang: payload.sourceLang,
            target_lang: payload.targetLang,
            sent_at: payload.sentAt || new Date().toISOString(),
            tts_delivery: 'device_speech',
        };
        if (typeof payload.seqId === 'number' && Number.isFinite(payload.seqId)) {
            message.seq_id = payload.seqId;
        }
        if (typeof payload.utteranceId === 'string' && payload.utteranceId.trim()) {
            message.utterance_id = payload.utteranceId.trim().slice(0, 128);
        }
        if (typeof payload.chunkIndex === 'number' && Number.isFinite(payload.chunkIndex)) {
            message.chunk_index = Math.max(0, Math.floor(payload.chunkIndex));
        }
        if (typeof payload.isFinal === 'boolean') {
            message.is_final = payload.isFinal;
        }
        if (typeof payload.detectedLang === 'string' && payload.detectedLang.trim()) {
            message.detected_lang = payload.detectedLang.trim().slice(0, 32);
        }
        if (typeof payload.captureTrust === 'string' && payload.captureTrust.trim()) {
            message.capture_trust = payload.captureTrust.trim().slice(0, 16);
        }
        if (typeof payload.correlationId === 'string' && payload.correlationId.trim()) {
            // V.2 ID 백본 — 전송(딜리버리) 채널로 상관 ID 전파(수신측 음성 발화가 동일 ID에 붙음).
            message.correlation_id = payload.correlationId.trim().slice(0, 128);
        }
        this.sendSignalingMessage(message);
        return true;
    }

    /**
     * Connect to signaling server via WebSocket
     */
    async connectSignaling(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                let settled = false;
                let opened = false;
                let lastErrorType: string | null = null;
                console.log(`[VoIP][DiagLine] connectSignaling:start callId=${this.config.callId} state=${this.getSocketReadyStateLabel()}`);
                console.log('[VoIP][Diag] connectSignaling:start', {
                    callId: this.config.callId,
                    signalingServerUrl: this.config.signalingServerUrl,
                    socketState: this.getSocketReadyStateLabel(),
                });
                const socket = new WebSocket(this.config.signalingServerUrl);
                this.signalingSocket = socket;

                socket.onopen = () => {
                    if (this.signalingSocket !== socket) {
                        return;
                    }
                    console.log('[VoIP] Signaling connected');
                    console.log(`[VoIP][DiagLine] connectSignaling:open callId=${this.config.callId} state=${this.getSocketReadyStateLabel()} queuedIce=${this.iceCandidateQueue.length}`);
                    console.log('[VoIP][Diag] connectSignaling:open', {
                        callId: this.config.callId,
                        socketState: this.getSocketReadyStateLabel(),
                        queuedIceCandidates: this.iceCandidateQueue.length,
                    });
                    opened = true;
                    settled = true;
                    this.startSignalingKeepalive(this.signalingSocket as WebSocket);
                    this.flushICECandidateQueue();
                    resolve();
                };

                socket.onmessage = (event: any) => {
                    if (this.signalingSocket !== socket) {
                        return;
                    }
                    try {
                        const rawData = typeof event?.data === 'string' ? event.data : String(event?.data ?? '');
                        console.log(`[VoIP][DiagLine] connectSignaling:onmessage callId=${this.config.callId} state=${this.getSocketReadyStateLabel()} rawLength=${rawData.length}`);
                        console.log('[VoIP][Diag] connectSignaling:onmessage', {
                            callId: this.config.callId,
                            socketState: this.getSocketReadyStateLabel(),
                            rawLength: rawData.length,
                            rawPreview: rawData.slice(0, 240),
                        });
                        const message = JSON.parse(event.data);
                        this.handleSignalingMessage(message);
                    } catch (err) {
                        console.error('[VoIP] Failed to parse signaling message', err);
                    }
                };

                socket.onerror = (error: Event) => {
                    if (this.signalingSocket !== socket) {
                        return;
                    }
                    lastErrorType = error?.type ?? 'unknown';
                    console.warn('[VoIP] Signaling error event observed', {
                        type: lastErrorType,
                        opened,
                    });
                    console.warn('[VoIP][Diag] connectSignaling:error-event', {
                        callId: this.config.callId,
                        socketState: this.getSocketReadyStateLabel(),
                        errorType: lastErrorType,
                        opened,
                    });
                };

                socket.onclose = (event: any) => {
                    if (this.signalingSocket !== socket) {
                        console.log('[VoIP][Diag] connectSignaling:close:stale-socket-ignored', {
                            callId: this.config.callId,
                            code: event?.code ?? null,
                            reason: event?.reason ?? '',
                            wasClean: event?.wasClean ?? null,
                        });
                        return;
                    }
                    console.log('[VoIP] Signaling closed');
                    console.log('[VoIP][Diag] connectSignaling:close', {
                        callId: this.config.callId,
                        socketState: this.getSocketReadyStateLabel(),
                        code: event?.code ?? null,
                        reason: event?.reason ?? '',
                        wasClean: event?.wasClean ?? null,
                    });
                    this.stopSignalingKeepalive();
                    this.isConnected = false;
                    if (this.onStateChangeCallback) {
                        this.onStateChangeCallback('disconnected');
                    }
                    if (!settled && !opened) {
                        settled = true;
                        const reason = typeof event?.reason === 'string' && event.reason.trim()
                            ? event.reason.trim()
                            : lastErrorType || 'websocket closed before open';
                        reject(new Error(`VoIP signaling 연결 실패 (${reason}, code=${event?.code ?? 'unknown'})`));
                    }
                };
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Handle incoming signaling messages
     */
    private async handleSignalingMessage(message: any): Promise<void> {
        try {
            const messageType = typeof message?.type === 'string' ? message.type.trim().toLowerCase() : '';
            console.log('[VoIP][Diag] handleSignalingMessage:dispatch', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                summary: this.summarizeSignalingMessage(message),
                normalizedType: messageType || null,
            });
            switch (messageType) {
                case 'offer':
                    // 서버 미디어 브리지(MCU)에서 callee 는 서버가 보낸 offer 를 받는다(§13/MB-5):
                    // P2P 와 달리 발신측 offer 가 아니라 'server_bridge' offer 이므로, 여기서도
                    // 브리지 모드를 켜야 callee 가 라이브 연속 음성 + 서버측 통역을 받게 된다.
                    if (message.from_role === 'server_bridge') {
                        this.serverBridgeMode = true;
                        setVoipServerBridgeActive(true);
                        console.log('[VoIP] server media bridge mode active (callee/offer)', { callId: this.config.callId });
                    }
                    // Handle offer from remote peer (receiver side)
                    await this.handleOffer(message.sdp);
                    break;
                case 'answer':
                    // 서버 미디어 브리지(MCU) answer 면 브리지 모드 활성화(§13/MB-5):
                    // 라이브 연속 음성 + 서버측 STT/번역/TTS. 클라 로컬 STT 는 중단된다.
                    if (message.from_role === 'server_bridge') {
                        this.serverBridgeMode = true;
                        setVoipServerBridgeActive(true);
                        console.log('[VoIP] server media bridge mode active', { callId: this.config.callId });
                    }
                    await this.handleAnswer(message.sdp);
                    break;
                case 'candidate':
                    await this.handleICECandidate(message);
                    break;
                case 'chat_message_rejected':
                    this.onChatMessageRejectedCallback?.(
                        typeof message.detail === 'string' && message.detail.trim()
                            ? message.detail.trim()
                            : '지정 언어와 다른 메시지는 전송할 수 없습니다.',
                    );
                    break;
                case 'chat_message':
                    if (typeof message.text === 'string' && message.text.trim()) {
                        this.onChatMessageCallback?.({
                            type: 'chat_message',
                            call_id: message.call_id || this.config.callId,
                            text: message.text.trim(),
                            sent_at: message.sent_at,
                            client_sent_at: typeof message.client_sent_at === 'string' ? message.client_sent_at.trim() : undefined,
                            from_role: message.from_role === 'callee' ? 'callee' : 'caller',
                            translated_text: typeof message.translated_text === 'string' ? message.translated_text.trim() : undefined,
                            source_lang: typeof message.source_lang === 'string' ? message.source_lang.trim() : undefined,
                            target_lang: typeof message.target_lang === 'string' ? message.target_lang.trim() : undefined,
                            translation_status: typeof message.translation_status === 'string' ? message.translation_status.trim() : undefined,
                            message_id: typeof message.message_id === 'string' ? message.message_id.trim() : undefined,
                            room_id: typeof message.room_id === 'string' ? message.room_id.trim() : undefined,
                            sender_label: typeof message.sender_label === 'string' ? message.sender_label.trim() : undefined,
                            sender_voice_id: typeof message.sender_voice_id === 'string' ? message.sender_voice_id.trim() : undefined,
                        });
                    }
                    break;
                case 'voice_translation':
                    if (typeof message.transcript === 'string' && message.transcript.trim() && typeof message.translated_text === 'string' && message.translated_text.trim()) {
                        this.onVoiceTranslationCallback?.({
                            type: 'voice_translation',
                            call_id: message.call_id || this.config.callId,
                            transcript: message.transcript.trim(),
                            translated_text: message.translated_text.trim(),
                            source_lang: String(message.source_lang || ''),
                            target_lang: String(message.target_lang || ''),
                            audio_url: typeof message.audio_url === 'string' ? message.audio_url : undefined,
                            audio_base64: typeof message.audio_base64 === 'string' ? message.audio_base64 : undefined,
                            audio_format: typeof message.audio_format === 'string' ? message.audio_format : undefined,
                            sent_at: message.sent_at,
                            from_role: message.from_role === 'callee' ? 'callee' : 'caller',
                            seq_id: typeof message.seq_id === 'number' ? message.seq_id : undefined,
                            utterance_id: typeof message.utterance_id === 'string' ? message.utterance_id.trim() : undefined,
                            chunk_index: typeof message.chunk_index === 'number' ? message.chunk_index : undefined,
                            is_final: typeof message.is_final === 'boolean' ? message.is_final : undefined,
                            detected_lang: typeof message.detected_lang === 'string' ? message.detected_lang.trim() : undefined,
                            capture_trust: typeof message.capture_trust === 'string' ? message.capture_trust.trim() : undefined,
                            correlation_id: typeof message.correlation_id === 'string' ? message.correlation_id.trim() : undefined,
                        });
                    }
                    break;
                case 'pong':
                    console.log('[VoIP][Diag] handleSignalingMessage:pong', {
                        callId: this.config.callId,
                        socketState: this.getSocketReadyStateLabel(),
                    });
                    break;
                case 'hangup':
                    await this.hangup();
                    break;
                default:
                    console.log('[VoIP][Diag] Unknown signaling message type ignored', {
                        callId: this.config.callId,
                        rawType: message?.type ?? null,
                        normalizedType: messageType || null,
                    });
            }
        } catch (err) {
            console.error('[VoIP] Error handling signaling message', err);
        }
    }

    /**
     * Handle offer from remote peer and send answer (callee side)
     */
    private async handleOffer(offerSDP: string): Promise<void> {
        if (!this.peerConnection) {
            throw new Error('PeerConnection not initialized');
        }

        try {
            console.log(`[VoIP][DiagLine] handleOffer:start callId=${this.config.callId} state=${this.getSocketReadyStateLabel()} offerLength=${offerSDP?.length ?? 0}`);
            console.log('[VoIP][Diag] handleOffer:start', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                peerConnectionState: this.peerConnection.connectionState,
                iceConnectionState: this.peerConnection.iceConnectionState,
                signalingState: this.peerConnection.signalingState,
                offerLength: offerSDP?.length ?? 0,
            });
            const offer = {
                type: 'offer',
                sdp: offerSDP,
            };

            // Set remote description with offer
            await this.peerConnection.setRemoteDescription(offer);
            this.remoteIceUsernameFragment = this.extractIceUsernameFragment(offerSDP);
            this.remoteDescriptionApplied = true;
            console.log('[VoIP] Offer received and set as remote description', offerSDP);
            console.log('[VoIP][Diag] handleOffer:setRemoteDescription:done', {
                callId: this.config.callId,
                remoteIceUsernameFragment: this.remoteIceUsernameFragment ?? null,
                peerConnectionState: this.peerConnection.connectionState,
                iceConnectionState: this.peerConnection.iceConnectionState,
                signalingState: this.peerConnection.signalingState,
            });

            // Create answer
            const answer = await this.peerConnection.createAnswer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: false,
            });
            console.log('[VoIP][Diag] handleOffer:createAnswer:done', {
                callId: this.config.callId,
                answerType: answer?.type ?? null,
                answerLength: answer?.sdp?.length ?? 0,
            });

            // Set local description with answer
            await this.peerConnection.setLocalDescription(answer);
            console.log('[VoIP] Answer created', answer);
            console.log('[VoIP][Diag] handleOffer:setLocalDescription:done', {
                callId: this.config.callId,
                peerConnectionState: this.peerConnection.connectionState,
                iceConnectionState: this.peerConnection.iceConnectionState,
                signalingState: this.peerConnection.signalingState,
                localDescriptionType: this.peerConnection.localDescription?.type ?? null,
                localDescriptionLength: this.peerConnection.localDescription?.sdp?.length ?? 0,
            });

            // Send answer back to remote peer
            this.sendSignalingMessage({
                type: 'answer',
                call_id: this.config.callId,
                sdp: answer.sdp,
            });

            console.log('[VoIP] Answer sent to remote peer');
            console.log('[VoIP][Diag] handleOffer:answer-sent', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                answerLength: answer?.sdp?.length ?? 0,
            });
            this.emitStateChange();
        } catch (err) {
            console.error('[VoIP] Failed to handle offer and create answer', err);
            console.error('[VoIP][Diag] handleOffer:error', {
                callId: this.config.callId,
                socketState: this.getSocketReadyStateLabel(),
                peerConnectionState: this.peerConnection.connectionState,
                iceConnectionState: this.peerConnection.iceConnectionState,
                signalingState: this.peerConnection.signalingState,
                remoteDescriptionType: this.peerConnection.remoteDescription?.type ?? null,
                localDescriptionType: this.peerConnection.localDescription?.type ?? null,
                error: err instanceof Error ? err.message : String(err),
            });
            throw err;
        }
    }

    /**
     * Get remote audio stream
     */
    getRemoteStream(): any {
        return this.remoteStream;
    }

    hasRemoteAudioTrack(): boolean {
        const isLiveAudioTrack = (track: any): boolean => (
            track?.kind === 'audio'
            && track?.enabled !== false
            && track?.readyState !== 'ended'
            && track?.readyState !== 'failed'
        );

        const streamTracks = this.remoteStream?.getAudioTracks?.() ?? [];
        if (streamTracks.some(isLiveAudioTrack)) {
            return true;
        }

        const receivers = this.peerConnection?.getReceivers?.() ?? [];
        return receivers.some((receiver: any) => isLiveAudioTrack(receiver?.track));
    }

    /**
     * Mute/unmute local audio
     */
    setLocalAudioEnabled(enabled: boolean): void {
        if (this.localStream) {
            this.localStream.getAudioTracks().forEach((track: any) => {
                track.enabled = enabled;
            });
        }
    }

    suspendLocalAudioForVoiceRelay(): void {
        if (!this.localStream || this.localAudioSuspendedForRelay) {
            return;
        }

        this.localAudioSuspendedForRelay = true;
        this.localStream.getAudioTracks().forEach((track: any) => {
            track.enabled = false;
            track.stop();
        });

        if (this.peerConnection) {
            this.peerConnection.getSenders().forEach((sender: any) => {
                if (sender.track?.kind === 'audio') {
                    void sender.replaceTrack(null);
                }
            });
        }

        this.localStream = null;
        console.log('[VoIP][Diag] suspendLocalAudioForVoiceRelay', {
            callId: this.config.callId,
            connectionState: this.getConnectionState(),
        });
    }

    async restoreLocalAudioAfterVoiceRelay(): Promise<void> {
        if (!this.localAudioSuspendedForRelay || !this.peerConnection) {
            return;
        }

        const constraints = this.config.mediaConstraints || {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
            video: false,
        };

        try {
            const mediaDevices = WebRTCMediaDevices || (navigator as any).mediaDevices;
            if (!mediaDevices || typeof mediaDevices.getUserMedia !== 'function') {
                throw new Error('mediaDevices.getUserMedia not available');
            }

            const stream = await mediaDevices.getUserMedia(constraints);
            const track = stream.getAudioTracks()[0];
            const sender = this.peerConnection.getSenders().find((candidate: any) => (
                candidate.track == null || candidate.track?.kind === 'audio'
            ));

            if (sender && track) {
                await sender.replaceTrack(track);
            } else if (track) {
                this.peerConnection.addTrack(track, stream);
            }

            this.localStream = stream;
            this.localAudioSuspendedForRelay = false;
            console.log('[VoIP][Diag] restoreLocalAudioAfterVoiceRelay', {
                callId: this.config.callId,
                connectionState: this.getConnectionState(),
                trackCount: stream.getAudioTracks().length,
            });
        } catch (err) {
            this.localAudioSuspendedForRelay = false;
            console.error('[VoIP] Failed to restore local audio after voice relay', err);
            throw err;
        }
    }

    setRemoteAudioEnabled(enabled: boolean): void {
        // 원하는 억제 상태를 영구 저장한다. 트랙이 아직 없더라도 상태를 기억했다가
        // ontrack/onaddstream 에서 applyRemoteAudioSuppression() 으로 재적용한다.
        this.remoteAudioSuppressed = !enabled;
        const tracks = this.remoteStream?.getAudioTracks?.() ?? [];
        tracks.forEach((track: any) => {
            track.enabled = enabled;
        });
        console.log('[VoIP][Diag] setRemoteAudioEnabled', {
            callId: this.config.callId,
            enabled,
            suppressed: this.remoteAudioSuppressed,
            trackCount: tracks.length,
            hadStream: !!this.remoteStream,
        });
    }

    /**
     * 현재 저장된 억제 상태(remoteAudioSuppressed)를 원격 오디오 트랙에 (재)적용한다.
     * 트랙이 늦게 도착하는 react-native-webrtc 의 ontrack 타이밍 문제를 보정하기 위해
     * onaddstream/ontrack 콜백에서 매번 호출한다.
     */
    private applyRemoteAudioSuppression(reason: string): void {
        if (!this.remoteStream) {
            return;
        }
        const tracks = this.remoteStream.getAudioTracks?.() ?? [];
        if (tracks.length === 0) {
            return;
        }
        const enabled = !this.remoteAudioSuppressed;
        let changed = false;
        tracks.forEach((track: any) => {
            if (track.enabled !== enabled) {
                track.enabled = enabled;
                changed = true;
            }
        });
        if (this.remoteAudioSuppressed || changed) {
            console.log('[VoIP][Diag] applyRemoteAudioSuppression', {
                callId: this.config.callId,
                reason,
                suppressed: this.remoteAudioSuppressed,
                enabled,
                trackCount: tracks.length,
                changed,
            });
        }
    }

    isRemoteAudioSuppressed(): boolean {
        return this.remoteAudioSuppressed;
    }

    getSignalingStateSnapshot(): { hasSocket: boolean; socketState: string; connectionState: string; hasRemoteAudio: boolean } {
        return {
            hasSocket: !!this.signalingSocket,
            socketState: this.getSocketReadyStateLabel(),
            connectionState: this.getPeerConnectionState(),
            hasRemoteAudio: this.hasRemoteAudioTrack(),
        };
    }

    /**
     * opt-in: WebRTC QoS(RTT/jitter/loss/bitrate) 표본을 백엔드로 주기 보고(off-path, fail-open).
     * 화면/훅이 연결 성공 후 명시적으로 호출할 때만 활성화된다(미호출 시 완전 비활성 → 통화 동작 무변경).
     * 기술서 §0.22.5 / 체크리스트 §10.3.
     */
    startStatsReporter(opts: {
        apiBaseUrl: string;
        authToken: string;
        role: 'caller' | 'callee' | string;
        intervalMs?: number;
    }): void {
        try {
            if (this.statsReporter || !this.peerConnection) {
                return;
            }
            const pc = this.peerConnection;
            if (typeof pc.getStats !== 'function') {
                return;
            }
            this.statsReporter = new WebRTCStatsReporter({
                apiBaseUrl: opts.apiBaseUrl,
                authToken: opts.authToken,
                callId: this.config.callId,
                role: opts.role,
                intervalMs: opts.intervalMs,
                getStats: () => pc.getStats(),
            });
            this.statsReporter.start();
            console.log('[VoIP] stats reporter started', { callId: this.config.callId, role: opts.role });
        } catch (err) {
            console.warn('[VoIP] startStatsReporter skipped', err);
        }
    }

    private stopStatsReporter(): void {
        try {
            this.statsReporter?.stop();
        } catch {
            // off-path — 무시
        }
        this.statsReporter = null;
    }

    /**
     * Graceful hangup
     */
    async hangup(): Promise<void> {
        console.log('[VoIP] Hanging up');
        this.closed = true;
        this.reconnecting = false;
        this.iceRestartInFlight = false;
        // 통화 단위 런타임 플래그 해제(다음 통화가 P2P 일 수 있음).
        if (this.serverBridgeMode) {
            this.serverBridgeMode = false;
            setVoipServerBridgeActive(false);
        }
        this.clearIceReconnectTimers();
        this.stopStatsReporter();
        this.remoteDescriptionApplied = false;

        // Stop local tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach((track: any) => {
                track.stop();
            });
            this.localStream = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        // Close signaling socket
        if (this.signalingSocket) {
            this.stopSignalingKeepalive();
            this.signalingSocket.close();
            this.signalingSocket = null;
        }

        this.isConnected = false;
        if (this.onStateChangeCallback) {
            this.onStateChangeCallback('disconnected');
        }
    }

    /**
     * Get connection state
     */
    getConnectionState(): string {
        return this.getPeerConnectionState();
    }
}
