#!/usr/bin/env python3
"""Debloat a Samsung Tizen TV and set up Quiet Home, backing up every setting first.

Run these from a computer on the same Wi-Fi as the TV, in order:

  python3 tv.py find            find the TV on the network and remember it
  python3 tv.py pair            connect as a remote (choose Allow on the TV once)
  python3 tv.py backup          record every setting as it is now (changes nothing)
  python3 tv.py debloat         turn off ads, tracking and junk, one step at a time, asking first
  python3 tv.py install         build Quiet Home, install it, check it opens (one-time setup: docs/INSTALL.md)
  python3 tv.py autostart       pin Quiet Home and make the TV start in it
  python3 tv.py restore         undo everything above, from the backup (./restore.sh does the same)

On Windows type `python` instead of `python3`.

Other commands:
  python3 tv.py info            model, firmware, Developer Mode status
  python3 tv.py apps [WORD]     list installed apps and their IDs (for launcher/js/config.js)
  python3 tv.py launch ID...    open an app by ID, to check which ID works on this TV
  python3 tv.py key HOME RIGHT*2   press remote keys (NAME*N repeats)
  python3 tv.py snap NAME       file a photo of the TV into the current backup (optional)
  python3 tv.py status          what the latest backup has recorded and changed
  python3 tv.py restore --only dns     just put the DNS back (if the TV lost internet)
  python3 tv.py doctor          check this computer is ready to install Quiet Home
  python3 tv.py camera          use a webcam to photograph the TV at each step (optional)
  python3 tv.py weather "Town"  show the weather on Quiet Home (then install again)
  python3 tv.py hdmi 1 "Xbox"   name an HDMI tile (then install again)
  python3 tv.py featured KEY    slideshow of what's on your services (free TMDB key; then install)
  python3 tv.py cert --country GB      make the free Samsung signing certificate for this TV
  python3 tv.py install framex  build and install the FrameX TV app (framextv.cc, full screen)
  python3 tv.py uninstall [framex]     remove Quiet Home (or the FrameX TV app)

Checking each step: you confirm what the TV shows, and the TV's own reports are
checked where it gives them (Quiet Home installed, on screen, starting at power-on).
No photos are needed. Optional: point a webcam at the TV and run `python3 tv.py camera`
once, and each step is also photographed automatically (or TV_PHOTOS=ask asks
for a phone photo at each step instead).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import samsungtv as tv  # noqa: E402
import tizen  # noqa: E402
from steps import NOT_HERE, STEPS  # noqa: E402

BACKUPS = os.path.join(HERE, "backups")
TV_FILE = os.path.join(tv.STATE, "tv.json")
LAUNCHER_ID = "QuietHome1.Home"
LAUNCHER_PKG = "QuietHome1"
LOCAL_SETTINGS = os.path.join(tv.STATE, "launcher-settings.json")
LAUNCHER_JS = os.path.join(HERE, "launcher", "js")


# ---- small helpers ---------------------------------------------------------------

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


# Messages name the command to type next; on Windows that's `python`, not `python3`.
PY = "python" if os.name == "nt" else "python3"


def local(text):
    return str(text).replace("python3 ", PY + " ")


def say(text=""):
    print(local(text), flush=True)


def die(text):
    sys.exit(local(text))


def ask(prompt, default=""):
    try:
        answer = input(local(f"{prompt} ")).strip()
    except EOFError:
        answer = ""
    return answer or default


def yes(prompt, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    answer = ask(f"{prompt} {hint}").lower()
    return default if not answer else answer.startswith("y")


def choose(prompt, options):
    say(prompt)
    for i, opt in enumerate(options, 1):
        say(f"  {i}. {opt}")
    while True:
        answer = ask(">")
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        if answer:
            return answer  # free text is fine, it's a record
        say("Type a number, or describe it.")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def the_tv():
    saved = load_json(TV_FILE)
    ip = os.environ.get("TV_IP") or (saved or {}).get("ip")
    if not ip:
        die("No TV yet. Run:  python3 tv.py find")
    return ip


# ---- backup sessions --------------------------------------------------------------

class Session:
    """One folder under backups/: session.json, log.jsonl, photos/, and raw device data."""

    def __init__(self, path):
        self.path = path
        self.file = os.path.join(path, "session.json")
        self.data = load_json(self.file, {"created": now(), "steps": {}})
        os.makedirs(os.path.join(path, "photos"), exist_ok=True)

    @classmethod
    def latest(cls, required=True):
        pointer = os.path.join(BACKUPS, "LATEST")
        name = open(pointer, encoding="utf-8").read().strip() if os.path.exists(pointer) else ""
        if not name or not os.path.isdir(os.path.join(BACKUPS, name)):
            if required:
                die("No backup yet. Run:  python3 tv.py backup")
            return None
        return cls(os.path.join(BACKUPS, name))

    @classmethod
    def new(cls):
        name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        os.makedirs(os.path.join(BACKUPS, name))
        with open(os.path.join(BACKUPS, "LATEST"), "w", encoding="utf-8") as f:
            f.write(name + "\n")
        return cls(os.path.join(BACKUPS, name))

    def step(self, step_id):
        return self.data["steps"].setdefault(step_id, {})

    def save(self):
        save_json(self.file, self.data)

    def log(self, **entry):
        with open(os.path.join(self.path, "log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), **entry}) + "\n")

    def write(self, name, text):
        with open(os.path.join(self.path, name), "w", encoding="utf-8") as f:
            f.write(text)


# ---- photos of the TV ----------------------------------------------------------------

PHONECAM_LATEST = os.path.join(HERE, "photos", "live", "latest.jpg")
CAMERA_FILE = os.path.join(tv.STATE, "camera.json")


def camera_setting():
    """ffmpeg input as 'format:device': TV_CAMERA, else the one `tv.py camera` saved."""
    return os.environ.get("TV_CAMERA") or (load_json(CAMERA_FILE) or {}).get("camera", "")


def capture(camera, out):
    """One frame from a webcam with ffmpeg; returns (ok, error text)."""
    fmt, _, device = camera.partition(":")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", fmt]
    if fmt == "avfoundation":
        cmd += ["-framerate", "30"]
    # Skip the first second so the camera's exposure settles.
    cmd += ["-i", device, "-ss", "1", "-frames:v", "1", out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return p.returncode == 0 and os.path.exists(out), p.stderr.strip()[:300]


def list_cameras():
    """[(label, 'format:device')] for the webcams ffmpeg can see on this computer."""
    if sys.platform.startswith("linux"):
        import glob
        return [(d, "v4l2:" + d) for d in sorted(glob.glob("/dev/video*"))]
    if sys.platform == "darwin":
        cmd, fmt = ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""], "avfoundation"
    else:
        cmd, fmt = ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], "dshow"
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    text = p.stderr
    if fmt == "dshow":
        # Lines like: [dshow @ 0000...] "Integrated Camera" (video)
        names = re.findall(r'"([^"]+)"\s+\(video\)', text)
        return [(n, "dshow:video=" + n) for n in dict.fromkeys(names)]
    video = text.split("audio devices")[0]
    return [(name, f"avfoundation:{idx}") for idx, name in re.findall(r"\[(\d+)\] (.+)", video)]


def snap(session, name, ask_for_one=None):
    """Takes a photo of the TV into the session when a camera is set up; returns its path or None.

    No photos are needed: without a camera this returns None quietly, unless
    ask_for_one (or TV_PHOTOS=ask) asks you to take one with your phone.
    """
    if ask_for_one is None:
        ask_for_one = os.environ.get("TV_PHOTOS", "").lower() == "ask"
    count = len(os.listdir(os.path.join(session.path, "photos")))
    out = os.path.join(session.path, "photos", f"{count + 1:02d}-{name}.jpg")
    camera = camera_setting()
    if camera:
        time.sleep(1.2)  # let the TV finish animating
        ok, err = capture(camera, out)
        if ok:
            say(f"  photo: {os.path.relpath(out, HERE)}")
            session.log(photo=out, source="camera")
            return out
        say(f"  camera failed ({err}); no photo this time.")
    elif os.path.exists(PHONECAM_LATEST) and time.time() - os.path.getmtime(PHONECAM_LATEST) < 10:
        p = subprocess.run([sys.executable, os.path.join(HERE, "tools", "phonecam.py"), "snap", out])
        if p.returncode == 0 and os.path.exists(out):
            say(f"  photo: {os.path.relpath(out, HERE)}")
            session.log(photo=out, source="phonecam")
            return out
    if not ask_for_one:
        return None
    answer = ask("  Take a photo of the TV with your phone now. Then press Enter, "
                 "or drag the photo file here and press Enter to file it:").strip("'\" ")
    if answer and os.path.isfile(answer):
        out = os.path.splitext(out)[0] + os.path.splitext(answer)[1].lower()
        shutil.copy2(answer, out)
        say(f"  photo filed: {os.path.relpath(out, HERE)}")
        session.log(photo=out, source="file")
        return out
    session.log(photo=None, name=name, source="phone, not filed")
    return None


def show_step(step):
    say(f"\n=== {step['title']}")
    say(f"Why: {step['why']}")
    say("Where:")
    for w in step["where"]:
        say(f"  - {w}")
    if step.get("caution"):
        say(f"CAREFUL: {step['caution']}")


def open_keys(ip, step, session):
    keys = step.get("open")
    if not keys:
        return
    try:
        remote = tv.Remote(ip, wait_for_allow=10)
        sent = [remote.key(k) for k in keys]
        remote.close()
        session.log(keys=sent, step=step["id"])
    except (OSError, RuntimeError) as e:
        say(f"  (couldn't press {' '.join(keys)} for you: {e}; use the remote)")


def already_set(step, before):
    norm = lambda s: s.split(" (")[0].strip().lower()
    return norm(before) == norm(step["target"])


# ---- commands --------------------------------------------------------------------------

def cmd_find(args):
    found = tv.discover(args.subnet, log=say)
    if not found:
        die("No Samsung TV answered. Check the TV is on (not standby) and on the same network as this "
                 "computer (not a guest Wi-Fi), or pass --subnet 192.168.x.0/24.")
    for i, (ip, info) in enumerate(found, 1):
        d = info["device"]
        say(f"{i}. {ip}  {d.get('name')}  model {d.get('modelName')}  {d.get('OS', 'Tizen')}  "
            f"Developer Mode {'on (host ' + str(d.get('developerIP')) + ')' if d.get('developerMode') == '1' else 'off'}")
    pick = found[0]
    while len(found) > 1:
        ips = [ip for ip, _ in found]
        answer = choose("Which one is yours?", ips)
        if answer in ips:
            pick = found[ips.index(answer)]
            break
    os.makedirs(tv.STATE, exist_ok=True)
    d = pick[1]["device"]
    save_json(TV_FILE, {"ip": pick[0], "name": d.get("name"), "model": d.get("modelName"),
                        "mac": d.get("wifiMac"), "found": now()})
    say(f"Saved {pick[0]} ({d.get('modelName')}). This computer is {tv.local_ip()}.")
    say("Tip: give the TV a fixed address in your router (DHCP reservation) so it doesn't move.")


def cmd_info(args):
    ip = the_tv()
    info = tv.device_info(ip)
    if not info:
        die(f"{ip} didn't answer as a Samsung TV. Is it on? Run  python3 tv.py find  again.")
    d = info["device"]
    for k in ("name", "modelName", "OS", "firmwareVersion", "PowerState", "developerMode", "developerIP",
              "networkType", "ip", "wifiMac", "TokenAuthSupport"):
        say(f"{k:17} {d.get(k)}")
    if d.get("developerMode") == "1" and d.get("developerIP") != tv.local_ip():
        say(f"\nNote: Developer Mode's Host PC IP is {d.get('developerIP')}, but this computer is "
            f"{tv.local_ip()}. sdb and install need them to match.")


def cmd_pair(args):
    ip = the_tv()
    say("Connecting... choose Allow on the TV if it asks.")
    try:
        remote = tv.Remote(ip)
    except (OSError, RuntimeError) as e:
        die(str(e))
    remote.close()
    say("Paired. The TV will remember this computer.")


def cmd_key(args):
    ip = the_tv()
    try:
        remote = tv.Remote(ip, wait_for_allow=15)
    except (OSError, RuntimeError) as e:
        die(str(e))
    sent = []
    for spec in args.keys:
        name, _, times = spec.partition("*")
        for _ in range(int(times or 1)):
            sent.append(remote.key(name, delay=args.delay))
    remote.close()
    session = Session.latest(required=False)
    if session:
        session.log(keys=sent)
    say("sent: " + " ".join(sent))


def list_apps(ip):
    ok, out = tv.sdb(ip, "shell", "0", "vd_applist")
    if ok and "app_tizen_id" in out:
        return "sdb", out
    try:
        remote = tv.Remote(ip, wait_for_allow=10)
        apps = remote.installed_apps()
        remote.close()
    except (OSError, RuntimeError):
        apps = []
    if apps:
        return "remote", "\n".join(f"{a.get('appId', ''):<32} {a.get('name')}" for a in
                                   sorted(apps, key=lambda a: str(a.get("name")).lower()))
    return None, out


def cmd_apps(args):
    source, text = list_apps(the_tv())
    if not source:
        die("Couldn't list apps. Turn on Developer Mode and install sdb (docs/INSTALL.md); "
                 f"sdb said: {text}")
    rows = []
    if source == "sdb":
        # vd_applist prints a block of `key = value` lines per app; keep the id and title.
        app = {}
        for line in text.splitlines():
            key, _, value = line.strip().partition("=")
            key, value = key.strip(), value.strip()
            if key in ("app_title", "app_tizen_id"):
                if key in app:  # a new block started
                    app = {}
                app[key] = value
                if len(app) == 2:
                    rows.append(f"{app['app_tizen_id']:<40} {app['app_title']}")
                    app = {}
    else:
        rows = text.splitlines()
    word = (args.word or "").lower()
    shown = [r for r in rows if word in r.lower()]
    for row in shown:
        say(row)
    if word and not shown:
        say(f"No app matching '{args.word}'.")


def cmd_launch(args):
    """Open an app by id from this computer: tells whether that id works on this TV."""
    ip = the_tv()
    for app_id in args.app_ids:
        if tv.app_status(ip, app_id) is None:
            say(f"{app_id}: the TV doesn't know this id (not installed, or a different id on this TV).")
            continue
        how = tv.launch_app(ip, app_id)
        say(f"{app_id}: opened ({how})" if how else
            f"{app_id}: installed, but didn't come on screen. Look at the TV; try the next id.")
        if how and len(args.app_ids) > 1:
            ask("Press Enter to try the next one (the TV stays on this app until then):")


def cmd_camera(args):
    """Pick the webcam that photographs the TV at each step, test it, remember it."""
    if args.off:
        if os.path.exists(CAMERA_FILE):
            os.remove(CAMERA_FILE)
        say("Webcam photos are off.")
        return
    if not shutil.which("ffmpeg"):
        die("ffmpeg is needed for webcam photos. Install it, then run this again:\n"
            "  Windows:  winget install Gyan.FFmpeg   (then open a new PowerShell window)\n"
            "  macOS:    brew install ffmpeg\n"
            "  Linux:    sudo apt install ffmpeg")
    cameras = list_cameras()
    if not cameras:
        die("ffmpeg found no webcam. Is it plugged in, and not in use by another app (Teams, Zoom, Camera)?")
    if len(cameras) == 1:
        label, camera = cameras[0]
    else:
        labels = [c[0] for c in cameras]
        answer = choose("Which webcam points at the TV?", labels)
        label, camera = cameras[labels.index(answer)] if answer in labels else cameras[0]
    os.makedirs(tv.STATE, exist_ok=True)
    test = os.path.join(tv.STATE, "camera-test.jpg")
    say(f"Taking a test photo with {label}...")
    ok, err = capture(camera, test)
    if not ok:
        die(f"The test photo failed: {err}\nClose any app using the webcam and try again.")
    save_json(CAMERA_FILE, {"camera": camera, "label": label, "saved": now()})
    say(f"Saved. Test photo: {os.path.relpath(test, HERE)} - open it and check the TV is in view.")
    say("From now on each step is photographed automatically into the backup folder.")
    say("Turn it off with:  python3 tv.py camera --off")


def cmd_snap(args):
    session = Session.latest()
    out = snap(session, args.name, ask_for_one=True)
    if not out:
        say("No photo filed.")


def cmd_backup(args):
    ip = the_tv()
    info = tv.device_info(ip)
    if not info:
        die(f"{ip} didn't answer. Turn the TV on, then retry.")
    session = Session.latest(required=False)
    if session and not args.new and not session.data.get("complete"):
        say(f"Continuing the unfinished backup in {os.path.relpath(session.path, HERE)}")
    else:
        if session and not args.new:
            if not yes(f"A finished backup exists ({os.path.relpath(session.path, HERE)}). Start a new one?"):
                return
        session = Session.new()
    session.data["tv"] = {"ip": ip, "device": info["device"]}
    session.write("device.json", json.dumps(info, indent=2))
    session.save()
    say(f"Backup folder: {os.path.relpath(session.path, HERE)}")
    say(f"TV: {info['device'].get('modelName')}  {info['device'].get('name')}")

    say("\nReading the app list and device ID (read-only)...")
    source, text = list_apps(ip)
    if source:
        session.write("apps.txt", text)
        say(f"  saved apps.txt (via {source})")
    else:
        say("  app list not available yet (needs Developer Mode + sdb); it's read again at install time.")
    ok, duid = tv.sdb(ip, "shell", "0", "getduid")
    if ok:
        session.write("duid.txt", duid + "\n")
        session.data["duid"] = duid.strip()
        say(f"  device ID (DUID): {duid.strip()}")

    if "home_photo" not in session.data:
        open_keys(ip, {"id": "home", "open": ["HOME"]}, session)
        session.data["home_photo"] = snap(session, "home-before")
        session.save()

    say("\nNow each setting, as it is today. Nothing is changed: open the screen with your remote, "
        "tell me what it shows. Press Ctrl-C any time; rerun to continue.")
    for step in STEPS:
        rec = session.step(step["id"])
        if "before" in rec and not args.redo:
            continue
        show_step(step)
        open_keys(ip, step, session)
        before = choose("What is it set to now?", step["options"] + [NOT_HERE])
        if before.startswith("Enter manually"):
            before = "Enter manually: " + ask("Which DNS address is entered?")
        rec.update(before=before, checked=now())
        if before != NOT_HERE:
            rec["before_photo"] = snap(session, f"{step['id']}-before")
        session.save()
        session.log(step=step["id"], before=before)

    open_keys(ip, {"id": "exit", "open": ["EXIT"]}, session)
    session.data["complete"] = now()
    session.save()
    say(f"\nBackup complete: {os.path.relpath(session.path, HERE)}")
    say("Copy that folder somewhere off this computer too (it's what `python3 tv.py restore` uses).")


def run_phase(phase, args):
    ip = the_tv()
    session = Session.latest()
    if not session.data.get("complete"):
        die("The backup isn't finished. Run  python3 tv.py backup  first.")
    for step in STEPS:
        if step["phase"] != phase or (args.only and step["id"] not in args.only):
            continue
        rec = session.step(step["id"])
        before = rec.get("before")
        if before is None:
            die(f"No backed-up value for {step['id']}. Run  python3 tv.py backup --redo")
        if rec.get("applied") and not rec.get("restored"):
            say(f"\n(done already: {step['title']})")
            continue
        if before == NOT_HERE:
            continue
        if already_set(step, before):
            say(f"\n(already as wanted: {step['title']} - it was {before})")
            continue
        show_step(step)
        say(f"Now: {before}   ->   wanted: {step['target']}")
        if not yes("Change it?"):
            rec.update(skipped=now())
            session.save()
            session.log(step=step["id"], skipped=True)
            continue
        open_keys(ip, step, session)
        if ask("Make the change with your remote, then press Enter (or type s to skip):").lower() == "s":
            continue
        after_photo = snap(session, f"{step['id']}-after")
        detail = ask(step["freeform_after"]) if step.get("freeform_after") else ""
        if not yes(f"Does the TV now show: {step['target'].split(':')[0]}?", default=True):
            say("Then leave it as it is; nothing is recorded as changed. You can rerun this step later.")
            session.log(step=step["id"], failed=True, photo=after_photo)
            continue
        rec.update(applied=now(), after=step["target"], after_photo=after_photo, detail=detail)
        rec.pop("restored", None)
        rec.pop("skipped", None)
        session.save()
        session.log(step=step["id"], applied=step["target"], detail=detail)
    open_keys(ip, {"id": "exit", "open": ["EXIT"]}, session)
    cmd_status(args)


def cmd_debloat(args):
    say("Each change is explained first and only made if you say yes. Kept: casting/screen mirroring "
        "and the Samsung TV Plus app. Nothing is uninstalled.")
    run_phase("debloat", args)


def cmd_autostart(args):
    ip = the_tv()
    if tv.app_status(ip, LAUNCHER_ID) is None:
        die("Quiet Home isn't installed yet. Run  python3 tv.py install  first.")
    run_phase("home", args)
    say("\nCheck: open Quiet Home, turn the TV off with the remote, wait 10 s, turn it on.")
    session = Session.latest()
    ask("Press Enter once the TV is back on:")
    status = tv.app_status(ip, LAUNCHER_ID) or {}
    snap(session, "power-on")
    say("Quiet Home is in front." if status.get("visible") else
        "The TV didn't start in Quiet Home. Check Autorun Last App, and that you turned it off from Quiet Home.")
    session.log(check="power-on", visible=bool(status.get("visible")))


def prepare_launcher():
    """Writes the launcher's per-install files (both git-ignored) before a build.

    js/local-key.js: the secret the app and its photo website share; made once.
    js/config.local.js: your settings from `tv.py weather` and `tv.py hdmi`.
    """
    key_file = os.path.join(LAUNCHER_JS, "local-key.js")
    if not os.path.exists(key_file):
        with open(key_file, "w", encoding="utf-8") as f:
            f.write("// Quiet Home - secret shared by this app and its own photo website service.\n"
                    "// Made per install by tv.py, never in git, never served over the network.\n"
                    f"window.GH_LOCAL_KEY = '{secrets.token_urlsafe(32)}';\n")
    local = load_json(LOCAL_SETTINGS, {})
    with open(os.path.join(LAUNCHER_JS, "config.local.js"), "w", encoding="utf-8") as f:
        f.write("// Your settings, written by tv.py (weather, hdmi); not in git. Merged over js/config.js.\n"
                "(function () {\n  var c = window.QH.config;\n"
                f"  var mine = {json.dumps(local, indent=2, ensure_ascii=False)};\n"
                "  Object.keys(mine).forEach(function (k) {\n"
                "    c[k] = mine[k] && typeof mine[k] === 'object' && !Array.isArray(mine[k])\n"
                "      ? Object.assign({}, c[k], mine[k]) : mine[k];\n"
                "  });\n}());\n")


def save_setting(section, values):
    local = load_json(LOCAL_SETTINGS, {})
    local.setdefault(section, {}).update(values)
    os.makedirs(tv.STATE, exist_ok=True)
    save_json(LOCAL_SETTINGS, local)
    prepare_launcher()


def cmd_weather(args):
    if args.off:
        save_setting("weather", {"enabled": False})
        say("Weather is off. Run  python3 tv.py install  to update the TV.")
        return
    if not args.place:
        die('Which town? For example:  python3 tv.py weather "Melbourne"   (or --off)')
    query = urllib.parse.urlencode({"name": args.place, "count": 6, "language": "en", "format": "json"})
    try:
        with urllib.request.urlopen("https://geocoding-api.open-meteo.com/v1/search?" + query, timeout=15) as r:
            found = json.loads(r.read().decode("utf-8")).get("results") or []
    except (OSError, ValueError) as e:
        die(f"Couldn't look up '{args.place}': {e}")
    if not found:
        die(f"No place called '{args.place}'. Try a nearby town, or add the state: \"Ballarat Victoria\".")
    labels = [", ".join(x for x in (p.get("name"), p.get("admin1"), p.get("country")) if x) for p in found]
    pick = found[0]
    if len(found) > 1:
        answer = choose("Which one?", labels)
        if answer in labels:
            pick = found[labels.index(answer)]
    save_setting("weather", {"enabled": True, "place": pick["name"], "unit": "fahrenheit" if args.fahrenheit else "celsius",
                             # two decimals (about 1 km) is plenty, and all that is sent to Open-Meteo
                             "latitude": round(pick["latitude"], 2), "longitude": round(pick["longitude"], 2)})
    say(f"Weather set to {labels[found.index(pick)]}. Run  python3 tv.py install  to update the TV.")


def cmd_featured(args):
    """Featured slideshow: checks the TMDB key, then saves it with the region."""
    if args.off:
        save_setting("featured", {"enabled": False})
        say("Featured is off. Run  python3 tv.py install  to update the TV.")
        return
    if not args.key:
        die("Give your TMDB API key:  python3 tv.py featured YOUR_KEY\n"
            "Get one free: sign up at themoviedb.org, then Settings > API > Create (personal use).\n"
            "Either the 'API Key' or the longer 'API Read Access Token' works.")
    key = args.key.strip()
    url = "https://api.themoviedb.org/3/configuration"
    headers = {}
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    else:
        url += "?api_key=" + urllib.parse.quote(key)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as r:
            ok = r.status == 200
    except urllib.error.HTTPError as e:
        ok = False
        if e.code == 401:
            die("TMDB says that key isn't valid. Copy it again from themoviedb.org > Settings > API.")
    except OSError as e:
        die(f"Couldn't reach TMDB to check the key: {e}")
    if not ok:
        die("TMDB didn't accept the key.")
    region = args.region.upper()
    save_setting("featured", {"enabled": True, "apiKey": key, "region": region,
                              "language": args.language or f"en-{region}"})
    say(f"Featured is on, for what's streaming in {region}. Run  python3 tv.py install  to update the TV.")
    say("On the TV: press Up from the dock to pick a title, Left/Right for more, OK to open its app.")


def cmd_hdmi(args):
    names = load_json(LOCAL_SETTINGS, {}).get("inputs", {}).get("names", {})
    if args.name:
        names[str(args.port)] = args.name
    else:
        names.pop(str(args.port), None)
    save_setting("inputs", {"names": names})
    say((f"HDMI {args.port} is now called \"{args.name}\"." if args.name else f"HDMI {args.port} is back to its plain name.")
        + " Run  python3 tv.py install  to update the TV.")


def cmd_install(args):
    ip = the_tv()
    session = Session.latest()
    app = tizen.APPS[args.app]
    if args.app == "quiethome":
        prepare_launcher()
    try:
        say(f"\n--- Building {app.name}")
        tizen.build(app)
        say("\n--- Installing it on the TV")
        tizen.install(ip, app)
    except (tizen.ToolError, OSError, subprocess.SubprocessError) as e:
        die(f"\n{e}\n\nThat step failed; see docs/INSTALL.md (Troubleshooting).")
    say(f"\nChecking that {app.name} is open on the TV...")
    status = None
    for _ in range(20):
        status = tv.app_status(ip, app.app_id)
        if status and status.get("visible"):
            break
        time.sleep(1)
    snap(session, f"{args.app}-installed")
    ok = bool(status and status.get("visible"))
    session.data.setdefault("apps", {})[args.app] = {"installed": now(), "visible": ok}
    if args.app == "quiethome":
        session.data["launcher"] = {"installed": now(), "visible": ok}
    session.save()
    session.log(install=app.app_id, visible=ok)
    if not ok:
        say("Installed, but the TV doesn't report it on screen. Look at the TV, or open it from Apps.")
    elif args.app == "quiethome":
        say("Quiet Home is installed and on screen. Press Left/Right on the remote and open an app to try it.")
    else:
        say(f"{app.name} is installed and on screen. It's also in Quiet Home's dock (reinstall Quiet Home "
            "if the tile isn't there yet). Press Exit or Home on the remote to leave it.")


def remove_app(ip, session, key):
    """Uninstalls one of this project's apps, by Developer Mode or by hand; True if it's gone."""
    app = tizen.APPS[key]
    try:
        tizen.uninstall(ip, app)
    except (tizen.ToolError, OSError, subprocess.SubprocessError) as e:
        say(f"Couldn't uninstall from here: {e}")
        say(f"On the TV instead: Apps > App Settings (gear) > {app.name} > Delete.")
        ask("Press Enter when done:")
    gone = tv.app_status(ip, app.app_id) is None
    snap(session, f"{key}-removed")
    session.log(uninstall=app.app_id, gone=gone)
    say(f"{app.name} is removed." if gone else f"The TV still lists {app.name}.")
    return gone


def cmd_uninstall(args):
    ip = the_tv()
    session = Session.latest()
    if tv.app_status(ip, tizen.APPS[args.app].app_id) is None:
        say(f"{tizen.APPS[args.app].name} isn't installed.")
        return
    remove_app(ip, session, args.app)


def cmd_cert(args):
    try:
        tizen.make_certificate(the_tv(), args.country, new_tv=args.new_tv)
    except (tizen.ToolError, OSError, subprocess.SubprocessError) as e:
        die(f"\n{e}")


def cmd_doctor(args):
    """What this computer has for installing Quiet Home, and what's missing."""
    checks = [
        ("Python", sys.version.split()[0], True),
        ("Node.js (for the certificate)", shutil.which("node"), bool(shutil.which("node"))),
        ("Tizen SDK", tizen.tizen_home(), bool(tizen.tizen_home())),
        ("tizen CLI", tizen.tizen_exe(), bool(tizen.tizen_exe())),
        ("sdb", tizen.sdb_exe(), bool(tizen.sdb_exe())),
        ("Samsung certificate tool", tizen.skills_dir(), os.path.isdir(tizen.skills_dir())),
        ("OpenSSL (for the certificate)", tizen.openssl_dir() or "not found: comes with Git for Windows",
         bool(tizen.openssl_dir())),
        ("Signing profile '" + tizen.profile() + "'", tizen.cert_dir(),
         os.path.exists(os.path.join(tizen.cert_dir(), "distributor.p12"))),
        ("Webcam photos (optional)", camera_setting() or "off: no photos (not needed)", True),
    ]
    saved = load_json(TV_FILE)
    if saved:
        info = tv.device_info(saved["ip"])
        d = (info or {}).get("device", {})
        checks.append(("TV", f"{saved['ip']} {saved.get('model')}" + ("" if info else " (not answering)"), bool(info)))
        if info:
            dev_ok = d.get("developerMode") == "1" and d.get("developerIP") == tv.local_ip()
            checks.append(("Developer Mode, Host PC IP = this computer",
                           f"{d.get('developerMode')} / {d.get('developerIP')} (this computer: {tv.local_ip()})", dev_ok))
    else:
        checks.append(("TV", "not found yet: python tv.py find", False))
    for name, value, ok in checks:
        say(f"  [{'ok' if ok else '--'}] {name:45} {value}")
    say("\nFor anything marked --, see docs/INSTALL.md.")


