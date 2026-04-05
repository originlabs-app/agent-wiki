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

mkdir -p "$TMPDIR/external-vault/wiki" "$TMPDIR/external-vault/raw"
cat >"$TMPDIR/external-vault/raw/external-source.md" <<'EOF'
# External Source

Karpathy style wiki compilation for an attached vault instance.
EOF
cat >"$TMPDIR/origin-labs.conf" <<EOF
INSTANCE_NAME=origin-labs
WIKI_ROOT=$TMPDIR/external-vault/wiki
RAW_ROOT=$TMPDIR/external-vault/raw
SOURCE_DIRS=$TMPDIR/external-vault/projects:$TMPDIR/external-vault/clients
EOF
(
  cd "$TMPDIR/repo"
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" init
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" ingest "Attached Vault" "$TMPDIR/external-vault/raw/external-source.md"
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" query karpathy
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" heal
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" lint
  grep -Fq '[[wiki/projects/attached-vault]]' "$TMPDIR/external-vault/wiki/index.md"
)

echo "verify: ok"
