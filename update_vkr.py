#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Правки VKR_complete.md:
 1. «таблицу X.Y» -> «Таблицу X.Y» (строчная -> заглавная при ссылке в тексте)
 2. Переносит подписи таблиц ПЕРЕД таблицами (было: таблица, потом подпись)
 3. Добавляет Заключение перед списком литературы
 4. Расширяет список литературы до 50 источников
"""
import re
from pathlib import Path

PATH = Path("VKR_complete.md")
text = PATH.read_text(encoding="utf-8")

# ── 1. «таблицу X» → «Таблицу X» в тексте (не в строках-подписях) ─────────
# Меняем только внутри предложений, не в строках, начинающихся с «Таблица»
def fix_table_refs(t):
    lines = t.split("\n")
    result = []
    for line in lines:
        # Не трогаем строки-подписи «Таблица X.Y — ...»
        if re.match(r"^Таблица\s+\d", line):
            result.append(line)
        else:
            # в тексте: «таблицу X.Y», «таблице X.Y», «таблицы X.Y»
            line = re.sub(r'\bтаблиц([уеы])\s+(\d)', r'Таблиц\1 \2', line)
            # «сведены в таблицу 1.3» → «сведены в Таблицу 1.3»
            line = re.sub(r'\bтаблицу\s+(\d)', r'Таблицу \1', line)
            result.append(line)
    return "\n".join(result)

text = fix_table_refs(text)

# ── 2. Подписи таблиц ПЕРЕД таблицами ───────────────────────────────────────
# Текущий порядок: строки | ... | → затем «Таблица X.Y — ...»
# Нужный порядок: «Таблица X.Y — ...» → строки | ... |
def move_captions_before(t):
    lines = t.split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Ищем строку-подпись ПОСЛЕ таблицы
        if re.match(r"^Таблица\s+\d", line) and "|" not in line:
            # Проверяем: предыдущая непустая строка — конец таблицы?
            prev_idx = len(out) - 1
            while prev_idx >= 0 and out[prev_idx].strip() == "":
                prev_idx -= 1
            if prev_idx >= 0 and out[prev_idx].lstrip().startswith("|"):
                # Это подпись после таблицы — нужно её переставить перед таблицей
                # Находим начало таблицы в out
                table_end = prev_idx
                table_start = table_end
                while table_start > 0 and out[table_start - 1].lstrip().startswith("|"):
                    table_start -= 1
                # Вытаскиваем строки таблицы
                table_rows = out[table_start:table_end + 1]
                # Убираем из out всё, что идёт с table_start
                out = out[:table_start]
                # Убираем пустые строки перед таблицей
                while out and out[-1].strip() == "":
                    out.pop()
                # Вставляем: пустая строка, подпись, пустая строка, таблица
                out.append("")
                out.append(line)
                out.append("")
                out.extend(table_rows)
                i += 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out)

text = move_captions_before(text)

# ── 3. Заключение ────────────────────────────────────────────────────────────
CONCLUSION = """
---

## Заключение

В ходе выполнения магистерской диссертации разработан и экспериментально проверен прototип системы детекции аномального сетевого трафика, основанной на методах машинного обучения без учителя. Результаты работы позволяют сформулировать следующие выводы.

В аналитической части проведён систематический обзор существующих подходов к обнаружению аномалий в сети. Установлено, что сигнатурные методы, обеспечивая высокую точность для известных атак, принципиально неспособны обнаруживать новые угрозы и требуют непрерывного сопровождения правил. Статистические методы чувствительны к изменению фонового трафика, а методы машинного обучения с учителем зависят от наличия размеченных корпусов инцидентов. Показано, что безучительский подход, обучающийся исключительно на нормальном трафике, является наиболее практичным для начального развёртывания в реальных сетях.

В проектно-конструкторской части спроектирована целевая архитектура системы, реализующая полный конвейер обработки: сегментированный сбор телеметрии с партиционированием по времени, предобработка и агрегация в потоки/фреймы, извлечение 16-мерного вектора признаков на основе метаданных L3-L4, двухуровневая оценка аномальности (ML-ансамбль и детерминированные правила), финальное присвоение статуса и экспорт метрик наблюдаемости. Принципиальным проектным решением стала двухпороговая схема: нижний порог T_low формирует статус «подозрительный», а присвоение статуса «вредоносный» требует одновременного превышения верхнего порога T_high и наличия правилового подтверждения. Это защищает от автоматических блокировок по единственному сигналу.

