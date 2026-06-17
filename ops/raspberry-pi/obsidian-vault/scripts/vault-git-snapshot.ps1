#Requires -Version 5.1
<#
.SYNOPSIS
  Commit vault changes via separate git-dir (Windows mirror).
.PARAMETER Message
  Commit message (required).
.PARAMETER Push
  Push to origin after commit.
.PARAMETER SkipOneDriveSync
  Skip wait-onedrive-vault.ps1 (not recommended).
.PARAMETER SkipPull
  Skip fetch/rebase before commit and push (not recommended).
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$Push,

    [switch]$SkipOneDriveSync,

    [switch]$SkipPull,

    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"
$ScriptRoot = $PSScriptRoot
. (Join-Path $ScriptRoot "vault-git-common.ps1")

$paths = Get-ObsidianVaultPaths -ConfigPath $ConfigPath -ScriptRoot $ScriptRoot
$vaultPath = $paths.VaultPath
$gitDir = $paths.GitDir

if (-not $SkipOneDriveSync) {
    & (Join-Path $ScriptRoot "wait-onedrive-vault.ps1") -ConfigPath $ConfigPath
}

if (-not $SkipPull) {
    Sync-VaultGitRemote -GitDir $gitDir -WorkTree $vaultPath
}

$exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("add", "-A")
if ($exitCode -ne 0) { throw "git add failed" }

$exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("diff", "--cached", "--quiet")
if ($exitCode -eq 0) {
    Write-Host "No changes to commit."
    if ($Push) {
        if (-not $SkipPull) {
            Sync-VaultGitRemote -GitDir $gitDir -WorkTree $vaultPath
        }
        $exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("push", "origin", "main")
        if ($exitCode -ne 0) {
            $exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("push", "origin", "HEAD")
            if ($exitCode -ne 0) { throw "git push failed" }
        }
        Write-Host "Pushed to origin."
    }
    exit 0
}

$exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("commit", "-m", $Message)
if ($exitCode -ne 0) { throw "git commit failed" }

$hash = & git --git-dir=$gitDir --work-tree=$vaultPath rev-parse --short HEAD
Write-Host "Committed: $hash - $Message"

if ($Push) {
    if (-not $SkipPull) {
        Sync-VaultGitRemote -GitDir $gitDir -WorkTree $vaultPath
    }
    $exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("push", "origin", "main")
    if ($exitCode -ne 0) {
        $exitCode = Invoke-VaultGit -GitDir $gitDir -WorkTree $vaultPath -GitArgs @("push", "origin", "HEAD")
        if ($exitCode -ne 0) { throw "git push failed" }
    }
    Write-Host "Pushed to origin."
}
