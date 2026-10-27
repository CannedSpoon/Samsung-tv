#!/usr/bin/env python3
"""Writes launcher/img/marks/*.svg: brand marks in the colour each tile shows them.

Marks come from Simple Icons (CC0; trademarks belong to their owners, used only to
identify the app or device on its tile). Xbox comes from Arn0 Launcher's copy of
Custom Brand Icons (MIT). To regenerate:

  npm pack simple-icons@13.21.0 && mkdir si && tar -xzf simple-icons-13.21.0.tgz -C si
  python3 dev/brands.py si/package [path/to/arn0-tv]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "launcher", "img", "marks")

# key: (Simple Icons slug, colour of the mark on its tile)
MARKS = {
    "youtube": ("youtube", "#FF0000"),
    "primevideo": ("primevideo", "#FFFFFF"),
    "stremio": ("stremio", "#FFFFFF"),
    "samsung": ("samsung", "#FFFFFF"),
    "foxtel": ("foxtel", "#FFFFFF"),
    "playstation": ("playstation", "#FFFFFF"),
    "switch": ("nintendoswitch", "#FFFFFF"),
    "twitch": ("twitch", "#FFFFFF"),
    "plex": ("plex", "#EBAF00"),
    "spotify": ("spotify", "#1ED760"),
    "appletv": ("appletv", "#FFFFFF"),
    "crunchyroll": ("crunchyroll", "#FFFFFF"),
    "kodi": ("kodi", "#FFFFFF"),
    "tubi": ("tubi", "#FFFFFF"),
    "paramountplus": ("paramountplus", "#FFFFFF"),
    "netflix": ("netflix", "#E50914"),
}


def recolour(svg, colour):
    svg = re.sub(r"<title>.*?</title>", "", svg)
    svg = re.sub(r'\sfill="[^"]*"', "", svg)
    return svg.replace("<svg ", f'<svg fill="{colour}" ', 1)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    icons = os.path.join(sys.argv[1], "icons")
    os.makedirs(OUT, exist_ok=True)
    sources = ["# Brand marks", "",
               "Trademarks belong to their owners; used here only to identify apps and devices on their tiles.", ""]
    for key, (slug, colour) in MARKS.items():
        with open(os.path.join(icons, slug + ".svg"), encoding="utf-8") as f:
            svg = f.read()
        with open(os.path.join(OUT, key + ".svg"), "w", encoding="utf-8") as f:
            f.write(recolour(svg, colour) + "\n")
        sources.append(f"- {key}.svg: Simple Icons 13.21.0 `{slug}` (CC0)")
    if len(sys.argv) > 2:
        with open(os.path.join(sys.argv[2], "src", "img", "marks", "xbox.svg"), encoding="utf-8") as f:
            svg = f.read()
        with open(os.path.join(OUT, "xbox.svg"), "w", encoding="utf-8") as f:
            f.write(recolour(svg, "#FFFFFF") + "\n")
        sources.append("- xbox.svg: Custom Brand Icons via Arn0 Launcher (MIT)")
    with open(os.path.join(OUT, "SOURCES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sources) + "\n")
    print(f"wrote {len(os.listdir(OUT)) - 1} marks to launcher/img/marks/")


if __name__ == "__main__":
    main()
