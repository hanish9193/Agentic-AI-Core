import os

guide_path = "adactin_reference_guide.md"
prompts = [
    "backend/prompts/playwright_prompt.txt",
    "backend/prompts/test_case_prompt.txt",
    "backend/prompts/scenario_prompt.txt"
]

if not os.path.exists(guide_path):
    print(f"Error: {guide_path} not found.")
    exit(1)

with open(guide_path, "r", encoding="utf-8") as f:
    guide_content = f.read()

# Escape all '$' signs as '$$' to prevent string.Template from treating them as variables
escaped_guide = guide_content.replace("$", "$$")

appendix = f"\n\n<adactin_reference_guide>\n{escaped_guide}\n</adactin_reference_guide>\n"

for p in prompts:
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "<adactin_reference_guide>" in content:
            print(f"Guide already appended to {p}. Skipping.")
            continue
            
        with open(p, "w", encoding="utf-8") as f:
            f.write(content + appendix)
        print(f"Successfully appended escaped guide to {p}.")
    else:
        print(f"Warning: Prompt file {p} not found.")
