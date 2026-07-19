with open('backend/playwrightt/app/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'execute' in line.lower() or 'run' in line.lower():
        if 'fetch' in line or 'onclick' in line or 'button' in line:
            print(f"Line {idx+1}: {line.strip()}")
            # Print next 5 lines
            for j in range(1, 6):
                if idx + j < len(lines):
                    print(f"  +{j}: {lines[idx+j].strip()}")
