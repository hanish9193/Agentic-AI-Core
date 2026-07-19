import os

search_str = 'project-select'
for root, dirs, files in os.walk('.'):
    # Skip standard build/temporary directories
    if 'node_modules' in root or '.git' in root or '.next' in root or 'brain' in root:
        continue
    for file in files:
        if file.endswith(('.js', '.html', '.css', '.py', '.json')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if search_str in line:
                            print(f"{filepath}:{idx+1} {line.strip().encode('utf-8', errors='ignore').decode('utf-8')}")
            except Exception as e:
                pass
