#!/usr/bin/env python
"""Test script to verify source titles"""
import requests
import json

url = "http://localhost:3202/api/v1/chat/query"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiNTgzMzlhZi1kYjQ0LTQ1ZTgtYWRjMS0zNDFmMGEwYjk4NDkiLCJlbWFpbCI6ImhlbnJpQGV4YW1wbGUuY29tIiwiZXhwIjoxNzYyNDI0NTI3LCJpYXQiOjE3NjIzMzgxMjcsImp0aSI6ImE3NmYwMzNjLTYyMDQtNDM5OC1hMmE1LTRhMjcwNGEzMThlYiIsInR5cGUiOiJhY2Nlc3MifQ.rLyYZlMI1uILruVL8mWa4Q-MFpVvwqrAO0UFZWo10SQ"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

data = {
    "conversation_id": "test_titles_456",
    "query": "C'est quoi une société à responsabilité limitée ?"
}

print("Envoi de la requête...")
response = requests.post(url, headers=headers, json=data, timeout=60)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print("\n=== RÉPONSE ===")
    print(f"Answer: {result['answer'][:200]}...")
    print(f"\n=== SOURCES ({len(result['sources'])}) ===")
    for i, source in enumerate(result['sources'], 1):
        print(f"{i}. {source['title']}")
        print(f"   Score: {source['score']}")
else:
    print(f"Error: {response.text}")
