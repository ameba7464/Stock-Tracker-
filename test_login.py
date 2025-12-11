import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/auth/login"

# Login credentials
data = {
    "email": "miroslavbabenko228@gmail.com",
    "password": "asacud"
}

try:
    # Send POST request
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ LOGIN SUCCESSFUL!")
        access_token = response.json().get("access_token")
        print(f"Access Token: {access_token[:50]}...")
    else:
        print(f"\n❌ LOGIN FAILED: {response.json()}")
        
except Exception as e:
    print(f"❌ Error: {e}")
