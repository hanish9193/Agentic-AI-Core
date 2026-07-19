import os

prompts_dir = os.path.join("backend", "prompts")
for root, dirs, files in os.walk(prompts_dir):
    for f in files:
        print(os.path.join(root, f))
