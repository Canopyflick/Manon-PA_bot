#!/usr/bin/env python3
"""
Generate version.json file with Git information.
This script should be run during build/deployment to capture version info
for environments where Git is not available (like Docker containers).
"""

import json
import subprocess
import os
from datetime import datetime, timezone

def run_git_command(cmd, default="Unknown"):
    """Run a git command and return the result or default value."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return default

def generate_version_info():
    """Generate comprehensive version information."""
    
    # Get commit hash (full and short)
    commit_hash = run_git_command(['git', 'rev-parse', 'HEAD'])
    commit_short = commit_hash[:7] if commit_hash != "Unknown" else "Unknown"
    
    # Get branch name
    branch = run_git_command(['git', 'branch', '--show-current'])
    if branch == "Unknown" or not branch:
        # Fallback for detached HEAD (common in CI/CD)
        branch = run_git_command(['git', 'describe', '--all', '--exact-match', 'HEAD'], "Unknown")
        if branch != "Unknown":
            branch = branch.replace('heads/', '').replace('remotes/origin/', '')
    
    # Get commit date
    commit_date = run_git_command(['git', 'log', '-1', '--format=%ci', 'HEAD'])
    
    # Get commit message (first line only)
    commit_message = run_git_command(['git', 'log', '-1', '--format=%s', 'HEAD'])
    if len(commit_message) > 100:
        commit_message = commit_message[:97] + "..."
    
    # Check if working directory is dirty
    is_dirty = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD'], 
                             capture_output=True).returncode != 0
    
    # Get last tag
    last_tag = run_git_command(['git', 'describe', '--tags', '--abbrev=0'])
    
    # Get remote URL (sanitized)
    remote_url = run_git_command(['git', 'config', '--get', 'remote.origin.url'])
    
    version_info = {
        'commit_hash': commit_hash,
        'commit_short': commit_short,
        'branch': branch,
        'commit_date': commit_date,
        'commit_message': commit_message,
        'is_dirty': is_dirty,
        'last_tag': last_tag,
        'remote_url': remote_url,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'generated_by': 'generate_version.py'
    }
    
    return version_info

def main():
    """Main function to generate and save version info."""
    print("Generating version information...")
    
    version_info = generate_version_info()
    
    # Create the directory if it doesn't exist
    os.makedirs('utils', exist_ok=True)
    
    # Write to version.json
    version_file = os.path.join('utils', 'version.json')
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2)
    
    print(f"✅ Version info written to {version_file}")
    print(f"📋 Commit: {version_info['commit_short']}")
    print(f"🌿 Branch: {version_info['branch']}")
    print(f"📅 Date: {version_info['commit_date']}")
    print(f"🏷️ Tag: {version_info['last_tag']}")
    
    if version_info['is_dirty']:
        print("⚠️ Working directory has uncommitted changes")

if __name__ == "__main__":
    main()