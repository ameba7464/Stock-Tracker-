import csv

wb_file = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export.csv"

with open(wb_file, 'r', encoding='utf-8-sig') as f:
    # Read first 5 lines
    for i, line in enumerate(f):
        if i < 5:
            print(f"Line {i}: {line[:100]}")
        else:
            break
