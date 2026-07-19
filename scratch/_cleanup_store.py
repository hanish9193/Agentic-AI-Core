import json

path = r'E:\Agentic-AI-Automation\backend\database\project_store.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

before = len(data['projects'])
data['projects'] = [p for p in data['projects'] if p['name'] == 'Agentic AI Automation']
after = len(data['projects'])

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print(f'Before: {before} projects')
print(f'After: {after} projects')
print(f'Keeping: {[p["name"] for p in data["projects"]]}')
