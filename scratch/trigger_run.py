import urllib.request
import json

def main():
    project_id = '9752881f-0f09-4a35-a904-61745f0e2768'
    tc_id = 'a210efc6-bc63-45f2-a7fd-49d2a622acf3'
    url = f'http://127.0.0.1:8000/api/v1/projects/{project_id}/batches/execute'
    
    data = json.dumps([tc_id]).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Triggering execution for test case {tc_id}...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            print("Response status:", response.status)
            print("Response body:", res_data)
    except Exception as e:
        print("Error triggering execution:", e)

if __name__ == '__main__':
    main()
