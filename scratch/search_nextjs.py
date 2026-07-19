import os

search_str = 'fetchExecutions'
for root, dirs, files in os.walk('backend/playwrightt'):
    if 'node_modules' in root or '.next' in root:
        continue
    for file in files:
        if file.endswith(('.tsx', '.ts', '.js', '.jsx', '.json')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if search_str in line:
                            print(f"{filepath}:{idx+1} {line.strip()}")
            except Exception as e:
                pass
