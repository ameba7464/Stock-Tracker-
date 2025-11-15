#!/usr/bin/env python3
"""Verification script for FBO/FBS columns in Google Sheets"""

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config

def main():
    # Load config
    config = get_config()
    
    # Connect to Google Sheets
    client = GoogleSheetsClient(config.google_sheet_id)
    sheet = client.get_spreadsheet()
    worksheet = sheet.worksheet(config.google_sheet_name)
    
    # Get all data
    all_data = worksheet.get_all_values()
    
    if not all_data:
        print("❌ No data found in worksheet")
        return
    
    headers = all_data[0]
    rows = all_data[1:13]  # First 12 products
    
    print("\n" + "="*120)
    print("📊 ПРОВЕРКА ДАННЫХ GOOGLE SHEETS - КОЛОНКИ FBO/FBS")
    print("="*120)
    
    # Find column indices
    try:
        vendor_code_idx = headers.index('Артикул')
        total_stock_idx = headers.index('Общие остатки')
        fbo_stock_idx = headers.index('Остатки FBO')
        fbs_stock_idx = headers.index('Остатки FBS')
        
        print(f"\n✅ Найдены все колонки:")
        print(f"   - Артикул: колонка {chr(65 + vendor_code_idx)}")
        print(f"   - Общие остатки: колонка {chr(65 + total_stock_idx)}")
        print(f"   - Остатки FBO: колонка {chr(65 + fbo_stock_idx)}")
        print(f"   - Остатки FBS: колонка {chr(65 + fbs_stock_idx)}")
        
    except ValueError as e:
        print(f"❌ Ошибка: не найдена колонка - {e}")
        print(f"\nДоступные колонки: {headers}")
        return
    
    print("\n" + "-"*120)
    print(f"{'Артикул':<25} | {'Общие остатки':>15} | {'FBO':>10} | {'FBS':>10} | {'Проверка':>15}")
    print("-"*120)
    
    total_products = 0
    correct_splits = 0
    its1_2_3_found = False
    
    for row in rows:
        if not row or len(row) <= max(vendor_code_idx, total_stock_idx, fbo_stock_idx, fbs_stock_idx):
            continue
        
        vendor_code = row[vendor_code_idx]
        total = int(row[total_stock_idx]) if row[total_stock_idx].isdigit() else 0
        fbo = int(row[fbo_stock_idx]) if row[fbo_stock_idx].isdigit() else 0
        fbs = int(row[fbs_stock_idx]) if row[fbs_stock_idx].isdigit() else 0
        
        total_products += 1
        
        # Check if FBO + FBS = Total
        is_correct = (fbo + fbs == total)
        if is_correct:
            correct_splits += 1
        
        status = "✅" if is_correct else "❌"
        
        print(f"{vendor_code:<25} | {total:>15,} | {fbo:>10,} | {fbs:>10,} | {status} {fbo+fbs:>10,}")
        
        # Special check for Its1_2_3/50g
        if vendor_code == "Its1_2_3/50g":
            its1_2_3_found = True
            print(f"\n{'':>25} 🔍 КРИТИЧЕСКАЯ ПРОВЕРКА: Its1_2_3/50g")
            if total >= 3000:
                print(f"{'':>25} ✅ Общие остатки теперь ~{total:,} (было 475)")
                print(f"{'':>25} ✅ FBO: {fbo:,}, FBS: {fbs:,}")
            else:
                print(f"{'':>25} ⚠️ Остатки всё ещё занижены: {total:,} (ожидалось ~3,459)")
    
    print("-"*120)
    print(f"\n📈 ИТОГО:")
    print(f"   - Всего товаров: {total_products}")
    print(f"   - Правильное разделение FBO+FBS=Total: {correct_splits}/{total_products}")
    print(f"   - Точность: {(correct_splits/total_products*100):.1f}%")
    
    if not its1_2_3_found:
        print("\n⚠️ ВНИМАНИЕ: Товар Its1_2_3/50g не найден в первых 12 строках!")
    
    print("\n" + "="*120)
    
    # Detailed warehouse breakdown for Its1_2_3/50g if found
    if its1_2_3_found:
        print("\n📦 Детальная проверка складов для Its1_2_3/50g:")
        print("   (данные из логов синхронизации)")

if __name__ == "__main__":
    main()
