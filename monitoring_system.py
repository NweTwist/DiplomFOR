#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Наблюдаемость: экспорт метрик Prometheus (прототип по п. 8.9 ВКР)."""

from __future__ import annotations

import threading
import time
from typing import Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
except ImportError:  # pragma: no cover
    Counter = Histogram = Gauge = start_http_server = None  # type: ignore


class MonitoringSystem:
    def __init__(self, port: int = 9108):
        self.port = port
        self._thread: Optional[threading.Thread] = None
        if Counter is None:
            self._enabled = False
            return
        self._enabled = True
        self.packets_captured = Counter(
            "ndr_packets_captured_total", "Packets written by collectors"
        )
        self.frames_processed = Counter(
            "ndr_frames_processed_total", "Aggregated flow frames processed"
        )
        self.pipeline_latency_ms = Histogram(
            "ndr_pipeline_latency_ms",
            "End-to-end processing latency in milliseconds",
            buckets=(10, 25, 50, 100, 250, 500, 750, 1000, 2500, 5000),
        )
        self.decisions = Counter(
            "ndr_decisions_total",
            "Final decisions by status",
            labelnames=("status",),
        )
        self.anomaly_score = Histogram(
            "ndr_anomaly_score",
            "Distribution of anomaly scores",
            buckets=(0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95, 0.99, 1.0),
        )
        self.suspicious_rate = Gauge(
            "ndr_suspicious_rate",
            "Fraction of non-regular frames in last batch",
        )

    def start(self) -> None:
        if not self._enabled or start_http_server is None:
            return

        def _serve():
            start_http_server(self.port)
            while True:
                time.sleep(3600)

        self._thread = threading.Thread(target=_serve, name="PrometheusExporter", daemon=True)
        self._thread.start()

    def observe_batch(self, latency_ms: float, scores: list, statuses: list) -> None:
        if not self._enabled:
            return
        self.pipeline_latency_ms.observe(max(latency_ms, 0))
        reg = max(len(statuses), 1)
        susp = sum(1 for s in statuses if s != "regular")
        self.suspicious_rate.set(susp / reg)
        for s, sc in zip(statuses, scores):
            self.decisions.labels(status=str(s)).inc()
            self.anomaly_score.observe(min(max(float(sc), 0.0), 1.0))
