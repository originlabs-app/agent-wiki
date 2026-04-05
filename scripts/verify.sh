#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "$ROOT/install.sh"
bash -n "$ROOT/cli/wikictl"
bash -n "$ROOT/scripts/bootstrap-local.sh"
node --check "$ROOT/mcp/server.mjs"
python3 - "$ROOT/.claude/settings.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    json.load(f)
PY
"$ROOT/cli/wikictl" lint

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cp -R "$ROOT" "$TMPDIR/repo"
cat >"$TMPDIR/repo/raw/sample-source.md" <<'EOF'
# Sample Source

This is a sample source used to verify ingest, query, and heal.
EOF
(
  cd "$TMPDIR/repo"
  ./cli/wikictl ingest "Sample Project" raw/sample-source.md
  ./cli/wikictl query sample
  ./cli/wikictl heal
  ./cli/wikictl lint
  grep -Fq '[[wiki/projects/sample-project]]' wiki/index.md
)

echo "verify: ok"
