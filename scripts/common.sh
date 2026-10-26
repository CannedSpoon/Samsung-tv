# Shared by build.sh, install.sh and uninstall.sh.
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
[ -f scripts/tizen-env.sh ] || { echo "Copy scripts/tizen-env.example.sh to scripts/tizen-env.sh and fill it in first (docs/INSTALL.md)." >&2; exit 64; }
. scripts/tizen-env.sh
command -v tizen >/dev/null || { echo "The Tizen CLI is not on PATH; see docs/INSTALL.md, step 2." >&2; exit 69; }
[ -n "$TV_IP" ] || { echo "No TV address. Run: python3 tv.py find" >&2; exit 64; }
