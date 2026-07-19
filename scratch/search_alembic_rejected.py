import os

alembic_dir = os.path.join("backend", "database", "alembic", "versions")
found = False

if os.path.exists(alembic_dir):
    for root, dirs, files in os.walk(alembic_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'rejected' in content:
                            print(f"FOUND IN MIGRATION: {filepath}")
                            found = True
                except:
                    pass

if not found:
    print("No migrations adding 'rejected' found.")