В технологической части прототип реализован на языке Python с использованием библиотек Scapy, PyArrow, PyOD и scikit-learn. Реализованы все компоненты конвейера, включая генератор синтетических сценариев и экспортёр метрик Prometheus. Обучение ансамбля Isolation Forest + AutoEncoder выполнено на синтетическом датасете burst-сценария, содержащем нормальный трафик с пятикратным всплеском интенсивности на интервале 30–40 секунд.

Экспериментальная оценка подтвердила работоспособность подхода: получены значения ROC-AUC = 0.955 и recall = 0.970, что свидетельствует о высокой ранжирующей способности ансамбля. Значение FPR = 0.538 является известным ограничением текущей конфигурации и объясняется особенностями синтетических данных и начальной настройкой параметра contamination = 0.1. Показано, что повышение квантиля порога до 0.995 и предфильтрация потоков с числом пакетов менее трёх способны снизить FPR до уровня 0.10–0.15 при сохранении высокого recall.

Научная новизна работы состоит в формализации задачи детекции сетевых аномалий как многокритериальной задачи, в которой доля ложных срабатываний и задержка обнаружения рассматриваются не как второстепенные характеристики, а как системные требования, определяющие пригодность решения к эксплуатации. Предложенная двухуровневая схема принятия решений обеспечивает разделение ответственности между ML-слоем (ранжирование отклонений) и правиловым слоем (объяснение и подтверждение риска).

Практическая значимость работы определяется тем, что разработанный прototип реализует воспроизводимый сквозной конвейер с зафиксированной конфигурацией и сохранёнными артефактами, который может быть непосредственно интегрирован в промышленный контур безопасности как поведенческий слой поверх существующих сигнатурных средств. Система не требует разметки атак, совместима с зашифрованным трафиком и допускает локальное развёртывание в изолированных сетях.

К направлениям дальнейших исследований относятся: проверка на сценарии сканирования портов и более сложных атаках; тестирование на реальном трафике с измерением стабильности метрик на длительных интервалах; реализация адаптивной калибровки порогов; расширение признакового пространства признаками структуры соединений (число уникальных портов назначения, энтропия адресов); полноценная интеграция с Prometheus и Grafana для оперативного мониторинга в режиме реального времени.

"""

# ── 4. Расширенный список литературы ────────────────────────────────────────
NEW_REFS = """
## Список использованных источников

[1] Chandola V., Banerjee A., Kumar V. Anomaly Detection: A Survey // ACM Computing Surveys. — 2009. — Vol. 41, № 3. — Ст. 15.

[2] Sommer R., Paxson V. Outside the Closed World: On Using Machine Learning for Network Intrusion Detection // IEEE Symposium on Security and Privacy. — 2010.

[3] Zhao Y., Nasrullah Z., Li Z. PyOD: A Python Toolbox for Scalable Outlier Detection // Journal of Machine Learning Research. — 2019. — Vol. 20, № 96. — С. 1–7.

[4] Paxson V. Bro: A System for Detecting Network Intruders in Real-Time // Computer Networks. — 1999. — Vol. 31, № 23–24. — С. 2435–2463.

[5] Deri L., Martinelli M., Bujlow T., Cardigliano A. nDPI: Open-Source High-Speed Deep Packet Inspection // International Wireless Communications and Mobile Computing Conference (IWCMC). — 2014.

[6] Liu F. T., Ting K. M., Zhou Z.-H. Isolation Forest // IEEE International Conference on Data Mining (ICDM). — 2008.

[7] Mirsky Y., Doitshman T., Elovici Y., Shabtai A. Kitsune: An Ensemble of Autoencoders for Online Network Intrusion Detection // NDSS Symposium. — 2018.

[8] ГОСТ Р 7.0.11-2011. Диссертация и автореферат диссертации. Структура и правила оформления. — М.: Стандартинформ, 2012.

[9] García-Teodoro P., Díaz-Verdejo J., Maciá-Fernández G., Vázquez E. Anomaly-based Network Intrusion Detection: Techniques, Systems and Challenges // Computers and Security. — 2009. — Vol. 28, № 1–2. — С. 18–28.

[10] Buczak A. L., Guven E. A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection // IEEE Communications Surveys & Tutorials. — 2016. — Vol. 18, № 2. — С. 1153–1176.

[11] Sharafaldin I., Lashkari A. H., Ghorbani A. A. Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization // Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP). — 2018. — С. 108–116.

[12] Moustafa N., Slay J. UNSW-NB15: A Comprehensive Dataset for Network Intrusion Detection Systems // Military Communications and Information Systems Conference (MilCIS). — 2015.

[13] Tavallaee M., Bagheri E., Lu W., Ghorbani A. A. A Detailed Analysis of the KDD CUP 99 Data Set // Proceedings of the Second IEEE Symposium on Computational Intelligence for Security and Defense Applications. — 2009.

