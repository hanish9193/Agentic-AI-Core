import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    content = f.read()

if "\u0000" in content or "\x00" in content:
    print("Found NUL characters in the file content!")
else:
    print("No NUL characters found using direct string search.")

# Let's parse it and search key by key
data = json.loads(content)

def check_nul(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_nul(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            check_nul(item, f"{path}[{idx}]")
    elif isinstance(obj, str):
        if "\u0000" in obj or "\x00" in obj:
            print(f"NUL found at path: {path} (length: {len(obj)})")
            # Print context
            clean_str = obj.replace("\u0000", "[NUL]").replace("\x00", "[NUL]")
            print(f"Content: {clean_str[:200]}...")

check_nul(data)
