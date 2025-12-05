#!/bin/bash

# 1. Show current status
echo "--- Current Status ---"
git status -s
echo "----------------------"

# 2. Check if there are changes to commit
if [ -z "$(git status --porcelain)" ]; then
  echo "Nothing to commit! Working tree clean."
else
  # 3. Ask for commit message
  echo ""
  read -p "Enter commit message: " COMMIT_MSG
  
  if [ -z "$COMMIT_MSG" ]; then
    echo "Message cannot be empty. Aborting."
    exit 1
  fi

  # Stage and commit
  git add .
  git commit -m "$COMMIT_MSG"
fi

# 4. Handle Versioning
echo ""
# Get the latest tag, default to v0.0.0 if none exists
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Current Version: $CURRENT_TAG"

read -p "Enter new version (e.g. v1.0.1): " NEW_TAG

if [ -z "$NEW_TAG" ]; then
  echo "Version cannot be empty. Aborting."
  exit 1
fi

# 5. Execute Tag and Push
echo ""
echo "Tagging as $NEW_TAG..."
git tag "$NEW_TAG"

echo "Pushing code and tags to GitHub..."
git push origin main
git push origin "$NEW_TAG"

echo ""
echo "Done! GitHub Action should be running now."