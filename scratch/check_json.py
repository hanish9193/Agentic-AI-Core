with open('backend/database/project_store.json', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = 13940
end = 13970
for idx in range(start, min(end, len(lines))):
    print(f"{idx+1}: {lines[idx]}", end='')
