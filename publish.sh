#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting publication process for uni-tool..."

# 1. Install/Ensure build tools are present
echo "📦 Ensuring build tools (build, twine) are installed..."
uv add --dev build twine

# 2. Clean up old build artifacts
if [ -d "dist" ]; then
    echo "🧹 Cleaning up old 'dist' directory..."
    rm -rf dist
fi

# 3. Build the project
echo "🔨 Building the project..."
uv run python -m build

# Check if build was successful
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo "❌ Error: Build failed or dist directory is empty."
    exit 1
fi

echo "✅ Build successful. Artifacts:"
ls -lh dist/

# 4. Upload to PyPI
echo "📤 Ready to upload to PyPI."
echo "ℹ️  Username: __token__"
echo "ℹ️  Password: <your-pypi-api-token>"
echo "❓ Do you want to upload to PyPI now? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    uv run twine upload dist/*
    echo "🎉 Package published successfully!"
else
    echo "🚫 Upload cancelled."
fi
