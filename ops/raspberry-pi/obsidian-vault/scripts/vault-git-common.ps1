#Requires -Version 5.1
# Shared helpers for Windows Obsidian vault git mirror scripts.

function Get-ObsidianVaultConfig {
    param(
        [string]$ConfigPath,
        [string]$ScriptRoot
    )

    if (-not $ConfigPath) {
        $ConfigPath = Join-Path (Split-Path -Parent $ScriptRoot) "config.env"
    }

    if (-not (Test-Path $ConfigPath)) {
        throw "Config not found: $ConfigPath`nCopy config.example.env to config.env and run vault-git-bootstrap.ps1 first."
    }

    $config = @{}
    Get-Content $ConfigPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $value = [Environment]::ExpandEnvironmentVariables($parts[1].Trim())
            $config[$key] = $value
        }
    }
    return $config
}

function Get-ObsidianVaultPaths {
    param([string]$ConfigPath, [string]$ScriptRoot)

    $config = Get-ObsidianVaultConfig -ConfigPath $ConfigPath -ScriptRoot $ScriptRoot
    $vaultPath = [System.IO.Path]::GetFullPath($config["VAULT_PATH"])
    $gitDir = [System.IO.Path]::GetFullPath($config["GIT_DIR"])

    if (-not (Test-Path $gitDir)) {
        throw "Git dir not found: $gitDir`nRun vault-git-bootstrap.ps1 first."
    }
    if (-not (Test-Path $vaultPath)) {
        throw "Vault path not found: $vaultPath"
    }
    if (Test-Path (Join-Path $vaultPath ".git")) {
        throw "Refusing operation: .git found inside vault folder"
    }

    return [PSCustomObject]@{
        VaultPath = $vaultPath
        GitDir    = $gitDir
        Config    = $config
    }
}

function Invoke-VaultGit {
    param(
        [string]$GitDir,
        [string]$WorkTree,
        [string[]]$GitArgs
    )
    $allArgs = @("--git-dir=$GitDir", "--work-tree=$WorkTree") + $GitArgs
    & git @allArgs
    return $LASTEXITCODE
}

function Get-VaultGitPorcelainStatus {
    param([string]$GitDir, [string]$WorkTree)
    $output = & git --git-dir=$GitDir --work-tree=$WorkTree status --porcelain
    return @($output | Where-Object { $_ })
}

function Sync-VaultGitRemote {
    <#
      Fetch origin and rebase local main onto origin/main when behind.
      Stashes dirty worktree first if needed.
    #>
    param(
        [string]$GitDir,
        [string]$WorkTree,
        [string]$Branch = "main"
    )

    $exitCode = Invoke-VaultGit -GitDir $GitDir -WorkTree $WorkTree -GitArgs @(
        "fetch", "origin", "${Branch}:refs/remotes/origin/${Branch}"
    )
    if ($exitCode -ne 0) { throw "git fetch origin $Branch failed" }

    $behind = & git --git-dir=$GitDir --work-tree=$WorkTree rev-list --count "HEAD..refs/remotes/origin/$Branch" 2>$null
    $ahead = & git --git-dir=$GitDir --work-tree=$WorkTree rev-list --count "refs/remotes/origin/$Branch..HEAD" 2>$null
    if ((-not $behind -or [int]$behind -eq 0) -and (-not $ahead -or [int]$ahead -eq 0)) {
        Write-Host "Vault git mirror is up to date with origin/$Branch."
        return
    }
    if ($ahead -and [int]$ahead -gt 0) {
        Write-Host "Vault git mirror is $ahead commit(s) ahead of origin/$Branch (will push after commit if requested)."
    }
    if (-not $behind -or [int]$behind -eq 0) {
        return
    }

    Write-Host "Vault git mirror is $behind commit(s) behind origin/$Branch; rebasing..."

    $dirty = Get-VaultGitPorcelainStatus -GitDir $GitDir -WorkTree $WorkTree
    $stashed = $false
    if ($dirty.Count -gt 0) {
        Write-Host "Stashing $($dirty.Count) local change(s) before rebase..."
        $exitCode = Invoke-VaultGit -GitDir $GitDir -WorkTree $WorkTree -GitArgs @("stash", "push", "-u", "-m", "vault-git-autostash")
        if ($exitCode -ne 0) { throw "git stash failed before rebase" }
        $stashed = $true
    }

    $prevEditor = $env:GIT_EDITOR
    $env:GIT_EDITOR = "true"
    try {
        $exitCode = Invoke-VaultGit -GitDir $GitDir -WorkTree $WorkTree -GitArgs @("rebase", "refs/remotes/origin/$Branch")
        if ($exitCode -ne 0) {
            throw @"
git rebase refs/remotes/origin/$Branch failed (merge conflict).

Resolve conflicts in the vault, then:
  git --git-dir=$GitDir --work-tree=`"$WorkTree`" add -A
  `$env:GIT_EDITOR = 'true'; git --git-dir=$GitDir --work-tree=`"$WorkTree`" rebase --continue

Or abort: git --git-dir=$GitDir --work-tree=`"$WorkTree`" rebase --abort
"@
        }
    }
    finally {
        if ($null -ne $prevEditor) { $env:GIT_EDITOR = $prevEditor } else { Remove-Item Env:GIT_EDITOR -ErrorAction SilentlyContinue }
    }

    if ($stashed) {
        Write-Host "Restoring stashed vault changes..."
        $exitCode = Invoke-VaultGit -GitDir $GitDir -WorkTree $WorkTree -GitArgs @("stash", "pop")
        if ($exitCode -ne 0) {
            throw "git stash pop failed after rebase - resolve conflicts manually, then stash drop when done."
        }
    }

    Write-Host "Rebased onto refs/remotes/origin/$Branch."
}
