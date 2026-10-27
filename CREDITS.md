# Credits

## Projects this builds on

- [Glass Home](https://github.com/victaphu/glass-home-samsung-tv) (MIT, Glass Home
  contributors): the settings list and DNS filter choice (its
  `docs/SAMSUNG-SETTINGS.md`), the install and signing steps, app matching and the
  launch fallback in `launcher/js/platform.js`, the remote-control WebSocket in
  `tools/samsungtv.py`, `tools/phonecam.py` (copied), the twelve CC0 photos, the
  photo website (`launcher/service/` and `launcher/js/ytparse.js`, copied; only
  the package ID, site name and icons changed), its client in
  `launcher/js/service.js`, the long-press and screensaver handling, and the
  YouTube and website launch methods.
- [Arn0 Launcher](https://github.com/NelsonEU/arn0-tv) (MIT, Arnaud Etienne): the
  Smart Hub escape tile (`com.samsung.tv.csfs`), the rule of always keeping a
  route back to the TV's own menus, HDMI input switching (`launcher/js/inputs.js`)
  and eight photos. Its native Home-button helper is
  deliberately not used: it is untested beyond one TV and firmware.

## Brand marks

`launcher/img/marks/` (made by `dev/brands.py`): from
[Simple Icons](https://simpleicons.org/) 13.21.0 (CC0), and Xbox from Custom
Brand Icons via Arn0 Launcher (MIT); see its `SOURCES.md`. The marks and names
are trademarks of their owners, used only to identify each app or device on its
tile. Tile colours follow Arn0 Launcher's `brands.js` in part.

## Photos

- `nature-*.jpg` (12): CC0 1.0 (public domain) from Wikimedia Commons, as listed
  in Glass Home's credits.
- `unsplash-*.jpg` (8): under the [Unsplash License](https://unsplash.com/license),
  as bundled by Arn0 Launcher.

Titles, photographers and sources for each are in
[`launcher/wallpapers/manifest.json`](launcher/wallpapers/manifest.json).

## Weather

Weather data by [Open-Meteo.com](https://open-meteo.com/), CC BY 4.0 (credited
on screen when weather is on).

## Trademarks

Samsung, Tizen, Smart Hub, Samsung TV Plus, Apple TV, Netflix, YouTube, Prime
Video, Disney+, Stremio and other names belong to their owners. This project
isn't affiliated with any of them.
