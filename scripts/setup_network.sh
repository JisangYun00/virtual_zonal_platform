#!/usr/bin/env bash
# Make sure this device has its fixed addresses. Adds only what is missing (sudo only then),
# so it is safe to rerun. Addresses do not survive a reboot; bringup/ runs this on every start.
# Never touches other interfaces, wlan0, routes, or NetworkManager profiles.
# Usage: scripts/setup_network.sh zone_controller|central <interface>   (list them with `ip -br link`)
set -euo pipefail

usage="usage: setup_network.sh zone_controller|central <interface>"
role=${1:?$usage}
iface=${2:?$usage}

# Same numbers as core/zones.py.
case "$role" in
  central) hosts="1" ;;
  zone_controller) hosts="10 11 12 13 14" ;;  # management, FRONT, REAR, LEFT, RIGHT
  *) echo "$usage" >&2; exit 2 ;;
esac

current=$(ip -4 -o addr show dev "$iface")
sudo=""
[ "$(id -u)" -eq 0 ] || sudo="sudo"
for host in $hosts; do
  if ! grep -q "inet 192.168.10.$host/" <<<"$current"; then
    echo "adding 192.168.10.$host/24 to $iface" >&2
    $sudo ip addr replace "192.168.10.$host/24" dev "$iface"
  fi
done