def restore_text(step, rec):
    sid, before = step["id"], rec.get("before")
    if sid == "home_row":
        return ("Add these tiles back: Home > Apps > App Settings > the app > Add to Home:\n  "
                + (rec.get("detail") or "(none recorded)"))
    if sid == "pin_launcher":
        return "Home > highlight Quiet Home > hold OK > Remove (from the Home row only)."
    if sid == "dns":
        return f"Set DNS Setting back to: {before}"
    return f"Set it back to: {before}"


def cmd_restore(args):
    ip = the_tv()
    session = Session.latest()
    say(f"Restoring from {os.path.relpath(session.path, HERE)} (taken {session.data.get('created')}).")
    todo = [s for s in reversed(STEPS)
            if session.step(s["id"]).get("applied") and not session.step(s["id"]).get("restored")
            and (not args.only or s["id"] in args.only)]
    # Network first, so the TV has internet for everything else.
    todo.sort(key=lambda s: s["id"] != "dns")
    if not todo:
        say("Nothing to undo: no change is recorded as applied.")
    for step in todo:
        rec = session.step(step["id"])
        show_step(step)
        say(f"Backed-up value: {rec.get('before')}"
            + (f"   (photo: {rec['before_photo']})" if rec.get("before_photo") else ""))
        say("UNDO: " + restore_text(step, rec))
        if not yes("Undo this one now?", default=True):
            continue
        open_keys(ip, step, session)
        ask("Make the change with your remote, then press Enter:")
        photo = snap(session, f"{step['id']}-restored")
        if yes(f"Is it back to: {rec.get('before')}?", default=True):
            rec.update(restored=now(), restored_photo=photo)
            session.save()
            session.log(step=step["id"], restored=rec.get("before"))

    for key, app in tizen.APPS.items():
        if not args.only and tv.app_status(ip, app.app_id) is not None and yes(f"\nUninstall {app.name} too?"):
            remove_app(ip, session, key)
    open_keys(ip, {"id": "exit", "open": ["EXIT"]}, session)
    cmd_status(args)
    say("Developer Mode: if you turned it on, turn it off again (Apps > App Settings > 1 2 3 4 5 > Off, "
        "then restart the TV).")


