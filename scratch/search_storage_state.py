with open('backend/playwrightt/lib/execution-engine.ts', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'storage' in line.lower() or 'session' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
