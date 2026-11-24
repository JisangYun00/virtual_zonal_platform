#!/usr/bin/env bash
# Start the zone controller system on the Jetson.
# Usage: bringup/zone_controller.sh [--iface eth0] [--local]
#   --local  run on 127.0.0.x without network setup (any Linux machine, no hardware)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

iface=eth0
subnet=192.168.10
while [ $# -gt 0 ]; do
  case "$1" in
    --iface) iface=${2:?--iface needs an interface name}; shift ;;
    --local) subnet=127.0.0 ;;
    -h|--help) sed -n '2,4p' bringup/zone_controller.sh; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
  || { echo "Python 3.8+ required, found $(python3 --version)" >&2; exit 2; }
[ "$subnet" = 127.0.0 ] || scripts/setup_network.sh zone_controller "$iface"

# exec: Ctrl-C and kill reach Python directly. Add sibling processes (camera) here when they exist.
exec python3 -m zone_controller --subnet "$subnet"  # continues in zone_controller/__main__.py
