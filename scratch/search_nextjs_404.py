with open(r"C:\Users\Hanish\.gemini\antigravity-ide\brain\d9e2075f-dc05-499c-bcfc-c97bd4021853\.system_generated\tasks\task-288.log", "r", encoding="utf-8") as f:
    for line in f:
        if 'status' in line.lower() or '404' in line:
            print(line.strip())
