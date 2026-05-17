#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный pipeline: сбор -> предобработка/признаки -> обучение pyOD ->
инференс -> углубленная проверка -> решение -> события/метрики (логика главы 2 ВКР).
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from detection_core import (
    TrainedEnsemble,
    flow_rows_from_parquet,
    load_ensemble,
    predict_frames,
    save_ensemble,
    train_ensemble,
    write_events_jsonl,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

COLLECTOR_SRC = Path(__file__).parent / "Packet-Real-Time-Collector" / "src"


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_parquet_dir(root: Path) -> pd.DataFrame:
    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"Нет .parquet в {root}")
    parts = [pd.read_parquet(p) for p in files]
    return pd.concat(parts, ignore_index=True)


def _latest_parquet_under(roots: List[Path]) -> Path:
    cands: List[Path] = []
    for r in roots:
        if r.exists():
            cands.extend(r.rglob("*.parquet"))
    if not cands:
        raise FileNotFoundError("Parquet не найдены в raw/ и synthetic/")
    return max(cands, key=lambda p: p.stat().st_mtime)


class TrafficDetectionPipeline:
    def __init__(self, config_path: str = "pipeline_config.yaml"):
        self.config_path = Path(config_path)
        self.project_root = Path(__file__).parent
        self.config = _load_yaml(self.config_path) if self.config_path.exists() else {}

        self.data_dir = self.project_root / "data"
        self.models_dir = self.project_root / "models"
        self.results_dir = self.project_root / "results"
        self.logs_dir = self.project_root / "logs"

        for d in (self.data_dir, self.models_dir, self.results_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)

        sys.path.insert(0, str(COLLECTOR_SRC))
        logger.info("Pipeline инициализирован, конфиг: %s", self.config_path)

    def run_collection(self, interface: Optional[str] = None, duration: Optional[int] = None) -> bool:
        col = self.config.get("collection", {})
        interface = interface or col.get("interface", "Ethernet")
        duration = int(duration if duration is not None else col.get("duration", 60))
        bpf = col.get("filters", "tcp or udp")
        batch_size = int(col.get("batch_size", 1000))
        flush_iv = float(col.get("flush_interval", 2.0))

        logger.info("Сбор телеметрии: iface=%s, %s с, bpf=%s", interface, duration, bpf)

        try:
            from main import DatasetWriter, PacketCapture, list_ifaces
        except ImportError as e:
            logger.error("Не удалось импортировать коллектор: %s", e)
            return False

        ifaces = list_ifaces()
        if interface not in ifaces:
            logger.error("Интерфейс %s не найден. Доступные: %s", interface, ifaces)
            return False

        out_raw = self.data_dir / "raw"
        writer = DatasetWriter(
            out_dir=str(out_raw),
            fmt="parquet",
            batch_size=batch_size,
            flush_interval_sec=flush_iv,
        )
        writer.start()
        cap = PacketCapture(iface=interface, writer=writer, bpf_filter=bpf)

        try:
            cap.start(timeout_sec=float(duration))
        except KeyboardInterrupt:
            logger.info("Сбор прерван пользователем")
        finally:
            writer.stop()
            time.sleep(0.6)

        logger.info("Сбор завершён, данные в %s", out_raw)
        return True

    def run_preprocessing(self, input_data: Optional[str] = None) -> bool:
        logger.info("Предобработка")
        pre = self.config.get("preprocessing", {})
        window_size = int(pre.get("window_size", 100))

        try:
            if input_data:
                path = Path(input_data)
                if path.is_file():
                    df = pd.read_parquet(path)
                else:
                    df = _load_parquet_dir(path)
            else:
                raw_dir = self.data_dir / "raw"
                syn_dir = self.data_dir / "synthetic"
                latest = _latest_parquet_under([raw_dir, syn_dir])
                logger.info("Источник: %s", latest)
                df = pd.read_parquet(latest)

            frames = flow_rows_from_parquet(df, window_size)
            feats_df = pd.DataFrame(frames)
            proc_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = self.data_dir / "processed" / "features.csv"
            pkl_path = self.data_dir / "processed" / f"frames_{proc_ts}.pkl"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            feats_df.to_csv(csv_path, index=False)
            feats_df.to_pickle(pkl_path)

            logger.info("Фреймов: %s -> %s", len(frames), csv_path)
            return True
        except Exception as e:
            logger.exception("Ошибка предобработки: %s", e)
            return False

    def run_training(self, model_type: Optional[str] = None) -> bool:
        logger.info("Обучение модели")
        csv_path = self.data_dir / "processed" / "features.csv"
        if not csv_path.exists():
            logger.error("Нет %s — сначала preprocess", csv_path)
            return False

        cfg = dict(self.config)
        if model_type:
            cfg.setdefault("training", {})
            cfg["training"]["model_type"] = model_type

        try:
            df = pd.read_csv(csv_path)
            frames: List[Dict[str, Any]] = df.to_dict(orient="records")
            ensemble, _, _ = train_ensemble(frames, cfg)
            model_path = self.models_dir / "ensemble.joblib"
            save_ensemble(model_path, ensemble)
            logger.info(
                "Сохранено %s; T_low=%.4f T_high=%.4f",
                model_path,
                ensemble.t_low,
                ensemble.t_high,
            )
            return True
        except Exception as e:
            logger.exception("Ошибка обучения: %s", e)
            return False

    def run_inference(
        self,
        model_path: Optional[Path] = None,
        features_csv: Optional[Path] = None,
        record_metrics: bool = True,
    ) -> bool:
        """Инференс, углубленная проверка, запись SIEM-подобных событий."""
        t0 = time.perf_counter()
        mpath = model_path or (self.models_dir / "ensemble.joblib")
        fpath = features_csv or (self.data_dir / "processed" / "features.csv")
        if not mpath.exists():
            logger.error("Нет модели %s", mpath)
            return False
        if not fpath.exists():
            logger.error("Нет признаков %s", fpath)
            return False

        ensemble = load_ensemble(mpath)
        df = pd.read_csv(fpath)
        frames = df.to_dict(orient="records")
        events = predict_frames(ensemble, frames, self.config)

        out_jsonl = self.results_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        write_events_jsonl(events, out_jsonl)
        events.to_csv(self.results_dir / "last_decisions.csv", index=False)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        mon = self.config.get("monitoring", {})
        max_lat = float(mon.get("alert_thresholds", {}).get("latency", 1000))
        if elapsed_ms > max_lat:
            logger.warning("Превышение целевой latency: %.1f мс (порог %s)", elapsed_ms, max_lat)

        if record_metrics:
            try:
                from monitoring_system import MonitoringSystem

                ms = MonitoringSystem()
                statuses = events["status"].tolist()
                scores = events["anomaly_score"].astype(float).tolist()
                ms.observe_batch(elapsed_ms, scores, statuses)
                rate = float(events.attrs.get("suspicious_rate", 0))
                if events.attrs.get("anomaly_rate_alert"):
                    logger.warning(
                        "Доля подозрительных фреймов %.3f выше порога anomaly_rate", rate
                    )
            except ImportError:
                pass

        logger.info("Решения: %s (за %.1f мс) -> %s", len(events), elapsed_ms, out_jsonl)
        return True

    def run_validation(self, test_data: Optional[str] = None) -> bool:
        """Валидация: инференс + метрики, если в данных есть is_anomaly."""
        logger.info("Валидация")
        try:
            from sklearn.metrics import classification_report, roc_auc_score
        except ImportError:
            classification_report = None
            roc_auc_score = None

        test_path = Path(test_data) if test_data else (self.data_dir / "processed" / "features.csv")
        if not test_path.exists():
            logger.error("Нет данных: %s", test_path)
            return False

        mpath = self.models_dir / "ensemble.joblib"
        if not mpath.exists():
            logger.error("Нет обученной модели %s", mpath)
            return False

        ensemble = load_ensemble(mpath)
        df = pd.read_csv(test_path)
        if "is_anomaly" not in df.columns:
            logger.warning("Колонка is_anomaly отсутствует — только прогон инференса")
            return self.run_inference(model_path=mpath, features_csv=test_path, record_metrics=False)

        frames = df.to_dict(orient="records")
        events = predict_frames(ensemble, frames, self.config)

        y_true = df["is_anomaly"].astype(bool).values
        y_pred = events["status"].ne("regular").values

        report_path = self.results_dir / "validation_report.txt"
        lines = [
            f"Время: {datetime.now().isoformat()}",
            f"Записей: {len(df)}",
        ]
        if classification_report:
            lines.append(classification_report(y_true, y_pred, zero_division=0))
        if roc_auc_score and len(set(y_true)) > 1:
            try:
                auc = roc_auc_score(y_true, events["anomaly_score"].values)
                lines.append(f"ROC-AUC (score vs is_anomaly): {auc:.4f}")
            except ValueError:
                pass

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Отчёт: %s", report_path)
        return True

    def run_monitoring(self) -> bool:
        logger.info("Экспорт метрик Prometheus (Ctrl+C для остановки)")
        try:
            from monitoring_system import MonitoringSystem

            port = int(self.config.get("monitoring", {}).get("prometheus_port", 9108))
            m = MonitoringSystem(port=port)
            m.start()
            if not getattr(m, "_enabled", False):
                logger.warning("prometheus_client не установлен")
                return False
            logger.info("Метрики: http://127.0.0.1:%s/metrics", port)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return True
        except Exception as e:
            logger.exception("Мониторинг: %s", e)
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Traffic Detection Pipeline")
    parser.add_argument("--config", default="pipeline_config.yaml")
    parser.add_argument(
        "--stage",
        choices=[
            "all",
            "collect",
            "preprocess",
            "train",
            "infer",
            "validate",
            "monitor",
        ],
        default="all",
    )
    parser.add_argument("--interface", default=None)
    parser.add_argument("--duration", type=int, default=None)
    parser.add_argument("--model-type", choices=["autoencoder", "hybrid"], default=None)
    args = parser.parse_args()

    pipeline = TrafficDetectionPipeline(args.config)

    if args.stage == "all":
        ok = True
        ok &= pipeline.run_collection(args.interface, args.duration)
        ok &= pipeline.run_preprocessing()
        ok &= pipeline.run_training(args.model_type)
        ok &= pipeline.run_validation()
        _ = pipeline.run_inference(record_metrics=False)
        if not ok:
            sys.exit(1)
        logger.info("Полный pipeline выполнен")
        return

    if args.stage == "collect":
        sys.exit(0 if pipeline.run_collection(args.interface, args.duration) else 1)
    if args.stage == "preprocess":
        sys.exit(0 if pipeline.run_preprocessing() else 1)
    if args.stage == "train":
        sys.exit(0 if pipeline.run_training(args.model_type) else 1)
    if args.stage == "infer":
        sys.exit(0 if pipeline.run_inference() else 1)
    if args.stage == "validate":
        sys.exit(0 if pipeline.run_validation() else 1)
    if args.stage == "monitor":
        sys.exit(0 if pipeline.run_monitoring() else 1)


if __name__ == "__main__":
    main()
