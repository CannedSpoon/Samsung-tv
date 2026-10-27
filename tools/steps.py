"""The TV changes, in the order they're applied. Restore undoes them in reverse.

Samsung TVs don't let a computer change these settings (no API, and sdb on a
retail TV has no access to them), and blind key sequences are unsafe: menus
differ by model and year, and Factory Data Reset sits one item below Start
Screen Options. So each step is done by hand with the remote while the script
records the value before, the value after, and a photo of each.

Kept on purpose (you use them): screen mirroring / casting (SmartThings,
AirPlay), and the Samsung TV Plus app itself. Nothing is uninstalled. Not
included because they can't be undone: Reset PSID, disagreeing to Smart Hub
terms (that disables every app), Reset Smart Hub, Factory Data Reset.

Fields:
  id, title, why     shown to you
  where              menu paths; the first that matches your TV
  target             the value to set
  options            what the setting can be now ("Not on this TV" is always added)
  phase              'debloat' (tv.py debloat) or 'home' (tv.py autostart)
  open               keys sent to the TV to get you started (optional)
  caution            shown before the step (optional)
"""

PRIVACY = [
    "Home > left menu > Privacy Choices",
    "Settings > All Settings > General & Privacy > Terms & Privacy > Privacy Choices",
    "Settings > Support > Terms & Policy (2019-2021 TVs)",
]

