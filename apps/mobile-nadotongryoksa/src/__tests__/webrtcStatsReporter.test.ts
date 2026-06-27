/**
 * WebRTC QoS 표본 파서(순수함수) 테스트 — 기술서 §0.22.5 / 체크리스트 §10.3 (RTP-6).
 * 네이티브 모듈 비의존: RTCStatsReport(Map 유사)·배열 입력만으로 검증.
 */
import {
  extractWebRTCStatsSample,
  hasReportableStats,
} from '../features/voip-voice-relay/webrtcStatsReporter';

/** getStats 가 돌려주는 Map 유사 RTCStatsReport 흉내. */
function makeReport(stats: any[]): { forEach: (cb: (v: any) => void) => void } {
  return { forEach: (cb) => stats.forEach((s) => cb(s)) };
}

describe('extractWebRTCStatsSample', () => {
  it('candidate-pair / inbound-rtp / remote-inbound 에서 RTT·jitter·bitrate 를 ms/bps 로 추출', () => {
    const report = makeReport([
      {
        type: 'candidate-pair',
        nominated: true,
        state: 'succeeded',
        currentRoundTripTime: 0.024, // 24ms
        availableOutgoingBitrate: 48000,
      },
      {
        type: 'inbound-rtp',
        kind: 'audio',
        jitter: 0.003, // 3ms
        packetsReceived: 1000,
        packetsLost: 5,
      },
      { type: 'remote-inbound-rtp', roundTripTime: 0.05 },
    ]);

    const { sample } = extractWebRTCStatsSample(report);
    expect(sample.rttMs).toBeCloseTo(24, 5);
    expect(sample.jitterMs).toBeCloseTo(3, 5);
    expect(sample.outgoingBitrateBps).toBe(48000);
    // 직전 카운터가 없으면 손실률은 계산하지 않는다.
    expect(sample.packetLossRatio).toBeUndefined();
  });

  it('직전 누적 카운터 대비 델타로 손실률(0..1)을 계산', () => {
    const prev = { packetsReceived: 1000, packetsLost: 5 };
    const report = makeReport([
      { type: 'inbound-rtp', kind: 'audio', packetsReceived: 1090, packetsLost: 15 },
    ]);
    // 신규 수신 90 + 신규 손실 10 → 10/100 = 0.1
    const { sample, counters } = extractWebRTCStatsSample(report, prev);
    expect(sample.packetLossRatio).toBeCloseTo(0.1, 5);
    expect(counters).toEqual({ packetsReceived: 1090, packetsLost: 15 });
  });

  it('selected 가 아닌 candidate-pair 는 RTT/bitrate 에서 무시', () => {
    const report = makeReport([
      {
        type: 'candidate-pair',
        nominated: false,
        state: 'frozen',
        currentRoundTripTime: 0.999,
        availableOutgoingBitrate: 1,
      },
    ]);
    const { sample } = extractWebRTCStatsSample(report);
    expect(sample.rttMs).toBeUndefined();
    expect(sample.outgoingBitrateBps).toBeUndefined();
    expect(hasReportableStats(sample)).toBe(false);
  });

  it('remote-inbound roundTripTime 를 candidate-pair 부재 시 RTT 폴백으로 사용', () => {
    const report = makeReport([{ type: 'remote-inbound-rtp', roundTripTime: 0.04 }]);
    const { sample } = extractWebRTCStatsSample(report);
    expect(sample.rttMs).toBeCloseTo(40, 5);
  });

  it('빈/널 리포트에 안전(부작용 없음)', () => {
    expect(extractWebRTCStatsSample(null).sample).toEqual({});
    expect(extractWebRTCStatsSample([]).sample).toEqual({});
    expect(hasReportableStats({})).toBe(false);
  });
});
