import os
import re

uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

for root, dirs, files in os.walk('.'):
    if any(k in root for k in ['node_modules', '.git', '.hypothesis', '.pytest_cache', '.next']):
        continue
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts') or file.endswith('.js') or file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for idx, line in enumerate(f):
                        # Find any hardcoded UUIDs in the source files
                        uuids = uuid_pattern.findall(line)
                        for u in uuids:
                            print(f"UUID found in {filepath}:{idx+1} -> {u}")
                        # Also check if there is any scenario endpoint url
                        if 'scenarios/' in line or 'scenarios' in line:
                            if 'api/v1' in line:
                                print(f"Scenario URL in {filepath}:{idx+1} -> {line.strip()}")
            except:
                pass
