import os

search_folder = os.path.join("frontend", "js")
found = False

for root, dirs, files in os.walk(search_folder):
    for file in files:
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for idx, line in enumerate(f):
                    if '/scenarios' in line:
                        print(f"File {filepath}:{idx+1} -> {line.strip()}")
                        # Print surrounding lines
                        f.seek(0)
                        file_lines = f.readlines()
                        start = max(0, idx - 4)
                        end = min(len(file_lines), idx + 8)
                        print("Context:")
                        for j in range(start, end):
                            print(f"  {j+1}: {file_lines[j].strip()}")
                        print("-" * 50)
                        found = True
        except:
            pass

if not found:
    print("No /scenarios found in frontend/js/.")
