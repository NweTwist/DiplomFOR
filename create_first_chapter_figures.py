#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate figures for the first thesis chapter.

The figures are intentionally drawn with matplotlib primitives instead of
external diagram tools so the result is reproducible from the project
requirements on a clean Windows machine.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path("figures") / "chapter1"
DPI = 220
FONT_FAMILY = "DejaVu Sans"

BLUE = "#D9EAF7"
BLUE_DARK = "#2E75B6"
GREEN = "#E2F0D9"
GREEN_DARK = "#548235"
ORANGE = "#FCE4D6"
ORANGE_DARK = "#C65911"
GRAY = "#F2F2F2"
GRAY_DARK = "#666666"
PURPLE = "#E4DFEC"
PURPLE_DARK = "#7030A0"


def setup_canvas(width: float = 12, height: float = 6):
    plt.rcParams["font.family"] = FONT_FAMILY
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    facecolor: str = BLUE,
    edgecolor: str = BLUE_DARK,
    fontsize: int = 11,
    weight: str = "normal",
    wrap_width: int = 20,
    radius: float = 0.03,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=1.6,
        edgecolor=edgecolor,
        facecolor=facecolor,
        zorder=2,
    )
    ax.add_patch(patch)
    wrapped_text = "\n".join(fill(part, wrap_width) for part in text.splitlines())
    ax.text(
        x + w / 2,
        y + h / 2,
        wrapped_text,
        ha="center",
        va="center",
        fontsize=fontsize,
        weight=weight,
        color="#1F1F1F",
        linespacing=1.18,
        zorder=3,
    )
    return patch


def arrow(ax, start, end, *, color: str = GRAY_DARK, rad: float = 0.0, lw: float = 1.8):
    arr = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=lw,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=8,
        shrinkB=8,
        zorder=1,
    )
    ax.add_patch(arr)
    return arr


def center_right(rect):
    x, y, w, h = rect
    return (x + w, y + h / 2)


def center_left(rect):
    x, y, _w, h = rect
    return (x, y + h / 2)


def top_center(rect):
    x, y, w, h = rect
    return (x + w / 2, y + h)


def bottom_center(rect):
    x, y, w, _h = rect
    return (x + w / 2, y)


def title(ax, text: str):
    ax.text(0.5, 0.96, text, ha="center", va="top", fontsize=14, weight="bold", color="#1F1F1F")


