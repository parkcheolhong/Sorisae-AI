import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';

/**
 * VoIP Tone Service
 * Handles DTMF tones (dial), ringback tones (calling), and ringing tones (incoming)
 * Uses Web Audio API for web and Expo AV generated WAV tones for React Native.
 */

export type ToneType = 'dial' | 'ringback' | 'ringing' | 'dtmf' | 'message';

/**
 * DTMF (Dual-Tone Multi-Frequency) frequencies
 * Used for phone keypad sounds
 */
const DTMF_FREQUENCIES: Record<string, [number, number]> = {
  '0': [941, 1336],
  '1': [697, 1209],
  '2': [697, 1336],
  '3': [697, 1477],
  '4': [770, 1209],
  '5': [770, 1336],
  '6': [770, 1477],
  '7': [852, 1209],
  '8': [852, 1336],
  '9': [852, 1477],
  '*': [941, 1209],
  '#': [941, 1477],
};

/**
 * Standard tone frequencies and patterns
 */
const TONE_CONFIG: Record<ToneType, { freq1: number; freq2?: number; duration: number; interval?: number }> = {
  // 발신음 (Ringback tone): 한국 표준 440Hz + 480Hz, 1초 울림 + 2초 침묵
  ringback: { freq1: 440, freq2: 480, duration: 1000, interval: 3000 },
  
  // 수신음 (Ringing tone): 한국 표준 440Hz + 480Hz, 0.8초 울림 + 0.2초 침묵 + 0.8초 울림 + 1.2초 침묵
  ringing: { freq1: 440, freq2: 480, duration: 800, interval: 3000 },
  
  // 다이얼 톤 (Dial tone): 350Hz + 440Hz, 연속음
  dial: { freq1: 350, freq2: 440, duration: 100, interval: 0 },
  
  // DTMF (각 숫자마다 다름, 70ms 표준)
  dtmf: { freq1: 0, duration: 70, interval: 100 },

  // 채팅 알림음: 짧은 1회 알림
  message: { freq1: 880, freq2: 1320, duration: 180, interval: 0 },
};

// Type definitions for Web Audio API (used only in web environment)
type AudioContextType = any; // Avoid TS2304 - AudioContext undefined
type OscillatorNodeType = any;
type GainNodeType = any;

export class VoIPToneService {
  private audioContext: AudioContextType | null = null;
  private oscillators: OscillatorNodeType[] = [];
  private gains: GainNodeType[] = [];
  private isPlaying: boolean = false;
  private currentTimeoutId: NodeJS.Timeout | null = null;
  private isWebEnvironment: boolean = false;
  private nativeSound: Audio.Sound | null = null;
  private nativeToneUriCache: Record<string, string> = {};
  private nativePlaybackRequestId: number = 0;

  constructor() {
    this.initAudioContext();
  }

  /**
   * 초기화: AudioContext 생성 (Web only)
   */
  private initAudioContext(): void {
    // Check if we're in a web environment with AudioContext support
    const audioContextCtor = (globalThis as { AudioContext?: new () => AudioContextType }).AudioContext;
    if (audioContextCtor) {
      try {
        this.audioContext = new audioContextCtor();
        this.isWebEnvironment = true;
        console.log('[VoIPToneService] AudioContext initialized for web environment');
      } catch (error) {
        console.warn('[VoIPToneService] AudioContext initialization failed:', error);
        this.isWebEnvironment = false;
      }
    } else {
      // React Native or non-web environment
      console.log('[VoIPToneService] AudioContext not available (React Native environment)');
      this.isWebEnvironment = false;
    }
  }

  /**
   * 발신음 재생 (전화를 거는 중)
   * 한국 표준: 440Hz + 480Hz, 1초 울림, 2초 침묵 반복
   */
  playRingbackTone(): void {
    if (!this.isWebEnvironment) {
      void this.playNativeLoopingTone('ringback');
      return;
    }
    if (this.isPlaying) return;
    this.isPlaying = true;
    this._playRepeatingTone('ringback');
  }

  /**
   * 수신음 재생 (전화 벨소리)
   * 한국 표준: 440Hz + 480Hz, 0.8초 울림 패턴
   */
  playRingingTone(): void {
    if (!this.isWebEnvironment) {
      void this.playNativeLoopingTone('ringing');
      return;
    }
    if (this.isPlaying) return;
    this.isPlaying = true;
    this._playRepeatingTone('ringing');
  }

  /**
   * 다이얼 톤 재생 (받음음)
   * 350Hz + 440Hz, 연속음
   */
  playDialTone(): void {
    if (!this.isWebEnvironment) {
      void this.playNativeLoopingTone('dial');
      return;
    }
    if (this.isPlaying) return;
    this.isPlaying = true;
    this._playRepeatingTone('dial');
  }

  /**
   * DTMF 톤 재생 (키패드 음)
   * @param digit 0-9, *, #
   */
  playDTMFTone(digit: string): void {
    if (!this.isWebEnvironment) {
      void this.playNativeDTMFTone(digit);
      return;
    }
    if (!DTMF_FREQUENCIES[digit]) return;
    
    const [freq1, freq2] = DTMF_FREQUENCIES[digit];
    this._playDTMF(freq1, freq2);
  }

