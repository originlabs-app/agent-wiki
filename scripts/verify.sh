#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "$ROOT/cli/wikictl"
node --check "$ROOT/mcp/server.mjs"
"$ROOT/cli/wikictl" lint

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
cp -R "$ROOT" "$TMPDIR/repo"
mkdir -p "$TMPDIR/repo/raw/untracked"
cat >"$TMPDIR/repo/raw/untracked/sample-source.md" <<'EOF'
# Sample Source

This is a sample source used to verify ingest, query, and heal.
EOF
(
  cd "$TMPDIR/repo"
  ./cli/wikictl ingest "Sample Project" raw/untracked/sample-source.md
  ./cli/wikictl query sample
  ./cli/wikictl heal
  ./cli/wikictl lint
  grep -Fq '[[wiki/projects/sample-project]]' wiki/index.md
  test -f raw/ingested/sample-source.md
  test ! -f raw/untracked/sample-source.md
  grep -Fq '[[raw/ingested/sample-source.md]]' wiki/projects/sample-project.md
)

mkdir -p "$TMPDIR/external-vault/wiki" "$TMPDIR/external-vault/raw/untracked"
cat >"$TMPDIR/external-vault/raw/untracked/external-source.md" <<'EOF'
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
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" ingest "Attached Vault" "$TMPDIR/external-vault/raw/untracked/external-source.md"
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" query karpathy
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" heal
  ./cli/wikictl --config "$TMPDIR/origin-labs.conf" lint
  grep -Fq '[[wiki/projects/attached-vault]]' "$TMPDIR/external-vault/wiki/index.md"
  test -f "$TMPDIR/external-vault/raw/ingested/external-source.md"
  test ! -f "$TMPDIR/external-vault/raw/untracked/external-source.md"
)

echo "verify: ok"
