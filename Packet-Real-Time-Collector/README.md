# Packet Real-Time Collector (Windows)

Real-time packet capture with automatic dataset collection (Parquet/CSV), partitioned by `date/hour`.

## Prerequisites
- Windows 10/11.
- Npcap installed (https://npcap.com) — required for Scapy sniffing.
- Python 3.10+.

## Install
```bash
pip install -r requirements.txt
```

## Usage
List interfaces:
```bash
python src\main.py --list
```

Start capture (Parquet):
```bash
python src\main.py --iface "Ethernet" --out data --format parquet --batch-size 1000 --flush-interval 2 --filter "tcp or udp"
```

Start capture (CSV):
```bash
python src\main.py --iface "Ethernet" --out data --format csv
```

Dataset layout:
- Parquet: `data/date=YYYY-MM-DD/hour=HH/*.parquet`
- CSV: `data/csv/YYYY-MM-DD/HH/packets_<timestamp>.csv`

Columns: `ts_us,date,hour,iface,length,payload_len,direction,eth_type,src_mac,dst_mac,ip_version,protocol,src_ip,dst_ip,src_port,dst_port,tcp_flags,flow_key,payload_sample`.