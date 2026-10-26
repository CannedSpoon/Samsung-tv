# Copy to scripts/tizen-env.sh (git-ignored) and fill in the first block.
# build.sh, install.sh and uninstall.sh read it. Adapted from Glass Home.

# ---- your setup ------------------------------------------------------------
# The TV's address: taken from `python3 tv.py find` (state/tv.json) unless set here.
export TV_IP="${TV_IP:-$(python3 -c 'import json;print(json.load(open("state/tv.json"))["ip"])' 2>/dev/null)}"
export PROFILE=QuietHome                  # name for your Samsung signing profile
export SKILLS="$HOME/tizen-agent-skills/tizen-sdk-skills"   # git clone of Samsung/tizen-agent-skills
export DUID=                              # your TV's device ID (docs/INSTALL.md, step 5)

# ---- usually left as is ----------------------------------------------------
export TIZEN_HOME="$HOME/tizen-studio"
if [ -f "$TIZEN_HOME/sdk.info" ]; then
  TIZEN_DATA="$(sed -n 's/^TIZEN_SDK_DATA_PATH=//p' "$TIZEN_HOME/sdk.info")"
  export TIZEN_DATA
fi
export TIZEN_DATA="${TIZEN_DATA:-$HOME/tizen-studio-data}"
export PATH="$TIZEN_HOME/tools:$TIZEN_HOME/tools/ide/bin:$PATH"
export TV="$TV_IP:26101"
export CERTCLI="$SKILLS/common/lib/cli/cert-manager-cli.js"
export CA_DIR="$SKILLS/common/assets/samsung-tv-ca"
export CERT_DIR="$TIZEN_DATA/keystore/samsung/$PROFILE"
export APP_ID=QuietHome1.Home
export PKG_ID=QuietHome1
