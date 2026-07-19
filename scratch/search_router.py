with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'hashchange' in line.lower() or 'router' in line.lower() or 'handle_route' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print surrounding context
        start = max(0, idx - 4)
        end = min(len(lines), idx + 25)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].strip()}")
        print("-" * 50)
