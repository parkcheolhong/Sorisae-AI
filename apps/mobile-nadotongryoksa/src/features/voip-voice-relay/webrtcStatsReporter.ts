/**
 * WebRTC QoS 표본 리포터 (P2P RTP 지연 측정 — 기술서 §0.22.5 / 체크리스트 §10.3).
 *
 * P2P + TURN 구조는 서버측 RTP 중계 지점이 없으므로, 각 단말이 RTCPeerConnection.getStats()
 * 로 RTT/jitter/loss/bitrate 를 주기 표본화해 백엔드(POST /api/v1/voip/webrtc-stats)로 보고한다.
 * 백엔드는 off-path Prometheus 히스토그램으로 집계한다.
 *
 * 원칙: **off-path · opt-in · fail-open** — 표본 수집/전송 실패가 통화 경로에 절대 영향을 주지 않는다.
 * 수집 항목은 수치 QoS 뿐이며 식별정보(PII)는 보내지 않는다.
 */

/** getStats()가 돌려주는 RTCStatsReport(Map 유사) 또는 통계 객체 배열. */
type StatsLike =
  | { forEach: (cb: (value: any, key?: any) => void) => void }
  | any[]
  | null
  | undefined;

/** 손실률 누적 카운터(델타 계산용). */
export interface WebRTCStatsCounters {
  packetsReceived: number;
  packetsLost: number;
}

/** 한 번의 표본(없으면 필드 생략). */
export interface WebRTCStatsSample {
  rttMs?: number;
  jitterMs?: number;
  packetLossRatio?: number; // 0..1 (직전 표본 대비 수신 손실)
  outgoingBitrateBps?: number;
}

export interface WebRTCStatsExtraction {
  sample: WebRTCStatsSample;
  counters: WebRTCStatsCounters;
}

function _iterateStats(report: StatsLike, cb: (s: any) => void): void {
  if (!report) {
    return;
  }
  const anyReport = report as any;
  if (typeof anyReport.forEach === 'function') {
    anyReport.forEach((value: any) => cb(value));
    return;
  }
  if (Array.isArray(anyReport)) {
    anyReport.forEach((value: any) => cb(value));
  }
}

function _num(v: any): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

/**
 * RTCStatsReport → 표본 추출(순수함수). 손실률은 직전 누적 카운터(prev)와의 델타로 계산.
 *
 * 우선순위:
 * - RTT: candidate-pair(nominated/succeeded) currentRoundTripTime, 없으면 remote-inbound roundTripTime
 * - jitter: inbound-rtp(audio) jitter (초)
 * - loss: inbound-rtp(audio) 누적 packetsLost/packetsReceived 의 델타 비율
 * - bitrate: candidate-pair availableOutgoingBitrate
 * 모든 단위는 WebRTC 표준(초·bps)이며 출력 RTT/jitter는 ms로 변환.
 */
export function extractWebRTCStatsSample(
  report: StatsLike,
  prev?: WebRTCStatsCounters,
): WebRTCStatsExtraction {
  let rttSec: number | undefined;
  let remoteRttSec: number | undefined;
  let jitterSec: number | undefined;
  let outgoingBitrate: number | undefined;
  let packetsReceived = 0;
  let packetsLost = 0;
  let sawInbound = false;

  _iterateStats(report, (s: any) => {
    if (!s || typeof s !== 'object') {
      return;
    }
    const type = String(s.type ?? '');
    const kind = String(s.kind ?? s.mediaType ?? '');

    if (type === 'candidate-pair') {
      const selected =
        s.nominated === true || s.selected === true || s.state === 'succeeded';
      if (selected) {
        rttSec = _num(s.currentRoundTripTime) ?? rttSec;
        outgoingBitrate = _num(s.availableOutgoingBitrate) ?? outgoingBitrate;
      }
    } else if (type === 'inbound-rtp' && (kind === 'audio' || kind === '')) {
      jitterSec = _num(s.jitter) ?? jitterSec;
      const recv = _num(s.packetsReceived);
      const lost = _num(s.packetsLost);
      if (recv !== undefined) {
        packetsReceived += recv;
        sawInbound = true;
      }
      if (lost !== undefined) {
        packetsLost += lost;
        sawInbound = true;
      }
    } else if (type === 'remote-inbound-rtp') {
      remoteRttSec = _num(s.roundTripTime) ?? remoteRttSec;
    }
  });

  const counters: WebRTCStatsCounters = { packetsReceived, packetsLost };
  const sample: WebRTCStatsSample = {};

  const effectiveRtt = rttSec ?? remoteRttSec;
  if (effectiveRtt !== undefined) {
    sample.rttMs = effectiveRtt * 1000;
  }
  if (jitterSec !== undefined) {
    sample.jitterMs = jitterSec * 1000;
  }
  if (outgoingBitrate !== undefined) {
    sample.outgoingBitrateBps = outgoingBitrate;
  }
  if (sawInbound && prev) {
    const dRecv = packetsReceived - prev.packetsReceived;
    const dLost = packetsLost - prev.packetsLost;
    const denom = dRecv + dLost;
    if (denom > 0 && dLost >= 0) {
      sample.packetLossRatio = Math.min(1, Math.max(0, dLost / denom));
    }
  }

  return { sample, counters };
}

