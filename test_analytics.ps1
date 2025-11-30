# Test Analytics & Dashboard API Endpoints

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  Stock Tracker Analytics API Testing" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000/api/v1"

# 1. Login to get token
Write-Host "1️⃣ Logging in..." -ForegroundColor Yellow
try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method POST -Body (@{
        email = "test@example.com"
        password = "test123"
    } | ConvertTo-Json) -ContentType "application/json"
    
    $token = $loginResponse.access_token
    $headers = @{
        Authorization = "Bearer $token"
        "Content-Type" = "application/json"
    }
    Write-Host "✅ Login successful!" -ForegroundColor Green
} catch {
    Write-Host "❌ Login failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Test Dashboard Summary
Write-Host "2️⃣ Getting Dashboard Summary..." -ForegroundColor Yellow
try {
    $dashboard = Invoke-RestMethod -Uri "$baseUrl/analytics/dashboard" -Headers $headers
    Write-Host "✅ Dashboard data retrieved!" -ForegroundColor Green
    Write-Host "  📊 Total Products: $($dashboard.total_products)" -ForegroundColor Cyan
    Write-Host "  📦 Total Stock: $($dashboard.total_stock)" -ForegroundColor Cyan
    Write-Host "  🛒 Total Orders: $($dashboard.total_orders)" -ForegroundColor Cyan
    Write-Host "  ⚠️  Low Stock: $($dashboard.low_stock_count)" -ForegroundColor Yellow
    Write-Host "  ❌ Out of Stock: $($dashboard.out_of_stock_count)" -ForegroundColor Red
    Write-Host "  💚 Health Score: $($dashboard.health_score)%" -ForegroundColor Green
} catch {
    Write-Host "❌ Dashboard failed: $_" -ForegroundColor Red
}

Write-Host ""

# 3. Test Product Listing
Write-Host "3️⃣ Listing Products..." -ForegroundColor Yellow
try {
    $products = Invoke-RestMethod -Uri "$baseUrl/products?page=1&page_size=10" -Headers $headers
    Write-Host "✅ Products listed!" -ForegroundColor Green
    Write-Host "  📝 Total: $($products.total) products" -ForegroundColor Cyan
    Write-Host "  📄 Page: $($products.page)/$($products.total_pages)" -ForegroundColor Cyan
    
    if ($products.items.Count -gt 0) {
        Write-Host "  First product: $($products.items[0].seller_article) - Stock: $($products.items[0].total_stock)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Product listing failed: $_" -ForegroundColor Red
}

Write-Host ""

# 4. Test Low Stock Products
Write-Host "4️⃣ Getting Low Stock Products..." -ForegroundColor Yellow
try {
    $lowStockUrl = "$baseUrl/analytics/low-stock" + "?threshold=10" + [char]38 + "limit=20"
    $lowStock = Invoke-RestMethod -Uri $lowStockUrl -Headers $headers
    Write-Host "✅ Low stock products retrieved!" -ForegroundColor Green
    Write-Host "  Found $($lowStock.Count) low stock products" -ForegroundColor Yellow
    
    if ($lowStock.Count -gt 0) {
        foreach ($product in $lowStock | Select-Object -First 5) {
            Write-Host "    - $($product.seller_article): $($product.total_stock) units" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "❌ Low stock query failed: $_" -ForegroundColor Red
}

Write-Host ""

# 5. Test Stock Distribution
Write-Host "5️⃣ Getting Stock Distribution..." -ForegroundColor Yellow
try {
    $distribution = Invoke-RestMethod -Uri "$baseUrl/analytics/stock-distribution" -Headers $headers
    Write-Host "✅ Stock distribution retrieved!" -ForegroundColor Green
    Write-Host "  📊 Out of Stock: $($distribution.out_of_stock)" -ForegroundColor Red
    Write-Host "  Critical (1-5): $($distribution.critical)" -ForegroundColor Yellow
    Write-Host "  Low (6-20): $($distribution.low)" -ForegroundColor Yellow
    Write-Host "  Medium (21-50): $($distribution.medium)" -ForegroundColor Cyan
    Write-Host "  Good (51-100): $($distribution.good)" -ForegroundColor Green
    Write-Host "  Excellent (over 100): $($distribution.excellent)" -ForegroundColor Green
} catch {
    Write-Host "❌ Stock distribution failed: $_" -ForegroundColor Red
}

Write-Host ""

# 6. Test Sync History
Write-Host "6️⃣ Getting Sync History..." -ForegroundColor Yellow
try {
    $historyUrl = "$baseUrl/analytics/sync-history" + "?days=7" + [char]38 + "limit=10"
    $history = Invoke-RestMethod -Uri $historyUrl -Headers $headers
    Write-Host "✅ Sync history retrieved!" -ForegroundColor Green
    Write-Host "  Last $($history.Count) syncs:" -ForegroundColor Cyan
    
    foreach ($sync in $history | Select-Object -First 3) {
        $statusIcon = if ($sync.status -eq "completed") { "✅" } else { "❌" }
        Write-Host "    $statusIcon $($sync.status) - $($sync.products_synced) products - $([Math]::Round($sync.duration_ms/1000, 2))s" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Sync history failed: $_" -ForegroundColor Red
}

Write-Host ""

# 7. Test Warehouse Breakdown
Write-Host "7️⃣ Getting Warehouse Breakdown..." -ForegroundColor Yellow
try {
    $warehouses = Invoke-RestMethod -Uri "$baseUrl/analytics/warehouses" -Headers $headers
    Write-Host "✅ Warehouse data retrieved!" -ForegroundColor Green
    Write-Host "  🏭 Found $($warehouses.Count) warehouses:" -ForegroundColor Cyan
    
    foreach ($wh in $warehouses | Select-Object -First 5) {
        Write-Host "    - $($wh.warehouse_name): $($wh.total_stock) stock, $($wh.product_count) products" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Warehouse breakdown failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  ✅ All Analytics API Tests Completed!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
