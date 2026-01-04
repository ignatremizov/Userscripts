#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

APP="/Applications/Firefox.app"
RES="$APP/Contents/Resources"
PREF_DIR="$RES/defaults/pref"

rm -f "$PREF_DIR/autoconfig.js"
rm -f "$RES/firefox.cfg"

echo "Removed AutoConfig files from $APP"
echo "Restart Firefox to apply."
