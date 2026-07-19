import os

search_term = "016b1e9e"
found = False

for root, dirs, files in os.walk('.'):
    # Skip node_modules, .git, and other unnecessary folders
    if any(k in root for k in ['node_modules', '.git', '.hypothesis', '.pytest_cache', '.next']):
        continue
    for file in files:
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if search_term in content:
                    print(f"FOUND IN: {filepath}")
                    found = True
        except:
            pass

if not found:
    print("Could not find the term in any files.")
