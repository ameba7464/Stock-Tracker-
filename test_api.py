"""
Automated API testing script for Stock Tracker API.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_response(response, request_name):
    """Print formatted response."""
    print(f"\n🔹 {request_name}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print("-" * 80)

def test_api():
    """Run all API tests."""
    print_section("🚀 Stock Tracker API Testing Started")
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Store tokens
    access_token = None
    refresh_token = None
    
    # Test 1: Health check
    print_section("1️⃣ Health Check")
    try:
        response = requests.get(f"{BASE_URL}/")
        print_response(response, "GET /")
        
        if response.status_code != 200:
            print("❌ Server is not responding properly!")
            return
        print("✅ Server is running!")
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("Make sure the server is running on http://localhost:8000")
        return
    
    # Test 2: Register User
    print_section("2️⃣ Register New User")
    try:
        payload = {
            "email": "test@example.com",
            "password": "test12345678",
            "company_name": "Test Company",
            "marketplace_type": "wildberries"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print_response(response, "POST /api/v1/auth/register")
        
        if response.status_code == 201:
            data = response.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            print(f"✅ User registered successfully!")
            print(f"Access Token (first 50 chars): {access_token[:50]}...")
        elif response.status_code == 409:
            print("⚠️ User already exists, will try login...")
        else:
            print(f"❌ Registration failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Error during registration: {e}")
    
    # Test 3: Login (if registration failed or user exists)
    if not access_token:
        print_section("3️⃣ Login User")
        try:
            payload = {
                "email": "test@example.com",
                "password": "test12345678"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print_response(response, "POST /api/v1/auth/login")
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                print(f"✅ Login successful!")
                print(f"Access Token (first 50 chars): {access_token[:50]}...")
            else:
                print(f"❌ Login failed with status {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return
    
    if not access_token:
        print("\n❌ No access token available. Cannot continue with authenticated requests.")
        return
    
    # Test 4: Get Tenant Info
    print_section("4️⃣ Get Tenant Information")
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(
            f"{BASE_URL}/api/v1/tenants/me",
            headers=headers
        )
        print_response(response, "GET /api/v1/tenants/me")
        
        if response.status_code == 200:
            print("✅ Tenant info retrieved successfully!")
        else:
            print(f"❌ Failed to get tenant info: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting tenant info: {e}")
    
    # Test 5: Update Wildberries Credentials
    print_section("5️⃣ Update Wildberries Credentials")
    try:
        payload = {
            "wildberries_api_key": "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc3NjM3NjUyNywiaWQiOiIwMTk5ZWM3Mi0yNGRjLTcxMjItYjk0ZC0zNDFiYzM3YmFhYTIiLCJpaWQiOjEwMjEwNTIyNSwib2lkIjoxMjc4Njk0LCJzIjoxMDczNzQyOTcyLCJzaWQiOiJiYmY1MWY5MS0zYjFhLTQ5MGMtOGE4Ni1hNzNkYjgxZTlmNjkiLCJ0IjpmYWxzZSwidWlkIjoxMDIxMDUyMjV9.mPrskzcbBDjUj5lxTcJjmjaPtt2Mx5C0aeok7HytpUk2eWRYngILZotCc1oXVoIoAWJclh-4t0E4F4xeCgOtPg"
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/v1/tenants/me/credentials",
            json=payload,
            headers=headers
        )
        print_response(response, "PATCH /api/v1/tenants/me/credentials")
        
        if response.status_code == 200:
            print("✅ Wildberries credentials updated successfully!")
        else:
            print(f"❌ Failed to update credentials: {response.status_code}")
    except Exception as e:
        print(f"❌ Error updating credentials: {e}")
    
    # Test 6: Sync Products
    print_section("6️⃣ Sync Products")
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/products/sync",
            headers=headers
        )
        print_response(response, "POST /api/v1/products/sync")
        
        if response.status_code == 200:
            print("✅ Product sync initiated successfully!")
        else:
            print(f"❌ Failed to sync products: {response.status_code}")
    except Exception as e:
        print(f"❌ Error syncing products: {e}")
    
    # Final Summary
    print_section("📊 Testing Summary")
    print("✅ All API endpoints have been tested!")
    print(f"\nAccess Token: {access_token[:50] if access_token else 'N/A'}...")
    print(f"Refresh Token: {refresh_token[:50] if refresh_token else 'N/A'}...")
    print("\n" + "="*80)

if __name__ == "__main__":
    test_api()
