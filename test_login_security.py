#!/usr/bin/env python
"""Test script to verify login security improvements"""
import requests
import json

url = "http://localhost:3201/api/v1/auth/login"

# Credentials
data = {
    "email": "henri@example.com",
    "password": "Password123"
}

print("Test des ameliorations de securite du endpoint /login\n")
print("=" * 60)

response = requests.post(url, json=data)

print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    result = response.json()

    print("OK Login reussi!\n")
    print("Reponse complete:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("Verification de securite:\n")

    # Check user fields
    user = result.get("user", {})

    print(f"OK Token present: {bool(result.get('access_token'))}")
    print(f"OK Expiration (secondes): {result.get('expires_in')} (attendu: 3600)")

    print(f"\nChamps utilisateur presents:")
    for field in user.keys():
        print(f"  - {field}: {user[field]}")

    print(f"\nChamps sensibles (doivent etre absents):")
    sensitive_fields = ["is_superuser", "is_verified", "created_at", "updated_at", "last_login"]
    for field in sensitive_fields:
        if field in user:
            print(f"  [X] {field}: PRESENT (RISQUE DE SECURITE)")
        else:
            print(f"  [OK] {field}: absent (securise)")

    # Security assessment
    print(f"\n" + "=" * 60)
    has_sensitive = any(field in user for field in sensitive_fields)
    expires_ok = result.get('expires_in') == 3600

    if not has_sensitive and expires_ok:
        print("OK SECURITE: Toutes les ameliorations sont appliquees!")
    else:
        print("ATTENTION: Certaines ameliorations ne sont pas appliquees")
        if has_sensitive:
            print("   - Des champs sensibles sont encore exposes")
        if not expires_ok:
            print(f"   - Duree d'expiration incorrecte: {result.get('expires_in')}s (attendu: 3600s)")
else:
    print(f"ERREUR: {response.text}")
