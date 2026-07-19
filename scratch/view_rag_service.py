with open('backend/services/rag_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    print(f"{idx+1}: {line.rstrip()}")