def cmd_status(args):
    session = Session.latest()
    say(f"\nBackup {os.path.relpath(session.path, HERE)}:")
    for step in STEPS:
        rec = session.data["steps"].get(step["id"], {})
        if rec.get("restored"):
            state = f"restored to {rec.get('before')}"
        elif rec.get("applied"):
            state = f"CHANGED (was {rec.get('before')})"
        elif rec.get("skipped"):
            state = f"kept as {rec.get('before')} (you said no)"
        elif "before" in rec:
            state = f"unchanged: {rec.get('before')}"
        else:
            state = "not checked"
        say(f"  {step['id']:15} {state}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find")
    p.add_argument("--subnet", help="e.g. 192.168.1.0/24 (default: this computer's /24)")
    sub.add_parser("info")
    sub.add_parser("pair")
    p = sub.add_parser("key")
    p.add_argument("keys", nargs="+")
    p.add_argument("--delay", type=float, default=0.6)
    p = sub.add_parser("apps")
    p.add_argument("word", nargs="?", help="only apps whose id or name contains this, e.g. plus")
    p = sub.add_parser("launch")
    p.add_argument("app_ids", nargs="+", metavar="APP_ID")
    p = sub.add_parser("snap")
    p.add_argument("name")
    p = sub.add_parser("backup")
    p.add_argument("--new", action="store_true", help="start a fresh backup folder")
    p.add_argument("--redo", action="store_true", help="re-check steps already recorded")
    for name in ("debloat", "autostart", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--only", nargs="+", metavar="STEP", help="only these step ids (see tv.py status)")
    for name in ("install", "uninstall"):
        p = sub.add_parser(name)
        p.add_argument("app", nargs="?", default="quiethome", choices=sorted(tizen.APPS),
                       help="which app (default: quiethome)")
    sub.add_parser("doctor")
    p = sub.add_parser("weather")
    p.add_argument("place", nargs="?", help='your town, e.g. "Melbourne"')
    p.add_argument("--off", action="store_true")
    p.add_argument("--fahrenheit", action="store_true")
    p = sub.add_parser("featured")
    p.add_argument("key", nargs="?", help="your TMDB API key or read access token")
    p.add_argument("--region", default="AU", help="2-letter country for where-to-watch (default AU)")
    p.add_argument("--language", help="e.g. en-AU (default: en-<region>)")
    p.add_argument("--off", action="store_true")
    p = sub.add_parser("hdmi")
    p.add_argument("port", type=int, help="HDMI port number")
    p.add_argument("name", nargs="?", help='e.g. "PlayStation"; leave out to go back to "HDMI n"')
    p = sub.add_parser("camera")
    p.add_argument("--off", action="store_true", help="stop taking webcam photos")
    p = sub.add_parser("cert")
    p.add_argument("--country", required=True, help="your 2-letter country code, e.g. GB or US")
    p.add_argument("--new-tv", action="store_true", help="remake the distributor certificate for another TV")
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        globals()["cmd_" + args.cmd](args)
    except KeyboardInterrupt:
        say("\nStopped. Everything done so far is saved; rerun to continue.")


if __name__ == "__main__":
    main()
