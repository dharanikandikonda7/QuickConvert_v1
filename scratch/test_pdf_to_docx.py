import subprocess
import sys
from pathlib import Path

pdf_path = Path("test_samples/sample_resume.pdf").resolve()
docx_path = Path("test_samples/sample_resume_from_pdf.docx").resolve()
docx_path.unlink(missing_ok=True)

ps_script = f"""
$ErrorActionPreference = 'Stop'
$word = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = [Microsoft.Office.Interop.Word.WdAlertLevel]::wdAlertsNone
    $doc = $word.Documents.Open('{str(pdf_path).replace("'", "''")}')
    # 16 = wdFormatXMLDocument (.docx)
    $doc.SaveAs2([ref]'{str(docx_path).replace("'", "''")}', [ref]16)
    $doc.Close([ref]0)
    Write-Output "PDF_TO_DOCX_SUCCESS"
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
if res.returncode == 0 and docx_path.is_file():
    print("DOCX generated size:", docx_path.stat().st_size)
else:
    print("Stderr:", res.stderr.strip())
