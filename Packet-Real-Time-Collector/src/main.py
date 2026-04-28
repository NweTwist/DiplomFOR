# module top-level imports
import os
import time
import argparse
import threading
import queue
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scapy.all import sniff, get_if_list, Ether, IP, IPv6, TCP, UDP, Raw, get_if_hwaddr
import pyarrow as pa
import pyarrow.parquet as pq


class DatasetWriter:
    def __init__(
        self,
        out_dir: str,
        fmt: str = "parquet",
        batch_size: int = 1000,
        flush_interval_sec: float = 2.0,
    ):
        self.out_dir = out_dir
        self.fmt = fmt.lower()
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

        self.queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=20000)
        self.stop_event = threading.Event()
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()

        os.makedirs(self.out_dir, exist_ok=True)

        self.columns = [
            "ts_us",
            "date",
            "hour",
            "iface",
            "length",
            "payload_len",
            "direction",
            "eth_type",
            "src_mac",
            "dst_mac",
            "ip_version",
            "protocol",
            "src_ip",
            "dst_ip",
            "src_port",
            "dst_port",
            "tcp_flags",
            "flow_key",
            "payload_sample",
        ]

        self.schema = pa.schema(
            [
                pa.field("ts_us", pa.int64()),
                pa.field("date", pa.string()),
                pa.field("hour", pa.string()),
                pa.field("iface", pa.string()),
                pa.field("length", pa.int32()),
                pa.field("payload_len", pa.int32()),
                pa.field("direction", pa.string()),
                pa.field("eth_type", pa.string()),
                pa.field("src_mac", pa.string()),
                pa.field("dst_mac", pa.string()),
                pa.field("ip_version", pa.int32()),
                pa.field("protocol", pa.string()),
                pa.field("src_ip", pa.string()),
                pa.field("dst_ip", pa.string()),
                pa.field("src_port", pa.int32()),
                pa.field("dst_port", pa.int32()),
                pa.field("tcp_flags", pa.string()),
                pa.field("flow_key", pa.string()),
                pa.field("payload_sample", pa.string()),
            ]
        )

    def start(self):
        t = threading.Thread(target=self._run, name="DatasetWriter", daemon=True)
        t.start()
        return t

    def stop(self):
        self.stop_event.set()

    def put(self, record: Dict[str, Any]):
        try:
            self.queue.put(record, timeout=0.5)
        except queue.Full:
            # Drop silently to keep line-rate when writer lags
            pass

    def _run(self):
        while not self.stop_event.is_set():
            flushed = False
            try:
                item = self.queue.get(timeout=0.2)
                self.buffer.append(item)
                flushed = self._maybe_flush()
            except queue.Empty:
                pass

            if not flushed:
                now = time.time()
                if now - self.last_flush >= self.flush_interval_sec and self.buffer:
                    self._flush()

        if self.buffer:
            self._flush()

    def _maybe_flush(self) -> bool:
        if len(self.buffer) >= self.batch_size:
            self._flush()
            return True
        return False

    def _flush(self):
        buf = self.buffer
        self.buffer = []
        self.last_flush = time.time()
        if self.fmt == "parquet":
            self._write_parquet(buf)
        elif self.fmt == "csv":
            self._write_csv(buf)
        else:
            self._write_parquet(buf)

    def _write_parquet(self, records: List[Dict[str, Any]]):
        if not records:
            return
        if pa is None or pq is None:
            raise RuntimeError("PyArrow недоступен. Используй '--format csv' или установи pyarrow.")
        table = pa.Table.from_pylist(records, schema=self.schema)
        pq.write_to_dataset(
            table,
            root_path=self.out_dir,
            partition_cols=["date", "hour"],
            existing_data_behavior="overwrite_or_ignore",
        )

    def _write_csv(self, records: List[Dict[str, Any]]):
        if not records:
            return
        import csv

        # Partition dir: out_dir/csv/date/hour/
        date = records[0].get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        hour = records[0].get("hour", datetime.now(timezone.utc).strftime("%H"))
        part_dir = os.path.join(self.out_dir, "csv", date, hour)
        os.makedirs(part_dir, exist_ok=True)

        fname = f"packets_{int(time.time()*1000)}.csv"
        fpath = os.path.join(part_dir, fname)

        with open(fpath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.columns)
            w.writeheader()
            w.writerows(records)