def save(fig, filename: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / filename, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_1_1():
    fig, ax = setup_canvas(13.5, 7.2)
    title(ax, "Общая логика исследования")
    steps = [
        (0.08, 0.63, "Сетевая телеметрия", "пакеты, потоки,\nокна"),
        (0.39, 0.63, "Признаки", "интенсивность,\nразмеры, интервалы,\nпорты"),
        (0.70, 0.63, "ML-модель", "anomaly score\nдля потока/окна"),
        (0.70, 0.30, "Порог", "квантиль или\ncontamination"),
        (0.39, 0.30, "Метрики качества", "precision, recall,\nF1, FPR, latency"),
        (0.08, 0.30, "Проектная архитектура", "сбор, обработка,\nалерты, мониторинг"),
    ]
    boxes = []
    w, h = 0.22, 0.17
    for i, (x, y, head, body) in enumerate(steps):
        fc = BLUE if i < 2 else GREEN if i < 4 else ORANGE if i == 4 else PURPLE
        ec = BLUE_DARK if i < 2 else GREEN_DARK if i < 4 else ORANGE_DARK if i == 4 else PURPLE_DARK
        boxes.append((x, y, w, h))
        box(ax, x, y, w, h, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=10.5, weight="bold", wrap_width=18)
    for left, right in [(boxes[0], boxes[1]), (boxes[1], boxes[2])]:
        arrow(ax, center_right(left), center_left(right))
    arrow(ax, bottom_center(boxes[2]), top_center(boxes[3]))
    for right, left in [(boxes[3], boxes[4]), (boxes[4], boxes[5])]:
        arrow(ax, center_left(right), center_right(left))
    ax.text(
        0.5,
        0.13,
        "Идея рисунка: показать, что работа идет не от «модели ради модели», а от данных и признаков к измеримому решению.",
        ha="center",
        va="center",
        fontsize=10,
        color=GRAY_DARK,
    )
    save(fig, "figure_1_1_research_logic_v2.png")


def figure_1_2():
    fig, ax = setup_canvas(13.5, 7.4)
    title(ax, "Классификация методов детекции аномального сетевого трафика")
    root_rect = (0.37, 0.79, 0.26, 0.10)
    box(ax, *root_rect, "Методы детекции", facecolor=GRAY, edgecolor=GRAY_DARK, weight="bold", wrap_width=18)
    branches = [
        (0.06, 0.50, 0.26, 0.18, "Сигнатурные правила", "известные шаблоны\n+ объяснимость\n- зависимость от правил", BLUE, BLUE_DARK),
        (0.37, 0.50, 0.26, 0.18, "Статистические пороги", "отклонения pps/bps,\nразмеров и интервалов\n- чувствительность к фону", GREEN, GREEN_DARK),
        (0.68, 0.50, 0.26, 0.18, "ML без учителя", "обучение на норме\n+ anomaly score\n- настройка порога", ORANGE, ORANGE_DARK),
    ]
    branch_rects = []
    for x, y, w, h, head, body, fc, ec in branches:
        rect = (x, y, w, h)
        branch_rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=10, weight="bold", wrap_width=20)
        arrow(ax, bottom_center(root_rect), top_center(rect))
    hybrid_rect = (0.23, 0.15, 0.54, 0.15)
    box(
        ax,
        *hybrid_rect,
        "Гибридная схема: правила закрывают известное, статистика и ML подсвечивают неизвестные отклонения",
        facecolor=PURPLE,
        edgecolor=PURPLE_DARK,
        fontsize=10,
        weight="bold",
        wrap_width=50,
    )
    for rect, rad in zip(branch_rects, [-0.12, 0.0, 0.12]):
        arrow(ax, bottom_center(rect), top_center(hybrid_rect), rad=rad)
    save(fig, "figure_1_2_detection_methods_v2.png")


def figure_1_3():
    fig, ax = setup_canvas(13.5, 6.8)
    title(ax, "Место прототипа относительно IDS/NDR/SIEM")
    ids = (0.05, 0.60, 0.22, 0.14)
    ndr = (0.05, 0.31, 0.22, 0.14)
    proto = (0.39, 0.45, 0.25, 0.17)
    event = (0.39, 0.17, 0.25, 0.13)
    siem = (0.77, 0.45, 0.18, 0.17)
    box(ax, *ids, "NGFW/IDS/IPS\nправила и блокировки", facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=10, weight="bold", wrap_width=20)
    box(ax, *ndr, "NDR/DPI\nповеденческий контекст", facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=10, weight="bold", wrap_width=20)
    box(ax, *proto, "Прототип ВКР\nпризнаки + ML-score + порог", facecolor=GREEN, edgecolor=GREEN_DARK, fontsize=10.5, weight="bold", wrap_width=24)
    box(ax, *siem, "SIEM/SOC\nкорреляция\nи реакция", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=10, weight="bold", wrap_width=16)
    box(ax, *event, "Событие\nscore, статус, признаки,\nвремя, источник", facecolor=GRAY, edgecolor=GRAY_DARK, fontsize=9.8, wrap_width=24)
    arrow(ax, center_right(ids), center_left(proto), rad=-0.08)
    arrow(ax, center_right(ndr), center_left(proto), rad=0.08)
    arrow(ax, center_right(proto), center_left(siem))
    arrow(ax, bottom_center(proto), top_center(event))
    arrow(ax, center_right(event), bottom_center(siem), rad=-0.20)
    ax.text(0.515, 0.76, "Фокус работы", ha="center", fontsize=11, weight="bold", color=GREEN_DARK)
    save(fig, "figure_1_3_prototype_position_v2.png")


