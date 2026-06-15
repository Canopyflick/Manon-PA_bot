#Requires -Version 5.1
<#
.SYNOPSIS
  One-time bootstrap for Windows-side Obsidian vault git mirror.
.DESCRIPTION
  Clones the bare backup repo to a separate git-dir and verifies the work-tree
  points at the OneDrive vault. Never creates .git inside the vault folder.
#>
param(
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
        throw "Config not found: $Path`nCopy config.example.env to config.env first."
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
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$config = Get-ObsidianVaultConfig -Path $ConfigPath
$vaultPath = $config["VAULT_PATH"]
$gitDir = $config["GIT_DIR"]
$remote = $config["GIT_REMOTE"]

if (-not $vaultPath -or -not $gitDir -or -not $remote) {
    throw "config.env must define VAULT_PATH, GIT_DIR, and GIT_REMOTE"
}

$vaultPath = [System.IO.Path]::GetFullPath($vaultPath)
$gitDir = [System.IO.Path]::GetFullPath($gitDir)

Write-Host "Vault (work-tree): $vaultPath"
Write-Host "Git dir:           $gitDir"
Write-Host "Remote:            $remote"

if (-not (Test-Path $vaultPath)) {
    throw "Vault path does not exist: $vaultPath"
}

$gitInsideVault = Join-Path $vaultPath ".git"
if (Test-Path $gitInsideVault) {
    throw "Refusing bootstrap: .git found inside vault (would pollute OneDrive sync): $gitInsideVault"
}

$mdFiles = Get-ChildItem -Path $vaultPath -Filter "*.md" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mdFiles) {
    Write-Warning "No .md files found in vault; continuing anyway"
}

if (Test-Path $gitDir) {
    Write-Host "Git dir already exists; verifying configuration..."
    Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("rev-parse", "--git-dir")
    $currentRemote = & git --git-dir=$gitDir --work-tree=$vaultPath remote get-url origin 2>$null
    if ($currentRemote -and $currentRemote -ne $remote) {
        Write-Warning "Existing origin ($currentRemote) differs from config ($remote)"
    }
    Write-Host "Bootstrap already complete."
    exit 0
}

$gitParent = Split-Path -Parent $gitDir
if (-not (Test-Path $gitParent)) {
    New-Item -ItemType Directory -Path $gitParent -Force | Out-Null
}

Write-Host "Cloning bare repo to $gitDir ..."
& git clone --bare $remote $gitDir
if ($LASTEXITCODE -ne 0) {
    throw "git clone --bare failed. Ensure SSH access to $remote"
}

Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("config", "core.worktree", $vaultPath)
Invoke-Git -GitDir $gitDir -WorkTree $vaultPath -Args @("status", "--short")

Write-Host ""
Write-Host "Bootstrap complete. Use vault-git-snapshot.ps1 to commit changes."
