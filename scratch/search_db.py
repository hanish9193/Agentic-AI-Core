import os

search_str = 'provider'
for root, dirs, files in os.walk('backend'):
    if 'node_modules' in root or '.git' in root or '.next' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith(('.py', '.json')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if search_str in line:
                            print(f"{filepath}:{idx+1} {line.strip()}")
            except Exception as e:
                pass
