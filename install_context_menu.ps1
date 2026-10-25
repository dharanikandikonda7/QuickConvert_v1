# QuickConvert - add "Convert with QuickConvert" to the Explorer right-click menu.
# Per-user only (HKCU). No admin needed. Run from the project folder:
#     powershell -ExecutionPolicy Bypass -File .\install_context_menu.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$exe     = Join-Path $root "dist\QuickConvert\QuickConvert.exe"
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$main    = Join-Path $root "main.py"
$cfg     = Join-Path $root ".venv\pyvenv.cfg"
$icon    = Join-Path $root "assets\icon.ico"

if (Test-Path $exe) {
    # Built app: no Python needed
    $command = '"{0}" --popup "%1"' -f $exe
    $icon    = $exe
    Write-Host "Using built app: $exe"
}
elseif ((Test-Path $pythonw) -and (Test-Path $main)) {
    # Virtual environment. When the venv was created from Anaconda, its pythonw.exe
    # fails outside an activated shell ("failed to start embedded interpreter") because
    # the base Python's folders are not on PATH. A tiny hidden VBScript launcher fixes that.
    $baseHome = $null
    if (Test-Path $cfg) {
        foreach ($line in Get-Content $cfg) {
            if ($line -match '^\s*home\s*=\s*(.+)$') { $baseHome = $Matches[1].Trim() }
        }
    }

    if ($baseHome -and (Test-Path $baseHome)) {
        $vbsPath = Join-Path $root "quickconvert_launcher.vbs"
        $vbs = @'
Option Explicit
Dim sh, env, q, cmd
q = Chr(34)
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("Process")
env("PATH") = "@@HOME@@;@@HOME@@\Library\bin;@@HOME@@\Library\usr\bin;@@HOME@@\Scripts;" & env("PATH")
If WScript.Arguments.Count = 0 Then WScript.Quit
cmd = q & "@@PYW@@" & q & " " & q & "@@MAIN@@" & q & " --popup " & q & WScript.Arguments(0) & q
sh.Run cmd, 0, False
'@
        $vbs = $vbs.Replace("@@HOME@@", $baseHome).Replace("@@PYW@@", $pythonw).Replace("@@MAIN@@", $main)
        Set-Content -Path $vbsPath -Value $vbs -Encoding ASCII
        $command = 'wscript.exe "{0}" "%1"' -f $vbsPath
        Write-Host "Using virtual environment through launcher: $vbsPath"
        Write-Host "Base Python folder: $baseHome"
    }
    else {
        $command = '"{0}" "{1}" --popup "%1"' -f $pythonw, $main
        Write-Host "Using virtual environment: $pythonw"
    }
}
else {
    Write-Error "Could not find dist\QuickConvert\QuickConvert.exe or .venv\Scripts\pythonw.exe. Run this script from the project folder."
}

$extensions = @(".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
                ".gif", ".txt", ".html", ".htm", ".docx")

foreach ($ext in $extensions) {
    $key = "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\QuickConvert"
    New-Item -Path $key -Force | Out-Null
    Set-ItemProperty -Path $key -Name "(default)" -Value "Convert with QuickConvert"
    if (Test-Path $icon) {
        Set-ItemProperty -Path $key -Name "Icon" -Value $icon
    }
    New-Item -Path "$key\command" -Force | Out-Null
    Set-ItemProperty -Path "$key\command" -Name "(default)" -Value $command
}

Write-Host ""
Write-Host "Done. Right-click a supported file (Windows 11: 'Show more options') -> Convert with QuickConvert."