class PacketCapture:
    def __init__(self, iface: str, writer: DatasetWriter, bpf_filter: Optional[str] = None):
        self.iface = iface
        self.writer = writer
        self.bpf_filter = bpf_filter
        self.iface_mac = None
        try:
            self.iface_mac = get_if_hwaddr(self.iface)
        except Exception:
            self.iface_mac = None

    def start(self):
        sniff(
            iface=self.iface,
            filter=self.bpf_filter if self.bpf_filter else None,
            prn=self._on_packet,
            store=False,
        )

    def _on_packet(self, pkt):
        ts = pkt.time  # seconds float
        ts_us = int(ts * 1_000_000)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        date = dt.strftime("%Y-%m-%d")
        hour = dt.strftime("%H")

        length = len(pkt)
        src_mac = None
        dst_mac = None
        eth_type = None

        if Ether in pkt:
            eth = pkt[Ether]
            src_mac = eth.src
            dst_mac = eth.dst
            eth_type = f"0x{eth.type:04x}"

        ip_version = None
        src_ip = None
        dst_ip = None
        protocol = None
        src_port = None
        dst_port = None
        tcp_flags = None

        if IP in pkt:
            ip_version = 4
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            protocol = str(pkt[IP].proto)
        elif IPv6 in pkt:
            ip_version = 6
            src_ip = pkt[IPv6].src
            dst_ip = pkt[IPv6].dst
            protocol = str(pkt[IPv6].nh)

        if TCP in pkt:
            protocol = "TCP"
            src_port = int(pkt[TCP].sport)
            dst_port = int(pkt[TCP].dport)
            tcp_flags = str(pkt[TCP].flags)
        elif UDP in pkt:
            protocol = "UDP"
            src_port = int(pkt[UDP].sport)
            dst_port = int(pkt[UDP].dport)

        payload_len = 0
        payload_sample = ""
        try:
            if Raw in pkt:
                raw_bytes = bytes(pkt[Raw])
                payload_len = len(raw_bytes)
                payload_sample = raw_bytes[:32].hex()
        except Exception:
            pass

        direction = None
        if self.iface_mac and src_mac:
            direction = "out" if src_mac.lower() == self.iface_mac.lower() else "in"

        flow_key = None
        if src_ip and dst_ip and protocol:
            sp = str(src_port) if src_port is not None else "-"
            dp = str(dst_port) if dst_port is not None else "-"
            flow_key = f"{src_ip}:{sp}-{dst_ip}:{dp}-{protocol}"

        record = {
            "ts_us": ts_us,
            "date": date,
            "hour": hour,
            "iface": self.iface,
            "length": int(length),
            "payload_len": int(payload_len),
            "direction": direction,
            "eth_type": eth_type,
            "src_mac": src_mac,
            "dst_mac": dst_mac,
            "ip_version": int(ip_version) if ip_version is not None else None,
            "protocol": protocol,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": int(src_port) if src_port is not None else None,
            "dst_port": int(dst_port) if dst_port is not None else None,
            "tcp_flags": tcp_flags,
            "flow_key": flow_key,
            "payload_sample": payload_sample,
        }

        self.writer.put(record)


def list_ifaces() -> List[str]:
    return list(get_if_list())


def main():
    parser = argparse.ArgumentParser(description="Real-time packet capture -> dataset collector")
    parser.add_argument("--list", action="store_true", help="List available interfaces and exit")
    parser.add_argument("--iface", type=str, help="Interface name to capture")
    parser.add_argument("--out", type=str, default="data", help="Output dataset directory")
    parser.add_argument("--format", type=str, default="parquet", choices=["parquet", "csv"], help="Dataset format")
    parser.add_argument("--batch-size", type=int, default=1000, help="Records per batch write")
    parser.add_argument("--flush-interval", type=float, default=2.0, help="Flush interval seconds")
    parser.add_argument("--filter", type=str, default=None, help="Optional BPF filter (e.g. 'tcp or udp')")
    args = parser.parse_args()

    if args.list:
        for idx, name in enumerate(list_ifaces()):
            print(f"[{idx}] {name}")
        return

    if not args.iface:
        print("Please specify --iface. Use --list to see interfaces.")
        return

    writer = DatasetWriter(out_dir=args.out, fmt=args.format, batch_size=args.batch_size, flush_interval_sec=args.flush_interval)
    writer_thread = writer.start()

    cap = PacketCapture(iface=args.iface, writer=writer, bpf_filter=args.filter)

    print(f"Capturing on '{args.iface}' -> {args.format} dataset at '{args.out}'. Press Ctrl+C to stop.")
    try:
        cap.start()
    except KeyboardInterrupt:
        pass
    finally:
        writer.stop()
        # Give writer a moment to flush
        time.sleep(0.5)
        print("Stopped and flushed.")


if __name__ == "__main__":
    main()