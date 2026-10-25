# QuickConvert PyInstaller Build Script
# Compiles the application into dist\QuickConvert\QuickConvert.exe

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$pyinstallerExe = Join-Path $scriptDir ".venv\Scripts\pyinstaller.exe"
$iconPath = Join-Path $scriptDir "assets\icon.ico"

# Ensure icon exists
if (-not (Test-Path -LiteralPath $iconPath)) {
    Write-Host "Generating application icon..." -ForegroundColor Yellow
    & $pythonExe (Join-Path $scriptDir "utils\icon_generator.py")
}

# Stop any running instances of QuickConvert to prevent file locks
$running = Get-Process -Name "QuickConvert" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "Stopping running QuickConvert processes..." -ForegroundColor Yellow
    $running | Stop-Process -Force
    Start-Sleep -Milliseconds 500
}

Write-Host "Building QuickConvert with PyInstaller..." -ForegroundColor Cyan

# Clean previous build artifacts
$buildDir = Join-Path $scriptDir "build"
$distDir = Join-Path $scriptDir "dist"
$specFile = Join-Path $scriptDir "QuickConvert.spec"

if (Test-Path -LiteralPath $buildDir) {
    Remove-Item -Path $buildDir -Recurse -Force
}
if (Test-Path -LiteralPath $distDir) {
    Remove-Item -Path $distDir -Recurse -Force
}
if (Test-Path -LiteralPath $specFile) {
    Remove-Item -Path $specFile -Force
}

$assetsDir = Join-Path $scriptDir "assets"
$pysidePluginsDir = Join-Path $scriptDir ".venv\Lib\site-packages\PySide6\plugins"

if (-not (Test-Path -LiteralPath (Join-Path $pysidePluginsDir "platforms\qwindows.dll"))) {
    Write-Error "PySide6 Windows platform plugin (qwindows.dll) not found in $pysidePluginsDir."
    exit 1
}

& $pyinstallerExe `
    --noconfirm `
    --windowed `
    --name "QuickConvert" `
    --icon "$iconPath" `
    --add-data "$assetsDir;assets" `
    --add-data "$pysidePluginsDir;PySide6/plugins" `
    --collect-all "pypdfium2" `
    --collect-all "reportlab" `
    --collect-all "PIL" `
    --collect-all "docx" `
    --collect-all "markdown" `
    --hidden-import "PySide6.QtCore" `
    --hidden-import "PySide6.QtGui" `
    --hidden-import "PySide6.QtWidgets" `
    --hidden-import "shiboken6" `
    --hidden-import "html.parser" `
    --hidden-import "converters" `
    --hidden-import "services" `
    --hidden-import "utils" `
    --hidden-import "ui" `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

$distExe = Join-Path $scriptDir "dist\QuickConvert\QuickConvert.exe"
$distInternal = Join-Path $scriptDir "dist\QuickConvert\_internal"
$distBaseLib = Join-Path $distInternal "base_library.zip"
$distQWindows = Join-Path $distInternal "PySide6\plugins\platforms\qwindows.dll"

# Deploy qt.conf to configure Qt library paths at application level
$qtConfContent = @"
[Paths]
Prefix = _internal/PySide6
Plugins = plugins
Libraries = .
"@
Set-Content -Path (Join-Path $scriptDir "dist\QuickConvert\qt.conf") -Value $qtConfContent -Encoding ASCII
Set-Content -Path (Join-Path $distInternal "qt.conf") -Value $qtConfContent -Encoding ASCII

# Deploy standard root platforms fallback next to QuickConvert.exe
$rootPlatforms = Join-Path $scriptDir "dist\QuickConvert\platforms"
if (-not (Test-Path -LiteralPath $rootPlatforms)) {
    New-Item -ItemType Directory -Path $rootPlatforms -Force | Out-Null
}
Copy-Item -Path (Join-Path $pysidePluginsDir "platforms\qwindows.dll") -Destination (Join-Path $rootPlatforms "qwindows.dll") -Force

if ((Test-Path -LiteralPath $distExe) -and (Test-Path -LiteralPath $distBaseLib) -and (Test-Path -LiteralPath $distQWindows)) {
    Write-Host "`n==========================================" -ForegroundColor Green
    Write-Host "QuickConvert build completed successfully!" -ForegroundColor Green
    Write-Host "Executable: $distExe" -ForegroundColor Green
    Write-Host "Runtime library verified: $distBaseLib" -ForegroundColor Green
    Write-Host "Qt platform plugin verified: $distQWindows" -ForegroundColor Green
    Write-Host "Qt configuration deployed: qt.conf" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Error "Build finished but required runtime files were missing (distExe, base_library.zip, or qwindows.dll)."
    exit 1
}
