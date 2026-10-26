#!/bin/sh
# Removes Quiet Home from the TV (Developer Mode on). Without Developer Mode:
# on the TV, Apps > App Settings (gear) > Quiet Home > Delete.
set -eu
. "$(dirname "$0")/common.sh"
sdb connect "$TV"
tizen uninstall -s "$TV" -p "$PKG_ID"
