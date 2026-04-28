#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор синтетических данных для тестирования системы детекции трафика
Создает нормальный трафик и аномалии (burst, scanning, etc.)
"""

import argparse
import time
import random
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any

class SyntheticTrafficGenerator:
    """Генератор синтетического сетевого трафика"""

    def __init__(self, output_dir: str = 'data/synthetic'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Нормальные паттерны
        self.normal_ports = [80, 443, 22, 53, 25, 110, 143, 993, 995]
        self.normal_ips = [f"192.168.1.{i}" for i in range(10, 50)]
        self.external_ips = [f"10.0.0.{i}" for i in range(100, 150)]

    def generate_normal_traffic(self, duration_sec: int = 60, pps: int = 10) -> List[Dict[str, Any]]:
        """Генерация нормального трафика"""
        records = []
        base_time = time.time()

        for i in range(duration_sec * pps):
            ts = base_time + (i / pps) + random.uniform(-0.1, 0.1)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            # Случайные параметры
            src_ip = random.choice(self.normal_ips)
            dst_ip = random.choice(self.external_ips)
            src_port = random.randint(1024, 65535)
            dst_port = random.choice(self.normal_ports)
            protocol = random.choice(['TCP', 'UDP'])
            length = random.randint(64, 1500)
            payload_len = max(0, length - 40)  # Примерно

            record = {
                "ts_us": int(ts * 1_000_000),
                "date": dt.strftime("%Y-%m-%d"),
                "hour": dt.strftime("%H"),
                "iface": "Ethernet",
                "length": length,
                "payload_len": payload_len,
                "direction": random.choice(["in", "out"]),
                "eth_type": "0x0800",
                "src_mac": "00:11:22:33:44:55",
                "dst_mac": "66:77:88:99:aa:bb",
                "ip_version": 4,
                "protocol": protocol,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "tcp_flags": "S" if protocol == "TCP" else None,
                "flow_key": f"{src_ip}:{src_port}-{dst_ip}:{dst_port}-{protocol}",
                "payload_sample": "normal_payload_sample",
                "is_anomaly": False
            }
            records.append(record)

        return records

    def generate_anomaly_burst(self, base_records: List[Dict[str, Any]], burst_start: int, burst_duration: int = 10, multiplier: int = 5) -> List[Dict[str, Any]]:
        """Генерация burst аномалии"""
        anomalous_records = []

        for record in base_records:
            anomalous_records.append(record)

            # Добавление burst в указанное время
            if burst_start <= record['ts_us'] / 1_000_000 <= burst_start + burst_duration:
                # Создание дополнительных пакетов
                for _ in range(multiplier - 1):
                    burst_record = record.copy()
                    burst_record['ts_us'] += random.randint(1, 1000)  # Небольшое смещение времени
                    burst_record['length'] = random.randint(1000, 1500)  # Большие пакеты
                    burst_record['payload_len'] = burst_record['length'] - 40
                    burst_record['is_anomaly'] = True
                    anomalous_records.append(burst_record)

        return anomalous_records

    def generate_port_scan(self, duration_sec: int = 30, target_ip: str = "192.168.1.100") -> List[Dict[str, Any]]:
        """Генерация port scanning атаки"""
        records = []
        base_time = time.time()

        for i in range(duration_sec * 20):  # 20 сканирований в сек
            ts = base_time + (i / 20) + random.uniform(-0.01, 0.01)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            src_ip = random.choice(self.external_ips)
            dst_port = random.randint(1, 1024)  # Сканирование низких портов

            record = {
                "ts_us": int(ts * 1_000_000),
                "date": dt.strftime("%Y-%m-%d"),
                "hour": dt.strftime("%H"),
                "iface": "Ethernet",
                "length": 64,
                "payload_len": 0,
                "direction": "in",
                "eth_type": "0x0800",
                "src_mac": "aa:bb:cc:dd:ee:ff",
                "dst_mac": "00:11:22:33:44:55",
                "ip_version": 4,
                "protocol": "TCP",
                "src_ip": src_ip,
                "dst_ip": target_ip,
                "src_port": random.randint(1024, 65535),
                "dst_port": dst_port,
                "tcp_flags": "S",
                "flow_key": f"{src_ip}:{random.randint(1024, 65535)}-{target_ip}:{dst_port}-TCP",
                "payload_sample": "",
                "is_anomaly": True
            }
            records.append(record)

        return records

    def save_to_parquet(self, records: List[Dict[str, Any]], filename: str):
        """Сохранение в Parquet"""
        import pyarrow as pa
        import pyarrow.parquet as pq

        df = pd.DataFrame(records)
        table = pa.Table.from_pandas(df)

        output_path = self.output_dir / filename
        pq.write_to_dataset(
            table,
            root_path=str(self.output_dir),
            partition_cols=["date", "hour"],
            existing_data_behavior="overwrite_or_ignore",
        )

        print(f"Сохранено {len(records)} записей в {output_path}")

    def generate_dataset(self, normal_duration: int = 60, anomaly_type: str = 'burst', anomaly_start: int = 30):
        """Генерация полного датасета с нормой и аномалией"""
        print("Генерация нормального трафика...")
        normal_records = self.generate_normal_traffic(normal_duration)

        if anomaly_type == 'burst':
            print("Добавление burst аномалии...")
            all_records = self.generate_anomaly_burst(normal_records, anomaly_start)
        elif anomaly_type == 'scan':
            print("Добавление port scan аномалии...")
            scan_records = self.generate_port_scan(20)
            all_records = normal_records + scan_records
        else:
            all_records = normal_records

        # Сохранение
        filename = f"synthetic_{anomaly_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        self.save_to_parquet(all_records, filename)

        return all_records

def main():
    parser = argparse.ArgumentParser(description='Synthetic Traffic Generator')
    parser.add_argument('--output-dir', default='data/synthetic', help='Output directory')
    parser.add_argument('--normal-duration', type=int, default=60, help='Normal traffic duration (seconds)')
    parser.add_argument('--anomaly-type', choices=['none', 'burst', 'scan'], default='burst', help='Anomaly type')
    parser.add_argument('--anomaly-start', type=int, default=30, help='Anomaly start time (seconds)')

    args = parser.parse_args()

    generator = SyntheticTrafficGenerator(args.output_dir)
    generator.generate_dataset(args.normal_duration, args.anomaly_type, args.anomaly_start)

if __name__ == '__main__':
    main()