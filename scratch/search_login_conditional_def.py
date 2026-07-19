with open('backend/services/batch_queue_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'def _make_login_conditional' in line or '_make_login_conditional(' in line:
        print(f"Line {idx+1}: {line.strip()}")
        # Print surrounding context
        start = max(0, idx - 4)
        end = min(len(lines), idx + 25)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].strip()}")
        print("-" * 50)
        break
