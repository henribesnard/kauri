#!/usr/bin/env python
"""Test streaming endpoint with RAG question"""
import requests
import json

url = "http://localhost:3202/api/v1/chat/stream"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiNTgzMzlhZi1kYjQ0LTQ1ZTgtYWRjMS0zNDFmMGEwYjk4NDkiLCJlbWFpbCI6ImhlbnJpQGV4YW1wbGUuY29tIiwiZXhwIjoxNzYyNDQzNjczLCJpYXQiOjE3NjIzNTcyNzMsImp0aSI6IjMzNGQ3NDBjLTE0YWMtNDc5Yy1hMzhiLTQ2MzZmOTRkMTcwNiIsInR5cGUiOiJhY2Nlc3MifQ.TStZm61ErO5aeYwr9CJhSsFx9uBdfNC_Gq7dflHc4Nk"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

data = {
    "query": "Quels sont les principes comptables OHADA ?",
    "conversation_id": "test_stream_rag_123"
}

print("Test du endpoint /stream avec question RAG\n")
print("=" * 60)

try:
    response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)

    print(f"Status: {response.status_code}\n")

    if response.status_code == 200:
        print("Streaming events:\n")
        num_sources = 0
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    data_str = decoded[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type")

                        if event_type == "sources":
                            num_sources = len(event.get('sources', []))
                            print(f"[{event_type}] ({num_sources} sources)")
                        elif event_type == "token":
                            pass  # Skip printing tokens for brevity
                        elif event_type == "done":
                            print(f"\n[done]")
                            print(f"Metadata: {event.get('metadata', {})}")
                        elif event_type == "error":
                            print(f"\n[ERROR]: {event.get('content')}")
                    except json.JSONDecodeError:
                        print(f"Non-JSON: {data_str}")

        print(f"\n\nOK Stream completed with {num_sources} sources!")
    else:
        print(f"ERROR: {response.text}")

except Exception as e:
    print(f"ERROR: {str(e)}")
