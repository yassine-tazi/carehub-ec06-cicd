#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="${1:-$(dirname "$ROOT")/carehub_execution_repo}"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$ROOT/01_pipeline" "$DEST/"
cp -R "$ROOT/02_conteneurisation" "$DEST/"
cp "$ROOT/README.md" "$DEST/"
cp -R "$ROOT/01_pipeline/.github" "$DEST/.github"
cp "$ROOT/01_pipeline/.pre-commit-config.yaml" "$DEST/.pre-commit-config.yaml"
cp "$ROOT/01_pipeline/.gitignore" "$DEST/.gitignore"
echo "Execution repository prepared at: $DEST"
