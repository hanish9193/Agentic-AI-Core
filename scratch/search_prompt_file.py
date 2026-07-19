import os

for root, dirs, files in os.walk('.'):
    if 'node_modules' in root or '.git' in root or '.next' in root:
        continue
    for file in files:
        if 'playwright_prompt' in file:
            print(f"FOUND PROMPT FILE: {os.path.join(root, file)}")
