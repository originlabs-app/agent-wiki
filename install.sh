#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_LOCAL=0

for arg in "$@"; do
  case "$arg" in
    --bootstrap|--local)
      BOOTSTRAP_LOCAL=1
      ;;
    *)
      echo "unknown flag: $arg" >&2
      exit 1
      ;;
  esac
done

chmod +x "$ROOT/cli/wikictl"

"$ROOT/cli/wikictl" init

if [[ $BOOTSTRAP_LOCAL -eq 1 ]]; then
  "$ROOT/scripts/bootstrap-local.sh"
fi

echo "Installed the local knowledge-base scaffold at:"
echo "  $ROOT"
echo
echo "Next:"
echo "  - open the repo in Claude, Codex, Cursor, or Hermès"
echo "  - let the agent read AGENTS.md first"
echo "  - run ./scripts/bootstrap-local.sh to link local tool configs"
echo "  - or use ./install.sh --bootstrap to do both"
echo "  - use ./cli/wikictl sync <agent> <op> <description> for write-back"
