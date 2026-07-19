with open(r"C:\Users\Hanish\.gemini\antigravity-ide\brain\d9e2075f-dc05-499c-bcfc-c97bd4021853\.system_generated\logs\transcript_full.jsonl", 'r', encoding='utf-8') as f:
    for line in f:
        if 'login_success_verify' in line or 'login_success_verification' in line:
            print(line[:300])
