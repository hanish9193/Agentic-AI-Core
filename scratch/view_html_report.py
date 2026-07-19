import os
from bs4 import BeautifulSoup

report_path = os.path.join("backend", "playwrightt", "public", "artifacts", "dd76e3a0-753d-4684-b1f5-4ae7374a006f", "report.html")

if os.path.exists(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    # Print headings, text, or script execution summary
    print("Report Page Title:", soup.title.string if soup.title else "None")
    # Find text matching error or success
    body_text = soup.get_text()
    for line in body_text.splitlines():
        if "Timeline" in line or "error" in line.lower() or "fail" in line.lower() or "pass" in line.lower():
            if len(line.strip()) > 0:
                print(line.strip()[:150])
else:
    print(f"File {report_path} not found.")
