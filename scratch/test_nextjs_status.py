import urllib.request
import json

try:
    url = "http://localhost:3000/api/status?projectId=b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()}")
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Connection failed: {e}")
