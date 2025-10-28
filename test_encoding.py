import csv

wb_file = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export.csv"

for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'windows-1251']:
    print(f"\nTrying {encoding}:")
    try:
        with open(wb_file, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            print(f"Headers: {reader.fieldnames[:5]}")
            row = next(reader)
            print(f"First article: {row.get('Артикул продавца', 'NOT FOUND')}")
            break
    except Exception as e:
        print(f"Error: {e}")
