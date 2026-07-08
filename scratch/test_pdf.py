import fitz
from pathlib import Path

pdf_path = Path("data/reports/report_aadbfd55-2882-4b1a-a472-35d102973fbe.pdf")
print("PDF path:", pdf_path)
print("File size:", pdf_path.stat().st_size)

try:
    doc = fitz.open(str(pdf_path))
    print("Page count:", len(doc))
    for i in range(len(doc)):
        page = doc[i]
        print(f"Page {i+1} size:", page.rect)
        print(f"Page {i+1} text length:", len(page.get_text()))
    doc.close()
    print("PDF loaded successfully without corruption!")
except Exception as e:
    print("Error loading PDF:", e)
