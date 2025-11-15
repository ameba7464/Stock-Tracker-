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
    
    # Читаем CSV с правильными параметрами
    df = pd.read_csv(csv_path, encoding='utf-8', sep=',', skiprows=1)  # Пропускаем первую строку
    
    print(f"📊 Всего записей в файле: {len(df)}")
    print(f"📋 Основные колонки: Артикул продавца, Склад, Остатки, Заказы")
    
    # Анализ складов
    warehouses = df['Склад'].value_counts()
    print(f"\n🏭 АНАЛИЗ СКЛАДОВ:")
    print(f"Уникальных складов: {len(warehouses)}")
    print("Топ-10 складов:")
    for warehouse, count in warehouses.head(10).items():
        print(f"  - {warehouse}: {count} записей")
    
    marketplace_data = df[df['Склад'] == 'Маркетплейс']
    print(f"\n📍 СКЛАД 'МАРКЕТПЛЕЙС':")
    print(f"Записей: {len(marketplace_data)}")
    
    if len(marketplace_data) > 0:
        marketplace_stock = marketplace_data['Остатки на текущий день, шт'].fillna(0).sum()
        marketplace_orders = marketplace_data['Заказали, шт'].fillna(0).sum()
        print(f"Остатки: {marketplace_stock:.0f} шт")
        print(f"Заказы: {marketplace_orders:.0f} шт")
        
        marketplace_articles = marketplace_data['Артикул продавца'].unique()
        print(f"Артикулы на Маркетплейс: {len(marketplace_articles)}")
        for article in marketplace_articles:
            article_data = marketplace_data[marketplace_data['Артикул продавца'] == article]
            stock = article_data['Остатки на текущий день, шт'].fillna(0).sum()
            orders = article_data['Заказали, шт'].fillna(0).sum()
            print(f"  - {article}: {stock:.0f} остатков, {orders:.0f} заказов")
    
    # Анализ FBS товаров
    fbs_data = df[df['Артикул продавца'].str.contains('.FBS', na=False)]
    print(f"\n🎯 FBS ТОВАРЫ:")
    print(f"FBS записей: {len(fbs_data)}")
    
    if len(fbs_data) > 0:
        fbs_stock = fbs_data['Остатки на текущий день, шт'].fillna(0).sum()
        fbs_orders = fbs_data['Заказали, шт'].fillna(0).sum()
        print(f"Общие остатки FBS: {fbs_stock:.0f} шт")
        print(f"Общие заказы FBS: {fbs_orders:.0f} шт")
        
        fbs_articles = fbs_data['Артикул продавца'].unique()
        for article in fbs_articles:
            article_data = fbs_data[fbs_data['Артикул продавца'] == article]
            stock = article_data['Остатки на текущий день, шт'].fillna(0).sum()
            orders = article_data['Заказали, шт'].fillna(0).sum()
            warehouses_for_article = article_data['Склад'].unique()
            print(f"  - {article}: {stock:.0f} остатков, {orders:.0f} заказов")
            print(f"    Склады: {', '.join(warehouses_for_article)}")
    
    # Группировка по артикулам
    print(f"\n📦 ГРУППИРОВКА ПО АРТИКУЛАМ:")
    grouped = df.groupby('Артикул продавца').agg({
        'Остатки на текущий день, шт': lambda x: x.fillna(0).sum(),
        'Заказали, шт': lambda x: x.fillna(0).sum(),
        'Склад': lambda x: list(x.unique())
    }).reset_index()
    
    critical_issues = []
    for _, row in grouped.iterrows():
        article = row['Артикул продавца']
        stock = row['Остатки на текущий день, шт']
        orders = row['Заказали, шт']
        warehouses_list = row['Склад']
        
        print(f"\n📋 {article}:")
        print(f"  Общие остатки: {stock:.0f} шт")
        print(f"  Общие заказы: {orders:.0f} шт")
        print(f"  Склады ({len(warehouses_list)}): {', '.join(warehouses_list)}")
        
        # Проверяем наличие Маркетплейс
        if 'Маркетплейс' in warehouses_list:
            mp_data = df[(df['Артикул продавца'] == article) & (df['Склад'] == 'Маркетплейс')]
            mp_stock = mp_data['Остатки на текущий день, шт'].fillna(0).sum()
            mp_orders = mp_data['Заказали, шт'].fillna(0).sum()
            print(f"  ⚠️  МАРКЕТПЛЕЙС: {mp_stock:.0f} остатков, {mp_orders:.0f} заказов")
            
            # Если на Маркетплейс большая часть товара - это критично
            if stock > 0 and mp_stock / stock > 0.3:  # Более 30% на Маркетплейс
                critical_issues.append({
                    'article': article,
                    'marketplace_stock': mp_stock,
                    'total_stock': stock,
                    'marketplace_percent': (mp_stock / stock * 100) if stock > 0 else 0
                })
    
    # Создаем тестовые данные для валидации
    test_data = {}
    for _, row in grouped.iterrows():
        article = row['Артикул продавца']
        test_data[article] = {
            'stock': float(row['Остатки на текущий день, шт']),
            'orders': float(row['Заказали, шт']),
            'warehouses': row['Склад']
        }
    
    # Сохраняем тестовые данные
    with open('real_wb_test_data.json', 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🚨 КРИТИЧНЫЕ ПРОБЛЕМЫ (Marketplace > 30% остатков):")
    for issue in critical_issues:
        print(f"  - {issue['article']}: {issue['marketplace_stock']:.0f} из {issue['total_stock']:.0f} ({issue['marketplace_percent']:.1f}%)")
    
    print(f"\n💾 Тестовые данные сохранены в 'real_wb_test_data.json'")
    return test_data

if __name__ == "__main__":
    csv_path = r"c:\Users\miros\Downloads\24-10-2025-a-s-18-10-2025-po-24-10-2025_export.csv"
    analyze_wb_csv(csv_path)