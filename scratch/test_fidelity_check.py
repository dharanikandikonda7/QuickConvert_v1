import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.fidelity import FidelityVerifier

report = FidelityVerifier.verify_conversion(
    Path("test_samples/sample_resume.docx"),
    [Path("test_samples/sample_resume_registry_test.pdf")],
    "docx",
    "pdf"
)
print("Status:", report.status)
print("Summary:", report.summary)
print("Pages:", report.output_pages)
print("Char count:", report.details.get("output_char_count"))
print("Warnings:", report.warnings)
