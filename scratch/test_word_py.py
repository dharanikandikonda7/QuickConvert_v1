import subprocess
import sys
from pathlib import Path

def convert_docx_with_word(docx_path: Path, pdf_path: Path) -> bool:
    docx_path = Path(docx_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    
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
    $doc.Close([ref]0) # 0 = wdDoNotSaveChanges
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
    print("Stderr:", res.stderr.strip())
    return res.returncode == 0 and pdf_path.is_file() and pdf_path.stat().st_size > 0

out = Path("test_samples/test_word_py.pdf")
out.unlink(missing_ok=True)
success = convert_docx_with_word(Path("test_samples/sample_word.docx"), out)
print("Success:", success)
if success:
    print("Output size:", out.stat().st_size)
