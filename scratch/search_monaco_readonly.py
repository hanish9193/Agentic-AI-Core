import os

search_dir = os.path.join("backend", "playwrightt")
found = False

for root, dirs, files in os.walk(search_dir):
    if 'node_modules' in root or '.next' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith(('.tsx', '.ts', '.jsx', '.js', '.html')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if 'readonly' in line.lower():
                            print(f"{filepath}:{idx+1} {line.strip()}")
                            found = True
            except:
                pass

if not found:
    print("No readOnly configurations found in playwrightt.")