  playMessageTone(): void {
    if (!this.isWebEnvironment) {
      void this.playNativeOneShotTone('message');
      return;
    }

    const config = TONE_CONFIG.message;
    this._playTone(config.freq1, config.freq2, config.duration);
  }

  /**
   * 모든 톤 정지
   */
  stopAll(): void {
    this.isPlaying = false;
    this.nativePlaybackRequestId += 1;

    void this.stopNativeTone();

    if (!this.isWebEnvironment) {
      return;
    }
    
    if (this.currentTimeoutId) {
      clearTimeout(this.currentTimeoutId);
      this.currentTimeoutId = null;
    }

    this.oscillators.forEach((osc) => {
      try {
        osc.stop(this.audioContext!.currentTime);
      } catch {
        // 이미 정지됨
      }
    });
    this.oscillators = [];
    this.gains = [];
  }

  private async playNativeLoopingTone(toneType: ToneType): Promise<void> {
    if (this.isPlaying) return;
    this.isPlaying = true;
    const requestId = ++this.nativePlaybackRequestId;

    try {
      const uri = await this.getNativeToneUri(toneType);
      if (!uri || !this.isPlaying || requestId !== this.nativePlaybackRequestId) return;

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: false,
        playThroughEarpieceAndroid: false,
        staysActiveInBackground: false,
      });
      if (!this.isPlaying || requestId !== this.nativePlaybackRequestId) return;

