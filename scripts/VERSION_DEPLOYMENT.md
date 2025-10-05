# Version Tracking System for PA Bot

This system provides automatic version tracking that works both in development (with live Git access) and production (Docker containers without Git).

## How it Works

The `/version` command shows:
- **🌿 Live Git info** when Git is available (development)
- **📁 Build-time snapshot** when using `version.json` file (production)

## For Production Deployment

### 1. Add to your build process

Before building your Docker image, run:
```bash
python3 scripts/generate_version.py
```

This creates `utils/version.json` with all Git information captured at build time.

### 2. Docker Integration

Add this to your Dockerfile (before the final `CMD`):
```dockerfile
# Generate version information during build
RUN python3 scripts/generate_version.py
```

### 3. GitHub Actions Integration

Add this step to your workflow before building:
```yaml
- name: Generate Version Info
  run: |
    python3 scripts/generate_version.py
    echo "Generated version.json for deployment"
```

### 4. Manual Build Script

Use the provided build script:
```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

## What You'll See

### In Development (with Git):
```
🤖 Bot Version Info 🌿

Commit: c937d33
Branch: agent/warp-initial
Date: 2025-10-05 13:54
Tag: pre-agent-2025-10-05
Last commit: Add /version command with Git info

🌿 Live Git information

⚠️ Working directory has uncommitted changes
```

### In Production (Docker with version.json):
```
🤖 Bot Version Info 📁

Commit: c937d33
Branch: main
Date: 2025-10-05 13:54
Tag: v1.2.3
Last commit: Deploy production version

📁 Info from build-time snapshot
Generated: 2025-10-05 14:30 UTC
```

## Troubleshooting

If you see old version info in production:
1. Make sure `scripts/generate_version.py` runs during build
2. Verify `utils/version.json` exists in your Docker image
3. Check that the file contains current Git info

## Files

- `scripts/generate_version.py` - Generates version.json from Git
- `utils/version.py` - Core version utilities with fallback logic  
- `utils/version_command.py` - Telegram command handler
- `scripts/build.sh` - Simple build script
- `scripts/docker-version-snippet.dockerfile` - Docker integration example
- `scripts/github-actions-snippet.yml` - GitHub Actions example