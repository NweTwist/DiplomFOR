#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate figures for the second thesis chapter."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from create_first_chapter_figures import (
    BLUE,
    BLUE_DARK,
    DPI,
    GRAY,
    GRAY_DARK,
    GREEN,
    GREEN_DARK,
    ORANGE,
    ORANGE_DARK,
    PURPLE,
    PURPLE_DARK,
    arrow,
    bottom_center,
    box,
    center_left,
    center_right,
    setup_canvas,
    title,
    top_center,
)


OUT_DIR = Path("figures") / "chapter2"


def save(fig, filename: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / filename, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_2_1() -> None:
    fig, ax = setup_canvas(14.5, 7.4)
    title(ax, "Целевой конвейер обработки сетевого трафика")
    rects = [
        (0.04, 0.64, 0.18, 0.13, "Коллекторы", "сегменты сети,\nTCP/UDP"),
        (0.28, 0.64, 0.18, 0.13, "Сырые данные", "pcap/Parquet,\nпартиции date/hour"),
        (0.52, 0.64, 0.18, 0.13, "Предобработка", "очистка,\nтипы, окна"),
        (0.76, 0.64, 0.18, 0.13, "Признаки", "flow/window\nfeatures"),
        (0.76, 0.34, 0.18, 0.13, "ML-оценка", "anomaly score\nи порог"),
        (0.52, 0.34, 0.18, 0.13, "Углубленная\nпроверка", "правила, DPI,\nинспектор"),
        (0.28, 0.34, 0.18, 0.13, "Решение", "regular,\nsuspicious,\nmalicious"),
        (0.04, 0.34, 0.18, 0.13, "Интеграции", "SIEM, алертинг,\nмониторинг"),
    ]
    colors = [BLUE, BLUE, GREEN, GREEN, ORANGE, ORANGE, PURPLE, PURPLE]
    edges = [BLUE_DARK, BLUE_DARK, GREEN_DARK, GREEN_DARK, ORANGE_DARK, ORANGE_DARK, PURPLE_DARK, PURPLE_DARK]
    drawn = []
    for rect, fc, ec in zip(rects, colors, edges):
        x, y, w, h, head, body = rect
        drawn.append((x, y, w, h))
        box(ax, x, y, w, h, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=9.4, weight="bold", wrap_width=18)
    for left, right in [(drawn[0], drawn[1]), (drawn[1], drawn[2]), (drawn[2], drawn[3])]:
        arrow(ax, center_right(left), center_left(right))
    arrow(ax, bottom_center(drawn[3]), top_center(drawn[4]))
    for right, left in [(drawn[4], drawn[5]), (drawn[5], drawn[6]), (drawn[6], drawn[7])]:
        arrow(ax, center_left(right), center_right(left))
    ax.text(0.5, 0.16, "Быстрый слой обрабатывает весь поток, глубокая проверка запускается только для подозрительных событий.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_2_1_traffic_pipeline.png")


def figure_2_2() -> None:
    fig, ax = setup_canvas(13.5, 7.2)
    title(ax, "Сегментированный сбор сетевой телеметрии")
    segments = [
        (0.05, 0.65, "Пользовательский\nсегмент"),
        (0.05, 0.42, "Серверный\nсегмент"),
        (0.05, 0.19, "DMZ / лабораторный\nстенд"),
    ]
    collector_rects = []
    for x, y, name in segments:
        seg = (x, y, 0.22, 0.12)
        col = (0.34, y, 0.18, 0.12)
        box(ax, *seg, name, facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=10, weight="bold", wrap_width=18)
        box(ax, *col, "Локальный\nколлектор", facecolor=GREEN, edgecolor=GREEN_DARK, fontsize=10, weight="bold", wrap_width=16)
        arrow(ax, center_right(seg), center_left(col))
        collector_rects.append(col)
    storage = (0.64, 0.52, 0.24, 0.13)
    pipeline = (0.64, 0.28, 0.24, 0.13)
    box(ax, *storage, "Общий слой хранения\nraw/processed", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=10.2, weight="bold", wrap_width=22)
    box(ax, *pipeline, "Центральный pipeline\nпризнаки + ML", facecolor=PURPLE, edgecolor=PURPLE_DARK, fontsize=10.2, weight="bold", wrap_width=22)
    for col in collector_rects:
        arrow(ax, center_right(col), center_left(storage), rad=0.08)
    arrow(ax, bottom_center(storage), top_center(pipeline))
    ax.text(0.5, 0.09, "Разделение по сегментам сохраняет разные базовые линии трафика и снижает шум модели.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_2_2_segmented_collection.png")


def figure_2_3() -> None:
    fig, ax = setup_canvas(13.5, 6.6)
    title(ax, "Преобразование пакетов одного потока в признаки")
    steps = [
        (0.05, 0.46, 0.17, 0.16, "Пакеты", "ts, длина,\nпорты, flags"),
        (0.28, 0.46, 0.17, 0.16, "flow_key", "src/dst IP,\nports, protocol"),
        (0.51, 0.46, 0.17, 0.16, "Сортировка", "по времени\nвнутри потока"),
        (0.74, 0.46, 0.19, 0.16, "Статистики", "duration, pps,\nbps, intervals"),
    ]
    rects = []
    for i, rect in enumerate(steps):
        x, y, w, h, head, body = rect
        fc, ec = (BLUE, BLUE_DARK) if i == 0 else (GREEN, GREEN_DARK)
        rects.append((x, y, w, h))
        box(ax, x, y, w, h, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=9.7, weight="bold", wrap_width=17)
        if i:
            arrow(ax, center_right(rects[i - 1]), center_left(rects[i]))
    out = (0.35, 0.18, 0.30, 0.13)
    box(ax, *out, "Вектор признаков для модели\nfeatures.csv / data_processed", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=10, weight="bold", wrap_width=30)
    arrow(ax, bottom_center(rects[3]), top_center(out), rad=-0.20)
    ax.text(0.5, 0.78, "Признаки строятся из метаданных, поэтому полный payload не требуется.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_2_3_packet_to_features.png")


def figure_2_4() -> None:
    fig, ax = setup_canvas(14, 7.4)
    title(ax, "Работа ансамбля ML-классификаторов")
    input_rect = (0.05, 0.47, 0.18, 0.14)
    box(ax, *input_rect, "Вектор признаков\nпотока/окна", facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=10, weight="bold", wrap_width=18)
    models = [
        (0.34, 0.66, 0.20, 0.12, "AutoEncoder", "нелинейные\nотклонения"),
        (0.34, 0.47, 0.20, 0.12, "Isolation Forest", "быстрый\nбейзлайн"),
        (0.34, 0.28, 0.20, 0.12, "Другие pyOD\nмодели", "сравнение\nметодов"),
    ]
    model_rects = []
    for x, y, w, h, head, body in models:
        rect = (x, y, w, h)
        model_rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=GREEN, edgecolor=GREEN_DARK, fontsize=9.6, weight="bold", wrap_width=18)
        arrow(ax, center_right(input_rect), center_left(rect), rad=0.08 if y > 0.5 else -0.08 if y < 0.4 else 0)
    norm = (0.64, 0.47, 0.16, 0.14)
    threshold = (0.84, 0.47, 0.12, 0.14)
    box(ax, *norm, "Нормировка\nи агрегация\nscore", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=9.7, weight="bold", wrap_width=16)
    box(ax, *threshold, "Пороги\nT_low\nT_high", facecolor=PURPLE, edgecolor=PURPLE_DARK, fontsize=9.7, weight="bold", wrap_width=12)
    for rect in model_rects:
        arrow(ax, center_right(rect), center_left(norm), rad=0.08)
    arrow(ax, center_right(norm), center_left(threshold))
    ax.text(0.90, 0.28, "suspicious\n-> углубленная\nпроверка", ha="center", va="center", fontsize=10, color=GRAY_DARK, weight="bold")
    arrow(ax, bottom_center(threshold), (0.90, 0.35))
    save(fig, "figure_2_4_ml_ensemble.png")


