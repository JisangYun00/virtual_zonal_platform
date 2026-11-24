#!/usr/bin/env bash
# Start the central controller system on the laptop.
# Usage: bringup/central.sh [--iface IFACE] [--local]
#   --iface  assign 192.168.10.1 to IFACE if missing (find it with `ip -br link`)
#   --local  talk to a zone controller started with --local on this machine
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

iface=""
subnet=192.168.10
while [ $# -gt 0 ]; do
  case "$1" in
    --iface) iface=${2:?--iface needs an interface name}; shift ;;
    --local) subnet=127.0.0 ;;
    -h|--help) sed -n '2,5p' bringup/central.sh; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
  || { echo "Python 3.8+ required, found $(python3 --version)" >&2; exit 2; }
if [ "$subnet" != 127.0.0 ]; then
  if [ -n "$iface" ]; then
    scripts/setup_network.sh central "$iface"
  elif ! ip -4 -o addr | grep -q 'inet 192.168.10.1/'; then
    echo "this machine has no 192.168.10.1; rerun with --iface <name> (see ip -br link)" >&2
    exit 2
  fi
  ping -c 1 -W 1 192.168.10.10 >/dev/null \
    || echo "warning: Jetson management address 192.168.10.10 does not answer ping" >&2
fi

exec python3 -m central --subnet "$subnet"  # continues in central/__main__.py
