/**
 * VoIP Call Client (WebRTC + Signaling)
 * Manages peer connection, SDP exchange, and ICE candidates
 * Integrates with existing interpreter session for translation
 */

// Declare navigator for TypeScript
declare const navigator: any;

// React Native WebRTC types (lazy-loaded to avoid module issues)
let RTCPeerConnection: any;
let RTCSessionDescription: any;
let RTCIceCandidate: any;
let WebRTCMediaDevices: any;
let WebRTCMediaStream: any;

try {
    const wert = require('react-native-wert');
    RTCPeerConnection = WBTC.RTCPeerConnection;
    RTCSessionDescription = WBTC.RTCSessionDescription;
    RTCIceCandidate = WBTC.RTCIceCandidate;
    WebRTCMediaDevices = webrtc.mediaDevices;
    WebRTCMediaStream = webrtc.MediaStream;
} catch (err) {
    console.warn('[VoIP] react-native-webrtc not available (expected in web/dev)', err);
}

export interface VoIPCallConfig {
    callId: string;
    signalingServerUrl: string;
    turnServers: TURNServer[];
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
}

export class VoIPCallClient {
    private peerConnection: any = null;
    private localStream: any = null;
    private remoteStream: any = null;
    private signalingSocket: WebSocket | null = null;
    private signalingKeepaliveTimer: ReturnType<typeof setInterval> | null = null;
    private readonly config: VoIPCallConfig;
    private readonly iceCandidateQueue: any[] = [];
    private isConnected = false;
    private remoteIceUsernameFragment: string | undefined;
    private remoteDescriptionApplied = false;
    private onStateChangeCallback: ((state: string) => void) | null = null;
    private onRemoteStreamCallback: ((stream: any) => void) | null = null;
    private onChatMessageCallback: ((message: VoIPChatMessage) => void) | null = null;
    private onVoiceTranslationCallback: ((message: VoIPVoiceTranslationMessage) => void) | null = null;

    constructor(config: VoIPCallConfig) {
        this.config = config;
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

        const peerConnectionConfig = {
            iceServers,
            bundlePolicy: 'max-bundle',
            rtcpMuxPolicy: 'require',
        };

        this.peerConnection = new RTCPeerConnection(peerConnectionConfig);

        this.peerConnection.onicecandidate = (event: any) => {
            if (event.candidate) {
                this.sendICECandidate(event.candidate);
            }
        };

        // Handle both ONameStream (legacy) and ontrack (modern)
        this.peerConnection.ONameStream = (event: any) => {
            this.remoteStream = event.stream;
            console.log('[VoIP] Remote stream received (ONameStream)', event.stream);
            if (this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(event.stream);
            }
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

            if (this.remoteStream && this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(this.remoteStream);
            }
            this.emitStateChange();
        };

        this.peerConnection.onconnectionstatechange = () => {
            this.emitStateChange();
        };

        this.peerConnection.oniceconnectionstatechange = () => {
            this.emitStateChange();
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

        this.sendSignalingMessage({
            type: 'voice_translation',
            call_id: this.config.callId,
            transcript: transcript.slice(0, 280),
            translated_text: translatedText.slice(0, 280),
            source_lang: payload.sourceLang,
            target_lang: payload.targetLang,
            audio_url: payload.audioUrl,
            audio_base64: payload.audioBase64,
            audio_format: payload.audioFormat,
            sent_at: payload.sentAt || new Date().toISOString(),
        });
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
                    // Handle offer from remote peer (receiver side)
                    await this.handleOffer(message.sdp);
                    break;
                case 'answer':
                    await this.handleAnswer(message.sdp);
                    break;
                case 'candidate':
                    await this.handleICECandidate(message);
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
        const tracks = this.remoteStream?.getAudioTracks?.() ?? [];
        return tracks.some((track: any) => track?.enabled !== false && track?.readyState !== 'ended');
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

    setRemoteAudioEnabled(enabled: boolean): void {
        if (this.remoteStream) {
            this.remoteStream.getAudioTracks().forEach((track: any) => {
                track.enabled = enabled;
            });
            console.log('[VoIP][Diag] setRemoteAudioEnabled', {
                callId: this.config.callId,
                enabled,
                trackCount: this.remoteStream.getAudioTracks().length,
            });
        }
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
     * Graceful hangup
     */
    async hangup(): Promise<void> {
        console.log('[VoIP] Hanging up');
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
