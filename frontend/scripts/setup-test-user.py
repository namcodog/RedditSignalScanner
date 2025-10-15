#!/usr/bin/env python3
"""
Setup test user and get authentication token for frontend development.
"""

import requests
import json

API_BASE_URL = "http://localhost:8006"

def register_user(email: str, password: str):
    """Register a new user."""
    url = f"{API_BASE_URL}/api/auth/register"
    data = {
        "email": email,
        "password": password
    }
    
    print(f"Registering user: {email}")
    response = requests.post(url, json=data)
    
    if response.status_code == 201:
        print("✅ User registered successfully!")
        return response.json()
    elif response.status_code == 400 or response.status_code == 409:
        print("⚠️  User already exists, trying to login...")
        return login_user(email, password)
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        return None

def login_user(email: str, password: str):
    """Login existing user."""
    url = f"{API_BASE_URL}/api/auth/login"
    data = {
        "email": email,
        "password": password
    }
    
    print(f"Logging in user: {email}")
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        print("✅ Login successful!")
        return response.json()
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def main():
    print("=" * 60)
    print("🔑 Frontend Test User Setup")
    print("=" * 60)
    print()
    
    # Try to register/login test user
    result = register_user("frontend-test@example.com", "TestPass123")
    
    if result and "access_token" in result:
        print()
        print("=" * 60)
        print("✅ Authentication Token:")
        print("=" * 60)
        print(result["access_token"])
        print()
        print("💡 Usage:")
        print(f"   export TEST_TOKEN='{result['access_token']}'")
        print("   ./frontend/scripts/test-api.sh")
        print()
    else:
        print("❌ Failed to get authentication token")

if __name__ == "__main__":
    main()

