#!/usr/bin/env bash
# HungOver — one-command bootstrap for Priority 0.
#   ./setup.sh          # venv + install + env check, then offer to run the smoke test
#   ./setup.sh --smoke  # also run backend/smoke_test.py at the end (non-interactive)
#
# Run this on a PERSONAL machine that can pip install (not the corp pod).
set -euo pipefail
cd "$(dirname "$0")"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓ %s\033[0m\n" "$1"; }
warn() { printf "\033[33m! %s\033[0m\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "HungOver · Cold Case Connector — setup"

# 1. find Python >= 3.10 (Cognee requires it)
PY=""
for c in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || echo 0)
    major=${v%%.*}; minor=${v##*.}
    if [ "${major:-0}" -eq 3 ] && [ "${minor:-0}" -ge 10 ]; then PY="$c"; break; fi
  fi
done
[ -n "$PY" ] || die "Need Python >= 3.10 (Cognee requires it). Install it and re-run."
ok "Python: $("$PY" --version 2>&1) ($PY)"

# 2. virtualenv
if [ ! -d .venv ]; then
  "$PY" -m venv .venv || die "Could not create .venv (need the venv module)."
  ok "Created .venv"
else
  ok ".venv already exists"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. dependencies
bold "Installing dependencies (this can take a few minutes the first time)…"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt || die "pip install failed — see output above."
ok "Dependencies installed"

# 4. .env
if [ ! -f .env ]; then
  cp .env.example .env
  warn "Created .env from template — open it and set LLM_API_KEY."
fi

# 5. key check
set +u; KEY=$(grep -E '^LLM_API_KEY=' .env | cut -d= -f2-); set -u
if [ -z "${KEY// }" ] || [ "${KEY}" = "sk-..." ]; then
  warn "LLM_API_KEY is not set in .env yet."
  echo
  bold "Next step:"
  echo "  1. Edit .env and set LLM_API_KEY=<your key>"
  echo "  2. Re-run:  ./setup.sh --smoke"
  exit 0
fi
ok "LLM_API_KEY is set"

# 6. smoke test (Priority 0)
RUN_SMOKE="ask"
[ "${1:-}" = "--smoke" ] && RUN_SMOKE="yes"
if [ "$RUN_SMOKE" = "ask" ]; then
  printf "\nRun the Priority-0 smoke test now (verifies the live Cognee SDK)? [Y/n] "
  read -r ans || ans="y"
  case "${ans:-y}" in [nN]*) RUN_SMOKE="no";; *) RUN_SMOKE="yes";; esac
fi

if [ "$RUN_SMOKE" = "yes" ]; then
  bold "Running backend/smoke_test.py…"
  python backend/smoke_test.py
  echo
  ok "Smoke test finished — paste its output into docs/API_NOTES.md and pin any # VERIFY in backend/memory_service.py"
else
  echo
  bold "When ready:  source .venv/bin/activate && python backend/smoke_test.py"
fi

echo
bold "After Priority 0, you can run:"
echo "  python demo/demo.py --reset            # the live demo"
echo "  python benchmark/benchmark.py          # the benchmark (or --naive offline)"
echo "  uvicorn backend.main:app --port 8000   # the backend"
