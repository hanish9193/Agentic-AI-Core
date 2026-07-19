with open('backend/services/playwright_runner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'env' in line.lower() or 'target_password' in line.lower() or 'target_username' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print surrounding context
        start = max(0, idx - 4)
        end = min(len(lines), idx + 12)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].strip()}")
        print("-" * 50)
