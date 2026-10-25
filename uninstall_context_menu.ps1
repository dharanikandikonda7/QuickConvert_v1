<#
.SYNOPSIS
    QuickConvert — Windows Explorer Context Menu Uninstaller

.DESCRIPTION
    Removes the "Convert with QuickConvert" context-menu entry from HKCU.
    Only the keys that the installer created are deleted:
        HKCU\Software\Classes\*\shell\QuickConvert          (and all sub-keys)

    No other registry keys are touched. Safe to run even if the key is
    already absent. Does not require administrator privileges.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"

$parentKeyPath = "Software\Classes\*\shell"
$entryName     = "QuickConvert"
$fullKeyPath   = "$parentKeyPath\$entryName"

Write-Host "Removing QuickConvert context menu from HKCU\$fullKeyPath ..." -ForegroundColor Yellow

try {
    $parentKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($parentKeyPath, $true)

    if ($null -eq $parentKey) {
        Write-Host "Parent key 'HKCU\$parentKeyPath' does not exist — nothing to remove." -ForegroundColor Gray
        exit 0
    }

    $existingSubKeys = $parentKey.GetSubKeyNames()
    if ($entryName -notin $existingSubKeys) {
        $parentKey.Close()
        Write-Host "QuickConvert context menu was not found (already uninstalled or never installed)." -ForegroundColor Gray
        exit 0
    }

    # DeleteSubKeyTree removes the key and ALL its children (e.g., "command").
    # The second argument ($false) suppresses the exception if the key is absent.
    $parentKey.DeleteSubKeyTree($entryName, $false)
    $parentKey.Close()

    # ── Post-removal verification ─────────────────────────────────────────────
    $verifyParent = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($parentKeyPath, $false)
    if ($null -ne $verifyParent) {
        $remaining = $verifyParent.GetSubKeyNames()
        $verifyParent.Close()
        if ($entryName -in $remaining) {
            Write-Host "VERIFICATION FAILED: the key still exists after deletion." -ForegroundColor Red
            exit 1
        }
    }

    Write-Host "SUCCESS: QuickConvert context menu removed." -ForegroundColor Green
    Write-Host ""
    Write-Host "To reinstall later:" -ForegroundColor White
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\install_context_menu.ps1" -ForegroundColor DarkCyan

} catch {
    Write-Host "QuickConvert context menu was not found or already removed." -ForegroundColor Gray
}
