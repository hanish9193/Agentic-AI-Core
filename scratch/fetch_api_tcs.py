import requests

url = "http://localhost:8000/api/v1/projects"
print("GET /api/v1/projects:")
r = requests.get(url)
print("Status:", r.status_code)
if r.status_code == 200:
    projects = r.json()
    print(f"Projects found ({len(projects)}):")
    for p in projects:
        print(f"  ID: {p.get('id')} | Name: {p.get('name')}")
else:
    print(r.text)

project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
tc_url = f"http://localhost:8000/api/v1/projects/{project_id}/testcases"
print(f"\nGET /api/v1/projects/{project_id}/testcases:")
r = requests.get(tc_url)
print("Status:", r.status_code)
if r.status_code == 200:
    tcs = r.json()
    print(f"Test cases found ({len(tcs)}):")
    for tc in tcs:
        print(f"  ID: {tc.get('id')} | Title: {tc.get('title')}")
else:
    print(r.text)
