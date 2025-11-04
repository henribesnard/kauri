#!/usr/bin/env python
"""
Script de test pour valider les endpoints d'authentification
Usage: python test_auth_endpoints.py
"""
import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api/v1"


class Colors:
    """Couleurs pour le terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(message: str):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def print_error(message: str):
    print(f"{Colors.RED}✗{Colors.END} {message}")


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def print_section(title: str):
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}{title}{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}\n")


def test_health_check():
    """Test du health check"""
    print_section("TEST 1: Health Check")

    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check OK: {data['status']}")
            print_info(f"Service: {data['service']} v{data['version']}")
            print_info(f"Database: {data.get('database', 'unknown')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {str(e)}")
        return False


def test_register(email: str, password: str) -> Optional[str]:
    """Test de l'enregistrement"""
    print_section("TEST 2: Register User")

    try:
        payload = {
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User"
        }

        response = requests.post(f"{API_BASE}/auth/register", json=payload)

        if response.status_code == 201:
            data = response.json()
            token = data.get("access_token")
            print_success(f"User registered successfully")
            print_info(f"Email: {email}")
            print_info(f"Token: {token[:50]}...")
            print_info(f"Expires in: {data.get('expires_in')} seconds")
            return token
        else:
            error = response.json()
            print_error(f"Registration failed: {error.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Registration error: {str(e)}")
        return None


def test_login(email: str, password: str) -> Optional[str]:
    """Test de la connexion"""
    print_section("TEST 3: Login User")

    try:
        payload = {
            "email": email,
            "password": password
        }

        response = requests.post(f"{API_BASE}/auth/login", json=payload)

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_success(f"Login successful")
            print_info(f"Email: {email}")
            print_info(f"Token: {token[:50]}...")
            print_info(f"Expires in: {data.get('expires_in')} seconds")
            return token
        else:
            error = response.json()
            print_error(f"Login failed: {error.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return None


def test_me(token: str) -> bool:
    """Test de récupération des infos utilisateur"""
    print_section("TEST 4: Get Current User (me)")

    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(f"{API_BASE}/auth/me", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_success(f"User info retrieved")
            print_info(f"User ID: {data['user_id']}")
            print_info(f"Email: {data['email']}")
            print_info(f"Name: {data.get('first_name', '')} {data.get('last_name', '')}")
            print_info(f"Active: {data['is_active']}")
            print_info(f"Verified: {data['is_verified']}")
            return True
        else:
            error = response.json()
            print_error(f"Get user info failed: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_error(f"Get user info error: {str(e)}")
        return False


def test_logout(token: str) -> bool:
    """Test de la déconnexion"""
    print_section("TEST 5: Logout User")

    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.post(f"{API_BASE}/auth/logout", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Logout successful: {data['message']}")
            return True
        else:
            error = response.json()
            print_error(f"Logout failed: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_error(f"Logout error: {str(e)}")
        return False


def test_me_after_logout(token: str) -> bool:
    """Test que le token est bien révoqué après logout"""
    print_section("TEST 6: Verify Token Revoked After Logout")

    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(f"{API_BASE}/auth/me", headers=headers)

        if response.status_code == 401:
            print_success(f"Token correctly revoked (401 Unauthorized)")
            return True
        else:
            print_error(f"Token should be revoked but still works!")
            return False
    except Exception as e:
        print_error(f"Token revocation check error: {str(e)}")
        return False


def main():
    """Exécute tous les tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}KAURI USER SERVICE - TESTS D'AUTHENTIFICATION{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

    # Variables de test
    test_email = "test@kauri.com"
    test_password = "TestPass123!"

    results = []

    # Test 1: Health Check
    results.append(("Health Check", test_health_check()))

    # Test 2: Register
    token = test_register(test_email, test_password)
    results.append(("Register", token is not None))

    if token:
        # Test 3: Get User Info
        results.append(("Get User Info", test_me(token)))

        # Test 4: Logout
        logout_ok = test_logout(token)
        results.append(("Logout", logout_ok))

        # Test 5: Verify token revoked
        if logout_ok:
            results.append(("Token Revoked", test_me_after_logout(token)))

    # Test 6: Login (avec le compte créé)
    if token:
        login_token = test_login(test_email, test_password)
        results.append(("Login", login_token is not None))

        if login_token:
            # Test 7: Get User Info après login
            results.append(("Get User Info (after login)", test_me(login_token)))

    # Résumé
    print_section("RÉSUMÉ DES TESTS")

    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed

    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}Tests réussis: {passed}/{total}{Colors.END}")
    if failed > 0:
        print(f"{Colors.RED}Tests échoués: {failed}/{total}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