def figure_2_5() -> None:
    fig, ax = setup_canvas(13.5, 7.2)
    title(ax, "Дерево углубленной проверки подозрительного фрейма")
    start = (0.39, 0.76, 0.22, 0.12)
    box(ax, *start, "Подозрительный\nфрейм", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=10.5, weight="bold", wrap_width=18)
    checks = [
        (0.08, 0.48, 0.22, 0.13, "Правила", "scan, SYN-серии,\nподозрительные порты"),
        (0.39, 0.48, 0.22, 0.13, "Протокол/DPI", "фактический тип\nприложения"),
        (0.70, 0.48, 0.22, 0.13, "Нейроинспектор", "сложная комбинация\nпризнаков"),
    ]
    check_rects = []
    for x, y, w, h, head, body in checks:
        rect = (x, y, w, h)
        check_rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=9.6, weight="bold", wrap_width=20)
        arrow(ax, bottom_center(start), top_center(rect), rad=0.10)
    evidence = (0.29, 0.20, 0.42, 0.13)
    box(ax, *evidence, "Набор свидетельств\nscore, правила, признаки, контекст", facecolor=GREEN, edgecolor=GREEN_DARK, fontsize=10.2, weight="bold", wrap_width=34)
    for rect in check_rects:
        arrow(ax, bottom_center(rect), top_center(evidence), rad=0.08)
    ax.text(0.5, 0.09, "Финальный статус повышается только при наличии подтверждающих сигналов.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_2_5_deep_inspection_tree.png")


def figure_2_6() -> None:
    fig, ax = setup_canvas(13.5, 7.4)
    title(ax, "Макет панели наблюдаемости Grafana")
    panel_specs = [
        (0.06, 0.58, 0.26, 0.18, "Входной поток", "packets/sec\nrecords/sec"),
        (0.37, 0.58, 0.26, 0.18, "Latency", "preprocess + ML\n+ decision"),
        (0.68, 0.58, 0.26, 0.18, "Доля статусов", "regular / suspicious\n/ malicious"),
        (0.06, 0.28, 0.26, 0.18, "Anomaly score", "распределение\nпо сегментам"),
        (0.37, 0.28, 0.26, 0.18, "Алерты", "число событий\nпо времени"),
        (0.68, 0.28, 0.26, 0.18, "Ресурсы", "CPU, RAM,\nочереди"),
    ]
    for x, y, w, h, head, body in panel_specs:
        ax.add_patch(Rectangle((x, y), w, h, linewidth=1.5, edgecolor=GRAY_DARK, facecolor=GRAY, zorder=1))
        box(ax, x + 0.02, y + 0.04, w - 0.04, h - 0.08, f"{head}\n{body}", facecolor="white", edgecolor=BLUE_DARK, fontsize=9.7, weight="bold", wrap_width=22)
    ax.text(0.5, 0.12, "Панель показывает не только атаки, но и состояние самого конвейера детекции.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_2_6_grafana_dashboard.png")


def main() -> None:
    figure_2_1()
    figure_2_2()
    figure_2_3()
    figure_2_4()
    figure_2_5()
    figure_2_6()
    print(f"Saved figures to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
