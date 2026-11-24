#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
subnet=192.168.10
if [ "${1:-}" = "--local" ]; then subnet=127.0.0; fi
exec python3 -m central.dashboard --subnet "$subnet"
