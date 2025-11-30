# API Testing Script
$baseUrl = "http://localhost:8000"

Write-Host "="*80 -ForegroundColor Cyan
Write-Host "  Stock Tracker API Testing" -ForegroundColor Yellow
Write-Host "="*80 -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n1️⃣ Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method GET
    Write-Host "✅ Server is running!" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit
}

# Test 2: Register User
Write-Host "`n2️⃣ Registering new user..." -ForegroundColor Yellow
try {
    $body = @{
        email = "test@example.com"
        password = "test12345678"
        company_name = "Test Company"
        marketplace_type = "wildberries"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/register" -Method POST -Body $body -ContentType "application/json"
    
    $accessToken = $response.access_token
    $refreshToken = $response.refresh_token
    
    Write-Host "✅ Registration successful!" -ForegroundColor Green
    Write-Host "Access Token: $($accessToken.Substring(0,50))..." -ForegroundColor Cyan
    $response | ConvertTo-Json
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "⚠️ User already exists, trying login..." -ForegroundColor Yellow
        
        # Try login
        $body = @{
            email = "test@example.com"
            password = "test12345678"
        } | ConvertTo-Json

        $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json"
        
        $accessToken = $response.access_token
        $refreshToken = $response.refresh_token
        
        Write-Host "✅ Login successful!" -ForegroundColor Green
        Write-Host "Access Token: $($accessToken.Substring(0,50))..." -ForegroundColor Cyan
        $response | ConvertTo-Json
    } else {
        Write-Host "❌ Error: $_" -ForegroundColor Red
        Write-Host $_.Exception.Response
        exit
    }
}

# Test 3: Get Tenant Info
Write-Host "`n3️⃣ Getting tenant information..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $accessToken"
    }
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/tenants/me" -Method GET -Headers $headers
    
    Write-Host "✅ Tenant info retrieved!" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Test 4: Update Wildberries Credentials
Write-Host "`n4️⃣ Updating Wildberries credentials..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $accessToken"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        wildberries_api_key = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc3NjM3NjUyNywiaWQiOiIwMTk5ZWM3Mi0yNGRjLTcxMjItYjk0ZC0zNDFiYzM3YmFhYTIiLCJpaWQiOjEwMjEwNTIyNSwib2lkIjoxMjc4Njk0LCJzIjoxMDczNzQyOTcyLCJzaWQiOiJiYmY1MWY5MS0zYjFhLTQ5MGMtOGE4Ni1hNzNkYjgxZTlmNjkiLCJ0IjpmYWxzZSwidWlkIjoxMDIxMDUyMjV9.mPrskzcbBDjUj5lxTcJjmjaPtt2Mx5C0aeok7HytpUk2eWRYngILZotCc1oXVoIoAWJclh-4t0E4F4xeCgOtPg"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/tenants/me/credentials" -Method PATCH -Headers $headers -Body $body
    
    Write-Host "✅ Credentials updated!" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Test 5: Sync Products
Write-Host "`n5️⃣ Triggering product sync..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $accessToken"
    }
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/products/sync" -Method POST -Headers $headers
    
    Write-Host "✅ Product sync initiated!" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host "="*80 -ForegroundColor Cyan
Write-Host "  ✅ All API Tests Completed!" -ForegroundColor Green
Write-Host "="*80 -ForegroundColor Cyan
