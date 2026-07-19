import json
import os

def main():
    active_path = 'backend/playwrightt/public/artifacts/active_executions.json'
    if os.path.exists(active_path):
        with open(active_path, 'r', encoding='utf-8') as f:
            active = json.load(f)
        for k, v in active.items():
            meta = v.get('metadata', {})
            print(f"ID: {k} | Cycle: {meta.get('testCycleId')} | Status: {meta.get('status')}")
    else:
        print("Active file not found.")

if __name__ == '__main__':
    main()
