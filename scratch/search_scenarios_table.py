with open('frontend/js/components.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = False
for idx, line in enumerate(lines):
    if 'scenariostable' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print next 35 lines
        for j in range(1, 40):
            if idx + j < len(lines):
                print(f"  +{j}: {lines[idx+j].strip()}")
        found = True
        break

if not found:
    print("ScenariosTable not found in components.js.")
