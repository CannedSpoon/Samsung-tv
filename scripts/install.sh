#!/bin/sh
# Installs dist/QuietHome.wgt on the TV (Developer Mode on) and opens it.
set -eu
. "$(dirname "$0")/common.sh"
[ -f dist/QuietHome.wgt ] || { echo "Run scripts/build.sh first." >&2; exit 66; }
sdb connect "$TV"
tizen install-permit -s "$TV"
tizen install -s "$TV" -n QuietHome.wgt -- "$root/dist"
tizen run -s "$TV" -p "$APP_ID"
