#!/usr/bin/env python3
"""
Test script to verify token refresh functionality works correctly.
This simulates how a mobile app would handle token refresh.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
REFRESH_URL = f"{BASE_URL}/auth/refresh"
PROTECTED_URL = f"{BASE_URL}/auth/users"  # Any protected endpoint

# Test credentials (adjust as needed)
TEST_CREDENTIALS = {
    "phone": 1234567890,
    "password": "supersecurepassword",
    "device_id": "test_device_123"
}

def test_login_and_refresh():
    """Test the complete login and refresh flow"""
    print("🔐 Testing Token Refresh Flow")
    print("=" * 50)
    
    # Step 1: Login to get initial tokens
    print("1. Logging in to get initial tokens...")
    login_response = requests.post(LOGIN_URL, json=TEST_CREDENTIALS)
    
    if login_response.status_code != 201:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    login_data = login_response.json()
    if login_data.get("status_code") != 201:
        print(f"❌ Login failed: {login_data.get('message')}")
        return False
    
    access_token = login_data["data"]["access_token"]
    refresh_token = login_data["data"]["refresh_token"]
    
    print(f"✅ Login successful!")
    print(f"   Access token: {access_token[:50]}...")
    print(f"   Refresh token: {refresh_token[:50]}...")
    
    # Step 2: Test access token works
    print("\n2. Testing access token with protected endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}
    protected_response = requests.get(PROTECTED_URL, headers=headers)
    
    if protected_response.status_code == 200:
        print("✅ Access token works!")
    else:
        print(f"❌ Access token failed: {protected_response.status_code}")
        print(f"Response: {protected_response.text}")
    
    # Step 3: Test refresh token
    print("\n3. Testing refresh token...")
    refresh_payload = {"refresh_token": refresh_token}
    refresh_response = requests.post(REFRESH_URL, json=refresh_payload)
    
    if refresh_response.status_code != 200:
        print(f"❌ Refresh failed: {refresh_response.status_code}")
        print(f"Response: {refresh_response.text}")
        return False
    
    refresh_data = refresh_response.json()
    if refresh_data.get("status_code") != 200:
        print(f"❌ Refresh failed: {refresh_data.get('message')}")
        return False
    
    new_access_token = refresh_data["data"]["access_token"]
    print(f"✅ Refresh successful!")
    print(f"   New access token: {new_access_token[:50]}...")
    
    # Step 4: Test new access token works
    print("\n4. Testing new access token...")
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    new_protected_response = requests.get(PROTECTED_URL, headers=new_headers)
    
    if new_protected_response.status_code == 200:
        print("✅ New access token works!")
        print("\n🎉 Token refresh flow completed successfully!")
        return True
    else:
        print(f"❌ New access token failed: {new_protected_response.status_code}")
        print(f"Response: {new_protected_response.text}")
        return False

def test_invalid_refresh_token():
    """Test that invalid refresh tokens are rejected"""
    print("\n🔒 Testing Invalid Refresh Token")
    print("=" * 50)
    
    invalid_refresh_payload = {"refresh_token": "invalid.token.here"}
    refresh_response = requests.post(REFRESH_URL, json=invalid_refresh_payload)
    
    if refresh_response.status_code == 401:
        print("✅ Invalid refresh token correctly rejected!")
        return True
    else:
        print(f"❌ Invalid refresh token should be rejected but got: {refresh_response.status_code}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Token Refresh Tests")
    print("Make sure your server is running on http://localhost:8000")
    print()
    
    try:
        # Test 1: Normal flow
        success1 = test_login_and_refresh()
        
        # Test 2: Invalid token
        success2 = test_invalid_refresh_token()
        
        print("\n" + "=" * 50)
        if success1 and success2:
            print("🎉 All tests passed! Token refresh is working correctly.")
            print("\n📱 Mobile App Integration:")
            print("   1. Store both access_token and refresh_token from login")
            print("   2. Use access_token for API calls")
            print("   3. When you get 401 error, call /auth/refresh with refresh_token")
            print("   4. Update stored access_token with the new one")
            print("   5. Retry the original API call")
        else:
            print("❌ Some tests failed. Check the implementation.")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
