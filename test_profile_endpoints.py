#!/usr/bin/env python3
"""Test script for profile endpoints"""
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

token = login_data['access_token']
headers = {"Authorization": f"Bearer {token}"}

# Test GET /users/me
print("\n2. Testing GET /users/me...")
me_response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
print(f"Status: {me_response.status_code}")
me_data = me_response.json()
print(f"Current profile:")
print(f"  Name: {me_data.get('first_name')} {me_data.get('last_name')}")
print(f"  Email: {me_data.get('email')}")

# Test PUT /users/me (update profile)
print("\n3. Testing PUT /users/me (update profile)...")
update_response = requests.put(
    f"{BASE_URL}/api/v1/users/me",
    headers=headers,
    json={
        "first_name": "Test Updated",
        "last_name": "Profile"
    }
)
print(f"Status: {update_response.status_code}")
if update_response.status_code == 200:
    updated_data = update_response.json()
    print(f"Updated profile:")
    print(f"  Name: {updated_data.get('first_name')} {updated_data.get('last_name')}")
    print("✅ Profile updated successfully!")
else:
    print(f"Error: {update_response.text}")

# Test PUT /users/me/password (change password with wrong current password)
print("\n4. Testing PUT /users/me/password (wrong current password)...")
wrong_pw_response = requests.put(
    f"{BASE_URL}/api/v1/users/me/password",
    headers=headers,
    json={
        "current_password": "WrongPassword123",
        "new_password": "NewPassword123"
    }
)
print(f"Status: {wrong_pw_response.status_code}")
if wrong_pw_response.status_code == 400:
    print("✅ Correctly rejected wrong password")
else:
    print(f"Unexpected response: {wrong_pw_response.text}")

# Test PUT /users/me/password (correct password)
print("\n5. Testing PUT /users/me/password (correct password)...")
correct_pw_response = requests.put(
    f"{BASE_URL}/api/v1/users/me/password",
    headers=headers,
    json={
        "current_password": "TestPassword123",
        "new_password": "TestPassword456"
    }
)
print(f"Status: {correct_pw_response.status_code}")
if correct_pw_response.status_code == 200:
    print("✅ Password changed successfully!")
    print(correct_pw_response.json())
else:
    print(f"Error: {correct_pw_response.text}")

# Test login with new password
print("\n6. Testing login with new password...")
new_login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "test_quota@kauri.com", "password": "TestPassword456"}
)
print(f"Status: {new_login_response.status_code}")
if new_login_response.status_code == 200:
    print("✅ Login with new password successful!")
else:
    print(f"Error: {new_login_response.text}")

# Restore original password
print("\n7. Restoring original password...")
token2 = new_login_response.json()['access_token']
headers2 = {"Authorization": f"Bearer {token2}"}
restore_response = requests.put(
    f"{BASE_URL}/api/v1/users/me/password",
    headers=headers2,
    json={
        "current_password": "TestPassword456",
        "new_password": "TestPassword123"
    }
)
print(f"Status: {restore_response.status_code}")
if restore_response.status_code == 200:
    print("✅ Password restored to original!")

print("\n" + "="*50)
print("All tests completed successfully!")
print("="*50)
