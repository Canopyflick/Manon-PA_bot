#Requires -Version 5.1
<#
.SYNOPSIS
  Best-effort wait for OneDrive to settle before Obsidian vault operations.
.DESCRIPTION
  OneDrive is the source of truth for vault content. This script verifies the
  vault path exists, OneDrive is running, and optionally waits before edits.
#>
param(
    [string]$ConfigPath,
    [int]$SettleSeconds = 5,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$ScriptRoot = $PSScriptRoot
. (Join-Path $ScriptRoot "vault-git-common.ps1")

$paths = Get-ObsidianVaultPaths -ConfigPath $ConfigPath -ScriptRoot $ScriptRoot
$vaultPath = $paths.VaultPath

if (-not (Get-Process -Name "OneDrive" -ErrorAction SilentlyContinue)) {
    $msg = "OneDrive.exe is not running. Start OneDrive and wait for sync before editing the vault."
    if ($Strict) { throw $msg }
    Write-Warning $msg
}

$syncRoots = @($env:OneDrive, $env:OneDriveConsumer) | Where-Object { $_ }
$underOneDrive = $false
foreach ($root in $syncRoots) {
    if ($vaultPath.StartsWith([System.IO.Path]::GetFullPath($root), [System.StringComparison]::OrdinalIgnoreCase)) {
        $underOneDrive = $true
        Write-Host "Vault is under OneDrive: $vaultPath"
        break
    }
}
if (-not $underOneDrive) {
    Write-Warning "Vault path may not be the active OneDrive folder: $vaultPath"
}

$pendingTmp = @(Get-ChildItem -Path $vaultPath -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^~|\.tmp$|\.partial$|\.swp$' })
if ($pendingTmp.Count -gt 0) {
    $msg = "Found $($pendingTmp.Count) temporary/partial file(s) under the vault - OneDrive or an editor may still be syncing."
    if ($Strict) { throw $msg }
    Write-Warning $msg
}

if ($SettleSeconds -gt 0) {
    Write-Host "Waiting ${SettleSeconds}s for OneDrive to settle..."
    Start-Sleep -Seconds $SettleSeconds
}

Write-Host "OneDrive vault preflight OK."
