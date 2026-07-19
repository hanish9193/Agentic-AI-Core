def main():
    with open('backend/playwrightt/app/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
        
    for line_num, line in enumerate(content.splitlines(), 1):
        if 'generate' in line.lower() or 'button' in line.lower() or 'run' in line.lower():
            if line_num <= 100 or line_num >= 650:
                print(f"Line {line_num}: {line.strip()}")

if __name__ == '__main__':
    main()
