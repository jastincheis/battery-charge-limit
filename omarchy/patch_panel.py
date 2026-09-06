#!/usr/bin/env python3
"""
Adds a CHARGE LIMIT slider to the user's Omarchy power panel plugin.

Omarchy has no plugin API for extending a built-in panel, so this works the
way Omarchy itself recommends for customizing a built-in widget: clone it
into ~/.config/omarchy/plugins/ (`omarchy plugin clone omarchy.power`, which
survives `omarchy update`), then edit the clone. This script does that clone
(if you don't already have one) and inserts the same snippets you'd
otherwise add by hand, matched against exact anchor text so it fails loudly
instead of corrupting the file if a future Omarchy version has changed the
panel's source around those anchors.

Safe to re-run: it no-ops if the CHARGE LIMIT section is already present.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

PLUGINS_DIR = Path.home() / ".config" / "omarchy" / "plugins"
MARKER = "CHARGE LIMIT"

FUNC_ANCHOR_OLD = '''  function setProfile(profile) {
    if (!profile || actionProc.running) return
    actionProc.command = ["omarchy-powerprofiles-set", root.discharging ? "battery" : "ac", profile]
    actionProc.running = true
  }'''

FUNC_ANCHOR_NEW = FUNC_ANCHOR_OLD + '''

  // The end threshold, parsed out of "N%" or "start-N%" — omarchy-battery-status
  // reports this whenever the sysfs attribute exists, not just while holding,
  // so it reflects the configured limit even mid-charge.
  readonly property int currentChargeLimit: {
    var t = root.batteryInfo.threshold
    if (!t) return 100
    var end = t.indexOf("-") >= 0 ? t.split("-")[1] : t
    var n = parseInt(end, 10)
    return isNaN(n) ? 100 : n
  }

  function setChargeLimit(percent) {
    if (limitProc.running) return
    limitProc.command = ["battery-charge-limit", percent >= 100 ? "off" : String(percent)]
    limitProc.running = true
  }'''

PROC_ANCHOR_OLD = '''  Process {
    id: actionProc
    onExited: root.refresh()
  }'''

PROC_ANCHOR_NEW = PROC_ANCHOR_OLD + '''

  Process {
    id: limitProc
    onExited: root.refresh()
  }'''

ROW_ANCHOR_OLD = '''                onHovered: function(h) {
                  if (h) {
                    root.cursorActive = true
                    root.profileIndex = index
                  }
                }
              }
            }
          }
        }
      }
    }
  }'''

ROW_ANCHOR_NEW = '''                onHovered: function(h) {
                  if (h) {
                    root.cursorActive = true
                    root.profileIndex = index
                  }
                }
              }
            }
          }
        }

        // ---------- Charge limit slider ----------
        PanelSeparator {
          foreground: root.bar.foreground
        }

        Column {
          width: parent.width
          spacing: Style.space(6)

          Item {
            width: parent.width
            implicitHeight: Math.max(limitHeader.implicitHeight, limitPercent.implicitHeight)

            PanelSectionHeader {
              id: limitHeader
              text: "CHARGE LIMIT"
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              anchors.left: parent.left
              anchors.verticalCenter: parent.verticalCenter
            }

            Text {
              id: limitPercent
              text: Math.round(chargeLimitSlider.dragging ? chargeLimitSlider.liveValue : root.currentChargeLimit) + "%"
              color: Qt.darker(root.bar.foreground, 1.4)
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
            }
          }

          PanelSlider {
            id: chargeLimitSlider
            bar: root.bar
            width: parent.width
            minimum: 20
            maximum: 100
            step: 5
            integer: true
            tickCount: 5
            value: root.currentChargeLimit
            onReleased: function(v) { root.setChargeLimit(Math.round(v)) }
          }
        }
      }
    }
  }'''


def find_existing_clone():
    if not PLUGINS_DIR.is_dir():
        return None
    for manifest_path in PLUGINS_DIR.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if manifest.get("omarchy", {}).get("clonedFrom") == "omarchy.power":
            return manifest_path.parent
    return None


def clone_power_panel():
    result = subprocess.run(
        ["omarchy", "plugin", "clone", "omarchy.power"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"omarchy plugin clone omarchy.power failed:\n{result.stderr}")
    match = re.search(r"Cloned omarchy\.power to (\S+)", result.stdout)
    if not match:
        sys.exit(f"Couldn't parse clone output:\n{result.stdout}")
    return Path(match.group(1))


def apply(old, new, text, label):
    if new in text:
        return text, False
    if old not in text:
        sys.exit(
            f"battery-charge-limit: couldn't find the {label} anchor in Panel.qml.\n"
            "Your Omarchy version's power panel has likely changed shape since this "
            "was written — patch it by hand (see README) instead of guessing."
        )
    return text.replace(old, new, 1), True


def main():
    plugin_dir = find_existing_clone()
    if plugin_dir is None:
        plugin_dir = clone_power_panel()
        print(f"Cloned omarchy.power to {plugin_dir}")
    else:
        print(f"Found existing power panel clone at {plugin_dir}")

    panel_qml = plugin_dir / "Panel.qml"
    text = panel_qml.read_text()

    if MARKER in text:
        print("Charge limit section already present — nothing to do.")
        return

    text, _ = apply(FUNC_ANCHOR_OLD, FUNC_ANCHOR_NEW, text, "setProfile function")
    text, _ = apply(PROC_ANCHOR_OLD, PROC_ANCHOR_NEW, text, "actionProc Process")
    text, changed = apply(ROW_ANCHOR_OLD, ROW_ANCHOR_NEW, text, "profile picker Row")

    panel_qml.write_text(text)
    print(f"Patched {panel_qml}")


if __name__ == "__main__":
    main()
