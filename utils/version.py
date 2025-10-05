# utils/version.py
import subprocess
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def load_version_from_file():
    """
    Load version information from version.json file (fallback for Docker/production).
    """
    version_file = os.path.join(os.path.dirname(__file__), 'version.json')
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded version info from {version_file}")
                return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Could not load version file: {e}")
    return None

def get_git_info():
    """
    Get Git information including commit hash, branch, and commit timestamp.
    First tries to get live Git information, then falls back to version.json file.
    Returns a dictionary with version information.
    """
    version_info = {
        'commit_hash': 'Unknown',
        'commit_short': 'Unknown', 
        'branch': 'Unknown',
        'commit_date': 'Unknown',
        'commit_message': 'Unknown',
        'is_dirty': False,
        'last_tag': 'Unknown',
        'source': 'unknown'
    }
    
    try:
        # Check if we're in a git repository and git is available
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode != 0:
            logger.info("Not in a git repository, trying version.json fallback")
            # Try to load from version.json file
            file_version = load_version_from_file()
            if file_version:
                # Map JSON fields to expected structure
                version_info.update({
                    'commit_hash': file_version.get('commit_hash', 'Unknown'),
                    'commit_short': file_version.get('commit_short', 'Unknown'),
                    'branch': file_version.get('branch', 'Unknown'),
                    'commit_date': file_version.get('commit_date', 'Unknown'),
                    'commit_message': file_version.get('commit_message', 'Unknown'),
                    'is_dirty': file_version.get('is_dirty', False),
                    'last_tag': file_version.get('last_tag', 'Unknown'),
                    'source': 'version.json',
                    'generated_at': file_version.get('generated_at', 'Unknown')
                })
                logger.info(f"Using version info from file: {version_info['commit_short']}")
            return version_info
            
        # We're in a Git repository, get live Git info
        version_info['source'] = 'git'
        
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
        logger.info("Git command not found, trying version.json fallback")
        # Try to load from version.json file
        file_version = load_version_from_file()
        if file_version:
            version_info.update({
                'commit_hash': file_version.get('commit_hash', 'Unknown'),
                'commit_short': file_version.get('commit_short', 'Unknown'),
                'branch': file_version.get('branch', 'Unknown'),
                'commit_date': file_version.get('commit_date', 'Unknown'),
                'commit_message': file_version.get('commit_message', 'Unknown'),
                'is_dirty': file_version.get('is_dirty', False),
                'last_tag': file_version.get('last_tag', 'Unknown'),
                'source': 'version.json',
                'generated_at': file_version.get('generated_at', 'Unknown')
            })
    except Exception as e:
        logger.warning(f"Error getting git info: {e}")
        # Try to load from version.json file as final fallback
        file_version = load_version_from_file()
        if file_version:
            version_info.update({
                'commit_hash': file_version.get('commit_hash', 'Unknown'),
                'commit_short': file_version.get('commit_short', 'Unknown'),
                'branch': file_version.get('branch', 'Unknown'),
                'commit_date': file_version.get('commit_date', 'Unknown'),
                'commit_message': file_version.get('commit_message', 'Unknown'),
                'is_dirty': file_version.get('is_dirty', False),
                'last_tag': file_version.get('last_tag', 'Unknown'),
                'source': 'version.json',
                'generated_at': file_version.get('generated_at', 'Unknown')
            })
        
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
    source_emoji = "📁" if info.get('source') == 'version.json' else "🌿" if info.get('source') == 'git' else "❓"
    
    message_parts = [
        f"<b>🤖 Bot Version Info</b> {source_emoji}",
        "",
        f"<b>Commit:</b> <code>{info['commit_short']}</code>",
        f"<b>Branch:</b> <code>{info['branch']}</code>",
        f"<b>Date:</b> <code>{commit_date_formatted}</code>",
    ]
    
    if info['last_tag'] != 'Unknown':
        message_parts.append(f"<b>Tag:</b> <code>{info['last_tag']}</code>")
        
    if info['commit_message'] != 'Unknown':
        message_parts.append(f"<b>Last commit:</b> <i>{info['commit_message']}</i>")
        
    # Show source information
    if info.get('source') == 'version.json':
        message_parts.append("")
        message_parts.append(f"<i>📁 Info from build-time snapshot</i>")
        if info.get('generated_at'):
            try:
                gen_time = datetime.fromisoformat(info['generated_at'].replace('Z', '+00:00'))
                gen_formatted = gen_time.strftime('%Y-%m-%d %H:%M UTC')
                message_parts.append(f"<i>Generated: {gen_formatted}</i>")
            except:
                pass
    elif info.get('source') == 'git':
        message_parts.append("")
        message_parts.append(f"<i>🌿 Live Git information</i>")
        
    if info['is_dirty']:
        message_parts.append("")
        message_parts.append("⚠️ <i>Working directory has uncommitted changes</i>")
        
    return "\n".join(message_parts)