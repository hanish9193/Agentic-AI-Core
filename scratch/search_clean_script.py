with open('backend/playwrightt/lib/execution-engine.ts', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'cleanScript' in line:
        print(f"Line {idx+1}: {line.strip()}")
