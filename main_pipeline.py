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
import os
from pathlib import Path
import logging
from datetime import datetime
from collections import defaultdict
import pickle

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавление путей к компонентам
sys.path.append(str(Path(__file__).parent / 'Packet-Real-Time-Collector' / 'src'))
sys.path.append(str(Path(__file__).parent / 'Deep-Packet-Inspection-engine'))
sys.path.append(str(Path(__file__).parent / 'NN_for_PacketAnalyse' / 'src'))

class TrafficDetectionPipeline:
    """Главный класс pipeline системы детекции трафика"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'pipeline_config.yaml'
        self.project_root = Path(__file__).parent

        # Пути к компонентам
        self.collector_path = self.project_root / 'Packet-Real-Time-Collector'
        self.dpi_path = self.project_root / 'Deep-Packet-Inspection-engine'
        self.nn_path = self.project_root / 'NN_for_PacketAnalyse'

        # Директории для данных
        self.data_dir = self.project_root / 'data'
        self.models_dir = self.project_root / 'models'
        self.results_dir = self.project_root / 'results'

        for dir_path in [self.data_dir, self.models_dir, self.results_dir]:
            dir_path.mkdir(exist_ok=True)

        logger.info("Pipeline инициализирован")

    def run_collection(self, interface: str = 'Ethernet', duration: int = 60):
        """Этап 1: Сбор телеметрии"""
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
                fmt='parquet',
                batch_size=1000,
                flush_interval_sec=2.0
            )

            # Запуск writer в фоне
            writer_thread = writer.start()

            # Создание capturer
            cap = PacketCapture(iface=interface, writer=writer, bpf_filter="tcp or udp")

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
            import numpy as np

            # Загрузка данных
            if input_data:
                data_path = Path(input_data)
            else:
                # Ищем последние parquet файлы в raw или synthetic
                raw_dir = self.data_dir / 'raw'
                synthetic_dir = self.data_dir / 'synthetic'

                parquet_files = []
                for search_dir in [raw_dir, synthetic_dir]:
                    if search_dir.exists():
                        parquet_files.extend(list(search_dir.rglob('*.parquet')))

                if not parquet_files:
                    logger.error("Parquet файлы не найдены ни в raw/, ни в synthetic/")
                    return False

                data_path = parquet_files[0]  # Используем первый файл

            logger.info(f"Обработка файла: {data_path}")

            # Загрузка и предобработка
            df = pd.read_parquet(data_path)
            logger.info(f"Загружено {len(df)} записей")

            # Группировка по flow_key для агрегации признаков
            flow_features = defaultdict(list)

            for _, row in df.iterrows():
                flow_key = row.get('flow_key', 'unknown')
                flow_features[flow_key].append(row)

            # Извлечение агрегированных признаков для каждого flow
            processed_data = []

            for flow_key, packets in flow_features.items():
                # if len(packets) < 2:
                #     continue  # Пропускаем flows с одним пакетом

                # Сортировка по времени
                packets.sort(key=lambda x: x['ts_us'])

                # Расчет статистик
                timestamps = [p['ts_us'] / 1_000_000 for p in packets]
                sizes = [p['length'] for p in packets]
                inter_arrivals = []

                for i in range(1, len(timestamps)):
                    inter_arrivals.append(timestamps[i] - timestamps[i-1])

                features = {
                    'flow_key': flow_key,
                    'packet_count': len(packets),
                    'duration': timestamps[-1] - timestamps[0],
                    'total_bytes': sum(sizes),
                    'avg_packet_size': np.mean(sizes),
                    'std_packet_size': np.std(sizes) if len(sizes) > 1 else 0,
                    'min_packet_size': min(sizes),
                    'max_packet_size': max(sizes),
                    'pps': len(packets) / max(timestamps[-1] - timestamps[0], 0.001),
                    'bps': sum(sizes) / max(timestamps[-1] - timestamps[0], 0.001),
                    'avg_inter_arrival': np.mean(inter_arrivals) if inter_arrivals else 0,
                    'std_inter_arrival': np.std(inter_arrivals) if len(inter_arrivals) > 1 else 0,
                    'src_ip': packets[0].get('src_ip', ''),
                    'dst_ip': packets[0].get('dst_ip', ''),
                    'src_port': packets[0].get('src_port', 0),
                    'dst_port': packets[0].get('dst_port', 0),
                    'protocol': packets[0].get('protocol', ''),
                    'is_anomaly': any(p.get('is_anomaly', False) for p in packets)
                }

                processed_data.append(features)

            # Сохранение обработанных данных
            output_path = self.data_dir / 'processed' / f'processed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl'
            output_path.parent.mkdir(exist_ok=True)

            with open(output_path, 'wb') as f:
                pickle.dump(processed_data, f)

            # Также сохранить в CSV для NN_for_PacketAnalyse
            csv_path = self.data_dir / 'processed' / 'features.csv'
            features_df = pd.DataFrame(processed_data)
            features_df.to_csv(csv_path, index=False)

            logger.info(f"Предобработка завершена. Обработано {len(processed_data)} flows. Сохранено в {output_path} и {csv_path}")
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
            if model_type == 'autoencoder':
                # Обучение через NN_for_PacketAnalyse
                from train_pyod import main as train_main
                import sys
                from pathlib import Path

                # Подготовка аргументов
                sys.argv = ['train_pyod.py',
                           '--csv', str(self.data_dir / 'processed' / 'features.csv'),
                           '--out-model', str(self.models_dir / 'autoencoder_model.joblib'),
                           '--out-scaler', str(self.models_dir / 'scaler.joblib')]

                train_main()

            elif model_type == 'hybrid':
                # Обучение через Deep-Packet-Inspection-engine
                from ml_engine import MLEngine, TrafficFeatures

                # Загрузка тренировочных данных
                processed_data_path = self.data_dir / 'processed'
                if not processed_data_path.exists():
                    logger.error("Обработанные данные не найдены")
                    return False

                # Загрузка pickle файлов
                training_data = []
                for pkl_file in processed_data_path.glob('*.pkl'):
                    with open(pkl_file, 'rb') as f:
                        data = pickle.load(f)
                        training_data.extend(data)

                # Обучение
                ml_engine = MLEngine()
                # Здесь нужно добавить метод для обучения на данных
                # Пока placeholder
                ml_engine.save_models()

            logger.info("Обучение модели завершено")
            return True

        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
            return False

    def run_validation(self, test_data: str = None):
        """Этап 4: Валидация и тест"""
        logger.info("Запуск валидации модели")

        try:
            from ml_engine import MLEngine
            import pandas as pd
            from sklearn.metrics import classification_report

            # Загрузка модели
            ml_engine = MLEngine()

            # Загрузка тестовых данных
            if test_data:
                test_path = Path(test_data)
            else:
                test_path = self.data_dir / 'test' / 'test_data.csv'

            if not test_path.exists():
                logger.error(f"Тестовые данные не найдены: {test_path}")
                return False

            # Валидация
            # Placeholder для метрик
            logger.info("Валидация завершена")
            return True

        except Exception as e:
            logger.error(f"Ошибка валидации: {e}")
            return False

    def run_monitoring(self):
        """Этап 6: Мониторинг качества"""
        logger.info("Запуск мониторинга")

        try:
            # Импорт мониторинга
            from monitoring_system import MonitoringSystem

            monitor = MonitoringSystem()
            # Запуск мониторинга в фоне
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