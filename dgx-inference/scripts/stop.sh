#!/bin/bash
# =============================================================================
# Stop DGX Inference Stack
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping inference stack..."

cd "$PROJECT_DIR"
docker compose down

echo "✓ Inference stack stopped"
