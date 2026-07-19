import os

for root, dirs, files in os.walk('backend'):
    if 'node_modules' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        if 'not found' in line.lower() and ('testcase' in line.lower() or 'test_case' in line.lower()):
                            print(f"{filepath}:{idx+1} {line.strip()}")
            except:
                pass
