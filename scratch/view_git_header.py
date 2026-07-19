import subprocess

git_content = subprocess.check_output(['git', 'show', 'HEAD:frontend/index.html']).decode('utf-8')
lines = git_content.splitlines()
for idx in range(130, 180):
    if idx < len(lines):
        line = lines[idx]
        print(f"Line {idx+1}: {ascii(line)}")
