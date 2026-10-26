#!/bin/sh
# Undo everything tv.py changed, step by step, from the latest backup in backups/.
# Emergency, TV has no internet after the DNS change:  ./restore.sh --only dns
# (or on the TV: Settings > All Settings > Connection > Network > Network Status >
#  IP Settings > DNS Setting > Get automatically > OK).
cd "$(dirname "$0")" && exec python3 tv.py restore "$@"