/** 표본에 실제 보고할 값이 하나라도 있는지. */
export function hasReportableStats(sample: WebRTCStatsSample): boolean {
  return (
    sample.rttMs !== undefined ||
    sample.jitterMs !== undefined ||
    sample.packetLossRatio !== undefined ||
    sample.outgoingBitrateBps !== undefined
  );
}

/** 백엔드로 표본 1건 전송(fail-open). 성공 시 true. */
export async function postWebRTCStats(
  apiBaseUrl: string,
  authToken: string,
  callId: string,
  role: string,
  sample: WebRTCStatsSample,
  fetchImpl: typeof fetch = fetch,
): Promise<boolean> {
  if (!apiBaseUrl || !authToken || !hasReportableStats(sample)) {
    return false;
  }
  try {
    const res = await fetchImpl(`${apiBaseUrl}/api/v1/voip/webrtc-stats`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        call_id: callId,
        role,
        rtt_ms: sample.rttMs,
        jitter_ms: sample.jitterMs,
        packet_loss_ratio: sample.packetLossRatio,
        outgoing_bitrate_bps: sample.outgoingBitrateBps,
      }),
    });
    return res.ok;
  } catch (err) {
    console.warn('[VoIP] postWebRTCStats 실패(무시)', err);
    return false;
  }
}

export interface WebRTCStatsReporterOptions {
  apiBaseUrl: string;
  authToken: string;
  callId: string;
  role: 'caller' | 'callee' | string;
  /** getStats 호출(보통 () => pc.getStats()). */
  getStats: () => Promise<StatsLike>;
  /** 표본 주기(ms). 기본 5000. */
  intervalMs?: number;
  fetchImpl?: typeof fetch;
}

/**
 * 주기적으로 getStats 표본을 백엔드로 보고하는 리포터. start()/stop().
 * 모든 동작은 fail-open — 어떤 실패도 통화에 영향을 주지 않는다.
 */
export class WebRTCStatsReporter {
  private readonly opts: WebRTCStatsReporterOptions;
  private timer: ReturnType<typeof setInterval> | null = null;
  private counters: WebRTCStatsCounters | undefined;
  private busy = false;

  constructor(opts: WebRTCStatsReporterOptions) {
    this.opts = opts;
  }

  start(): void {
    if (this.timer) {
      return;
    }
    const intervalMs = Math.max(1000, this.opts.intervalMs ?? 5000);
    this.timer = setInterval(() => {
      void this.tick();
    }, intervalMs);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private async tick(): Promise<void> {
    if (this.busy) {
      return;
    }
    this.busy = true;
    try {
      const report = await this.opts.getStats();
      const { sample, counters } = extractWebRTCStatsSample(report, this.counters);
      this.counters = counters;
      if (hasReportableStats(sample)) {
        await postWebRTCStats(
          this.opts.apiBaseUrl,
          this.opts.authToken,
          this.opts.callId,
          this.opts.role,
          sample,
          this.opts.fetchImpl ?? fetch,
        );
      }
    } catch (err) {
      console.warn('[VoIP] WebRTCStatsReporter tick 실패(무시)', err);
    } finally {
      this.busy = false;
    }
  }
}