def figure_1_4():
    fig, ax = setup_canvas(13.5, 7.2)
    title(ax, "Варианты получения сетевой телеметрии")
    sources = [
        (0.05, 0.64, 0.23, 0.13, "SPAN/TAP", "копия пакетов\nс сегмента сети"),
        (0.05, 0.40, 0.23, 0.13, "Packet capture", "Scapy/Npcap,\npcap/Parquet"),
        (0.05, 0.16, 0.23, 0.13, "NetFlow/IPFIX", "агрегированные\nпотоки"),
        (0.72, 0.64, 0.23, 0.13, "Zeek/DPI", "сессии и события\nпротоколов"),
        (0.72, 0.40, 0.23, 0.13, "Хостовая телеметрия", "процессы, сокеты,\nпользователи"),
    ]
    center_rect = (0.38, 0.43, 0.24, 0.16)
    choice_rect = (0.38, 0.16, 0.24, 0.14)
    box(ax, *center_rect, "Единый слой признаков\nдля детекции", facecolor=GREEN, edgecolor=GREEN_DARK, fontsize=11, weight="bold", wrap_width=20)
    for x, y, w, h, head, body in sources:
        rect = (x, y, w, h)
        box(ax, *rect, f"{head}\n{body}", facecolor=BLUE, edgecolor=BLUE_DARK, fontsize=9.8, weight="bold", wrap_width=20)
        if x < 0.5:
            arrow(ax, center_right(rect), center_left(center_rect), rad=-0.08 if y > 0.5 else 0.08)
        else:
            arrow(ax, center_left(rect), center_right(center_rect), rad=0.08 if y > 0.5 else -0.08)
    box(ax, *choice_rect, "Выбор ВКР\nпакетная телеметрия\nбез полного payload", facecolor=ORANGE, edgecolor=ORANGE_DARK, fontsize=10, weight="bold", wrap_width=22)
    arrow(ax, bottom_center(center_rect), top_center(choice_rect))
    save(fig, "figure_1_4_telemetry_sources_v2.png")


def figure_1_5():
    fig, ax = setup_canvas(13.5, 6.2)
    title(ax, "Преобразование пакетов в признаки")
    steps = [
        ("Пакетная запись", "timestamp, IP, ports,\nprotocol, length"),
        ("Группировка", "flow_key или\nвременное окно"),
        ("Статистики", "count, bytes,\npps/bps, intervals"),
        ("Очистка", "NaN/inf,\nкороткие потоки"),
        ("features.csv", "строка признаков\nдля модели"),
    ]
    colors = [(BLUE, BLUE_DARK), (GREEN, GREEN_DARK), (GREEN, GREEN_DARK), (ORANGE, ORANGE_DARK), (PURPLE, PURPLE_DARK)]
    x0, y, w, h, gap = 0.045, 0.43, 0.155, 0.18, 0.035
    rects = []
    for i, ((head, body), (fc, ec)) in enumerate(zip(steps, colors)):
        x = x0 + i * (w + gap)
        rect = (x, y, w, h)
        rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=9.2, weight="bold", wrap_width=16)
        if i:
            arrow(ax, center_right(rects[i - 1]), center_left(rect))
    ax.text(0.5, 0.22, "Payload не требуется: используются метаданные и агрегированные характеристики поведения.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_1_5_feature_pipeline_v2.png")


