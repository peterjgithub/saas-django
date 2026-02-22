#!/usr/bin/env bash
# Run once after cloning: bash scripts/install-hooks.sh
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
ln -sf "$REPO_ROOT/scripts/pre-commit" "$REPO_ROOT/.git/hooks/pre-commit"
chmod +x "$REPO_ROOT/scripts/pre-commit"
echo "✓ pre-commit hook installed (symlinked)"
