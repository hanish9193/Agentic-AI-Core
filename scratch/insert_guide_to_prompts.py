import os

guide_path = "adactin_reference_guide.md"
if not os.path.exists(guide_path):
    print(f"Error: {guide_path} not found.")
    exit(1)

with open(guide_path, "r", encoding="utf-8") as f:
    guide_content = f.read()

# Escape '$' as '$$' for template variables safety
escaped_guide = guide_content.replace("$", "$$")

guide_block = f"\n\nFor this specific project, use the following verified application guide as the source of truth for pages, flows, selectors, and test data:\n<adactin_reference_guide>\n{escaped_guide}\n</adactin_reference_guide>\n"

# 1. Insert into playwright_prompt.txt (inside <source_of_truth>)
playwright_path = "backend/prompts/playwright_prompt.txt"
if os.path.exists(playwright_path):
    with open(playwright_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "</source_of_truth>"
    if target in content and "<adactin_reference_guide>" not in content:
        insert_index = content.find(target)
        new_content = content[:insert_index] + guide_block + content[insert_index:]
        with open(playwright_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully inserted guide into {playwright_path} before </source_of_truth>.")
    else:
        print(f"Skipped/Not matching target in {playwright_path}.")

# 2. Insert into test_case_prompt.txt (after requirement description)
testcase_path = "backend/prompts/test_case_prompt.txt"
if os.path.exists(testcase_path):
    with open(testcase_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "Requirement description: $description"
    if target in content and "<adactin_reference_guide>" not in content:
        insert_index = content.find(target) + len(target)
        new_content = content[:insert_index] + guide_block + content[insert_index:]
        with open(testcase_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully inserted guide into {testcase_path}.")
    else:
        print(f"Skipped/Not matching target in {testcase_path}.")

# 3. Insert into scenario_prompt.txt (after requirement description)
scenario_path = "backend/prompts/scenario_prompt.txt"
if os.path.exists(scenario_path):
    with open(scenario_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "Requirement description: $description"
    if target in content and "<adactin_reference_guide>" not in content:
        insert_index = content.find(target) + len(target)
        new_content = content[:insert_index] + guide_block + content[insert_index:]
        with open(scenario_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully inserted guide into {scenario_path}.")
    else:
        print(f"Skipped/Not matching target in {scenario_path}.")
