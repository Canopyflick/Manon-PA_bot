#Requires -Version 5.1
<#
.SYNOPSIS
  Commit vault changes via separate git-dir (Windows mirror).
.PARAMETER Message
  Commit message (required).
.PARAMETER Push
  Push to origin after commit.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$Push,

    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"

function Get-ObsidianVaultConfig {
    param([string]$Path)

    if (-not $Path) {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $Path = Join-Path (Split-Path -Parent $scriptDir) "config.env"
    }

    if (-not (Test-Path $Path)) {
        throw "Config not found: $Path`nCopy config.example.env to config.env and run vault-git-bootstrap.ps1 first."
    }

    $config = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim()
            if ($value -match "^%(.+)%$") {
                $value = [Environment]::GetEnvironmentVariable($Matches[1])
            }
            $config[$key] = $value
        }
    }
    return $config
}

function Invoke-Git {
    param(
        [string]$GitDir,
        [string]$WorkTree,
        [string[]]$Args
    )
    $allArgs = @("--git-dir=$GitDir", "--work-tree=$WorkTree") + $Args
    & git @allArgs
    return $LASTEXITCODE
}

$config = Get-ObsidianVaultConfig -Path $ConfigPath
$vaultPath = [System.IO.Path]::GetFullPath($config["VAULT_PATH"])
$gitDir = [System.IO.Path]::GetFullPath($config["GIT_DIR"])

if (-not (Test-Path $gitDir)) {
    throw "Git dir not found: $gitDir`nRun vault-git-bootstrap.ps1 first."
}

if (Test-Path (Join-Path $vaultPath ".git")) {
    throw "Refusing snapshot: .git found inside vault folder"
}

$exitCode = Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("add", "-A")
if ($exitCode -ne 0) { throw "git add failed" }

$exitCode = Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("diff", "--cached", "--quiet")
if ($exitCode -eq 0) {
    Write-Host "No changes to commit."
    exit 0
}

$exitCode = Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("commit", "-m", $Message)
if ($exitCode -ne 0) { throw "git commit failed" }

$hash = & git --git-dir=$gitDir --work-tree=$vaultPath rev-parse --short HEAD
Write-Host "Committed: $hash — $Message"

if ($Push) {
    $exitCode = Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("push", "origin", "main")
    if ($exitCode -ne 0) {
        $exitCode = Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("push", "origin", "HEAD")
        if ($exitCode -ne 0) { throw "git push failed" }
    }
    Write-Host "Pushed to origin."
}
