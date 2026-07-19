import json
import os

transcript_path = r"C:\Users\Hanish\.gemini\antigravity-ide\brain\d9e2075f-dc05-499c-bcfc-c97bd4021853\.system_generated\logs\transcript_full.jsonl"

if os.path.exists(transcript_path):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '"type":"BROWSER_SUBAGENT"' in line or '"type":"BROWSER_SUBAGENT_RESPONSE"' in line:
                try:
                    data = json.loads(line)
                    print(f"Step {data.get('step_index')}: Type: {data.get('type')}, Status: {data.get('status')}")
                    # Let's print a snippet
                    content = data.get('content', '')
                    if content:
                        print(content[:500])
                        print("-" * 50)
                except Exception as e:
                    print("Error:", e)
else:
    print("Transcript path does not exist")
