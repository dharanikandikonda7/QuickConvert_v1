import subprocess
import pypdfium2 as pdfium
from pathlib import Path

docx_path = Path("test_samples/sample_resume.docx").resolve()
pdf_path = Path("test_samples/sample_resume.pdf").resolve()
pdf_path.unlink(missing_ok=True)

ps_script = f"""
$ErrorActionPreference = 'Stop'
$word = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = [Microsoft.Office.Interop.Word.WdAlertLevel]::wdAlertsNone
    $doc = $word.Documents.Open('{str(docx_path).replace("'", "''")}')
    # 17 = wdFormatPDF
    $doc.SaveAs([ref]'{str(pdf_path).replace("'", "''")}', [ref]17)
    $doc.Close([ref]0)
    Write-Output "CONVERSION_SUCCESS"
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}} finally {{
    if ($word) {{
        $word.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
        [System.GC]::Collect()
        [System.GC]::WaitForPendingFinalizers()
    }}
}}
"""
cmd = [
    "powershell.exe",
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy", "Bypass",
    "-Command", ps_script
]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("Return code:", res.returncode)
print("Stdout:", res.stdout.strip())
if res.returncode != 0:
    print("Stderr:", res.stderr.strip())
    exit(1)

print("PDF size:", pdf_path.stat().st_size)

# Render to PNG
doc = pdfium.PdfDocument(pdf_path)
page = doc[0]
bitmap = page.render(scale=2.0)
img = bitmap.to_pil()
preview_path = Path("docs/resume_output_preview.png")
preview_path.parent.mkdir(parents=True, exist_ok=True)
img.save(preview_path)
print(f"Rendered preview saved to {preview_path} ({img.size})")

# Check links and text
text = page.get_textpage().get_text_range()
print("Contains 'ALEXANDER HAMILTON':", "ALEXANDER HAMILTON" in text)
print("Contains 'Professional Summary':", "Professional Summary" in text)
print("Contains 'portfolio.dev':", "portfolio.dev" in text)
