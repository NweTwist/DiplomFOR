#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ядро детекции: предобработка/признаки, ансамбль pyOD, углубленная проверка, финальный статус.
Соответствует логике главы 2 (ВКР): потоки/фреймы, безучительский слой, правила, пороги T_low/T_high.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

EPS_DUR = 0.001


def _entropy_bytes(data: bytes) -> float:
    if not data:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    p = counts[counts > 0] / len(data)
    return float(-np.sum(p * np.log2(p)))


def payload_sample_entropy(sample: Any) -> float:
    """Энтропия короткого образца payload (hex от коллектора или произвольная строка)."""
    if sample is None or (isinstance(sample, float) and math.isnan(sample)):
        return 0.0
    s = str(sample).strip()
    if not s:
        return 0.0
    raw: Optional[bytes] = None
    if len(s) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in s):
        try:
            raw = bytes.fromhex(s)
        except ValueError:
            raw = None
    if raw is None:
        raw = s.encode("utf-8", errors="ignore")
    return _entropy_bytes(raw)


def _minmax_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    if chunk_size <= 0:
        return [items]
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def flow_rows_from_parquet(df: pd.DataFrame, window_size: int) -> List[Dict[str, Any]]:
    """Группировка пакетов по flow_key, опциональные фреймы по window_size пакетов."""
    by_flow: Dict[Any, List[pd.Series]] = {}
    for _, row in df.iterrows():
        fk = row.get("flow_key") or "unknown"
        by_flow.setdefault(fk, []).append(row)

    out: List[Dict[str, Any]] = []
    for flow_key, packets in by_flow.items():
        packets.sort(key=lambda r: int(r["ts_us"]) if pd.notna(r.get("ts_us")) else 0)
        for part_idx, chunk in enumerate(_chunk_list(packets, window_size)):
            feats = extract_frame_features(flow_key, part_idx, chunk)
            out.append(feats)
    return out


def extract_frame_features(flow_key: str, part_index: int, packets: Sequence[pd.Series]) -> Dict[str, Any]:
    ts = [int(p["ts_us"]) / 1_000_000 for p in packets]
    sizes = [int(p["length"]) for p in packets]

    inter: List[float] = []
    for i in range(1, len(ts)):
        inter.append(ts[i] - ts[i-1])

    dur = (ts[-1] - ts[0]) if len(ts) > 1 else 0.0
    dur_eff = max(dur, EPS_DUR)

    synish = 0
    flag_parts: List[str] = []
    entropies: List[float] = []
    for p in packets:
        fl = p.get("tcp_flags")
        if fl is not None and pd.notna(fl):
            fs = str(fl)
            flag_parts.append(fs)
            if "S" in fs:
                synish += 1
        entropies.append(payload_sample_entropy(p.get("payload_sample")))

    p0 = packets[0]
    proto = p0.get("protocol", "") or ""
    frame_key = f"{flow_key}#w{part_index}" if part_index else str(flow_key)

    label = False
    for p in packets:
        v = p.get("is_anomaly")
        if v is True or v == 1 or str(v).lower() == "true":
            label = True
            break

    feats = {
        "frame_key": frame_key,
        "flow_key": str(flow_key),
        "part_index": int(part_index),
        "packet_count": len(packets),
        "duration": float(dur),
        "total_bytes": int(sum(sizes)),
        "avg_packet_size": float(np.mean(sizes)),
        "std_packet_size": float(np.std(sizes)) if len(sizes) > 1 else 0.0,
        "min_packet_size": int(min(sizes)),
        "max_packet_size": int(max(sizes)),
        "pps": len(packets) / dur_eff,
        "bps": float(sum(sizes)) * 8.0 / dur_eff,
        "avg_inter_arrival": float(np.mean(inter)) if inter else 0.0,
        "std_inter_arrival": float(np.std(inter)) if len(inter) > 1 else 0.0,
        "src_ip": str(p0.get("src_ip") or ""),
        "dst_ip": str(p0.get("dst_ip") or ""),
        "src_port": int(p0.get("src_port") or 0),
        "dst_port": int(p0.get("dst_port") or 0),
        "protocol": str(proto),
        "syn_flag_ratio": synish / max(len(packets), 1),
        "avg_payload_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "segment": str(p0.get("iface") or "default"),
        "is_anomaly": bool(label),
    }
    return feats


def _iqr_mask(df: pd.DataFrame, cols: List[str], factor: float = 1.5) -> pd.Series:
    m = pd.Series(True, index=df.index)
    for c in cols:
        q1 = df[c].quantile(0.25)
        q3 = df[c].quantile(0.75)
        iqr = q3 - q1
        lo = q1 - factor * iqr
        hi = q3 + factor * iqr
        m &= (df[c] >= lo) & (df[c] <= hi)
    return m


