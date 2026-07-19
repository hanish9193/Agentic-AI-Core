import json
import os

transcript_path = r"C:\Users\Hanish\.gemini\antigravity-ide\brain\d9e2075f-dc05-499c-bcfc-c97bd4021853\.system_generated\logs\transcript_full.jsonl"

if os.path.exists(transcript_path):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'capture_browser_console_logs' in line:
                try:
                    data = json.loads(line)
                    # We are interested in step logs from the subagent itself
                    if data.get('source') == 'SYSTEM' or 'tool_calls' in data:
                        # Let's search inside tool calls or tool responses
                        continue
                    # If this is the subagent response step containing 'capture_browser_console_logs' output
                    content = data.get('content', '')
                    if 'console' in content.lower() or 'step-60' in content.lower() or 'step 60' in content.lower():
                        print(f"Step {data.get('step_index')}:")
                        print(content[-3000:])
                except Exception as e:
                    print("Error:", e)
else:
    print("Transcript path does not exist")