STEPS = [
    {
        "id": "acr",
        "title": "Viewing Information Services: off",
        "why": "Content recognition (ACR). It fingerprints whatever is on screen, HDMI inputs included, "
               "and reports it for advertising. It also costs CPU.",
        "where": PRIVACY,
        "target": "Off (unticked)",
        "options": ["On (ticked)", "Off (unticked)"],
        "phase": "debloat",
    },
    {
        "id": "ads",
        "title": "Interest-Based Advertisements: off",
        "why": "Personalised ads on the Home screen built from your viewing profile.",
        "where": PRIVACY,
        "target": "Off (unticked)",
        "options": ["On (ticked)", "Off (unticked)"],
        "phase": "debloat",
    },
    {
        "id": "voice_terms",
        "title": "Voice Recognition Services: off",
        "why": "Sends voice recordings to Samsung/partners. You said you don't use the voice assistant. "
               "The remote's mic button stops working until this is turned back on.",
        "where": PRIVACY,
        "target": "Off (unticked)",
        "options": ["On (ticked)", "Off (unticked)"],
        "phase": "debloat",
    },
    {
        "id": "voice_wake",
        "title": "Voice Wake-up (\"Hi Bixby\"): off",
        "why": "Stops the TV's built-in microphone listening for a wake word.",
        "where": [
            "Settings > All Settings > General & Privacy > Voice > Voice Wake-up",
            "Settings > General > Voice > Voice Wake-up",
        ],
        "target": "Off",
        "options": ["On", "Off"],
        "phase": "debloat",
    },
    {
        "id": "promo",
        "title": "Samsung Promotion notifications: off",
        "why": "Pop-up adverts for Samsung offers and apps.",
        "where": [
            "Settings > Notification (just above All Settings) > gear icon > Samsung Promotion",
            "Settings > All Settings > General & Privacy > Notifications > Samsung Promotion",
        ],
        "target": "Off (unticked)",
        "options": ["On (ticked)", "Off (unticked)"],
        "phase": "debloat",
    },
    {
        "id": "tvplus_autorun",
        "title": "Autorun Samsung TV Plus: off",
        "why": "Stops the TV opening the free-channels app (and its ads) at power-on. "
               "The TV Plus app stays installed and stays in your dock.",
        "where": [
            "Settings > All Settings > General & Privacy > Start Screen Options > Autorun Samsung TV Plus",
            "Settings > General > Smart Features > Autorun Samsung TV Plus",
        ],
        "target": "Off",
        "options": ["On", "Off"],
        "phase": "debloat",
        "caution": "Factory Data Reset is near Start Screen Options. Don't press OK on anything else here.",
    },
    {
        "id": "autoplay",
        "title": "Home-screen video previews and sound: off",
        "why": "Trailers that autoplay on the Home screen are adverts, and they make the Home screen slow.",
        "where": [
            "Home > For You tab > scroll to the very bottom > Media Options > Autoplay Sound / Autoplay Video",
            "Settings > All Settings > General & Privacy > Start Screen Options > Autorun Preview",
            "Settings > General > Smart Features > Autoplay Sound / Autorun Preview",
        ],
        "target": "Off",
        "options": ["On", "Off"],
        "phase": "debloat",
    },
    {
        "id": "home_row",
        "title": "Tidy the Home row (remove tiles, uninstall nothing)",
        "why": "Removes tiles you don't use (for example Gaming Hub, Ambient/Art, e-Manual, "
               "promoted apps) so the Home row loads faster. The apps stay installed.",
        "where": [
            "Home > highlight a tile > hold OK (or press Down) > Remove. NOT \"Delete\".",
        ],
        "target": "Unused tiles removed",
        "options": ["As in the Home-screen photo"],
        "phase": "debloat",
        "freeform_after": "Which tiles did you remove? (comma-separated, for the restore list)",
        "caution": "Use Remove, never Delete. Delete uninstalls the app.",
        "open": ["HOME"],
    },
    {
        "id": "dns",
        "title": "Ad and tracker blocking DNS: 76.76.2.37",
        "why": "Blocks Samsung's ad servers, content-recognition hosts and log uploads for the whole TV. "
               "76.76.2.37 is Control D's free no-log \"HaGeZi Light\" filter; Glass Home tested that "
               "firmware updates, the app store, your Samsung account, Samsung TV Plus, YouTube, Netflix, "
               "Prime Video and Disney+ keep working. It does not remove ads inside videos.",
        "where": [
            "Settings > All Settings > Connection > Network > Network Status > IP Settings > DNS Setting",
            "Settings > General > Network > Network Status > IP Settings > DNS Setting",
        ],
        "target": "Enter manually: 76.76.2.37 (leave IP Setting on automatic)",
        "options": ["Get automatically", "Enter manually (type the address)"],
        "phase": "debloat",
        "caution": "The TV takes one DNS server. If the TV loses internet but your other devices don't, "
                   "set DNS Setting back to Get automatically (or run: python3 tv.py restore --only dns).",
    },
    {
        "id": "pin_launcher",
        "title": "Pin Quiet Home first on the Home row",
        "why": "So Samsung's Home button lands one press from Quiet Home.",
        "where": [
            "Home > Apps > App Settings (gear) > Quiet Home > Add to Home, then Left to move it first, OK",
        ],
        "target": "Pinned first",
        "options": ["Not pinned"],
        "phase": "home",
    },
    {
        "id": "start_smarthub",
        "title": "Start with Smart Hub Home: off",
        "why": "Otherwise the TV opens Samsung's Home at power-on instead of the last app (Quiet Home).",
        "where": [
            "Settings > All Settings > General & Privacy > Start Screen Options > Start with Smart Hub Home",
            "Settings > All Settings > General & Privacy > Advanced Features (Tizen 9 / One UI)",
            "Settings > General > Smart Features > Autorun Smart Hub",
        ],
        "target": "Off",
        "options": ["On", "Off"],
        "phase": "home",
        "caution": "Factory Data Reset is near Start Screen Options. Don't press OK on anything else here.",
    },
    {
        "id": "autorun_last",
        "title": "Autorun Last App: on",
        "why": "The TV reopens the last app at power-on. Turn the TV off from Quiet Home to start in it.",
        "where": [
            "Settings > All Settings > General & Privacy > Start Screen Options > Autorun Last App",
            "Settings > General > Smart Features > Autorun Last App",
        ],
        "target": "On",
        "options": ["On", "Off"],
        "phase": "home",
    },
]

NOT_HERE = "Not on this TV"
