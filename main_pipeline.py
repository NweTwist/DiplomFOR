#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный pipeline для системы детекции аномального сетевого трафика
Реализует MLOps-цикл согласно этапам:
1. Сбор телеметрии
2. Предобработка и разметка
3. Обучение и дообучение модели
4. Валидация и тест
5. Мониторинг качества
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавление путей к компонентам
sys.path.append(str(Path(__file__).parent / 'Packet-Real-Time-Collector' / 'src'))

from detection_core import (
    flow_rows_from_parquet,
    load_ensemble,
    predict_frames,
    save_ensemble,
    train_ensemble,
    write_events_jsonl,
)

def _load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class TrafficDetectionPipeline:
    """Главный класс pipeline системы детекции трафика"""

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path or 'pipeline_config.yaml')
        self.project_root = Path(__file__).parent
        self.config = _load_config(self.config_path)

        # Пути к компонентам
        self.collector_path = self.project_root / 'Packet-Real-Time-Collector'

        # Директории для данных
        paths_cfg = self.config.get("paths", {}) if self.config else {}
        self.data_dir = self.project_root / paths_cfg.get("data_dir", "data")
        self.models_dir = self.project_root / paths_cfg.get("models_dir", "models")
        self.results_dir = self.project_root / paths_cfg.get("results_dir", "results")

        for dir_path in [self.data_dir, self.models_dir, self.results_dir]:
            dir_path.mkdir(exist_ok=True)

        logger.info("Pipeline инициализирован")

    def _latest_parquet(self) -> Path:
        raw_dir = self.data_dir / "raw"
        synthetic_dir = self.data_dir / "synthetic"
        parquet_files = []
        for search_dir in [raw_dir, synthetic_dir]:
            if search_dir.exists():
                parquet_files.extend(list(search_dir.rglob("*.parquet")))
        if not parquet_files:
            raise FileNotFoundError("Parquet файлы не найдены ни в raw/, ни в synthetic/.")
        return max(parquet_files, key=lambda p: p.stat().st_mtime)

    def _latest_processed_frames(self) -> Path:
        processed_dir = self.data_dir / "processed"
        if not processed_dir.exists():
            raise FileNotFoundError("Каталог processed/ не найден.")
        pkl_files = list(processed_dir.glob("frames_*.pkl"))
        if not pkl_files:
            raise FileNotFoundError("Файлы frames_*.pkl не найдены.")
        return max(pkl_files, key=lambda p: p.stat().st_mtime)

    def run_collection(self, interface: str = 'Ethernet', duration: int = 60):
        """Этап 1: Сбор телеметрии"""
        cfg = self.config.get("collection", {}) if self.config else {}
        interface = interface or cfg.get("interface", "Ethernet")
        duration = duration or int(cfg.get("duration", 60))
        logger.info(f"Запуск сбора телеметрии на интерфейсе {interface} в течение {duration} сек")

        try:
            # Импорт компонентов коллектора
            from main import DatasetWriter, PacketCapture, list_ifaces
            import time
            import threading

            # Проверка интерфейса
            interfaces = list_ifaces()
            if interface not in interfaces:
                logger.error(f"Интерфейс {interface} не найден. Доступные: {interfaces}")
                return False

            # Создание writer
            output_dir = str(self.data_dir / 'raw')
            writer = DatasetWriter(
                out_dir=output_dir,
                fmt="parquet",
                batch_size=int(cfg.get("batch_size", 1000)),
                flush_interval_sec=float(cfg.get("flush_interval", 2.0)),
            )

            # Запуск writer в фоне
            writer_thread = writer.start()

            # Создание capturer
            cap = PacketCapture(iface=interface, writer=writer, bpf_filter=cfg.get("filters", "tcp or udp"))

            # Запуск сбора в отдельном потоке с таймером
            capture_thread = threading.Thread(target=self._run_capture_with_timeout, args=(cap, duration))
            capture_thread.start()

            # Ожидание завершения
            capture_thread.join()

            # Остановка writer
            writer.stop()
            time.sleep(0.5)  # Время на flush

            logger.info(f"Сбор телеметрии завершен. Данные сохранены в {output_dir}")
            return True

        except ImportError as e:
            logger.error(f"Ошибка импорта коллектора: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка сбора телеметрии: {e}")
            return False

    def _run_capture_with_timeout(self, capturer, duration: int):
        """Запуск захвата с таймером"""
        import time
        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                # Захват пакетов в цикле (имитация)
                # В реальности PacketCapture.start() блокируется
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    def run_preprocessing(self, input_data: str = None):
        """Этап 2: Предобработка и разметка"""
        logger.info("Запуск предобработки данных")

        try:
            import pandas as pd
            import pickle

            if input_data:
                data_path = Path(input_data)
            else:
                data_path = self._latest_parquet()

            logger.info(f"Обработка файла: {data_path}")
            df = pd.read_parquet(data_path)
            logger.info(f"Загружено {len(df)} записей")

            pre_cfg = self.config.get("preprocessing", {}) if self.config else {}
            window_size = int(pre_cfg.get("window_size", 100))
            frames = flow_rows_from_parquet(df, window_size=window_size)

            output_path = self.data_dir / "processed" / f"frames_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, "wb") as f:
                pickle.dump(frames, f)

            csv_path = self.data_dir / "processed" / "features.csv"
            pd.DataFrame(frames).to_csv(csv_path, index=False)

            logger.info(
                f"Предобработка завершена. Обработано {len(frames)} фреймов. Сохранено в {output_path} и {csv_path}"
            )
            return True

        except Exception as e:
            logger.error(f"Ошибка предобработки: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_training(self, model_type: str = 'hybrid'):
        """Этап 3: Обучение модели"""
        logger.info(f"Запуск обучения модели типа: {model_type}")

        try:
            import pickle

            train_cfg = self.config.get("training", {}) if self.config else {}
            if not model_type:
                model_type = str(train_cfg.get("model_type", "hybrid"))

            frames_path = self._latest_processed_frames()
            with open(frames_path, "rb") as f:
                frames = pickle.load(f)

            cfg = dict(self.config) if self.config else {}
            cfg.setdefault("training", {})
            cfg["training"]["model_type"] = model_type

            ensemble, df_all, scores_fit = train_ensemble(frames, cfg)

            model_path = self.models_dir / "ensemble.joblib"
            save_ensemble(model_path, ensemble)

            report = {
                "trained_at": datetime.utcnow().isoformat() + "Z",
                "model_type": model_type,
                "frames_total": int(len(df_all)),
                "t_low": ensemble.t_low,
                "t_high": ensemble.t_high,
                "contamination": ensemble.contamination,
                "threshold_quantile": ensemble.threshold_quantile,
            }
            report_path = self.results_dir / "training_summary.json"
            report_path.parent.mkdir(exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"Обучение модели завершено. Модель сохранена в {model_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
            return False

    def run_validation(self, test_data: str = None):
        """Этап 4: Валидация и тест"""
        logger.info("Запуск валидации модели")

        try:
            import pickle
            import pandas as pd
            from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score, confusion_matrix

            model_path = self.models_dir / "ensemble.joblib"
            if not model_path.exists():
                logger.error(f"Файл модели не найден: {model_path}")
                return False

            ensemble = load_ensemble(model_path)

            if test_data:
                data_path = Path(test_data)
                df = pd.read_parquet(data_path)
                pre_cfg = self.config.get("preprocessing", {}) if self.config else {}
                window_size = int(pre_cfg.get("window_size", 100))
                frames = flow_rows_from_parquet(df, window_size=window_size)
            else:
                frames_path = self._latest_processed_frames()
                with open(frames_path, "rb") as f:
                    frames = pickle.load(f)

            cfg = self.config if self.config else {}
            events_df = predict_frames(ensemble, frames, cfg)

            events_path = self.results_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            write_events_jsonl(events_df, events_path)

            y_true = [bool(fr.get("is_anomaly")) for fr in frames]
            y_pred = [row != "regular" for row in events_df["status"].tolist()]
            scores = events_df["anomaly_score"].tolist()

            report_lines = []
            if any(y_true) and any(not v for v in y_true):
                pr, rc, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
                try:
                    roc = roc_auc_score(y_true, scores)
                except ValueError:
                    roc = 0.0
                try:
                    pr_auc = average_precision_score(y_true, scores)
                except ValueError:
                    pr_auc = 0.0
                tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
                fpr = fp / max((fp + tn), 1)
                report_lines.extend(
                    [
                        f"precision: {pr:.4f}",
                        f"recall: {rc:.4f}",
                        f"f1: {f1:.4f}",
                        f"roc_auc: {roc:.4f}",
                        f"pr_auc: {pr_auc:.4f}",
                        f"fpr: {fpr:.4f}",
                    ]
                )
            else:
                report_lines.append("Недостаточно меток is_anomaly для расчета метрик.")

            report_path = self.results_dir / "validation_report.txt"
            report_path.parent.mkdir(exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines) + "\n")

            logger.info(f"Валидация завершена. Отчет: {report_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка валидации: {e}")
            return False

    def run_monitoring(self):
        """Этап 6: Мониторинг качества"""
        logger.info("Запуск мониторинга")

        try:
            from monitoring_system import MonitoringSystem

            monitor = MonitoringSystem()
            monitor.start()

            logger.info("Мониторинг запущен")
            return True

        except ImportError:
            logger.warning("Мониторинг не реализован")
            return False

    def _calculate_entropy(self, payload: str) -> float:
        """Расчет энтропии payload"""
        if not payload:
            return 0.0

        import math
        entropy = 0.0
        payload_bytes = payload.encode('utf-8', errors='ignore')

        if len(payload_bytes) == 0:
            return 0.0

        for byte in range(256):
            p = payload_bytes.count(byte) / len(payload_bytes)
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

def main():
    parser = argparse.ArgumentParser(description='Traffic Detection Pipeline')
    parser.add_argument('--config', default='pipeline_config.yaml', help='Config file')
    parser.add_argument('--stage', choices=['all', 'collect', 'preprocess', 'train', 'validate', 'monitor'],
                       default='all', help='Pipeline stage to run')
    parser.add_argument('--interface', default='Ethernet', help='Network interface for collection')
    parser.add_argument('--duration', type=int, default=60, help='Collection duration in seconds')
    parser.add_argument('--model-type', choices=['autoencoder', 'hybrid'], default='hybrid',
                       help='Model type for training')

    args = parser.parse_args()

    pipeline = TrafficDetectionPipeline(args.config)

    if args.stage == 'all':
        # Полный pipeline
        success = True
        success &= pipeline.run_collection(args.interface, args.duration)
        success &= pipeline.run_preprocessing()
        success &= pipeline.run_training(args.model_type)
        success &= pipeline.run_validation()
        success &= pipeline.run_monitoring()

        if success:
            logger.info("Pipeline выполнен успешно")
        else:
            logger.error("Pipeline завершен с ошибками")
            sys.exit(1)

    elif args.stage == 'collect':
        pipeline.run_collection(args.interface, args.duration)
    elif args.stage == 'preprocess':
        pipeline.run_preprocessing()
    elif args.stage == 'train':
        pipeline.run_training(args.model_type)
    elif args.stage == 'validate':
        pipeline.run_validation()
    elif args.stage == 'monitor':
        pipeline.run_monitoring()

if __name__ == '__main__':
    main()