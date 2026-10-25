$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open('D:\PROJECTS\QuickConvertMowa\test_samples\sample_word.docx')
    $doc.SaveAs([ref]'D:\PROJECTS\QuickConvertMowa\test_samples\test_out.pdf', [ref]17)
    $doc.Close()
    Write-Host "SUCCESS_WORD_CONVERTED"
} finally {
    $word.Quit()
}
