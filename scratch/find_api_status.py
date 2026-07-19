import os

for root, dirs, files in os.walk('backend/playwrightt'):
    if 'node_modules' in root or '.next' in root:
        continue
    for file in files:
        if 'status' in file.lower() or 'route' in file.lower():
            print(os.path.join(root, file))
