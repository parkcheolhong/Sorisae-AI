"""
train.py — LightGBM 학습, CV, 임계값 탐색, 피처 중요도
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import CFG, ModelConfig, ThresholdConfig
from utils import get_logger, save_csv, save_model, print_metrics

logger = get_logger(__name__)


# ─────────────────────────────────────────
# 의존성 임포트 (런타임 체크)
# ─────────────────────────────────────────
def _import_lgbm():
    try:
        import lightgbm as lgb
        return lgb
    except ImportError:
        raise ImportError("lightgbm 미설치. `pip install lightgbm` 실행 후 재시도하세요.")


def _import_sklearn():
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import (
        f1_score, precision_score, recall_score,
        roc_auc_score, accuracy_score, classification_report,
    )
    return TimeSeriesSplit, f1_score, precision_score, recall_score, roc_auc_score, accuracy_score, classification_report


# ─────────────────────────────────────────
# 단일 LightGBM 학습
# ─────────────────────────────────────────
def train_lgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    cfg: ModelConfig = None,
):
    """
    단일 학습-검증 분할 기준으로 LightGBM 을 학습합니다.
    조기 종료(early stopping) 적용.
    """
    lgb = _import_lgbm()
    cfg = cfg or CFG.model
    params = dict(cfg.lgbm_params)

    model = lgb.LGBMClassifier(
        **{k: v for k, v in params.items()
           if k not in ("objective", "metric")},
        early_stopping_rounds=cfg.early_stopping_rounds,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.log_evaluation(period=50)],
    )
    logger.info(f"학습 완료 — best_iteration: {model.best_iteration_}")
    return model


# ─────────────────────────────────────────
# 시계열 교차 검증
# ─────────────────────────────────────────
def cross_validate_lgbm(
    X: pd.DataFrame,
    y: pd.Series,
    cfg: ModelConfig = None,
) -> Tuple[object, List[dict]]:
    """
    TimeSeriesSplit CV 수행.
    마지막 fold 의 모델을 반환하고, 각 fold 지표 목록도 반환합니다.
    """
    lgb = _import_lgbm()
    TimeSeriesSplit, f1_score, precision_score, recall_score, roc_auc_score, accuracy_score, _ = _import_sklearn()
    cfg = cfg or CFG.model

    tscv = TimeSeriesSplit(n_splits=cfg.cv_folds)
    fold_metrics = []
    last_model = None

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMClassifier(
            **{k: v for k, v in cfg.lgbm_params.items()
               if k not in ("objective", "metric")},
            early_stopping_rounds=cfg.early_stopping_rounds,
        )
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.log_evaluation(period=200)],
        )
        proba = model.predict_proba(X_val)[:, 1]
        pred = (proba >= 0.5).astype(int)

        metrics = {
            "fold": fold,
            "n_train": len(y_tr),
            "n_val": len(y_val),
            "accuracy": accuracy_score(y_val, pred),
            "precision": precision_score(y_val, pred, zero_division=0),
            "recall": recall_score(y_val, pred, zero_division=0),
            "f1": f1_score(y_val, pred, zero_division=0),
            "auc": roc_auc_score(y_val, proba) if len(y_val.unique()) > 1 else 0.0,
        }
        fold_metrics.append(metrics)
        logger.info(
            f"Fold {fold} — AUC={metrics['auc']:.4f}  "
            f"F1={metrics['f1']:.4f}  Precision={metrics['precision']:.4f}"
        )
        last_model = model

    # 평균 지표
    mean_metrics = {
        k: np.mean([m[k] for m in fold_metrics])
        for k in ("accuracy", "precision", "recall", "f1", "auc")
    }
    print_metrics(mean_metrics, title="CV 평균 지표")
    return last_model, fold_metrics


# ─────────────────────────────────────────
# 임계값 탐색
# ─────────────────────────────────────────
def find_optimal_threshold(
    y_true: pd.Series,
    proba: np.ndarray,
    cfg: ThresholdConfig = None,
) -> Tuple[float, pd.DataFrame]:
    """
    다양한 임계값에서 지표를 계산하고 최적 임계값을 반환합니다.
    (optimal_threshold, threshold_df) 반환
    """
    from sklearn.metrics import f1_score, precision_score, recall_score
    cfg = cfg or CFG.threshold

    thresholds = np.linspace(cfg.search_range_start, cfg.search_range_end, cfg.search_steps)
    records = []
    for thr in thresholds:
        pred = (proba >= thr).astype(int)
        n_signals = int(pred.sum())
        if n_signals < cfg.min_signal_count:
            continue
        # 수익 팩터: True Positive / False Positive
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        profit_factor = tp / fp if fp > 0 else np.inf

        records.append({
            "threshold": round(thr, 4),
            "n_signals": n_signals,
            "precision": precision_score(y_true, pred, zero_division=0),
            "recall": recall_score(y_true, pred, zero_division=0),
            "f1": f1_score(y_true, pred, zero_division=0),
            "profit_factor": profit_factor,
        })

    if not records:
        logger.warning("임계값 탐색: 최소 신호 수를 만족하는 임계값 없음. 기본값 0.5 사용.")
        return 0.5, pd.DataFrame()

    thr_df = pd.DataFrame(records)
    opt_row = thr_df.loc[thr_df[cfg.optimize_metric].idxmax()]
    optimal = float(opt_row["threshold"])
    logger.info(
        f"최적 임계값: {optimal:.4f}  "
        f"{cfg.optimize_metric}={opt_row[cfg.optimize_metric]:.4f}  "
        f"precision={opt_row['precision']:.4f}  "
        f"recall={opt_row['recall']:.4f}  "
        f"signals={int(opt_row['n_signals'])}"
    )
    return optimal, thr_df


# ─────────────────────────────────────────
# 테스트 세트 평가
# ─────────────────────────────────────────
def evaluate_on_test(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
) -> Dict[str, float]:
    from sklearn.metrics import (
        f1_score, precision_score, recall_score,
        roc_auc_score, accuracy_score, classification_report,
    )
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)

    metrics = {
        "threshold": threshold,
        "n_total": len(y_test),
        "n_signals": int(pred.sum()),
        "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "f1": f1_score(y_test, pred, zero_division=0),
        "auc": roc_auc_score(y_test, proba) if len(y_test.unique()) > 1 else 0.0,
    }
    print_metrics(metrics, title="테스트 세트 평가")
    logger.info("\n" + classification_report(y_test, pred, zero_division=0))
    return metrics, proba


# ─────────────────────────────────────────
# 피처 중요도 저장
# ─────────────────────────────────────────
def save_feature_importance(model, feature_cols: List[str], path: str = None) -> pd.DataFrame:
    path = path or CFG.model.feature_importance_path
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance_gain": model.booster_.feature_importance(importance_type="gain"),
        "importance_split": model.booster_.feature_importance(importance_type="split"),
    }).sort_values("importance_gain", ascending=False).reset_index(drop=True)
    save_csv(importance, path, index=False)
    logger.info(f"Top 10 피처:\n{importance.head(10).to_string(index=False)}")
    return importance


# ─────────────────────────────────────────
# 통합 학습 파이프라인
# ─────────────────────────────────────────
def run_training(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str],
    cfg_model: ModelConfig = None,
    cfg_thr: ThresholdConfig = None,
    signal_only: bool = True,
) -> Tuple[object, float, dict, pd.DataFrame]:
    """
    학습 → 임계값 탐색 → 테스트 평가 까지 일괄 수행.

    signal_only=True: signal_mask==True 인 행만 학습/평가에 사용
    반환: (model, optimal_threshold, test_metrics, pred_test_df)
    """
    cfg_model = cfg_model or CFG.model
    cfg_thr = cfg_thr or CFG.threshold
    target = CFG.label.target_col

    def _filter(df):
        if signal_only and "signal_mask" in df.columns:
            return df[df["signal_mask"]].copy()
        return df.copy()

    tr = _filter(train_df)
    vl = _filter(val_df)
    te = _filter(test_df)

    X_tr, y_tr = tr[feature_cols], tr[target]
    X_vl, y_vl = vl[feature_cols], vl[target]
    X_te, y_te = te[feature_cols], te[target]

    logger.info(
        f"학습 입력 — train:{len(X_tr)} val:{len(X_vl)} test:{len(X_te)}  "
        f"positive_rate_train={y_tr.mean():.3f}"
    )

    # 학습 (CV 또는 단순 hold-out)
    if cfg_model.cv_folds > 1 and cfg_model.time_series_cv:
        # train+val 합쳐서 CV
        X_all = pd.concat([X_tr, X_vl])
        y_all = pd.concat([y_tr, y_vl])
        model, _ = cross_validate_lgbm(X_all, y_all, cfg_model)
    else:
        model = train_lgbm(X_tr, y_tr, X_vl, y_vl, cfg_model)

    # 피처 중요도
    save_feature_importance(model, feature_cols)

    # 임계값 탐색 (검증 세트 기준)
    val_proba = model.predict_proba(X_vl)[:, 1]
    optimal_thr, thr_df = find_optimal_threshold(y_vl, val_proba, cfg_thr)
    if not thr_df.empty:
        save_csv(thr_df, "artifacts/threshold_search.csv", index=False)

    # 테스트 평가
    test_metrics, test_proba = evaluate_on_test(model, X_te, y_te, optimal_thr)

    # 모델 저장
    save_model(model, cfg_model.model_save_path)

    # 예측 확률을 테스트 df에 붙여서 반환 (백테스트용)
    test_df = te.copy()
    test_df["proba"] = test_proba
    test_df["pred"] = (test_proba >= optimal_thr).astype(int)

    return model, optimal_thr, test_metrics, test_df
