import os

log_path = "C:/Users/Hanish/.gemini/antigravity-ide/brain/d9e2075f-dc05-499c-bcfc-c97bd4021853/.system_generated/tasks/task-1898.log"

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        print(f.read())
else:
    # Try finding it relative or list directories
    print("Log not found at primary path.")
    dir_path = "C:/Users/Hanish/.gemini/antigravity-ide/brain/d9e2075f-dc05-499c-bcfc-c97bd4021853/.system_generated/tasks"
    if os.path.exists(dir_path):
        print("Files in tasks directory:")
        for f in os.listdir(dir_path):
            print("  ", f)
    else:
        print("Tasks directory not found.")
