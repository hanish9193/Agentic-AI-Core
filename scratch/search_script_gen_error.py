with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'script generation failed' in line.lower() or 'testcase' in line.lower() and 'not found' in line.lower():
        if idx > 1000 and idx < 1500:
            print(f"Line {idx+1}: {line.strip()}")
