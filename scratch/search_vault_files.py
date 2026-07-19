import os

for root, dirs, files in os.walk('.'):
    if 'node_modules' in root or '.git' in root or '.next' in root:
        continue
    for file in files:
        if 'vault' in file.lower():
            filepath = os.path.join(root, file)
            print(f"FOUND VAULT FILE: {filepath} (size: {os.path.getsize(filepath)} bytes)")
