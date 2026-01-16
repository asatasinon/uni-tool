#!/bin/bash
set -e

# 1. Extract version from pyproject.toml
# Assumes the format: version = "0.1.0"
VERSION=$(grep -m 1 '^version = ' pyproject.toml | cut -d '"' -f 2)

if [ -z "$VERSION" ]; then
    echo "❌ Could not extract version from pyproject.toml"
    exit 1
fi

TAG="v$VERSION"

echo "Current project version: $VERSION"
echo "Target Tag: $TAG"

# 2. Check if git working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Working directory is not clean."
    echo "It is recommended to commit all changes before tagging."
    read -p "❓ Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "🚫 Cancelled."
        exit 1
    fi
fi

# 3. Check if tag already exists locally
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG already exists locally."
    exit 1
fi

# 4. Check if tag already exists on remote (optional but good)
# Note: This requires network access, might fail in some sandboxes/offline modes
# skipping explicitly to keep it fast, git push will fail if it exists anyway.

# 5. Confirmation
read -p "❓ Create tag '$TAG' and push to origin? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "🚫 Cancelled."
    exit 1
fi

# 6. Create Tag
echo "🏷️  Creating git tag..."
git tag -a "$TAG" -m "Release $TAG"

# 7. Push Tag
echo "🚀 Pushing tag to origin..."
git push origin "$TAG"

echo "✅ Done! Tag $TAG pushed."
echo "GitHub Action should be triggered now."
