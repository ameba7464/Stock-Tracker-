#!/usr/bin/env python3
"""
Анализ реальных данных WB для проверки работы исправленного Stock Tracker
"""
import pandas as pd
import json
from collections import defaultdict

def analyze_wb_csv(csv_path):
    """Анализируем CSV файл с данными WB"""
    print("🔍 АНАЛИЗ РЕАЛЬНЫХ ДАННЫХ WILDBERRIES")
    print("=" * 60)
    
    # Сначала посмотрим первые строки файла
    print("📄 ПЕРВЫЕ СТРОКИ ФАЙЛА:")
    with open(csv_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 5:
                print(f"Строка {i}: {line.strip()}")
            else:
                break
    
    # Читаем CSV с правильными параметрами
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', sep=',', skiprows=1)  # Пропускаем первую строку
    except:
        # Пробуем другой разделитель
        df = pd.read_csv(csv_path, encoding='utf-8', sep=';', skiprows=1)
    
    print(f"\n� Всего записей в файле: {len(df)}")
    print(f"📋 Колонки в файле ({len(df.columns)}): {list(df.columns)}")
    
    # Покажем первые несколько записей
    print(f"\n📋 ПЕРВЫЕ ЗАПИСИ:")
    print(df.head(3).to_string())
    
    return df

if __name__ == "__main__":
    csv_path = r"c:\Users\miros\Downloads\24-10-2025-a-s-18-10-2025-po-24-10-2025_export.csv"
    analyze_wb_csv(csv_path)