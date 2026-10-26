#!/usr/bin/env python3
"""Debloat a Samsung Tizen TV and set up Quiet Home, with a backup and a photo of every step.

Run these from a computer on the same Wi-Fi as the TV, in order:

  python3 tv.py find            find the TV on the network and remember it
  python3 tv.py pair            connect as a remote (choose Allow on the TV once)
  python3 tv.py backup          record every setting as it is now, with photos (changes nothing)
  python3 tv.py debloat         turn off ads, tracking and junk, one step at a time, asking first
  python3 tv.py install         build Quiet Home, install it, check it opens (needs docs/INSTALL.md)
  python3 tv.py autostart       pin Quiet Home and make the TV start in it
  ./restore.sh                  undo everything above, from the backup

Other commands:
  python3 tv.py info            model, firmware, Developer Mode status
  python3 tv.py apps            list installed apps and their IDs (for launcher/js/config.js)
  python3 tv.py key HOME RIGHT*2   press remote keys (NAME*N repeats)
  python3 tv.py snap NAME       take a photo of the TV into the current backup
  python3 tv.py status          what the latest backup has recorded and changed
  python3 tv.py restore [--only dns]   same as ./restore.sh

Photos of the TV: Samsung TVs can't send screenshots over the network, so a camera
pointed at the TV stands in. Set TV_CAMERA (see README.md) or run
`python3 tools/phonecam.py serve` and open it on your phone; otherwise you're asked
to take each photo with your phone yourself.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import samsungtv as tv  # noqa: E402
from steps import NOT_HERE, STEPS  # noqa: E402

BACKUPS = os.path.join(HERE, "backups")
TV_FILE = os.path.join(tv.STATE, "tv.json")
LAUNCHER_ID = "QuietHome1.Home"
LAUNCHER_PKG = "QuietHome1"


# ---- small helpers ---------------------------------------------------------------

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def say(text=""):
    print(text, flush=True)


def ask(prompt, default=""):
    try:
        answer = input(f"{prompt} ").strip()
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
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def the_tv():
    saved = load_json(TV_FILE)
    ip = os.environ.get("TV_IP") or (saved or {}).get("ip")
    if not ip:
        sys.exit("No TV yet. Run:  python3 tv.py find")
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
        name = open(pointer).read().strip() if os.path.exists(pointer) else ""
        if not name or not os.path.isdir(os.path.join(BACKUPS, name)):
            if required:
                sys.exit("No backup yet. Run:  python3 tv.py backup")
            return None
        return cls(os.path.join(BACKUPS, name))

    @classmethod
    def new(cls):
        name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        os.makedirs(os.path.join(BACKUPS, name))
        with open(os.path.join(BACKUPS, "LATEST"), "w") as f:
            f.write(name + "\n")
        return cls(os.path.join(BACKUPS, name))

    def step(self, step_id):
        return self.data["steps"].setdefault(step_id, {})

    def save(self):
        save_json(self.file, self.data)

    def log(self, **entry):
        with open(os.path.join(self.path, "log.jsonl"), "a") as f:
            f.write(json.dumps({"at": now(), **entry}) + "\n")

    def write(self, name, text):
        with open(os.path.join(self.path, name), "w") as f:
            f.write(text)


# ---- photos of the TV ----------------------------------------------------------------

PHONECAM_LATEST = os.path.join(HERE, "photos", "live", "latest.jpg")


def snap(session, name):
    """Takes a photo of the TV into the session; returns its path, or a note."""
    count = len(os.listdir(os.path.join(session.path, "photos")))
    out = os.path.join(session.path, "photos", f"{count + 1:02d}-{name}.jpg")
    camera = os.environ.get("TV_CAMERA", "")
    if camera:
        fmt, _, device = camera.partition(":")
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", fmt]
        if fmt == "avfoundation":
            cmd += ["-framerate", "30"]
        # Skip the first second so the camera's exposure settles.
        cmd += ["-i", device, "-ss", "1", "-frames:v", "1", out]
        time.sleep(1.2)  # let the TV finish animating
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0 and os.path.exists(out):
            say(f"  photo: {os.path.relpath(out, HERE)}")
            session.log(photo=out, source="camera")
            return out
        say(f"  camera failed ({p.stderr.strip()[:200]}); falling back to a phone photo.")
    elif os.path.exists(PHONECAM_LATEST) and time.time() - os.path.getmtime(PHONECAM_LATEST) < 10:
        p = subprocess.run([sys.executable, os.path.join(HERE, "tools", "phonecam.py"), "snap", out])
        if p.returncode == 0 and os.path.exists(out):
            say(f"  photo: {os.path.relpath(out, HERE)}")
            session.log(photo=out, source="phonecam")
            return out
    answer = ask("  Take a photo of the TV with your phone now. Then press Enter, "
                 "or drag the photo file here and press Enter to file it:").strip("'\" ")
    if answer and os.path.isfile(answer):
        out = os.path.splitext(out)[0] + os.path.splitext(answer)[1].lower()
        shutil.copy2(answer, out)
        say(f"  photo filed: {os.path.relpath(out, HERE)}")
        session.log(photo=out, source="file")
        return out
    session.log(photo=None, name=name, source="phone, not filed")
    return "taken on phone (not filed)"


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
        sys.exit("No Samsung TV answered. Check the TV is on (not standby) and on the same network as this "
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
        sys.exit(f"{ip} didn't answer as a Samsung TV. Is it on? Run  python3 tv.py find  again.")
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
        sys.exit(str(e))
    remote.close()
    say("Paired. The TV will remember this computer.")


def cmd_key(args):
    ip = the_tv()
    try:
        remote = tv.Remote(ip, wait_for_allow=15)
    except (OSError, RuntimeError) as e:
        sys.exit(str(e))
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
        sys.exit("Couldn't list apps. Turn on Developer Mode and install sdb (docs/INSTALL.md); "
                 f"sdb said: {text}")
    if source == "sdb":
        # vd_applist prints blocks of key = value lines; keep the useful two.
        title = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("app_title"):
                title = line.split("=", 1)[-1].strip()
            elif line.startswith("app_tizen_id"):
                say(f"{line.split('=', 1)[-1].strip():<40} {title}")
    else:
        say(text)


def cmd_snap(args):
    session = Session.latest()
    snap(session, args.name)


def cmd_backup(args):
    ip = the_tv()
    info = tv.device_info(ip)
    if not info:
        sys.exit(f"{ip} didn't answer. Turn the TV on, then retry.")
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
        say("  app list not available yet (needs Developer Mode + sdb); the Home-row photo is the record.")
    ok, duid = tv.sdb(ip, "shell", "0", "getduid")
    if ok:
        session.write("duid.txt", duid + "\n")
        session.data["duid"] = duid.strip()
        say(f"  device ID (DUID): {duid.strip()}")

    if "home_photo" not in session.data:
        say("\nFirst, a photo of the Home screen as it is now.")
        open_keys(ip, {"id": "home", "open": ["HOME"]}, session)
        session.data["home_photo"] = snap(session, "home-before")
        session.save()

    say("\nNow each setting, as it is today. Nothing is changed: open the screen with your remote, "
        "tell me what it shows, and take a photo. Press Ctrl-C any time; rerun to continue.")
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
    say("Copy that folder somewhere off this computer too (it's what ./restore.sh uses).")


def run_phase(phase, args):
    ip = the_tv()
    session = Session.latest()
    if not session.data.get("complete"):
        sys.exit("The backup isn't finished. Run  python3 tv.py backup  first.")
    for step in STEPS:
        if step["phase"] != phase or (args.only and step["id"] not in args.only):
            continue
        rec = session.step(step["id"])
        before = rec.get("before")
        if before is None:
            sys.exit(f"No backed-up value for {step['id']}. Run  python3 tv.py backup --redo")
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
        sys.exit("Quiet Home isn't installed yet. Run  python3 tv.py install  first.")
    run_phase("home", args)
    say("\nCheck: open Quiet Home, turn the TV off with the remote, wait 10 s, turn it on.")
    session = Session.latest()
    ask("Press Enter once the TV is back on:")
    status = tv.app_status(ip, LAUNCHER_ID) or {}
    snap(session, "power-on")
    say("Quiet Home is in front." if status.get("visible") else
        "The TV didn't start in Quiet Home. Check Autorun Last App, and that you turned it off from Quiet Home.")
    session.log(check="power-on", visible=bool(status.get("visible")))


def cmd_install(args):
    ip = the_tv()
    session = Session.latest()
    for script in ("build.sh", "install.sh"):
        say(f"\n--- scripts/{script}")
        if subprocess.run(["sh", os.path.join(HERE, "scripts", script)], env={**os.environ, "TV_IP": ip}).returncode:
            sys.exit(f"scripts/{script} failed; see docs/INSTALL.md (Troubleshooting).")
    say("\nChecking that Quiet Home is open on the TV...")
    status = None
    for _ in range(20):
        status = tv.app_status(ip, LAUNCHER_ID)
        if status and status.get("visible"):
            break
        time.sleep(1)
    snap(session, "launcher-installed")
    ok = bool(status and status.get("visible"))
    session.data["launcher"] = {"installed": now(), "visible": ok}
    session.save()
    session.log(install=LAUNCHER_ID, visible=ok)
    say("Quiet Home is installed and on screen. Press Left/Right on the remote and open an app to try it."
        if ok else "Installed, but the TV doesn't report it on screen. Check the photo / the TV.")


def restore_text(step, rec):
    sid, before = step["id"], rec.get("before")
    if sid == "home_row":
        return ("Add these tiles back: Home > Apps > App Settings > the app > Add to Home:\n  "
                + (rec.get("detail") or "(see the before photo)"))
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
        say(f"Backed-up value: {rec.get('before')}   (photo: {rec.get('before_photo', 'none')})")
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

    if not args.only and tv.app_status(ip, LAUNCHER_ID) is not None and yes("\nUninstall Quiet Home too?"):
        p = subprocess.run(["sh", os.path.join(HERE, "scripts", "uninstall.sh")], env={**os.environ, "TV_IP": ip})
        if p.returncode:
            say("Couldn't uninstall from here. On the TV: Apps > App Settings (gear) > Quiet Home > Delete.")
            ask("Press Enter when done:")
        gone = tv.app_status(ip, LAUNCHER_ID) is None
        snap(session, "launcher-removed")
        session.log(uninstall=LAUNCHER_ID, gone=gone)
        say("Quiet Home is removed." if gone else "The TV still lists Quiet Home.")
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
    sub.add_parser("apps")
    p = sub.add_parser("snap")
    p.add_argument("name")
    p = sub.add_parser("backup")
    p.add_argument("--new", action="store_true", help="start a fresh backup folder")
    p.add_argument("--redo", action="store_true", help="re-check steps already recorded")
    for name in ("debloat", "autostart", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--only", nargs="+", metavar="STEP", help="only these step ids (see tv.py status)")
    sub.add_parser("install")
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        globals()["cmd_" + args.cmd](args)
    except KeyboardInterrupt:
        say("\nStopped. Everything done so far is saved; rerun to continue.")


if __name__ == "__main__":
    main()
