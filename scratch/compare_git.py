import subprocess

git_content = subprocess.check_output(['git', 'show', 'HEAD:frontend/index.html']).decode('utf-8')
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    disk_content = f.read()

if git_content == disk_content:
    print("Disk file matches HEAD perfectly.")
else:
    print("Disk file differs from HEAD. Running diff...")
    import difflib
    git_lines = git_content.splitlines()
    disk_lines = disk_content.splitlines()
    diff = difflib.unified_diff(git_lines, disk_lines, fromfile='HEAD', tofile='disk', lineterm='')
    for line in list(diff)[:100]: # Print first 100 lines of diff
        print(line)
