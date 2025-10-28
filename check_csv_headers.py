#!/usr/bin/env python3
"""
Проверка заголовков CSV файлов
"""

import csv

wb_file = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export.csv"
our_file = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (3).csv"

print("WB файл заголовки:")
with open(wb_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print(list(reader.fieldnames))
    
print("\nНаш файл заголовки:")
with open(our_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print(list(reader.fieldnames))
