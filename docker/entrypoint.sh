#!/usr/bin/env bash
set -euo pipefail

# Source conda from the installed Miniforge location and activate the environment
if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
  # shellcheck source=/dev/null
  . /opt/conda/etc/profile.d/conda.sh
  # Try to activate the env; if activation fails, fall back to running via mamba/conda run
  if conda activate biomni_e1 2>/dev/null; then
    exec "$@"
  fi
fi

# Fallback: if mamba is available, use mamba run
if command -v mamba >/dev/null 2>&1; then
  exec mamba run -n biomni_e1 -- "$@"
fi

# Final fallback: just exec the command
exec "$@"
