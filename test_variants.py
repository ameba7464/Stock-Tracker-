"""
Тест логики startswith для вариантов артикулов
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher

def test_variants():
    """Тестирование учета вариантов артикулов"""
    
    print("\n" + "="*100)
    print("ТЕСТ: УЧЕТ ВАРИАНТОВ АРТИКУЛОВ")
    print("="*100)
    
    config = get_config()
    fetcher = DualAPIStockFetcher(config.wildberries_api_key)
    
    target = 'ItsSport2/50g'
    
    print(f"\nАртикул: {target}")
    print("-"*100)
    
    # Получаем все FBO данные
    print("\n1. Получение всех FBO данных...")
    fbo_stocks = fetcher.get_fbo_stocks()
    
    print(f"   Всего записей FBO: {len(fbo_stocks)}")
    
    # Ищем все записи с ItsSport2
    all_itssport2 = [s for s in fbo_stocks if 'ItsSport2' in s.get('supplierArticle', '')]
    
    print(f"\n2. Все записи с 'ItsSport2' в supplierArticle:")
    print(f"   Найдено: {len(all_itssport2)} записей")
    
    # Группируем по supplierArticle
    from collections import defaultdict
    by_article = defaultdict(int)
    
    for s in all_itssport2:
        art = s.get('supplierArticle', '')
        qty = s.get('quantityFull', 0)
        by_article[art] += qty
    
    print(f"\n   Детали по supplierArticle:")
    for art, qty in sorted(by_article.items()):
        print(f"      {art}: {qty} ед.")
    
    # Проверяем startswith
    print(f"\n3. Фильтрация с помощью startswith('{target}'):")
    filtered = [s for s in fbo_stocks if s.get('supplierArticle', '').startswith(target)]
    
    print(f"   Найдено: {len(filtered)} записей")
    
    by_article_filtered = defaultdict(int)
    for s in filtered:
        art = s.get('supplierArticle', '')
        qty = s.get('quantityFull', 0)
        by_article_filtered[art] += qty
    
    print(f"\n   Детали после фильтрации:")
    total = 0
    for art, qty in sorted(by_article_filtered.items()):
        print(f"      {art}: {qty} ед.")
        total += qty
    
    print(f"\n   ВСЕГО FBO после фильтрации: {total} ед.")
    
    # Получаем combined stocks
    print(f"\n4. Получение combined stocks через get_combined_stocks_by_article:")
    
    combined = fetcher.get_combined_stocks_by_article(target)
    
    if target in combined:
        data = combined[target]
        print(f"\n   Результат:")
        print(f"      FBO: {data.get('fbo_stock', 0)} ед.")
        print(f"      FBS: {data.get('fbs_stock', 0)} ед.")
        print(f"      ВСЕГО: {data.get('total_stock', 0)} ед.")
        print(f"      Баркоды: {len(data.get('barcodes', []))} шт.")
    else:
        print(f"\n   [ERROR] Нет данных для {target}")
    
    print("\n" + "="*100)
    print("ИТОГИ:")
    print("="*100)
    
    expected_fbo = sum(by_article_filtered.values())
    actual_fbo = data.get('fbo_stock', 0) if target in combined else 0
    
    print(f"\nОжидаемо FBO: {expected_fbo} ед. (сумма всех вариантов с startswith)")
    print(f"Фактически FBO: {actual_fbo} ед. (из get_combined_stocks_by_article)")
    
    if expected_fbo == actual_fbo:
        print("\n[OK] Логика работает корректно!")
    else:
        print(f"\n[ERROR] Расхождение: {actual_fbo - expected_fbo:+} ед.")
    
    print("="*100 + "\n")

if __name__ == '__main__':
    test_variants()