NUMERIC_FEATURE_COLS = [
    "packet_count",
    "duration",
    "total_bytes",
    "avg_packet_size",
    "std_packet_size",
    "min_packet_size",
    "max_packet_size",
    "pps",
    "bps",
    "avg_inter_arrival",
    "std_inter_arrival",
    "src_port",
    "dst_port",
    "syn_flag_ratio",
    "avg_payload_entropy",
]


def _encode_protocol(s: str) -> float:
    s = (s or "").upper()
    if s == "TCP":
        return 1.0
    if s == "UDP":
        return 0.0
    return -1.0


def frames_to_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    df = df.copy()
    for c in NUMERIC_FEATURE_COLS:
        if c not in df.columns:
            df[c] = 0.0
    if "protocol" not in df.columns:
        df["protocol"] = ""
    cols = NUMERIC_FEATURE_COLS + ["protocol_enc"]
    X_proto = df["protocol"].fillna("").map(_encode_protocol).astype(float)
    parts = [df[c].astype(float).fillna(0).values for c in NUMERIC_FEATURE_COLS]
    parts.append(X_proto.values)
    X = np.column_stack(parts)
    return X, cols


@dataclass
class TrainedEnsemble:
    scaler: StandardScaler
    iforest: Optional[Any]
    autoencoder: Optional[Any]
    feature_columns: List[str]
    contamination: float
    threshold_quantile: float
    t_low: float
    t_high: float
    model_version: str = "pyod_iforest+autoencoder.v1"

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.scaler.transform(X)

    def decision_scores(self, X: np.ndarray) -> np.ndarray:
        Xs = self.transform(X)
        parts: List[np.ndarray] = []
        if self.iforest is not None:
            parts.append(_minmax_1d(self.iforest.decision_function(Xs)))
        if self.autoencoder is not None:
            parts.append(_minmax_1d(self.autoencoder.decision_function(Xs)))
        if not parts:
            raise RuntimeError("Нет ни одной обученной модели в ансамбле.")
        return np.mean(np.vstack(parts), axis=0)


