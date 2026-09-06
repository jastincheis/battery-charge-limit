#!/bin/bash
set -euo pipefail

echo "==> Removing CLI"
rm -f "$HOME/.local/bin/battery-charge-limit"

echo "==> Removing udev rule (needs sudo)"
sudo rm -f /etc/udev/rules.d/90-battery-charge-control-permissions.rules
sudo udevadm control --reload

cat << 'EOF'

The battery panel's CHARGE LIMIT buttons are left in place (they're part of
your own ~/.config/omarchy/plugins/<you>.power clone, which you may have
customized further since). To remove them too:

  1. Delete the CHARGE LIMIT section from that plugin's Panel.qml, or
  2. Run `omarchy refresh shell` to reset the whole bar to Omarchy's stock
     config (this discards ANY other bar customizations you've made), or
  3. Delete ~/.config/omarchy/plugins/<you>.power entirely and remove its
     "id" entry from ~/.config/omarchy/shell.json so the bar falls back to
     the built-in omarchy.power widget.
EOF
