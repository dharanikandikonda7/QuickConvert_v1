<#
.SYNOPSIS
    QuickConvert — Windows Explorer Context Menu Installer

.DESCRIPTION
    Adds "Convert with QuickConvert" to the Windows Explorer right-click menu
    for ALL file types.

    Writes only to HKCU\Software\Classes\*\shell\QuickConvert (no HKLM,
    no admin rights required).  Launcher priority:
        1. dist\QuickConvert\QuickConvert.exe  (packaged build)
        2. .venv\Scripts\pythonw.exe main.py   (development environment)

    The command template uses "%1" so Windows Shell passes the full, already-
    quoted path of each selected file as a single argument. Paths with spaces,
    Unicode characters, and long paths are handled correctly.

    On Windows 11 the entry appears in the LEGACY context menu, accessible via
    "Show more options". Modern primary-menu integration requires an
    IExplorerCommand COM extension and is not yet implemented.

.NOTES
    Safe to run multiple times — overwrites only the QuickConvert sub-tree.
    Does not touch any other registry entries.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# ── Locate the project root (same folder as this script) ─────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ── Candidate executable paths ────────────────────────────────────────────────
$exePath      = Join-Path $scriptDir "dist\QuickConvert\QuickConvert.exe"
$pythonwPath  = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"
$mainPyPath   = Join-Path $scriptDir "main.py"
$iconPath     = Join-Path $scriptDir "assets\icon.ico"

# ── Determine the command string written to the registry ─────────────────────
#
# Registry command value format:
#     "<exe>" [args] "%1"
#
# "%1" is the Windows Shell macro for the selected file path. The Shell
# surrounds it with double-quotes when expanding, so paths with spaces are
# passed to the process correctly as a single argv element.
#
if (Test-Path -LiteralPath $exePath) {
    # ── Packaged build ────────────────────────────────────────────────────────
    $launcherDescription = "packaged executable"
    # Command: "C:\path\to\QuickConvert.exe" "%1"
    $targetCommand = "`"$exePath`" --popup `"%1`""
    $iconTarget    = $exePath
    Write-Host "Launcher : $launcherDescription" -ForegroundColor Cyan
    Write-Host "           $exePath" -ForegroundColor DarkCyan

} elseif ((Test-Path -LiteralPath $pythonwPath) -and (Test-Path -LiteralPath $mainPyPath)) {
    # ── Development environment ───────────────────────────────────────────────
    $launcherDescription = "Python virtual environment"
    # Command: "pythonw.exe" "main.py" "%1"
    $targetCommand = "`"$pythonwPath`" `"$mainPyPath`" --popup `"%1`""
    $iconTarget    = if (Test-Path -LiteralPath $iconPath) { $iconPath } else { $pythonwPath }
    Write-Host "Launcher : $launcherDescription" -ForegroundColor Cyan
    Write-Host "           $pythonwPath" -ForegroundColor DarkCyan

} else {
    Write-Host ""
    Write-Host "ERROR: Cannot find a valid launcher." -ForegroundColor Red
    Write-Host ""
    Write-Host "Expected one of:" -ForegroundColor Yellow
    Write-Host "  [packaged]    $exePath" -ForegroundColor Yellow
    Write-Host "  [dev]         $pythonwPath  +  $mainPyPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To fix:" -ForegroundColor White
    Write-Host "  * Packaged build  : run  .\build.ps1" -ForegroundColor White
    Write-Host "  * Dev environment : run  python -m venv .venv  then  pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# ── Write registry keys using .NET API ───────────────────────────────────────
#
# We use Microsoft.Win32.Registry directly to avoid PowerShell's HKCR: drive
# which can have path-parsing issues with the literal '*' character.
#
$keyPath  = "Software\Classes\*\shell\QuickConvert"

Write-Host ""
Write-Host "Registering context menu under HKCU\$keyPath ..." -ForegroundColor Yellow

$shellKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($keyPath)
$shellKey.SetValue("",       "Convert with QuickConvert")
$shellKey.SetValue("Icon",   $iconTarget)

# MUIVerb is the localisation-friendly display label (also used by Win11).
$shellKey.SetValue("MUIVerb", "Convert with QuickConvert")

$cmdKey = $shellKey.CreateSubKey("command")
$cmdKey.SetValue("", $targetCommand)

$cmdKey.Close()
$shellKey.Close()

# ── Verify the written values ─────────────────────────────────────────────────
$verify = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($keyPath + "\command", $false)
$writtenCmd = $verify.GetValue("")
$verify.Close()

if ($writtenCmd -ne $targetCommand) {
    Write-Host "VERIFICATION FAILED: the written command does not match expected value." -ForegroundColor Red
    Write-Host "  Written  : $writtenCmd" -ForegroundColor Red
    Write-Host "  Expected : $targetCommand" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "SUCCESS: QuickConvert context menu installed." -ForegroundColor Green
Write-Host ""
Write-Host "HOW TO USE:" -ForegroundColor White
Write-Host "  1. Open Windows Explorer and right-click any supported file." -ForegroundColor White
Write-Host "  2. On Windows 11: click 'Show more options' to reveal the legacy menu." -ForegroundColor White
Write-Host "  3. Click 'Convert with QuickConvert'." -ForegroundColor White
Write-Host ""
Write-Host "VERIFICATION (run in PowerShell after install):" -ForegroundColor White
Write-Host "  Get-ItemProperty 'HKCU:\Software\Classes\*\shell\QuickConvert\command'" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "UNINSTALL:" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File .\uninstall_context_menu.ps1" -ForegroundColor DarkCyan
Write-Host ""
