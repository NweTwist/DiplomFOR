# Система детекции аномального сетевого трафика

Интеллектуальная система обнаружения аномалий в сетевом трафике на основе гибридного подхода (сигнатурная детекция + машинное обучение), реализующая MLOps-цикл согласно статье "Трансформация систем межсетевой защиты в интеллектуальные системы детекции трафика".

## Архитектура

Проект состоит из четырех основных компонентов:

1. **Packet-Real-Time-Collector** - Сбор и хранение сетевых пакетов в реальном времени
2. **NN_for_PacketAnalyse** - Нейросетевые модели для анализа трафика (PyOD AutoEncoder)
3. **Deep-Packet-Inspection-engine** - Глубокий анализ пакетов с ML (RandomForest, Isolation Forest)
4. **Main Pipeline** - Оркестрация всего MLOps-цикла

## Установка

### 1. Клонирование и установка зависимостей
```bash
git clone <repository-url>
cd DiplomFOR

# Установка основных зависимостей
pip install -r requirements.txt

# Установка зависимостей компонентов
pip install -r Packet-Real-Time-Collector/requirements.txt
```

### 2. Установка системных зависимостей

**Windows:**
- Npcap: https://npcap.com/
- Microsoft Visual C++ Redistributable

**Linux:**
```bash
sudo apt-get install python3-dev libpcap-dev
```

## Запуск

### Полный pipeline
```bash
python main_pipeline.py --stage all
```

### Поэтапный запуск
```bash
# 1. Сбор данных (60 секунд на интерфейсе Ethernet)
python main_pipeline.py --stage collect --interface Ethernet --duration 60

# 2. Предобработка
python main_pipeline.py --stage preprocess

# 3. Обучение модели
python main_pipeline.py --stage train --model-type autoencoder

# 4. Валидация
python main_pipeline.py --stage validate

# 6. Мониторинг
python main_pipeline.py --stage monitor
```

### Тестирование на синтетических данных
```bash
# Генерация тестовых данных
python synthetic_generator.py --normal-duration 60 --anomaly-type burst --anomaly-start 30

# Запуск тестов
python test_pipeline.py
```

## Конфигурация

Основные настройки в `pipeline_config.yaml`:

```yaml
collection:
  interface: "Ethernet"
  duration: 60
  filters: "tcp or udp"

training:
  model_type: "hybrid"  # или "autoencoder"
  epochs: 50
  contamination: 0.1

monitoring:
  enabled: true
  alert_thresholds:
    anomaly_rate: 0.1
```

## Структура данных

```
data/
├── raw/                    # Raw пакеты (Parquet)
├── processed/              # Обработанные признаки
├── synthetic/              # Синтетические данные для тестов
└── test/                   # Тестовые датасеты

models/                     # Сохраненные модели
├── autoencoder_model.joblib
├── scaler.joblib
└── traffic_classifier.joblib

results/                    # Результаты валидации
logs/                       # Логи работы
```

## Модели

### AutoEncoder (PyOD)
- Обучение на нормальном трафике
- Детекция аномалий по reconstruction error
- Признаки: pps, bps, packet_size stats, inter-arrival times

### Hybrid Model (Deep Packet Inspection)
- RandomForest для классификации протоколов
- Isolation Forest для anomaly detection
- Статистические правила + ML

## Мониторинг

Система включает мониторинг ключевых метрик:
- Количество обработанных пакетов
- Уровень детекции аномалий
- Latency обработки
- Точность модели

## Разработка и тестирование

### Добавление новых признаков
1. Обновить `TrafficFeatures` в `ml_engine.py`
2. Добавить извлечение в `extract_anomaly_features()`
3. Переобучить модель

### Тестирование на реальных данных
1. Запустить сбор на реальном интерфейсе
2. Провести предобработку
3. Оценить качество на известных атаках (nmap, hping3)

### MLOps улучшения
- Версионирование моделей (DVC)
- Автоматическое retraining при дрейфе
- A/B тестирование моделей

## Результаты

Система демонстрирует:
- Высокую точность на синтетических атаках
- Низкий false positive rate на нормальном трафике
- Масштабируемость для реального трафика
- Интерпретируемость решений

## Документация

- [Статья](Статья.md) - Теоретические основы
- [API Reference](docs/api.md) - Документация по классам
- [Experiments](docs/experiments.md) - Результаты тестирования