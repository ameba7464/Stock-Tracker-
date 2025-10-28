#!/usr/bin/env python3
"""Simple verification script for FBO/FBS columns in Google Sheets"""

import gspread
from google.oauth2.service_account import Credentials
import os
from pathlib import Path

def main():
    # Get credentials path from environment
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Sheet1')
    
    if not creds_path or not sheet_id:
        print("❌ Environment variables not set. Please check .env file.")
        return
    
    # Authenticate with Google Sheets
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(sheet_name)
    
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
        vendor_code_idx = headers.index('Артикул продавца')
        total_stock_idx = headers.index('Остатки (всего)')
        fbo_stock_idx = headers.index('Остатки FBO')
        fbs_stock_idx = headers.index('Остатки FBS')
        
        print(f"\n✅ Найдены все колонки:")
        print(f"   - Артикул продавца: колонка {chr(65 + vendor_code_idx)}")
        print(f"   - Остатки (всего): колонка {chr(65 + total_stock_idx)}")
        print(f"   - Остатки FBO: колонка {chr(65 + fbo_stock_idx)}")
        print(f"   - Остатки FBS: колонка {chr(65 + fbs_stock_idx)}")
        
    except ValueError as e:
        print(f"❌ Ошибка: не найдена колонка - {e}")
        print(f"\nДоступные колонки: {headers}")
        return
    
    print("\n" + "-"*120)
    print(f"{'Артикул':<25} | {'Остатки (всего)':>15} | {'FBO':>10} | {'FBS':>10} | {'Проверка':>15}")
    print("-"*120)
    
    total_products = 0
    correct_splits = 0
    its1_2_3_found = False
    its1_2_3_total = 0
    
    for row in rows:
        if not row or len(row) <= max(vendor_code_idx, total_stock_idx, fbo_stock_idx, fbs_stock_idx):
            continue
        
        vendor_code = row[vendor_code_idx]
        if not vendor_code:
            continue
            
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
            its1_2_3_total = total
            print(f"\n{'':>25} 🔍 КРИТИЧЕСКАЯ ПРОВЕРКА: Its1_2_3/50g")
            if total >= 3000:
                print(f"{'':>25} ✅ Общие остатки теперь ~{total:,} (было 475)")
                print(f"{'':>25} ✅ FBO: {fbo:,}, FBS: {fbs:,}")
                print(f"{'':>25} ✅ Расхождение устранено!")
            else:
                print(f"{'':>25} ⚠️ Остатки всё ещё занижены: {total:,} (ожидалось ~3,459)")
    
    print("-"*120)
    print(f"\n📈 ИТОГО:")
    print(f"   - Всего товаров: {total_products}")
    print(f"   - Правильное разделение FBO+FBS=Total: {correct_splits}/{total_products}")
    print(f"   - Точность: {(correct_splits/total_products*100):.1f}%")
    
    if not its1_2_3_found:
        print("\n⚠️ ВНИМАНИЕ: Товар Its1_2_3/50g не найден в первых 12 строках!")
    elif its1_2_3_total >= 3000:
        print("\n✅ УСПЕХ: Проблема с остатками Its1_2_3/50g решена!")
        print(f"   Было: 475 → Стало: {its1_2_3_total:,}")
        print(f"   Improvement: {((its1_2_3_total - 475) / 475 * 100):.0f}% increase")
    
    print("\n" + "="*120)
    print("\n💡 Примечание:")
    print("   - Колонка I (FBO): Склад WB - остатки на складах Wildberries")
    print("   - Колонка J (FBS): Склад продавца - остатки на маркетплейс складах")

if __name__ == "__main__":
    main()
