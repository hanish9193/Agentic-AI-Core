with open('frontend/js/components.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if '_scenarioactions' in line.lower() or 'approve' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
