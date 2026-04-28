#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования pipeline системы детекции трафика
"""

import sys
import os
from pathlib import Path

# Добавление корневой директории в путь
sys.path.insert(0, str(Path(__file__).parent))

from main_pipeline import TrafficDetectionPipeline

def test_synthetic_data_generation():
    """Тест генерации синтетических данных"""
    print("=== Тест генерации синтетических данных ===")

    from synthetic_generator import SyntheticTrafficGenerator

    generator = SyntheticTrafficGenerator()
    records = generator.generate_dataset(normal_duration=30, anomaly_type='burst', anomaly_start=15)

    print(f"Сгенерировано {len(records)} записей")
    anomalies = sum(1 for r in records if r.get('is_anomaly', False))
    print(f"Из них аномалий: {anomalies}")

    return True

def test_pipeline():
    """Тест полного pipeline"""
    print("=== Тест pipeline ===")

    pipeline = TrafficDetectionPipeline()

    # Генерация тестовых данных
    print("1. Генерация синтетических данных...")
    from synthetic_generator import SyntheticTrafficGenerator
    generator = SyntheticTrafficGenerator()
    records = generator.generate_dataset(normal_duration=30, anomaly_type='burst', anomaly_start=15)

    # Предобработка
    print("2. Предобработка данных...")
    success = pipeline.run_preprocessing()
    if not success:
        print("Ошибка предобработки")
        return False

    # Обучение
    print("3. Обучение модели...")
    success = pipeline.run_training('autoencoder')
    if not success:
        print("Ошибка обучения")
        return False

    # Валидация
    print("4. Валидация модели...")
    success = pipeline.run_validation()
    if not success:
        print("Ошибка валидации")
        return False

    print("Pipeline тест завершен успешно!")
    return True

def main():
    print("Запуск тестов системы детекции трафика")

    # Тест генерации данных
    test_synthetic_data_generation()

    # Тест pipeline
    test_pipeline()

if __name__ == '__main__':
    main()