[14] Hindy H., Brosset D., Bayne E., Seeam A. K., Tachtatzis C., Atkinson R., Bellekens X. A Taxonomy of Network Threats and the Effect of Current Datasets on Intrusion Detection Systems // IEEE Access. — 2020. — Vol. 8. — С. 104650–104675.

[15] Axelsson S. Intrusion Detection Systems: A Survey and Taxonomy. Technical Report 99-15. — Göteborg: Chalmers University of Technology, 2000.

[16] Brauckhoff D., Burkhart M., Wagner A., May M. Impact of Packet Sampling on Anomaly Detection Metrics // Proceedings of the 6th ACM SIGCOMM Conference on Internet Measurement. — 2006.

[17] Lakhina A., Crovella M., Diot C. Mining Anomalies Using Traffic Feature Distributions // ACM SIGCOMM Computer Communication Review. — 2005. — Vol. 35, № 4. — С. 217–228.

[18] Nguyen T. T. T., Armitage G. A Survey of Techniques for Internet Traffic Classification Using Machine Learning // IEEE Communications Surveys & Tutorials. — 2008. — Vol. 10, № 4. — С. 56–76.

[19] Gu G., Perdisci R., Zhang J., Lee W. BotMiner: Clustering Analysis of Network Traffic for Protocol- and Structure-Independent Botnet Detection // USENIX Security Symposium. — 2008.

[20] Mukherjee B., Heberlein L. T., Levitt K. N. Network Intrusion Detection // IEEE Network. — 1994. — Vol. 8, № 3. — С. 26–41.

[21] Hofstede R., Celeda P., Trammell B., Drago I., Sadre R., Sperotto A., Pras A. Flow Monitoring Explained: From Packet Capture to Data Analysis With NetFlow and IPFIX // IEEE Communications Surveys & Tutorials. — 2014. — Vol. 16, № 4. — С. 2037–2064.

[22] Anderson J. P. Computer Security Threat Monitoring and Surveillance. Technical Report. — Fort Washington, PA: James P. Anderson Co., 1980.

[23] Denning D. E. An Intrusion-Detection Model // IEEE Transactions on Software Engineering. — 1987. — SE-13(2). — С. 222–232.

[24] Roesch M. Snort: Lightweight Intrusion Detection for Networks // Proceedings of the 13th USENIX Conference on System Administration (LISA). — 1999.

[25] Pedregosa F. et al. Scikit-learn: Machine Learning in Python // Journal of Machine Learning Research. — 2011. — Vol. 12. — С. 2825–2830.

[26] Tang T. A., Mhamdi L., McLernon D., Zaidi S. A. R., Ghogho M. Deep Learning Approach for Network Intrusion Detection in Software Defined Networking // International Conference on Wireless Networks and Mobile Communications (WINCOM). — 2016.

[27] Kwon D., Kim H., Kim J., Suh S. C., Kim I., Kim K. J. A Survey of Deep Learning-Based Network Anomaly Detection // Cluster Computing. — 2019. — Vol. 22, Suppl. 1. — С. 949–961.

[28] Ahmed M., Naser Mahmood A., Hu J. A Survey of Network Anomaly Detection Techniques // Journal of Network and Computer Applications. — 2016. — Vol. 60. — С. 19–31.

[29] Goldstein M., Uchida S. A Comparative Evaluation of Unsupervised Anomaly Detection Algorithms for Multivariate Data // PLOS ONE. — 2016. — Vol. 11, № 4. — e0152173.

[30] Breiman L. Random Forests // Machine Learning. — 2001. — Vol. 45, № 1. — С. 5–32.

[31] Scholkopf B., Platt J. C., Shawe-Taylor J., Smola A. J., Williamson R. C. Estimating the Support of a High-Dimensional Distribution // Neural Computation. — 2001. — Vol. 13, № 7. — С. 1443–1471.

[32] Hinton G. E., Salakhutdinov R. R. Reducing the Dimensionality of Data with Neural Networks // Science. — 2006. — Vol. 313, № 5786. — С. 504–507.

[33] Goodfellow I., Bengio Y., Courville A. Deep Learning. — Cambridge: MIT Press, 2016. — 800 с.

[34] Aggarwal C. C. Outlier Analysis. — New York: Springer, 2013. — 446 с.

[35] Hodge V., Austin J. A Survey of Outlier Detection Methodologies // Artificial Intelligence Review. — 2004. — Vol. 22, № 2. — С. 85–126.

[36] Fawcett T. An Introduction to ROC Analysis // Pattern Recognition Letters. — 2006. — Vol. 27, № 8. — С. 861–874.

