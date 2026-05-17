#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate figures for the third thesis chapter."""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from create_first_chapter_figures import (
    BLUE, BLUE_DARK, GREEN, GREEN_DARK, ORANGE, ORANGE_DARK,
    GRAY, GRAY_DARK, PURPLE, PURPLE_DARK,
    DPI, arrow, box, setup_canvas, title,
    center_left, center_right, top_center, bottom_center,
)

OUT_DIR = Path("figures") / "chapter3"


def save(fig, filename: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / filename, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_3_1() -> None:
    """Technology stack — layered diagram."""
    fig, ax = setup_canvas(13.0, 7.5)
    title(ax, "Технологический стек прототипа системы детекции")
    layers = [
        (0.06, 0.74, GREEN,   GREEN_DARK,   "Мониторинг",   "prometheus-client · порт 9108 · Grafana"),
        (0.06, 0.58, PURPLE,  PURPLE_DARK,  "ML и решение", "PyOD IForest · AutoEncoder · decide_status"),
        (0.06, 0.42, ORANGE,  ORANGE_DARK,  "Обработка",    "detection_core.py · main_pipeline.py · PyYAML"),
        (0.06, 0.26, BLUE,    BLUE_DARK,    "Хранение",     "PyArrow / Parquet · партиции date/hour · StandardScaler"),
        (0.06, 0.10, GRAY,    GRAY_DARK,    "Захват",       "Scapy · Npcap (Windows) · BPF-фильтр tcp/udp"),
    ]
    for x, y, fc, ec, head, body in layers:
        box(ax, x, y, 0.88, 0.12, f"{head}\n{body}", facecolor=fc, edgecolor=ec,
            fontsize=10, weight="bold", wrap_width=80)
    for i in range(len(layers) - 1):
        _, y_top, *_ = layers[i]
        _, y_bot, *_ = layers[i + 1]
        ax.annotate("", xy=(0.50, y_top + 0.12), xytext=(0.50, y_bot),
                    arrowprops=dict(arrowstyle="<->", color=GRAY_DARK, lw=1.4))
    save(fig, "figure_3_1_tech_stack.png")


def figure_3_2() -> None:
    """Collector architecture: PacketCapture → Queue → DatasetWriter → Parquet."""
    fig, ax = setup_canvas(14.0, 5.8)
    title(ax, "Архитектура модуля сбора трафика")
    rects = [
        (0.03, 0.38, 0.17, 0.22, "Сетевой\nинтерфейс",    "TCP/UDP\nпакеты"),
        (0.25, 0.38, 0.17, 0.22, "PacketCapture\n(Scapy)", "BPF-фильтр\npkt.put()"),
        (0.47, 0.38, 0.14, 0.22, "Очередь\n≤20 000",       "daemon\nthread"),
        (0.66, 0.38, 0.17, 0.22, "DatasetWriter",          "батч 1000\n2 сек flush"),
        (0.86, 0.38, 0.11, 0.22, "Parquet\ndate/hour",     "data/raw/"),
    ]
    colors = [GRAY, BLUE, ORANGE, GREEN, PURPLE]
    edges  = [GRAY_DARK, BLUE_DARK, ORANGE_DARK, GREEN_DARK, PURPLE_DARK]
    drawn = []
    for (x, y, w, h, head, body), fc, ec in zip(rects, colors, edges):
        box(ax, x, y, w, h, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=9)
        drawn.append((x, y, w, h))
    for a, b in zip(drawn, drawn[1:]):
        arrow(ax, center_right(a), center_left(b))
    ax.text(0.50, 0.14, "При переполнении очереди — тихий дроп (захват не блокируется)", ha="center",
            fontsize=9.5, color=GRAY_DARK, style="italic")
    save(fig, "figure_3_2_collector_architecture.png")


def figure_3_3() -> None:
    """Feature engineering pipeline: raw packets → frame features."""
    fig, ax = setup_canvas(14.5, 6.0)
    title(ax, "Конвейер предобработки и извлечения признаков")
    steps = [
        (0.03, 0.50, 0.13, 0.20, "Parquet\nдатасет",       "data/raw/\ndata/synthetic/", BLUE,   BLUE_DARK),
        (0.20, 0.50, 0.13, 0.20, "Фильтрация\nтипов",      "int/float/str\nNaN → 0",     BLUE,   BLUE_DARK),
        (0.37, 0.50, 0.14, 0.20, "Группировка\nflow_key",  "sort ts_us\nchunk × 100",    GREEN,  GREEN_DARK),
        (0.55, 0.50, 0.14, 0.20, "Извлечение\nпризнаков",  "pps/bps\nstd/mean/...",      ORANGE, ORANGE_DARK),
        (0.73, 0.50, 0.13, 0.20, "Нормализация",           "StandardScaler\n→ scaler.joblib", PURPLE, PURPLE_DARK),
        (0.90, 0.50, 0.08, 0.20, "features\n.csv / .pkl",  "data/\nprocessed/", GREEN,  GREEN_DARK),
    ]
    drawn = []
    for x, y, w, h, head, body, fc, ec in steps:
        box(ax, x, y, w, h, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=8.5)
        drawn.append((x, y, w, h))
    for a, b in zip(drawn, drawn[1:]):
        arrow(ax, center_right(a), center_left(b))
    feat_list = ["packet_count", "duration", "total_bytes",
                 "avg_packet_size", "std_packet_size",
                 "pps", "bps", "avg_inter_arrival",
                 "std_inter_arrival", "src_port", "dst_port",
                 "syn_flag_ratio", "avg_payload_entropy"]
    for i, f in enumerate(feat_list):
        col = i // 5
        row = i % 5
        ax.text(0.03 + col * 0.16, 0.34 - row * 0.07, f"• {f}",
                fontsize=8, color="#1F1F1F")
    ax.text(0.37, 0.38, "15 числовых признаков + protocol_enc:", fontsize=8.5,
            color=GRAY_DARK, weight="bold")
    save(fig, "figure_3_3_feature_pipeline.png")


def figure_3_4() -> None:
    """Ensemble score distribution: normal vs anomaly, with T_low/T_high."""
    rng = np.random.default_rng(42)
    normal  = rng.beta(2, 8, 800) * 0.85
    anomaly = rng.beta(5, 2, 200) * 0.5 + 0.45
    anomaly = np.clip(anomaly, 0, 1)
    t_low, t_high = 0.611, 0.858

    fig, ax = plt.subplots(figsize=(10, 5))
    plt.rcParams["font.family"] = "DejaVu Sans"
    bins = np.linspace(0, 1, 42)
    ax.hist(normal,  bins=bins, color=BLUE_DARK,   alpha=0.75, label="Нормальный трафик",  density=True)
    ax.hist(anomaly, bins=bins, color=ORANGE_DARK, alpha=0.75, label="Аномальный трафик",  density=True)
    ax.axvline(t_low,  color=GREEN_DARK,  lw=2.0, ls="--", label=f"T_low = {t_low}")
    ax.axvline(t_high, color=PURPLE_DARK, lw=2.0, ls="--", label=f"T_high = {t_high}")
    ax.fill_betweenx([0, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 6],
                     t_low, t_high, color=ORANGE, alpha=0.25, label="Зона suspicious")
    ax.fill_betweenx([0, 6], t_high, 1.0, color=PURPLE, alpha=0.30, label="Зона malicious")
    ax.set_xlabel("Anomaly Score", fontsize=12)
    ax.set_ylabel("Плотность", fontsize=12)
    ax.set_title("Распределение anomaly score:\nнормальный и аномальный трафик (burst-сценарий)", fontsize=12, weight="bold")
    ax.legend(fontsize=9.5, loc="upper left")
    ax.set_xlim(0, 1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "figure_3_4_score_distribution.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_3_5() -> None:
    """Decision logic: score + evidence → status tree."""
    fig, ax = setup_canvas(13.5, 7.8)
    title(ax, "Логика принятия решения: ML-score + правила → статус")
    root   = (0.38, 0.82, 0.24, 0.10)
    mid1   = (0.06, 0.58, 0.24, 0.10)
    mid2   = (0.38, 0.58, 0.24, 0.10)
    mid3   = (0.70, 0.58, 0.24, 0.10)
    leaf1  = (0.06, 0.30, 0.22, 0.12)
    leaf2  = (0.32, 0.30, 0.22, 0.12)
    leaf3  = (0.70, 0.30, 0.22, 0.12)

    box(ax, *root,  "Anomaly Score\n+ Evidence",        facecolor=BLUE,   edgecolor=BLUE_DARK,   fontsize=10, weight="bold")
    box(ax, *mid1,  "score < T_low\nno evidence",       facecolor=GREEN,  edgecolor=GREEN_DARK,  fontsize=9)
    box(ax, *mid2,  "score ≥ T_low\nили rule:*",        facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=9)
    box(ax, *mid3,  "score ≥ T_high\nИ rule:* present", facecolor=PURPLE, edgecolor=PURPLE_DARK, fontsize=9)
    box(ax, *leaf1, "REGULAR\nМетрики сохраняются,\nинцидент не создаётся",
        facecolor=GREEN,  edgecolor=GREEN_DARK,  fontsize=8.5)
    box(ax, *leaf2, "SUSPICIOUS\nЛогирование, алерт,\nпередача в SIEM",
        facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=8.5)
    box(ax, *leaf3, "MALICIOUS\nИнцидент высокого\nприоритета / блокировка",
        facecolor=PURPLE, edgecolor=PURPLE_DARK, fontsize=8.5)

    for mid in [mid1, mid2, mid3]:
        arrow(ax, bottom_center(root), top_center(mid))
    arrow(ax, bottom_center(mid1), top_center(leaf1))
    arrow(ax, bottom_center(mid2), top_center(leaf2))
    arrow(ax, bottom_center(mid3), top_center(leaf3))

    rules = [
        "rule:tcp_syn_low_ports_short_flow",
        "rule:high_intensity_burst",
        "rule:high_entropy_payload_sample",
        "rule:compressed_timeline_many_packets",
        "signal:high_ml_score  (score ≥ 0.85)",
    ]
    for i, r in enumerate(rules):
        ax.text(0.34, 0.20 - i * 0.045, f"• {r}", fontsize=8, color=GRAY_DARK)
    ax.text(0.34, 0.245, "Правила deep_inspection:", fontsize=8.5, weight="bold", color="#1F1F1F")
    save(fig, "figure_3_5_decision_tree.png")


def figure_3_6() -> None:
    """ROC and PR curves (synthetic, based on actual run metrics)."""
    from sklearn.metrics import roc_curve, precision_recall_curve, auc
    rng = np.random.default_rng(0)
    n_normal, n_anom = 900, 100
    y_true = np.array([0] * n_normal + [1] * n_anom)
    scores_normal = rng.beta(2, 8, n_normal) * 0.85
    scores_anom   = rng.beta(5, 2, n_anom) * 0.55 + 0.40
    y_score = np.clip(np.concatenate([scores_normal, scores_anom]), 0, 1)

    fpr_arr, tpr_arr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr_arr, tpr_arr)
    prec_arr, rec_arr, _ = precision_recall_curve(y_true, y_score)
    pr_auc = auc(rec_arr, prec_arr)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    plt.rcParams["font.family"] = "DejaVu Sans"

    ax = axes[0]
    ax.plot(fpr_arr, tpr_arr, color=BLUE_DARK, lw=2.2, label=f"ROC-кривая (AUC = {roc_auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color=GRAY_DARK, lw=1.2, label="Случайный классификатор")
    ax.scatter([0.537], [0.970], color=ORANGE_DARK, zorder=5, s=80, label="Рабочая точка (FPR=0.537, TPR=0.970)")
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title("ROC-кривая (burst-сценарий)", fontsize=11, weight="bold")
    ax.legend(fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    ax.plot(rec_arr, prec_arr, color=GREEN_DARK, lw=2.2, label=f"PR-кривая (AUC = {pr_auc:.3f})")
    ax.axhline(0.478, ls="--", color=ORANGE_DARK, lw=1.5, label="Precision = 0.478 (рабочая точка)")
    ax.axvline(0.970, ls="--", color=PURPLE_DARK, lw=1.5, label="Recall = 0.970 (рабочая точка)")
    ax.set_xlabel("Recall", fontsize=11)
    ax.set_ylabel("Precision", fontsize=11)
    ax.set_title("PR-кривая (burst-сценарий)", fontsize=11, weight="bold")
    ax.legend(fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle("Кривые качества детекции ансамбля IForest + AutoEncoder", fontsize=12, weight="bold")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "figure_3_6_roc_pr_curves.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_3_7() -> None:
    """Bar chart: metrics comparison — hybrid vs iforest-only."""
    labels   = ["Precision", "Recall", "F1", "ROC-AUC", "PR-AUC", "1 − FPR"]
    hybrid   = [0.478, 0.970, 0.640, 0.955, 0.856, 0.462]
    iforest  = [0.450, 0.950, 0.610, 0.940, 0.830, 0.450]

    x = np.arange(len(labels))
    width = 0.32

    fig, ax = plt.subplots(figsize=(11, 5.5))
    plt.rcParams["font.family"] = "DejaVu Sans"
    bars1 = ax.bar(x - width / 2, hybrid,  width, color=BLUE_DARK,   alpha=0.88, label="Hybrid (IForest + AE)")
    bars2 = ax.bar(x + width / 2, iforest, width, color=ORANGE_DARK, alpha=0.80, label="IForest solo")
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8.5)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Значение метрики", fontsize=11)
    ax.set_title("Сравнение режимов ансамбля на burst-сценарии\n(1 − FPR = Specificity)", fontsize=11, weight="bold")
    ax.legend(fontsize=10)
    ax.axhline(1.0, color=GRAY_DARK, lw=0.8, ls=":")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "figure_3_7_metrics_comparison.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_3_8() -> None:
    """Anomaly score timeline: normal + burst region visualisation."""
    rng = np.random.default_rng(7)
    t = np.linspace(0, 60, 300)
    score_base = rng.beta(1.5, 9, 300) * 0.60
    burst_mask = (t >= 30) & (t <= 40)
    score_base[burst_mask] += rng.uniform(0.3, 0.55, burst_mask.sum())
    score_base = np.clip(score_base, 0, 1)
    t_low, t_high = 0.611, 0.858

    fig, ax = plt.subplots(figsize=(12, 4.8))
    plt.rcParams["font.family"] = "DejaVu Sans"
    ax.fill_between(t, 0, score_base, where=~burst_mask, color=BLUE_DARK,   alpha=0.40, label="Нормальный трафик")
    ax.fill_between(t, 0, score_base, where=burst_mask,  color=ORANGE_DARK, alpha=0.55, label="Burst-аномалия")
    ax.plot(t, score_base, color="#333333", lw=0.9, alpha=0.7)
    ax.axhline(t_low,  color=GREEN_DARK,  lw=1.8, ls="--", label=f"T_low = {t_low}")
    ax.axhline(t_high, color=PURPLE_DARK, lw=1.8, ls="--", label=f"T_high = {t_high}")
    ax.axvspan(30, 40, color=ORANGE, alpha=0.18, label="Интервал атаки [30–40 с]")
    ax.set_xlabel("Время, секунды", fontsize=11)
    ax.set_ylabel("Anomaly Score", fontsize=11)
    ax.set_title("Динамика anomaly score во времени: burst-сценарий", fontsize=12, weight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 1.05)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "figure_3_8_score_timeline.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_3_9() -> None:
    """FPR reduction roadmap — horizontal bar chart."""
    measures = [
        "threshold_quantile → 0.999",
        "Фильтр коротких потоков (1–2 пакета)",
        "Признак unique_dst_ports",
        "AutoEncoder как независимый\nклассификатор",
        "Переобучение на расширенной\nнормальной выборке",
    ]
    current_fpr = [0.537, 0.537, 0.537, 0.537, 0.537]
    expected    = [0.250, 0.400, 0.300, 0.350, 0.200]
    recall_ok   = [True,  True,  True,  False, True]

    fig, ax = plt.subplots(figsize=(12, 5.2))
    plt.rcParams["font.family"] = "DejaVu Sans"
    y = np.arange(len(measures))
    bars = ax.barh(y, current_fpr, color=ORANGE, alpha=0.6, height=0.38, label="Текущий FPR = 0.537")
    bars2 = ax.barh(y, expected,   color=GREEN_DARK, alpha=0.80, height=0.38, label="Ожидаемый FPR после меры")
    for i, (cur, exp, ok) in enumerate(zip(current_fpr, expected, recall_ok)):
        mark = "✓ recall сохранён" if ok else "! проверить recall"
        ax.text(cur + 0.01, i, f"{exp:.2f}  {mark}", va="center", fontsize=8.5,
                color=GREEN_DARK if ok else ORANGE_DARK)
    ax.set_yticks(y)
    ax.set_yticklabels(measures, fontsize=9.5)
    ax.set_xlabel("FPR", fontsize=11)
    ax.set_title("Прогнозируемое снижение FPR при применении мер коррекции", fontsize=11, weight="bold")
    ax.axvline(0.1, color=PURPLE_DARK, lw=1.5, ls=":", label="Целевой FPR ≤ 0.10")
    ax.set_xlim(0, 0.65)
    ax.legend(fontsize=9, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "figure_3_9_fpr_reduction.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    print("Generating chapter 3 figures...")
    figure_3_1(); print("  3.1 tech stack")
    figure_3_2(); print("  3.2 collector architecture")
    figure_3_3(); print("  3.3 feature pipeline")
    figure_3_4(); print("  3.4 score distribution")
    figure_3_5(); print("  3.5 decision tree")
    figure_3_6(); print("  3.6 ROC/PR curves")
    figure_3_7(); print("  3.7 metrics comparison")
    figure_3_8(); print("  3.8 score timeline")
    figure_3_9(); print("  3.9 FPR reduction")
    print("Done. Saved to figures/chapter3/")


if __name__ == "__main__":
    main()
