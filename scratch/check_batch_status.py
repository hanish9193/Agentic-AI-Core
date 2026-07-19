import json
import time
import os

def main():
    active_path = 'backend/playwrightt/public/artifacts/active_executions.json'
    batch_id = '50af5859-75f5-47a4-88ee-2b42a3021135'
    
    print(f"Monitoring batch {batch_id}...")
    for _ in range(30):
        if not os.path.exists(active_path):
            print("active_executions.json does not exist yet.")
            time.sleep(2)
            continue
            
        with open(active_path, 'r', encoding='utf-8') as f:
            try:
                active = json.load(f)
            except Exception:
                time.sleep(2)
                continue
                
        # Find execution belonging to this batch
        batch_execs = []
        for k, v in active.items():
            meta = v.get('metadata', {})
            if meta.get('testCycleId') == batch_id or meta.get('test_cycle_id') == batch_id:
                batch_execs.append((k, meta.get('status')))
                
        if not batch_execs:
            print("No active executions found for this batch yet.")
        else:
            print("Active executions in batch:")
            for k, status in batch_execs:
                print(f"  {k}: {status}")
                
            # If all found executions are completed/failed, we might be done
            if all(status in {'completed', 'failed', 'error', 'passed'} for _, status in batch_execs):
                print("All executions in batch have completed!")
                break
                
        time.sleep(3)

if __name__ == '__main__':
    main()
