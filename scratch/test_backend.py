import urllib.request
import json

try:
    url = "http://127.0.0.1:8000/api/v1/projects"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        status = response.getcode()
        body = response.read().decode('utf-8')
        print(f"Status: {status}")
        print(f"Response (truncated): {body[:200]}")
except Exception as e:
    print(f"Failed to connect to backend: {e}")
