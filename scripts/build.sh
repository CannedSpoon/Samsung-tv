#!/bin/sh
# Builds and signs dist/QuietHome.wgt with your Samsung certificate profile.
set -eu
. "$(dirname "$0")/common.sh"
rm -rf launcher/.buildResult
tizen build-web -e ".*" -e "*.md" -e "wallpapers/manifest.json" -- "$root/launcher"
tizen package -t wgt -s "$PROFILE" -- "$root/launcher/.buildResult"
mkdir -p dist
cp "$(ls -t launcher/.buildResult/*.wgt | head -1)" dist/QuietHome.wgt
rm -rf launcher/.buildResult
echo "Built dist/QuietHome.wgt"
