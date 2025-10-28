import csv

csv_path = r"26-10-2025 История остатков с 20-10-2025 по 26-10-2025_export.csv"

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    row = next(reader)
    
    print("Колонки:")
    for i, key in enumerate(row.keys(), 1):
        print(f"  {i}. {key}")
    
    print("\nПервая строка данных:")
    for key, value in list(row.items())[:10]:
        print(f"  {key}: {value}")
