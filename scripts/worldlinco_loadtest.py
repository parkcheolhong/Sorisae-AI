#!/usr/bin/env python3
"""WorldLinco V.2 음성통역 부하 테스트 (STT + MT 동접 시뮬레이터).

실제 VOIP 경로(`mode="voip"`, `device_tts=True` → 서버 TTS 합성 비용 제외)와
동일한 페이로드로 `/api/llm/voice-translate` 에 동시 요청을 쏘아
단계별(동접 50→100→200…) P50/P90/P95/P99 지연과 처리량(req/s), 오류율을 측정한다.

두 가지 모드:
  - mt  : transcript 직접 입력 → LLM 번역 경로만(STT 제외). 번역 throughput 격리 측정.
  - stt : audio_base64 입력 → STT(large-v3) + LLM 번역 전체 경로. 실부하에 가장 근접.

사용 예:
  # 번역(MT) 경로만, 동접 20→50→100 각 20초
  python scripts/worldlinco_loadtest.py --mode mt --stages 20,50,100 --duration 20

  # 전체(STT+MT) 경로. Windows면 SAPI로 음성 자동 합성, 그 외엔 --audio 필요
  python scripts/worldlinco_loadtest.py --mode stt --stages 10,20,40 --duration 30 --gen-audio

  # 기존 WAV 사용
  python scripts/worldlinco_loadtest.py --mode stt --audio sample.wav --stages 10,20

종속성: httpx (requirements.txt 에 이미 포함).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    print("httpx 가 필요합니다: pip install httpx", file=sys.stderr)
    sys.exit(2)


# 번역 부하용 샘플 문장(짧은/중간/긴 발화 혼합 — 실통화 분포 근사)
_MT_SAMPLES_KO = [
    "안녕하세요.",
    "오늘 회의는 몇 시에 시작하나요?",
    "이번 주말에 같이 저녁 먹을 시간 있으세요?",
    "방금 보내주신 자료 잘 받았습니다. 검토 후에 다시 연락드리겠습니다.",
    "공항에서 호텔까지 가는 가장 빠른 방법이 무엇인지 알려주시겠어요?",
    "죄송하지만 다시 한 번 천천히 말씀해 주시겠어요?",
    "계약 조건에 대해 몇 가지 확인하고 싶은 부분이 있습니다.",
    "내일 오전에 비가 온다고 하니 우산을 챙기는 것이 좋겠습니다.",
]


@dataclass
class StageResult:
    concurrency: int
    total: int = 0
    ok: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)
    wall_seconds: float = 0.0

    def add_error(self, key: str) -> None:
        self.errors[key] = self.errors.get(key, 0) + 1

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
        return s[idx]

    def summary(self) -> dict:
        thr = (self.ok / self.wall_seconds) if self.wall_seconds > 0 else 0.0
        return {
            "concurrency": self.concurrency,
            "total": self.total,
            "ok": self.ok,
            "error_rate": round(1 - (self.ok / self.total), 4) if self.total else 0.0,
            "throughput_rps": round(thr, 2),
            "latency_ms": {
                "p50": round(self.percentile(50), 1),
                "p90": round(self.percentile(90), 1),
                "p95": round(self.percentile(95), 1),
                "p99": round(self.percentile(99), 1),
                "max": round(max(self.latencies_ms), 1) if self.latencies_ms else 0.0,
            },
            "errors": self.errors,
            "wall_seconds": round(self.wall_seconds, 1),
        }


def _synthesize_wav_windows(text: str) -> bytes:
    """Windows SAPI(System.Speech)로 음성 WAV 합성. 실패 시 RuntimeError."""
    out = Path(tempfile.gettempdir()) / "worldlinco_lt_sample.wav"
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.SetOutputToWaveFile('{out}');"
        f"$s.Speak('{text}');"
        "$s.Dispose();"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"SAPI 합성 실패: {proc.stderr.strip()}")
    return out.read_bytes()


def _resolve_audio_b64(args) -> str:
    if args.audio:
        data = Path(args.audio).read_bytes()
    elif args.gen_audio:
        if os.name != "nt":
            raise SystemExit("--gen-audio 는 Windows(SAPI) 전용입니다. 그 외엔 --audio <wav> 를 주세요.")
        # 발신 언어에 맞춘 문장(영어 합성이 SAPI 기본). 부하 측정엔 내용보다 길이/음성이 중요.
        data = _synthesize_wav_windows(
            "Hello, how are you today? The weather is very nice this weekend.",
        )
    else:
        raise SystemExit("stt 모드는 --audio <wav> 또는 --gen-audio(Windows) 가 필요합니다.")
    return base64.b64encode(data).decode("ascii")


def _build_payload(args, audio_b64: str | None, i: int) -> dict:
    base = {
        "from_lang": args.from_lang,
        "to_lang": args.to_lang,
        "mode": "voip",        # 지정 언어 고정(실통화 hot path)
        "device_tts": True,     # 서버 TTS 합성 제외(폰에서 합성 → 서버 GPU 부하 격리)
    }
    if args.mode == "mt":
        base["transcript"] = _MT_SAMPLES_KO[i % len(_MT_SAMPLES_KO)]
    else:
        base["audio_base64"] = audio_b64
    return base


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    payload_factory,
    stop_at: float,
    result: StageResult,
    counter: list[int],
) -> None:
    while time.monotonic() < stop_at:
        idx = counter[0]
        counter[0] += 1
        payload = payload_factory(idx)
        t0 = time.monotonic()
        try:
            resp = await client.post(url, json=payload)
            dt = (time.monotonic() - t0) * 1000.0
            result.total += 1
            if resp.status_code == 200:
                result.ok += 1
                result.latencies_ms.append(dt)
            else:
                result.add_error(f"http_{resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            result.total += 1
            result.add_error(type(exc).__name__)


async def _run_stage(args, url: str, audio_b64: str | None, concurrency: int) -> StageResult:
    result = StageResult(concurrency=concurrency)
    counter = [0]
    timeout = httpx.Timeout(args.timeout, connect=10.0)
    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)

    def factory(i: int) -> dict:
        return _build_payload(args, audio_b64, i)

    t_start = time.monotonic()
    stop_at = t_start + args.duration
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        workers = [
            asyncio.create_task(_worker(client, url, factory, stop_at, result, counter))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)
    result.wall_seconds = time.monotonic() - t_start
    return result


def _print_stage(s: StageResult) -> None:
    d = s.summary()
    lat = d["latency_ms"]
    print(
        f"  동접 {d['concurrency']:>4} | ok {d['ok']:>5}/{d['total']:<5} "
        f"| 오류율 {d['error_rate']*100:>5.1f}% | {d['throughput_rps']:>6.1f} req/s "
        f"| p50 {lat['p50']:>6.0f}  p95 {lat['p95']:>6.0f}  p99 {lat['p99']:>6.0f}  max {lat['max']:>6.0f} ms"
    )
    if d["errors"]:
        print(f"        errors: {d['errors']}")


async def _main_async(args) -> int:
    url = args.base_url.rstrip("/") + "/api/llm/voice-translate"
    audio_b64 = _resolve_audio_b64(args) if args.mode == "stt" else None

    print(f"[worldlinco-loadtest] mode={args.mode} url={url}")
    print(f"  lang={args.from_lang}->{args.to_lang} stages={args.stages} duration={args.duration}s/stage timeout={args.timeout}s")
    if args.mode == "stt":
        print(f"  audio={'(SAPI 합성)' if args.gen_audio and not args.audio else args.audio} (~{len(audio_b64)//1024}KB b64)")
    print("-" * 96)

    report = {"mode": args.mode, "base_url": args.base_url, "stages": []}
    for c in args.stages:
        s = await _run_stage(args, url, audio_b64, c)
        _print_stage(s)
        report["stages"].append(s.summary())
        if args.cooldown > 0 and c != args.stages[-1]:
            await asyncio.sleep(args.cooldown)

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("-" * 96)
        print(f"리포트 저장: {args.out}")

    # 권고: P95 < 2000ms & 오류율 < 1% 를 SLA 통과 기준으로 판단
    print("-" * 96)
    print("SLA 가이드: 각 단계 p95 < 2000ms 이고 오류율 < 1% 인 최대 동접이 단일 GPU 처리 한계 추정치입니다.")
    return 0


def _parse_stages(value: str) -> list[int]:
    return [int(x) for x in value.replace(" ", "").split(",") if x]


def main() -> int:
    ap = argparse.ArgumentParser(description="WorldLinco V.2 STT+MT 부하 테스트")
    ap.add_argument("--base-url", default=os.getenv("LOADTEST_BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--mode", choices=["mt", "stt"], default="mt")
    ap.add_argument("--stages", type=_parse_stages, default=[20, 50, 100],
                    help="동접 단계 (콤마구분). 예: 20,50,100,200")
    ap.add_argument("--duration", type=float, default=20.0, help="단계별 부하 지속 시간(초)")
    ap.add_argument("--cooldown", type=float, default=5.0, help="단계 간 GPU 안정화 대기(초)")
    ap.add_argument("--timeout", type=float, default=30.0, help="요청 타임아웃(초)")
    ap.add_argument("--from-lang", default="ko")
    ap.add_argument("--to-lang", default="en")
    ap.add_argument("--audio", default=None, help="stt 모드용 WAV 경로")
    ap.add_argument("--gen-audio", action="store_true", help="stt 모드에서 Windows SAPI로 음성 자동 합성")
    ap.add_argument("--out", default=None, help="JSON 리포트 저장 경로")
    args = ap.parse_args()

    # stt 모드에서 영어 음성을 합성하므로 기본 언어쌍을 en->ko 로 권장
    if args.mode == "stt" and args.gen_audio and args.from_lang == "ko" and not args.audio:
        args.from_lang, args.to_lang = "en", "ko"

    try:
        return asyncio.run(_main_async(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
