#!/usr/bin/env bash
set -e

if command -v micromamba >/dev/null 2>&1; then
  exec micromamba run -n biomni_e1 "$@"
fi

exec "$@"
