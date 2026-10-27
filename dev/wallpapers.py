#!/usr/bin/env python3
"""Regenerates launcher/js/wallpapers.js from launcher/wallpapers/manifest.json.

To add a photo: put a 1920x1080 JPEG in launcher/wallpapers/, add an entry to
manifest.json (file, title, author, licence, source), run this, reinstall.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
manifest = json.load(open(os.path.join(ROOT, "launcher", "wallpapers", "manifest.json"), encoding="utf-8"))
rows = [json.dumps({"file": "wallpapers/" + w["file"], "title": w["title"], "author": w["author"]}) for w in manifest]
with open(os.path.join(ROOT, "launcher", "js", "wallpapers.js"), "w", encoding="utf-8") as f:
    f.write("/* Bundled photos (see CREDITS.md): CC0 1.0 from Wikimedia Commons and Unsplash License.\n"
            "   Generated from wallpapers/manifest.json by dev/wallpapers.py. */\n")
    f.write("window.QH = window.QH || {};\nwindow.QH.wallpapers = [\n  " + ",\n  ".join(rows) + "\n];\n")
print(f"{len(rows)} photos")
