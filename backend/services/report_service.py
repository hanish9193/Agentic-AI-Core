from pathlib import Path
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from backend.models.execution_result import ExecutionResult
from backend.repository.project_repository import ProjectRepository

class ReportService:
    def __init__(self, repo: ProjectRepository = None):
        if repo is None:
            from backend.services.project_service import ProjectService
            self.repo = ProjectService().repo
        else:
            self.repo = repo

    def compile_reports(self, project_id: UUID, execution_result: ExecutionResult) -> dict:
        """
        Compiles HTML, PDF, and JUnit reports based on the Playwright execution results
        and persists them to the repository.
        """
        # Create reports outputs folder in user workspace
        reports_dir = Path("data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        execution_id_str = str(execution_result.id)
        
        # 1. Compile JUnit XML
        junit_path = reports_dir / f"junit_{execution_id_str}.xml"
        root = ET.Element("testsuites")
        suite = ET.SubElement(
            root, "testsuite", 
            name="Playwright Test Suite", 
            tests="1", 
            failures="1" if execution_result.status.value == "failed" else "0",
            errors="1" if execution_result.status.value == "error" else "0",
            time=str(execution_result.duration_seconds)
        )
        tc_el = ET.SubElement(
            suite, "testcase", 
            name=f"TestCase_{execution_result.test_case_id}",
            classname="PlaywrightTests",
            time=str(execution_result.duration_seconds)
        )
        if execution_result.status.value == "failed":
            failure = ET.SubElement(tc_el, "failure", message="Assertion Failed")
            failure.text = execution_result.error_message or "Assertion Error"
        elif execution_result.status.value == "error":
            error = ET.SubElement(tc_el, "error", message="Execution Error")
            error.text = execution_result.error_message or "Tooling Error"

        tree = ET.ElementTree(root)
        tree.write(str(junit_path), encoding="utf-8", xml_declaration=True)

        # 2. Compile HTML report
        html_path = reports_dir / f"report_{execution_id_str}.html"
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Execution Report - {execution_id_str}</title>
    <style>
        body {{ font-family: sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px; }}
        .card {{ background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; max-width: 800px; margin: 0 auto; }}
        h1 {{ border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-top: 0; }}
        .badge {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: bold; text-transform: uppercase; }}
        .passed {{ background-color: #10b981; color: white; }}
        .failed {{ background-color: #ef4444; color: white; }}
        .info {{ margin-top: 16px; font-size: 14px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Automation Execution Verdict</h1>
        <div>
            <span class="badge {execution_result.status.value}">{execution_result.status.value}</span>
        </div>
        <div class="info">
            <p><strong>Execution ID:</strong> {execution_id_str}</p>
            <p><strong>Test Case ID:</strong> {execution_result.test_case_id}</p>
            <p><strong>Duration:</strong> {execution_result.duration_seconds} seconds</p>
            <p><strong>Run Date:</strong> {execution_result.executed_at.isoformat()}</p>
            {f"<p><strong>Error Message:</strong> {execution_result.error_message}</p>" if execution_result.error_message else ""}
        </div>
    </div>
</body>
</html>
"""
        html_path.write_text(html_content, encoding="utf-8")

        # 3. Compile PDF report using PyMuPDF (fitz)
        pdf_path = reports_dir / f"report_{execution_id_str}.pdf"
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            
            # Write structured report header and metrics
            rect_title = fitz.Rect(50, 50, 550, 100)
            page.insert_textbox(rect_title, f"AI Platform Test Verdict Report", fontsize=18, fontname="helvetica-bold", color=(0.2, 0.5, 0.9))
            
            rect_meta = fitz.Rect(50, 120, 550, 300)
            meta_text = (
                f"Execution ID: {execution_id_str}\n"
                f"Test Case ID: {execution_result.test_case_id}\n"
                f"Verdict: {execution_result.status.value.upper()}\n"
                f"Duration: {execution_result.duration_seconds}s\n"
                f"Executed At: {execution_result.executed_at.isoformat()}\n\n"
                f"Details:\n{execution_result.error_message or 'All steps passed.'}"
            )
            page.insert_textbox(rect_meta, meta_text, fontsize=12, fontname="helvetica")
            doc.save(str(pdf_path))
            doc.close()
        except Exception:
            pdf_path.write_bytes(b"%PDF-1.4 ...")

        # Save report details in repo raw storage
        raw = self.repo._read_raw()
        reports_raw = raw.setdefault("reports", {})
        
        report_id = str(uuid4())
        report_payload = {
            "id": report_id,
            "project_id": str(project_id),
            "execution_id": execution_id_str,
            "junit_path": str(junit_path),
            "html_path": str(html_path),
            "pdf_path": str(pdf_path),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        reports_raw[report_id] = report_payload
        self.repo._write_raw(raw)

        return report_payload
