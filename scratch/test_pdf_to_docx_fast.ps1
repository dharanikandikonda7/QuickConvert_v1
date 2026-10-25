$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles, PasswordDocument, PasswordTemplate, Revert, WritePasswordDocument, WritePasswordTemplate, Format)
    $doc = $word.Documents.Open('D:\PROJECTS\QuickConvertMowa\test_samples\sample_resume.pdf', $false, $true)
    $doc.SaveAs2('D:\PROJECTS\QuickConvertMowa\test_samples\sample_resume_from_pdf.docx', 16)
    $doc.Close(0)
    Write-Host "PDF_TO_DOCX_SUCCESS"
} catch {
    Write-Host "ERROR: $_"
} finally {
    $word.Quit()
}
