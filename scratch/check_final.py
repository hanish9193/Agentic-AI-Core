import json
import os

def main():
    active_path = 'backend/playwrightt/public/artifacts/active_executions.json'
    batch_id = '50af5859-75f5-47a4-88ee-2b42a3021135'
    
    if os.path.exists(active_path):
        with open(active_path, 'r', encoding='utf-8') as f:
            active = json.load(f)
        for k, v in active.items():
            meta = v.get('metadata', {})
            if meta.get('testCycleId') == batch_id or meta.get('test_cycle_id') == batch_id:
                print(f"Execution {k} Status: {meta.get('status')}")
                if v.get('error'):
                    print(f"Error: {v.get('error')}")
                else:
                    print("No error message reported.")
    else:
        print("Active file does not exist.")

if __name__ == '__main__':
    main()
