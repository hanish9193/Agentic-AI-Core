import re

with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

matches = re.findall(r"navigateTo\(['\"]([^'\"]+)['\"]\)", content)
print("navigateTo arguments found in app.js:")
print("=" * 50)
for m in sorted(set(matches)):
    print(f"- {m}")
