#!/usr/bin/env bash
# Every gate a pull request must pass, run locally. There is no CI: the maintainer
# runs this before merging, and contributors run it before opening a pull request.
#
#   scripts/check.sh            # contributors: a gate whose tool is missing is skipped and counted
#   scripts/check.sh --dev      # the maintainer: every tool is required and the .denylist is checked
#
# Tools, with the versions the pack was last verified against: python3 with
# pyyaml 6.0.3 and pytest 9.0.1; uv (skills-ref is pinned to 0.1.1 below);
# the claude CLI 2.1.267; gh 2.100.0 (2.90 or later for `gh skill`); gitleaks 8.28.0.
set -euo pipefail
cd "$(dirname "$0")/.."

dev=0
[ "${1:-}" = "--dev" ] && dev=1
skipped=0

# need <tool> <gate name> <probe args...>: 0 when the tool answers the probe;
# otherwise the gate is skipped and counted, or fails outright under --dev.
need() {
  local tool="$1" gate="$2"; shift 2
  if command -v "$tool" >/dev/null 2>&1 && "$tool" "$@" >/dev/null 2>&1; then return 0; fi
  if [ "$dev" = 1 ]; then echo "== $gate: $tool is required for --dev" >&2; exit 1; fi
  echo "== $gate: skipped ($tool not installed, or too old to answer)"; skipped=$((skipped+1)); return 1
}

echo "== tests"
python3 -m pytest tests evals/tests -q

echo "== pack lint"
if [ "$dev" = 1 ]; then python3 scripts/lint_pack.py --require-denylist; else python3 scripts/lint_pack.py; fi
if [ "$dev" = 1 ]; then python3 scripts/check_live.py; fi

echo "== agent skills spec (skills-ref 0.1.1)"
command -v uvx >/dev/null 2>&1 || { echo "uv is required (https://docs.astral.sh/uv/)" >&2; exit 1; }
for d in skills/*/; do uvx --from skills-ref==0.1.1 agentskills validate "$d"; done

if need claude "claude plugin validation" --version; then
  echo "== claude plugin validation"
  claude plugin validate --strict .claude-plugin/plugin.json
  claude plugin validate --strict .claude-plugin/marketplace.json
fi

if need gh "gh skill publish preflight" skill --help; then
  echo "== gh skill publish preflight"
  gh skill publish --dry-run
fi

if need gitleaks "secret scan" version; then
  echo "== secret scan"
  gitleaks git --no-banner --redact --exit-code 1 .
fi

if [ "$skipped" = 0 ]; then echo "all gates passed"; else echo "gates passed with $skipped skipped; the maintainer runs them all with --dev"; fi
