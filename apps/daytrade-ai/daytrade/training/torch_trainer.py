"""torch 시퀀스 모델(LSTM / Transformer) — 설계서 §3-3 딥러닝 추론기.

피처 윈도 [B, seq_len, F] → 방향 확률 [B, 2]=(prob_buy, prob_sell).
표준화(mean/std)를 모듈 버퍼로 내장해 ONNX export 시 **원시 피처**가 그대로 들어와도
런타임(`SequenceOnnxModel`)과 동일 결과를 낸다(train/serve skew 제거).

torch 미설치 환경에서는 import 시점에 실패하므로, 호출부(테스트/CLI)에서 가드한다.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from ..features.engine import FEATURE_NAMES
from .dataset import DatasetBundle, make_sequences, train_val_split


class SeqClassifier(nn.Module):
    """LSTM 또는 Transformer 인코더 기반 2-head 확률 분류기(표준화 내장)."""

    def __init__(
        self,
        n_features: int,
        kind: str = "lstm",
        hidden: int = 32,
        num_layers: int = 1,
        nhead: int = 4,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.kind = kind
        self.n_features = n_features
        self.register_buffer("mean", torch.zeros(n_features))
        self.register_buffer("std", torch.ones(n_features))

        if kind == "lstm":
            self.encoder = nn.LSTM(
                n_features, hidden, num_layers=num_layers, batch_first=True, dropout=dropout
            )
            self.head = nn.Linear(hidden, 2)
        elif kind == "transformer":
            self.input_proj = nn.Linear(n_features, hidden)
            layer = nn.TransformerEncoderLayer(
                d_model=hidden, nhead=nhead, dim_feedforward=hidden * 2,
                dropout=dropout, batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
            self.head = nn.Linear(hidden, 2)
        else:
            raise ValueError(f"unknown kind: {kind!r} (use 'lstm' or 'transformer')")

    def set_standardization(self, mean: "np.ndarray", std: "np.ndarray") -> None:
        self.mean.copy_(torch.as_tensor(mean, dtype=torch.float32))
        self.std.copy_(torch.as_tensor(std, dtype=torch.float32))

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        xn = (x - self.mean) / self.std
        if self.kind == "lstm":
            out, _ = self.encoder(xn)
            last = out[:, -1, :]
        else:
            h = self.input_proj(xn)
            enc = self.encoder(h)
            last = enc[:, -1, :]
        return torch.sigmoid(self.head(last))


def build_sequence_dataset(
    bundle: DatasetBundle, seq_len: int
) -> tuple["np.ndarray", "np.ndarray"]:
    """DatasetBundle → (seqs [M, seq_len, F], Y [M, 2])."""
    seqs, label_idx = make_sequences(bundle.X, seq_len)
    Y = np.stack([bundle.y_buy[label_idx], bundle.y_sell[label_idx]], axis=1)
    return seqs.astype(np.float32), Y.astype(np.float32)


def train_sequence_model(
    seqs: "np.ndarray",
    Y: "np.ndarray",
    *,
    kind: str = "lstm",
    hidden: int = 32,
    num_layers: int = 1,
    epochs: int = 30,
    lr: float = 1e-2,
    val_frac: float = 0.2,
    seed: int = 42,
) -> tuple[SeqClassifier, dict]:
    """시퀀스 모델 학습. (module, metrics) 반환. 표준화는 train 구간에서만 추정."""
    torch.manual_seed(seed)
    seqs = np.asarray(seqs, dtype=np.float32)
    Y = np.asarray(Y, dtype=np.float32)
    n, seq_len, f = seqs.shape
    if n == 0:
        raise ValueError("empty sequence dataset")

    tr, va = train_val_split(n, val_frac)
    flat_tr = seqs[tr].reshape(-1, f)
    mean = flat_tr.mean(axis=0)
    std = flat_tr.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)

    model = SeqClassifier(n_features=f, kind=kind, hidden=hidden, num_layers=num_layers)
    model.set_standardization(mean, std)

    Xtr = torch.as_tensor(seqs[tr])
    Ytr = torch.as_tensor(Y[tr])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCELoss()

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        pred = model(Xtr)
        loss = loss_fn(pred, Ytr)
        loss.backward()
        opt.step()

    model.eval()

    def _metrics(idx: "np.ndarray") -> dict:
        if len(idx) == 0:
            return {"n": 0}
        with torch.no_grad():
            proba = model(torch.as_tensor(seqs[idx])).numpy()
        out = {"n": int(len(idx))}
        for k, name in enumerate(("buy", "sell")):
            yk = Y[idx, k]
            pk = proba[:, k]
            out[name] = {
                "acc": float(np.mean((pk >= 0.5).astype(np.float32) == yk)),
                "pos_rate": float(yk.mean()),
            }
        return out

    metrics = {
        "kind": kind,
        "seq_len": seq_len,
        "n_features": f,
        "train": _metrics(tr),
        "val": _metrics(va),
        "epochs": epochs,
    }
    return model, metrics
