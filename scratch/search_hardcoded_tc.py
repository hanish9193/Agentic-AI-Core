import os

search_term = "c2bec44c"
found = False

for root, dirs, files in os.walk('.'):
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