      await this.stopNativeTone();
      if (!this.isPlaying || requestId !== this.nativePlaybackRequestId) return;
      const { sound } = await Audio.Sound.createAsync(
        { uri },
        { shouldPlay: true, isLooping: true, volume: 0.35 }
      );
      if (!this.isPlaying || requestId !== this.nativePlaybackRequestId) {
        try {
          await sound.stopAsync();
        } catch {
          // Already stopped.
        }
        try {
          await sound.unloadAsync();
        } catch {
          // Already unloaded.
        }
        return;
      }
      this.nativeSound = sound;
    } catch (error) {
      console.warn('[VoIPToneService] Native tone playback failed:', error);
      if (requestId === this.nativePlaybackRequestId) {
        this.isPlaying = false;
      }
    }
  }

  private async playNativeDTMFTone(digit: string): Promise<void> {
    if (!DTMF_FREQUENCIES[digit]) return;

    try {
      const uri = await this.getNativeToneUri('dtmf', digit);
      if (!uri) return;
      const { sound } = await Audio.Sound.createAsync(
        { uri },
        { shouldPlay: true, isLooping: false, volume: 0.35 }
      );
      sound.setOnPlaybackStatusUpdate((status) => {
        if ('didJustFinish' in status && status.didJustFinish) {
          sound.unloadAsync().catch(() => {});
        }
      });
    } catch (error) {
      console.warn('[VoIPToneService] Native DTMF playback failed:', error);
    }
  }

  private async playNativeOneShotTone(toneType: ToneType): Promise<void> {
    try {
      const uri = await this.getNativeToneUri(toneType);
      if (!uri) return;
      const { sound } = await Audio.Sound.createAsync(
        { uri },
        { shouldPlay: true, isLooping: false, volume: 0.35 }
      );
      sound.setOnPlaybackStatusUpdate((status) => {
        if ('didJustFinish' in status && status.didJustFinish) {
          sound.unloadAsync().catch(() => {});
        }
      });
    } catch (error) {
      console.warn(`[VoIPToneService] Native ${toneType} playback failed:`, error);
    }
  }

  private async stopNativeTone(): Promise<void> {
    if (!this.nativeSound) return;
    const sound = this.nativeSound;
    this.nativeSound = null;
    try {
      await sound.stopAsync();
    } catch {
      // Already stopped.
    }
    try {
      await sound.unloadAsync();
    } catch {
      // Already unloaded.
    }
  }

  private async getNativeToneUri(toneType: ToneType, dtmfDigit?: string): Promise<string | null> {
    if (!FileSystem.cacheDirectory) return null;
    const cacheKey = dtmfDigit ? `dtmf-${dtmfDigit}` : toneType;
    if (this.nativeToneUriCache[cacheKey]) {
      return this.nativeToneUriCache[cacheKey] ?? null;
    }

    const uri = `${FileSystem.cacheDirectory}voip-tone-${cacheKey}.wav`;
    const base64 = this.createToneWavBase64(toneType, dtmfDigit);
    await FileSystem.writeAsStringAsync(uri, base64, { encoding: FileSystem.EncodingType.Base64 });
    this.nativeToneUriCache[cacheKey] = uri;
    return uri;
  }

  private createToneWavBase64(toneType: ToneType, dtmfDigit?: string): string {
    const sampleRate = 8000;
    const config = TONE_CONFIG[toneType];
    const totalMs = toneType === 'dtmf' ? config.duration : Math.max(config.duration, config.interval || config.duration);
    const toneMs = config.duration;
    const sampleCount = Math.floor(sampleRate * totalMs / 1000);
    const dataSize = sampleCount * 2;
    const bytes = new Uint8Array(44 + dataSize);
    const view = new DataView(bytes.buffer);

    this.writeAscii(bytes, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    this.writeAscii(bytes, 8, 'WAVE');
    this.writeAscii(bytes, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    this.writeAscii(bytes, 36, 'data');
    view.setUint32(40, dataSize, true);

    const toneSampleLimit = Math.floor(sampleRate * toneMs / 1000);
    const [dtmfFreq1, dtmfFreq2] = dtmfDigit ? DTMF_FREQUENCIES[dtmfDigit] : [config.freq1, config.freq2];
    const freq1 = dtmfFreq1;
    const freq2 = dtmfFreq2;

    for (let index = 0; index < sampleCount; index += 1) {
      let sample = 0;
      if (index < toneSampleLimit) {
        const t = index / sampleRate;
        const wave1 = Math.sin(2 * Math.PI * freq1 * t);
        const wave2 = freq2 ? Math.sin(2 * Math.PI * freq2 * t) : wave1;
        sample = Math.max(-1, Math.min(1, (wave1 + wave2) / 2)) * 0.45;
      }
      view.setInt16(44 + index * 2, Math.floor(sample * 32767), true);
    }

    return this.bytesToBase64(bytes);
  }

  private writeAscii(bytes: Uint8Array, offset: number, text: string): void {
    for (let index = 0; index < text.length; index += 1) {
      bytes[offset + index] = text.charCodeAt(index);
    }
  }

  private bytesToBase64(bytes: Uint8Array): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let output = '';
    for (let index = 0; index < bytes.length; index += 3) {
      const byte1 = bytes[index];
      const byte2 = bytes[index + 1];
      const byte3 = bytes[index + 2];
      output += chars[byte1 >> 2];
      output += chars[((byte1 & 3) << 4) | ((byte2 ?? 0) >> 4)];
      output += index + 1 < bytes.length ? chars[((byte2 & 15) << 2) | ((byte3 ?? 0) >> 6)] : '=';
      output += index + 2 < bytes.length ? chars[(byte3 ?? 0) & 63] : '=';
    }
    return output;
  }

  /**
   * 반복 톤 재생 (발신음, 수신음)
   */
  private _playRepeatingTone(toneType: ToneType): void {
    if (!this.audioContext) {
      this.initAudioContext();
      if (!this.audioContext) return;
    }

    const config = TONE_CONFIG[toneType];
    const playOnce = () => {
      if (!this.isPlaying) return;

      this._playTone(config.freq1, config.freq2, config.duration);

      // 반복 간격이 있으면 다음 톤 예약
      if (config.interval && config.interval > 0) {
        this.currentTimeoutId = setTimeout(() => {
          playOnce();
        }, config.interval);
      }
    };

    playOnce();
  }

  /**
   * DTMF 톤 재생
   */
  private _playDTMF(freq1: number, freq2: number): void {
    if (!this.audioContext) {
      this.initAudioContext();
      if (!this.audioContext) return;
    }

    const config = TONE_CONFIG.dtmf;
    this._playTone(freq1, freq2, config.duration);

    // DTMF는 일단만 재생 후 자동 정지
    setTimeout(() => {
      this.stopAll();
    }, config.duration + 50);
  }

  /**
   * 기본 톤 재생
   */
  private _playTone(freq1: number, freq2?: number, duration: number = 100): void {
    if (!this.audioContext) return;

    try {
      const ctx = this.audioContext;
      const now = ctx.currentTime;

      // Gain node (음량 조절)
      const gainNode = ctx.createGain();
      gainNode.connect(ctx.destination);
      gainNode.gain.setValueAtTime(0.2, now); // 20% 음량 (청각 보호)

      // 첫 번째 주파수
      const osc1 = ctx.createOscillator();
      osc1.frequency.value = freq1;
      osc1.type = 'sine';
      osc1.connect(gainNode);
      osc1.start(now);
      osc1.stop(now + duration / 1000);

      this.oscillators.push(osc1);
      this.gains.push(gainNode);

      // 두 번째 주파수 (있으면)
      if (freq2) {
        const osc2 = ctx.createOscillator();
        osc2.frequency.value = freq2;
        osc2.type = 'sine';
        osc2.connect(gainNode);
        osc2.start(now);
        osc2.stop(now + duration / 1000);

        this.oscillators.push(osc2);
      }
    } catch (error) {
      console.error('[VoIPToneService] Error playing tone:', error);
    }
  }

  /**
   * 정리: 모든 리소스 해제
   */
  dispose(): void {
    this.stopAll();
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
  }
}

// 싱글톤 인스턴스
let toneServiceInstance: VoIPToneService | null = null;

/**
 * VoIPToneService 싱글톤 획득
 */
export function getVoIPToneService(): VoIPToneService {
  if (!toneServiceInstance) {
    toneServiceInstance = new VoIPToneService();
  }
  return toneServiceInstance;
}
