#!/usr/bin/env python3
"""Test script for quota API endpoints"""
import requests
import json

BASE_URL = "http://localhost:3201"

# Login
print("1. Testing login...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "test_quota@kauri.com", "password": "TestPassword123"}
)
print(f"Status: {login_response.status_code}")
login_data = login_response.json()
print(f"User: {login_data['user']['email']}")
print(f"Subscription: {login_data['user']['subscription_tier']}")

token = login_data['access_token']
headers = {"Authorization": f"Bearer {token}"}

# Test quota endpoint
print("\n2. Testing quota endpoint...")
quota_response = requests.get(f"{BASE_URL}/api/v1/subscription/quota", headers=headers)
print(f"Status: {quota_response.status_code}")
quota_data = quota_response.json()
print(f"Quota Info:")
print(json.dumps(quota_data, indent=2))

# Test usage stats endpoint
print("\n3. Testing usage stats endpoint...")
stats_response = requests.get(f"{BASE_URL}/api/v1/subscription/usage/stats", headers=headers)
print(f"Status: {stats_response.status_code}")
stats_data = stats_response.json()
print(f"Usage Stats:")
print(json.dumps(stats_data, indent=2))

print("\n✅ All tests completed!")
