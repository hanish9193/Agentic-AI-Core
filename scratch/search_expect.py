with open('backend/playwrightt/lib/execution-engine.ts', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'expect' in line.lower():
        # Print lines around the definition
        if 'function' in line or 'const ' in line or 'class ' in line or 'expect(' in line:
            print(f"Line {idx+1}: {line.strip()}")
