with open('backend/prompts/playwright_prompt.txt', 'r', encoding='utf-8') as f:
    content = f.read()

print("File length:", len(content))
print("Guide block exists:", "<adactin_reference_guide>" in content)
if "<adactin_reference_guide>" in content:
    idx = content.find("<adactin_reference_guide>")
    print("Guide block snippet:")
    print("=" * 60)
    print(content[idx:idx+500])
    print("=" * 60)