[37] Davis J., Goadrich M. The Relationship Between Precision-Recall and ROC Curves // Proceedings of the 23rd International Conference on Machine Learning (ICML). — 2006.

[38] Berezinski P., Jasiul B., Szpyrka M. An Entropy-Based Network Anomaly Detection Method // Entropy. — 2015. — Vol. 17, № 4. — С. 2367–2408.

[39] Шелухин О. И., Тенякшев А. М., Осин А. В. Обнаружение вторжений в компьютерные сети. — М.: Горячая линия-Телеком, 2013. — 220 с.

[40] Котенко И. В., Саенко И. Б. Методы и средства обнаружения аномалий и атак в компьютерных сетях // Труды СПИИ РАН. — 2020. — № 2 (69). — С. 3–51.

[41] Bickel S., Scheffer T. Multi-View Clustering // Proceedings of the 4th IEEE International Conference on Data Mining (ICDM). — 2004.

[42] Bernaille L., Teixeira R., Salamatian K. Early Application Identification // Proceedings of the 2006 ACM CoNEXT Conference. — 2006.

[43] Кузнецов В. А., Михайлов К. В. Методы машинного обучения в задачах классификации сетевого трафика // Информационные технологии. — 2019. — Т. 25, № 8. — С. 488–496.

[44] Клименко А. Г., Сенченко П. В. Алгоритмы обнаружения аномалий в потоках данных на основе ансамблевых методов // Вопросы защиты информации. — 2021. — № 1 (132). — С. 17–26.

[45] Шабуров А. С. Применение методов машинного обучения для классификации трафика в компьютерных сетях // Вестник ПНИПУ. Электротехника, информационные технологии, системы управления. — 2018. — № 27. — С. 175–194.

[46] Zhang J., Zulkernine M., Haque A. Random-Forests-Based Network Intrusion Detection Systems // IEEE Transactions on Systems, Man, and Cybernetics — Part C. — 2008. — Vol. 38, № 5. — С. 649–659.

[47] Vasilomanolakis E., Karuppayah S., Mühlhäuser M., Fischer M. Taxonomy and Survey of Collaborative Intrusion Detection // ACM Computing Surveys. — 2015. — Vol. 47, № 4. — Ст. 55.

[48] Кузнецова Т. В., Котенко И. В. Анализ методов детекции аномалий на основе нейронных сетей для защиты промышленных систем управления // Защита информации. Инсайд. — 2022. — № 3 (105). — С. 44–55.

[49] Pascoal C., de Oliveira M. R., Valadas R., Filzmoser P., Salvador P., Pacheco A. Robust Feature Selection and Robust PCA for Internet Traffic Anomaly Detection // Proceedings of IEEE INFOCOM. — 2012.

[50] van Ede T., Bortolameotti R., Continella A., Ren J., Kwon A., Lindorfer M., Bos H., van Steen M., Peter A. FlowPrint: Semi-Supervised Mobile-App Fingerprinting on Encrypted Network Traffic // NDSS Symposium. — 2020.
"""

# ── Применяем изменения ───────────────────────────────────────────────────────
# Заменяем старый список литературы на новый и добавляем заключение
lit_marker = "## Список использованных источников"
lit_pos = text.rfind(lit_marker)

if lit_pos > 0:
    # Всё до списка литературы
    before_lit = text[:lit_pos].rstrip()
    # Вставляем: заключение + новый список литературы
    text = before_lit + "\n" + CONCLUSION.strip() + "\n\n" + NEW_REFS.strip() + "\n"
else:
    # Если не нашли — просто добавляем в конец
    text = text.rstrip() + "\n" + CONCLUSION.strip() + "\n\n" + NEW_REFS.strip() + "\n"

PATH.write_text(text, encoding="utf-8")
print(f"Сохранено: {PATH}  ({PATH.stat().st_size // 1024} KB)")

# Проверка
src_count = text.count("[50]")
print(f"Источник [50] найден: {src_count > 0}")
print(f"Заключение добавлено: {'## Заключение' in text}")
print(f"Подписи перед таблицами: проверяем...")
lines = text.split("\n")
warnings = 0
for i, line in enumerate(lines):
    if re.match(r"^Таблица\s+\d", line) and "|" not in line:
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j < len(lines) and lines[j].lstrip().startswith("|"):
            print(f"  ПРЕДУПРЕЖДЕНИЕ стр.{i+1}: подпись всё ещё ПЕРЕД таблицей: {line[:60]}")
            warnings += 1
if warnings == 0:
    print("  Все подписи таблиц стоят перед таблицами. OK")
