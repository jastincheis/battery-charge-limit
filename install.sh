#!/bin/bash
# Installs battery-charge-limit:
#   1. the CLI, to ~/.local/bin
#   2. a udev rule so your user (via the 'wheel' group) can write the
#      charge-limit sysfs files without sudo each time
#   3. (Omarchy only) a "CHARGE LIMIT" button row in the battery panel
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Installing CLI"
mkdir -p "$HOME/.local/bin"
install -m 755 bin/battery-charge-limit "$HOME/.local/bin/battery-charge-limit"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "    Note: $HOME/.local/bin isn't on your PATH — add it in your shell rc." ;;
esac

echo "==> Detecting battery device"
DEVICE=""
for f in /sys/class/power_supply/*/charge_control_end_threshold; do
  [[ -e $f ]] || continue
  DEVICE="$(basename "$(dirname "$f")")"
  break
done
if [[ -z $DEVICE ]]; then
  echo "    No power_supply exposes charge_control_end_threshold on this machine."
  echo "    Your battery driver likely doesn't support a charge limit; stopping here."
  exit 1
fi
echo "    Using $DEVICE"

echo "==> Installing udev rule (needs sudo)"
RULE=/etc/udev/rules.d/90-battery-charge-control-permissions.rules
sudo tee "$RULE" > /dev/null << EOF
# Installed by battery-charge-limit: let the wheel group set the battery
# charge limit without root. https://github.com/jastincheis/battery-charge-limit
ACTION=="add|change", SUBSYSTEM=="power_supply", KERNEL=="$DEVICE", \\
  RUN+="/usr/bin/chgrp wheel /sys%p/charge_control_end_threshold /sys%p/charge_control_start_threshold /sys%p/uevent", \\
  RUN+="/usr/bin/chmod g+w /sys%p/charge_control_end_threshold /sys%p/charge_control_start_threshold /sys%p/uevent"
EOF
sudo udevadm control --reload
sudo udevadm trigger --sysname-match="$DEVICE"

if ! groups | grep -qw wheel; then
  echo "    Warning: your user isn't in the 'wheel' group, so the rule above won't"
  echo "    help you. Add yourself with: sudo usermod -aG wheel \$USER (then log out/in)"
fi

if command -v omarchy > /dev/null; then
  echo "==> Adding the charge-limit buttons to the Omarchy battery panel"
  python3 omarchy/patch_panel.py
  echo "==> Restarting the Omarchy shell to load it"
  omarchy restart shell
else
  echo "==> Omarchy not found — skipping panel integration, CLI-only install."
fi

echo
echo "Done. Try: battery-charge-limit 80"
