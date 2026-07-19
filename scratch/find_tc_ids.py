import json

def main():
    with open('backend/database/project_store.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    project_id = '9752881f-0f09-4a35-a904-61745f0e2768'
    tc_ids = []
    
    for tc_id, tc in data.get('test_cases', {}).items():
        if tc.get('project_id') == project_id or tc.get('playwright_script'):
            # Double check if it belongs to this project
            # Find scenarios belonging to this project
            scenario_id = tc.get('scenario_id')
            sc = data.get('scenarios', {}).get(scenario_id, {})
            req_id = sc.get('requirement_id')
            req = data.get('requirements', {}).get(req_id, {})
            # If the requirement belongs to the project requirements list
            project = None
            for p in data.get('projects', []):
                if p['id'] == project_id:
                    project = p
                    break
            if project and req_id in project.get('requirements', []):
                tc_ids.append(tc_id)
                print(f"Test Case: {tc.get('title')} ({tc_id})")
                
    print("Project test case IDs:", tc_ids)

if __name__ == '__main__':
    main()
