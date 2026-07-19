with open('backend/playwrightt/lib/execution-engine.ts', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'const test =' in line or 'test(' in line or 'test =' in line:
        if 'test(' in line and 'test_cases' in line:
            continue
        print(f"Line {idx+1}: {line.strip()}")
