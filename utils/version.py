# utils/version.py
import subprocess
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_git_info():
    """
    Get Git information including commit hash, branch, and commit timestamp.
    Returns a dictionary with version information.
    """
    version_info = {
        'commit_hash': 'Unknown',
        'commit_short': 'Unknown', 
        'branch': 'Unknown',
        'commit_date': 'Unknown',
        'commit_message': 'Unknown',
        'is_dirty': False,
        'last_tag': 'Unknown'
    }
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode != 0:
            logger.warning("Not in a git repository")
            return version_info
            
        # Get commit hash (full)
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            version_info['commit_hash'] = result.stdout.strip()
            version_info['commit_short'] = result.stdout.strip()[:7]
            
        # Get branch name
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0 and result.stdout.strip():
            version_info['branch'] = result.stdout.strip()
        else:
            # Fallback for detached HEAD (common in CI/CD)
            result = subprocess.run(['git', 'describe', '--all', '--exact-match', 'HEAD'], 
                                  capture_output=True, text=True, cwd=os.path.dirname(__file__))
            if result.returncode == 0:
                version_info['branch'] = result.stdout.strip().replace('heads/', '')
                
        # Get commit date
        result = subprocess.run(['git', 'log', '-1', '--format=%ci', 'HEAD'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            version_info['commit_date'] = result.stdout.strip()
            
        # Get commit message (first line only)
        result = subprocess.run(['git', 'log', '-1', '--format=%s', 'HEAD'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            version_info['commit_message'] = result.stdout.strip()[:100]  # Limit length
            
        # Check if working directory is dirty
        result = subprocess.run(['git', 'diff-index', '--quiet', 'HEAD'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        version_info['is_dirty'] = result.returncode != 0
        
        # Get last tag
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            version_info['last_tag'] = result.stdout.strip()
            
    except FileNotFoundError:
        logger.warning("Git command not found")
    except Exception as e:
        logger.warning(f"Error getting git info: {e}")
        
    return version_info

def format_version_message():
    """
    Format version information into a user-friendly message.
    """
    info = get_git_info()
    
    # Format commit date nicely
    commit_date_formatted = "Unknown"
    if info['commit_date'] != 'Unknown':
        try:
            # Parse the git date format: "2025-01-05 14:30:45 +0100"
            dt = datetime.strptime(info['commit_date'][:19], '%Y-%m-%d %H:%M:%S')
            commit_date_formatted = dt.strftime('%Y-%m-%d %H:%M')
        except:
            commit_date_formatted = info['commit_date']
    
    # Build message parts
    message_parts = [
        f"<b>🤖 Bot Version Info</b>",
        "",
        f"<b>Commit:</b> <code>{info['commit_short']}</code>",
        f"<b>Branch:</b> <code>{info['branch']}</code>",
        f"<b>Date:</b> <code>{commit_date_formatted}</code>",
    ]
    
    if info['last_tag'] != 'Unknown':
        message_parts.append(f"<b>Tag:</b> <code>{info['last_tag']}</code>")
        
    if info['commit_message'] != 'Unknown':
        message_parts.append(f"<b>Last commit:</b> <i>{info['commit_message']}</i>")
        
    if info['is_dirty']:
        message_parts.append("")
        message_parts.append("⚠️ <i>Working directory has uncommitted changes</i>")
        
    return "\n".join(message_parts)