def train_ensemble(
    frames: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> Tuple[TrainedEnsemble, pd.DataFrame, np.ndarray]:
    """Обучение на нормальном подмножестве (is_anomaly==False) после опционального IQR."""
    train_cfg = cfg.get("training", {})
    pre_cfg = cfg.get("preprocessing", {})
    ad_cfg = train_cfg.get("anomaly_detection", {})

    contamination = float(ad_cfg.get("contamination", 0.1))
    threshold_q = float(ad_cfg.get("threshold_quantile", 0.99))
    epochs = int(train_cfg.get("epochs", 30))
    model_type = str(train_cfg.get("model_type", "hybrid")).lower()

    df = pd.DataFrame(frames)
    if "is_anomaly" in df.columns:
        df_fit = df[~df["is_anomaly"]].copy()
    else:
        df_fit = df.copy()

    if pre_cfg.get("outlier_removal", True) and len(df_fit) > 10:
        m = _iqr_mask(df_fit, [c for c in NUMERIC_FEATURE_COLS if c in df_fit.columns])
        df_fit = df_fit[m]

    if len(df_fit) < 5:
        raise ValueError("Слишком мало нормальных наблюдений для обучения (после фильтров).")

    X, feat_cols = frames_to_matrix(df_fit)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    from pyod.models.iforest import IForest

    iforest: Optional[Any] = None
    autoencoder: Optional[Any] = None

    if model_type == "autoencoder":
        try:
            from pyod.models.auto_encoder import AutoEncoder

            autoencoder = AutoEncoder(
                epochs=max(5, min(epochs, 100)),
                contamination=contamination,
                verbose=0,
            )
            autoencoder.fit(Xs)
        except Exception:
            autoencoder = None
        if autoencoder is None:
            iforest = IForest(contamination=contamination, random_state=42, n_estimators=200)
            iforest.fit(Xs)
    else:
        iforest = IForest(contamination=contamination, random_state=42, n_estimators=200)
        iforest.fit(Xs)
        try:
            from pyod.models.auto_encoder import AutoEncoder

            autoencoder = AutoEncoder(
                epochs=max(5, min(epochs, 100)),
                contamination=contamination,
                verbose=0,
            )
            autoencoder.fit(Xs)
        except Exception:
            autoencoder = None

    te = TrainedEnsemble(
        scaler=scaler,
        iforest=iforest,
        autoencoder=autoencoder,
        feature_columns=feat_cols,
        contamination=contamination,
        threshold_quantile=threshold_q,
        t_low=0.0,
        t_high=0.0,
    )
    scores_fit = te.decision_scores(X)
    t_low = float(np.quantile(scores_fit, 0.90))
    t_high = float(np.quantile(scores_fit, threshold_q))
    te.t_low = t_low
    te.t_high = t_high
    return te, df, scores_fit


def deep_inspection(row: Dict[str, Any], score: float) -> List[str]:
    """Упрощённый модуль углубленной проверки (правила + эвристики)."""
    ev: List[str] = []
    proto = str(row.get("protocol") or "").upper()
    dst = int(row.get("dst_port") or 0)
    synr = float(row.get("syn_flag_ratio") or 0.0)
    pps = float(row.get("pps") or 0.0)
    bps = float(row.get("bps") or 0.0)
    pc = int(row.get("packet_count") or 0)
    dur = float(row.get("duration") or 0.0)
    ent = float(row.get("avg_payload_entropy") or 0.0)

    if proto == "TCP" and dst > 0 and dst < 1024 and synr >= 0.5 and pc <= 5:
        ev.append("rule:tcp_syn_low_ports_short_flow")
    if pps >= 8000 or bps >= 80_000_000:
        ev.append("rule:high_intensity_burst")
    if ent >= 7.2 and pc >= 3:
        ev.append("rule:high_entropy_payload_sample")
    if dur <= 0.01 and pc >= 20:
        ev.append("rule:compressed_timeline_many_packets")
    if score >= 0.85:
        ev.append("signal:high_ml_score")
    return ev


def decide_status(score: float, t_low: float, t_high: float, evidence: Sequence[str]) -> str:
    strong = any(e.startswith("rule:") for e in evidence)
    if score >= t_high and strong:
        return "malicious"
    if score >= t_low or evidence:
        return "suspicious"
    return "regular"


def save_ensemble(path: Path, ensemble: TrainedEnsemble) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(ensemble, f)


def load_ensemble(path: Path) -> TrainedEnsemble:
    with open(path, "rb") as f:
        obj = pickle.load(f)
    if not isinstance(obj, TrainedEnsemble):
        raise TypeError("Неверный формат файла модели")
    return obj


def predict_frames(
    ensemble: TrainedEnsemble,
    frames: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> pd.DataFrame:
    """Инференс + углубленная проверка + статусы; возвращает таблицу событий."""
    df = pd.DataFrame(frames)
    X, _ = frames_to_matrix(df)
    scores = ensemble.decision_scores(X)

    monitoring_cfg = cfg.get("monitoring", {})
    alert = monitoring_cfg.get("alert_thresholds", {}) if monitoring_cfg else {}
    anomaly_rate_alert = float(alert.get("anomaly_rate", 0.1))

    rows_out = []
    suspicious_cnt = 0
    for i, fr in enumerate(frames):
        score = float(scores[i])
        ev = deep_inspection(fr, score)
        status = decide_status(score, ensemble.t_low, ensemble.t_high, ev)
        if status != "regular":
            suspicious_cnt += 1

        top_feats = _top_deviating_features(fr)

        rows_out.append(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "frame_key": fr.get("frame_key"),
                "flow_key": fr.get("flow_key"),
                "segment": fr.get("segment"),
                "status": status,
                "anomaly_score": score,
                "thresholds": {"T_low": ensemble.t_low, "T_high": ensemble.t_high},
                "evidence": list(ev),
                "top_features": top_feats,
                "context": {
                    "src_ip": fr.get("src_ip"),
                    "dst_ip": fr.get("dst_ip"),
                    "src_port": fr.get("src_port"),
                    "dst_port": fr.get("dst_port"),
                    "protocol": fr.get("protocol"),
                },
                "model_version": ensemble.model_version,
            }
        )

    result_df = pd.DataFrame(rows_out)
    n = max(len(result_df), 1)
    frac = suspicious_cnt / n
    result_df.attrs["suspicious_rate"] = frac
    result_df.attrs["anomaly_rate_alert"] = frac > anomaly_rate_alert
    return result_df


def _top_deviating_features(fr: Dict[str, Any], k: int = 5) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for c in NUMERIC_FEATURE_COLS:
        if c in fr:
            try:
                out[c] = float(fr[c])
            except (TypeError, ValueError):
                continue
    return dict(sorted(out.items(), key=lambda kv: abs(kv[1]), reverse=True)[:k])


def write_events_jsonl(df_events: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for _, row in df_events.iterrows():
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
