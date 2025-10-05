#!/bin/bash
# scripts/build.sh
# Build script that generates version information for deployment

set -e  # Exit on any error

echo "🚀 Starting build process..."

# Generate version information
echo "📋 Generating version information..."
python3 scripts/generate_version.py

echo "✅ Build completed successfully!"

# If this is being run in Docker or CI/CD, you might want to:
# - Copy version.json to the final image
# - Set environment variables
# - Run other build steps

echo "📦 Version file ready for deployment"