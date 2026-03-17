#!/bin/zsh
set -euo pipefail

PLIST_SRC="/Users/yuekuoming/lvyou/scripts/ai.openclaw.gateway.system.plist"
PLIST_DST="/Library/LaunchDaemons/ai.openclaw.gateway.system.plist"

launchctl bootout gui/501/ai.openclaw.gateway >/dev/null 2>&1 || true
launchctl bootout system/ai.openclaw.gateway.system >/dev/null 2>&1 || true

pkill -f openclaw-gateway >/dev/null 2>&1 || true

cp "$PLIST_SRC" "$PLIST_DST"
chown root:wheel "$PLIST_DST"
chmod 644 "$PLIST_DST"

launchctl bootstrap system "$PLIST_DST"
launchctl kickstart -k system/ai.openclaw.gateway.system

launchctl print system/ai.openclaw.gateway.system | sed -n '1,160p'
