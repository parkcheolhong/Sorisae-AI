"""
run_pipeline.py — 전체 파이프라인 오케스트레이터
실행: python run_pipeline.py [--ticker AAPL] [--interval 5m] [--signal-mode any]

단계:
  1. OHLCV 데이터 로드
  2. 후보 신호 생성
  3. 피처 생성
  4. 라벨 부착
  5. 학습/검증/테스트 분할
  6. LightGBM 학습 + 임계값 탐색
  7. 필터 전/후 백테스트
  8. 수익 곡선 저장
"""

import argparse
import sys
import time
from pathlib import Path

from config import CFG, ProjectConfig
from utils import get_logger, set_seed, ensure_artifacts_dir, time_split
from signals import generate_signals
from features import build_features
from labeling import attach_labels
from train import run_training
from backtest import compare_before_after_filter, plot_equity_curves

logger = get_logger("pipeline")


# ─────────────────────────────────────────
# CLI 인수
# ─────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="단타 LightGBM 자동매매 파이프라인")
    p.add_argument("--ticker", type=str, default=None, help="종목 티커 (예: AAPL, 005930.KS)")
    p.add_argument("--interval", type=str, default=None, help="봉 인터벌 (예: 5m, 15m, 1h)")
    p.add_argument("--start", type=str, default=None, help="시작일 YYYY-MM-DD")
    p.add_argument("--end", type=str, default=None, help="종료일 YYYY-MM-DD")
    p.add_argument("--signal-mode", type=str, default="any",
                   help="신호 통합 방식: any | all | vote_N")
    p.add_argument("--label-mode", type=str, default=None,
                   help="라벨 방식: binary | ternary")
    p.add_argument("--no-cv", action="store_true",
                   help="CV 없이 단순 hold-out 학습")
    p.add_argument("--no-plot", action="store_true",
                   help="수익 곡선 그래프 생략")
    return p.parse_args()


# ─────────────────────────────────────────
# 설정 오버라이드 (CLI → CFG)
# ─────────────────────────────────────────
def apply_cli_overrides(args: argparse.Namespace) -> None:
    if args.ticker:
        CFG.data.ticker = args.ticker
    if args.interval:
        CFG.data.interval = args.interval
    if args.start:
        CFG.data.start_date = args.start
    if args.end:
        CFG.data.end_date = args.end
    if args.label_mode:
        CFG.label.label_mode = args.label_mode
    if args.no_cv:
        CFG.model.cv_folds = 0


# ─────────────────────────────────────────
# 메인 파이프라인
# ─────────────────────────────────────────
def main() -> int:
    args = parse_args()
    apply_cli_overrides(args)
    set_seed(CFG.random_seed)
    ensure_artifacts_dir()

    t_start = time.time()
    logger.info("=" * 60)
    logger.info(f"  단타 LightGBM 파이프라인 시작")
    logger.info(f"  ticker={CFG.data.ticker}  interval={CFG.data.interval}")
    logger.info(f"  {CFG.data.start_date} ~ {CFG.data.end_date}")
    logger.info("=" * 60)

    # ── STEP 1: 데이터 로드 ──────────────────
    logger.info("[STEP 1] OHLCV 로드")
    from utils import load_ohlcv
    df = load_ohlcv(CFG.data)

    # ── STEP 2: 후보 신호 생성 ───────────────
    logger.info(f"[STEP 2] 신호 생성 (mode={args.signal_mode})")
    df = generate_signals(df, mode=args.signal_mode)

    # ── STEP 3: 피처 생성 ────────────────────
    logger.info("[STEP 3] 피처 생성")
    df, feature_cols = build_features(df, CFG.feature)

    # ── STEP 4: 라벨 부착 ────────────────────
    logger.info("[STEP 4] 라벨 생성")
    df = attach_labels(df, CFG.label, drop_na=True)

    if len(df) < 200:
        logger.error(
            f"데이터 부족: 라벨링 후 {len(df)}행. 날짜 범위를 넓히거나 인터벌을 조정하세요."
        )
        return 1

    # ── STEP 5: 학습/검증/테스트 분할 ─────────
    logger.info("[STEP 5] 시계열 분할")
    train_df, val_df, test_df = time_split(df)

    signal_counts = {
        "train": int(train_df["signal_mask"].sum()),
        "val": int(val_df["signal_mask"].sum()),
        "test": int(test_df["signal_mask"].sum()),
    }
    logger.info(f"신호 수 — {signal_counts}")

    if signal_counts["test"] < 10:
        logger.warning("테스트 신호 수 < 10. 백테스트 결과의 통계적 의미가 낮을 수 있습니다.")

    # ── STEP 6: 모델 학습 + 임계값 탐색 ───────
    logger.info("[STEP 6] 모델 학습")
    model, optimal_thr, test_metrics, pred_test_df = run_training(
        train_df, val_df, test_df,
        feature_cols=feature_cols,
        signal_only=True,
    )
    logger.info(f"최적 임계값: {optimal_thr:.4f}")

    # pred_test_df 는 signal_mask==True 인 행만 포함
    # 백테스트는 전체 test_df 에 pred 컬럼을 붙여서 수행
    full_test = test_df.copy()
    full_test["proba"] = 0.0
    full_test["pred"] = 0
    if len(pred_test_df) > 0:
        full_test.loc[pred_test_df.index, "proba"] = pred_test_df["proba"]
        full_test.loc[pred_test_df.index, "pred"] = pred_test_df["pred"]

    # ── STEP 7: 필터 전/후 백테스트 ──────────
    logger.info("[STEP 7] 백테스트")
    bt_results = compare_before_after_filter(full_test, CFG.backtest)

    # ── STEP 8: 수익 곡선 저장 ───────────────
    if not args.no_plot:
        logger.info("[STEP 8] 수익 곡선 저장")
        plot_equity_curves(
            bt_results["before_equity"],
            bt_results["after_equity"],
        )

    elapsed = time.time() - t_start
    logger.info(f"\n파이프라인 완료 — 소요 시간: {elapsed:.1f}초")
    logger.info(f"산출물 위치: {Path(CFG.artifacts_dir).resolve()}")

    # 최종 요약 출력
    _print_final_summary(test_metrics, bt_results["before"], bt_results["after"])
    return 0


# ─────────────────────────────────────────
# 최종 요약
# ─────────────────────────────────────────
def _print_final_summary(model_metrics: dict, before: dict, after: dict) -> None:
    bar = "★" * 60
    print(f"\n{bar}")
    print("  최종 요약")
    print(bar)
    print(f"  [모델 성능]  AUC={model_metrics.get('auc', 0):.4f}  "
          f"F1={model_metrics.get('f1', 0):.4f}  "
          f"Precision={model_metrics.get('precision', 0):.4f}")
    print(f"  [필터 전]  거래수={before.get('n_trades', 0)}  "
          f"승률={before.get('win_rate', 0):.2%}  "
          f"Sharpe={before.get('sharpe', 0):.2f}  "
          f"MDD={before.get('max_drawdown', 0):.2%}")
    print(f"  [필터 후]  거래수={after.get('n_trades', 0)}  "
          f"승률={after.get('win_rate', 0):.2%}  "
          f"Sharpe={after.get('sharpe', 0):.2f}  "
          f"MDD={after.get('max_drawdown', 0):.2%}")
    pf_improvement = after.get("profit_factor", 0) - before.get("profit_factor", 0)
    print(f"  [Profit Factor 개선] {pf_improvement:+.4f}")
    print(bar)


if __name__ == "__main__":
    sys.exit(main())