def figure_1_6():
    fig, ax = setup_canvas(14.5, 7.0)
    title(ax, "Архитектура прототипа по модулям репозитория")
    modules = [
        (0.04, 0.59, 0.21, 0.16, "Packet-Real-Time-Collector", "сбор пакетов\nи Parquet"),
        (0.29, 0.59, 0.18, 0.16, "main pipeline", "предобработка\nи признаки"),
        (0.52, 0.59, 0.18, 0.16, "NN PacketAnalyse", "AutoEncoder\nи score"),
        (0.75, 0.59, 0.21, 0.16, "DPI engine", "углубленная\nпроверка"),
    ]
    module_rects = []
    for i, (x, y, w, h, head, body) in enumerate(modules):
        fc, ec = (BLUE, BLUE_DARK) if i == 0 else (GREEN, GREEN_DARK) if i in (1, 2) else (ORANGE, ORANGE_DARK)
        rect = (x, y, w, h)
        module_rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=8.8, weight="bold", wrap_width=20)
        if i:
            arrow(ax, center_right(module_rects[i - 1]), center_left(rect))
    lower = [
        (0.18, 0.23, 0.18, 0.13, "models/", "scaler, model,\nthreshold"),
        (0.42, 0.23, 0.18, 0.13, "results/", "метрики,\nотчеты"),
        (0.66, 0.23, 0.18, 0.13, "logs/monitoring", "latency,\nдоля алертов"),
    ]
    lower_rects = []
    for x, y, w, h, head, body in lower:
        rect = (x, y, w, h)
        lower_rects.append(rect)
        box(ax, *rect, f"{head}\n{body}", facecolor=GRAY, edgecolor=GRAY_DARK, fontsize=9.8, weight="bold", wrap_width=18)
    arrow(ax, bottom_center(module_rects[2]), top_center(lower_rects[0]), rad=0.25)
    arrow(ax, bottom_center(module_rects[2]), top_center(lower_rects[1]))
    arrow(ax, bottom_center(module_rects[3]), top_center(lower_rects[2]), rad=-0.18)
    save(fig, "figure_1_6_repository_architecture_v2.png")


def figure_1_7():
    fig, ax = setup_canvas(13.5, 7.0)
    title(ax, "Экспериментальный план оценки качества")
    top = [
        (0.05, 0.65, 0.18, 0.13, "Нормальный трафик", "обучающий\nинтервал"),
        (0.30, 0.65, 0.18, 0.13, "Обучение", "scaler + модель\nбез учителя"),
        (0.55, 0.65, 0.18, 0.13, "Порог", "quantile или\ncontamination"),
        (0.80, 0.65, 0.18, 0.13, "Артефакты", "model, scaler,\nthreshold"),
    ]
    bottom = [
        (0.05, 0.30, 0.18, 0.13, "Тестовый прогон", "норма +\nburst/scan"),
        (0.30, 0.30, 0.18, 0.13, "Инференс", "score для\nпотока/окна"),
        (0.55, 0.30, 0.18, 0.13, "Алерты", "score > threshold"),
        (0.80, 0.30, 0.18, 0.13, "Метрики", "F1, FPR, PR-AUC,\nlatency"),
    ]
    for row, fc, ec in [(top, GREEN, GREEN_DARK), (bottom, ORANGE, ORANGE_DARK)]:
        prev = None
        for x, y, w, h, head, body in row:
            rect = (x, y, w, h)
            box(ax, *rect, f"{head}\n{body}", facecolor=fc, edgecolor=ec, fontsize=9.8, weight="bold", wrap_width=18)
            if prev is not None:
                arrow(ax, center_right(prev), center_left(rect))
            prev = rect
    arrow(ax, bottom_center(top[2][:4]), top_center(bottom[2][:4]))
    ax.text(0.5, 0.08, "Разделение обучения и теста по времени защищает оценку от утечки данных.", ha="center", fontsize=10.5, color=GRAY_DARK)
    save(fig, "figure_1_7_experiment_plan_v2.png")


def main() -> None:
    figure_1_1()
    figure_1_2()
    figure_1_3()
    figure_1_4()
    figure_1_5()
    figure_1_6()
    figure_1_7()
    print(f"Saved figures to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
