import requests
import time
import psycopg2

project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
tc_id = "d462aba4-2f31-4862-a318-32220d21b55c"

url = f"http://localhost:8000/api/v1/projects/{project_id}/testcases/{tc_id}/execute"

print(f"Triggering execution for testcase {tc_id}...")
response = requests.post(url)
if response.status_code == 200:
    res_data = response.json()
    exec_id = res_data.get("execution_id")
    print(f"Execution started! ID: {exec_id}")
    
    # Poll database for execution status
    print("Waiting for execution to complete...")
    for attempt in range(60): # up to 60 seconds
        time.sleep(1)
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="Agentic_ai",
                user="postgres",
                password="hanish13"
            )
            cur = conn.cursor()
            cur.execute("SELECT status, error_message, duration_seconds FROM executions WHERE id = %s", (exec_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row:
                status, error_msg, duration = row
                print(f"[{attempt+1}s] Status: {status}")
                if status in ["passed", "failed", "error"]:
                    print(f"Finished in {duration}s!")
                    if error_msg:
                        print(f"Error Message: {error_msg}")
                    break
            else:
                print(f"[{attempt+1}s] Waiting for execution record to be created...")
        except Exception as e:
            print(f"DB check failed: {e}")
else:
    print(f"Failed to trigger test: Status {response.status_code} | {response.text}")
