#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Объединяет три главы в один Markdown-файл:
  - Исправляет нумерацию ссылок (в гл.1 [6] → [3] для PyOD)
  - Удаляет отдельные списки литературы из каждой главы
  - Добавляет единый список литературы в конце
  - Сохраняет как VKR_complete.md
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Пути к файлам
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
CH1  = ROOT / "Первая глава.md"
CH2  = ROOT / "Вторая глава.md"
CH3  = ROOT / "Третья глава.md"
OUT  = ROOT / "VKR_complete.md"

# ---------------------------------------------------------------------------
# Единый список литературы
# ---------------------------------------------------------------------------
REFS = """\
## Список использованных источников

[1] Chandola V., Banerjee A., Kumar V. Anomaly Detection: A Survey // ACM Computing Surveys. — 2009. — Vol. 41, № 3. — Ст. 15.

[2] Sommer R., Paxson V. Outside the Closed World: On Using Machine Learning for Network Intrusion Detection // IEEE Symposium on Security and Privacy. — 2010.

[3] Zhao Y., Nasrullah Z., Li Z. PyOD: A Python Toolbox for Scalable Outlier Detection // Journal of Machine Learning Research. — 2019. — Vol. 20, № 96. — С. 1–7.

[4] Paxson V. Bro: A System for Detecting Network Intruders in Real-Time // Computer Networks. — 1999. — Vol. 31, № 23–24. — С. 2435–2463.

[5] Deri L., Martinelli M., Bujlow T., Cardigliano A. nDPI: Open-Source High-Speed Deep Packet Inspection // International Wireless Communications and Mobile Computing Conference (IWCMC). — 2014.

[6] Liu F. T., Ting K. M., Zhou Z.-H. Isolation Forest // IEEE International Conference on Data Mining (ICDM). — 2008.

[7] Mirsky Y., Doitshman T., Elovici Y., Shabtai A. Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection // NDSS Symposium. — 2018.

[8] ГОСТ Р 7.0.11-2011. Диссертация и автореферат диссертации. Структура и правила оформления. — М.: Стандартинформ, 2012.
"""

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _strip_chapter_refs(text: str) -> str:
    """Удаляет блок «Источники к главе N» / «Список литературы» в конце файла."""
    # Ищем заголовок блока источников — от него до конца файла
    patterns = [
        r'\n---\s*\nИсточники к главе.*',
        r'\nИсточники к главе.*',
        r'\n## Список использованных источников.*',
        r'\n### Список литературы.*',
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL | re.IGNORECASE)
        if m:
            text = text[:m.start()]
    return text.rstrip()


def _fix_ch1_refs(text: str) -> str:
    """
    В главе 1 ссылка [6] используется для PyOD (Zhao et al.) —
    в единой нумерации это [3]. Заменяем только «[6]» без других цифр рядом.
    """
    # Заменяем [6] -> [3] только если рядом нет других цифр (изолированная ссылка)
    text = re.sub(r'\[6\]', '[3]', text)
    return text


def _clean_trailing_blank_lines(text: str) -> str:
    return text.rstrip() + "\n"


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def merge():
    ch1_raw = CH1.read_text(encoding="utf-8")
    ch2_raw = CH2.read_text(encoding="utf-8")
    ch3_raw = CH3.read_text(encoding="utf-8")

    # 1. Исправляем ссылки в гл.1
    ch1 = _fix_ch1_refs(ch1_raw)
    ch2 = ch2_raw
    ch3 = ch3_raw

    # 2. Удаляем отдельные списки литературы
    ch1 = _strip_chapter_refs(ch1)
    ch2 = _strip_chapter_refs(ch2)
    ch3 = _strip_chapter_refs(ch3)

    # 3. Убираем мета-заголовок ВКР из главы 1 (первые две строки)
    #    «# ВКР магистра» и «Тема: ...» — они войдут в titulniy list DOCX,
    #    но в MD-файле их оставляем как шапку всего документа.
    #    Зато убираем дублирующий «# Глава 2» из начала второй главы
    #    и «# Глава 3» из начала третьей главы (они уже есть внутри как ##).

    # Убираем первые строки гл.1 (мета-заголовок «# ВКР магистра» и строку «Тема:»)
    # — находим первый ## и берём с него
    first_section = re.search(r'^##\s+', ch1, flags=re.MULTILINE)
    if first_section:
        ch1 = ch1[first_section.start():]

    # Убираем верхний # заголовок из гл.2 и гл.3 (они будут ## внутри)
    ch2 = re.sub(r'^# Глава 2\..*\n', '', ch2.lstrip(), flags=re.MULTILINE)
    ch3 = re.sub(r'^# Глава 3\..*\n', '', ch3.lstrip(), flags=re.MULTILINE)

    # 4. Сборка
    parts = [
        "# ВКР магистра\n\n"
        "**Тема:** «Разработка системы детекции аномального сетевого трафика "
        "с использованием методов машинного обучения»\n",

        "---\n",

        # Глава 1 (включает Введение)
        ch1.lstrip(),

        "---\n",

        # Глава 2
        "# Глава 2. Проектно-конструкторский раздел\n\n" + ch2.lstrip(),

        "---\n",

        # Глава 3
        "# Глава 3. Технологическая реализация и экспериментальная оценка системы\n\n"
        + ch3.lstrip(),

        "---\n",

        # Единый список литературы
        REFS,
    ]

    result = "\n\n".join(_clean_trailing_blank_lines(p) for p in parts)

    OUT.write_text(result, encoding="utf-8")
    size_kb = OUT.stat().st_size // 1024
    print(f"Сохранено: {OUT.name}  ({size_kb} KB)")

    # Краткая проверка ссылок
    print("\nПроверка ссылок в итоговом файле:")
    for m in re.finditer(r'\[\d+(?:;\s*\d+)*\]', result):
        # Уникальные номера
        nums = re.findall(r'\d+', m.group())
        for n in nums:
            if int(n) > 8:
                print(f"  ПРЕДУПРЕЖДЕНИЕ: ссылка [{n}] > 8 — возможно не в списке")
    print("  Проверка завершена.")


if __name__ == "__main__":
    merge()
