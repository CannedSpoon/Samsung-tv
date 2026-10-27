"""Samsung's Tizen SDK tools, run the same way on Windows, macOS and Linux.

Finds the `tizen` CLI and `sdb` in the SDK folder, makes the Samsung signing
certificate, and builds, installs and uninstalls Quiet Home. The steps follow
Glass Home's install guide and scripts (github.com/victaphu/glass-home-samsung-tv, MIT).

Settings (all optional) come from environment variables:
  TIZEN_HOME    the SDK folder (default: ~/tizen-studio, or C:\\tizen-studio on Windows)
  TIZEN_SKILLS  the tizen-sdk-skills folder inside a clone of Samsung/tizen-agent-skills
                (default: ~/tizen-agent-skills/tizen-sdk-skills)
  TIZEN_PROFILE the signing profile name (default: QuietHome)
"""
import os
import re
import secrets
import shutil
import string
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHER = os.path.join(ROOT, "launcher")
DIST = os.path.join(ROOT, "dist")
WGT = "QuietHome.wgt"
APP_ID = "QuietHome1.Home"
PKG_ID = "QuietHome1"
WINDOWS = os.name == "nt"
HOME = os.path.expanduser("~")
SECRETS = os.path.join(HOME, ".quiet-home-secrets")
PASSWORD_FILE = os.path.join(SECRETS, "cert-password.env")


class ToolError(Exception):
    pass


def profile():
    return os.environ.get("TIZEN_PROFILE", "QuietHome")


def tizen_home():
    candidates = [os.environ.get("TIZEN_HOME"), os.path.join(HOME, "tizen-studio")]
    if WINDOWS:
        candidates.append(r"C:\tizen-studio")
    for path in candidates:
        if path and os.path.isdir(os.path.join(path, "tools")):
            return path
    return None


def tizen_data():
    home = tizen_home()
    info = os.path.join(home, "sdk.info") if home else None
    if info and os.path.exists(info):
        with open(info, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("TIZEN_SDK_DATA_PATH="):
                    return line.split("=", 1)[1].strip()
    return os.path.join(HOME, "tizen-studio-data")


def _tool(name, subdir):
    found = shutil.which(name)  # on Windows this also finds tizen.bat / sdb.exe through PATHEXT
    if found:
        return found
    home = tizen_home()
    if not home:
        return None
    for ext in ([".bat", ".exe", ""] if WINDOWS else [""]):
        path = os.path.join(home, subdir, name + ext)
        if os.path.exists(path):
            return path
    return None


def sdb_exe():
    return _tool("sdb", "tools")


def tizen_exe():
    return _tool("tizen", os.path.join("tools", "ide", "bin"))


def skills_dir():
    return os.environ.get("TIZEN_SKILLS") or os.path.join(HOME, "tizen-agent-skills", "tizen-sdk-skills")


def cert_dir():
    return os.path.join(tizen_data(), "keystore", "samsung", profile())


def run(cmd, quiet=False, timeout=600, secret=None):
    """Runs a tool, printing its output; raises ToolError if it fails."""
    shown = " ".join(("****" if secret and a == secret else a) for a in cmd)
    print(f"$ {shown}", flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = (p.stdout + p.stderr).strip()
    if out and not quiet:
        print(out, flush=True)
    # The tizen CLI sometimes exits 0 after printing an error, so check its words too.
    if p.returncode != 0 or re.search(r"(?im)^\s*(error|failed|\[error\])", out):
        raise ToolError(out or f"{os.path.basename(cmd[0])} exited with {p.returncode}")
    return out


def need_tizen():
    exe = tizen_exe()
    if not exe:
        raise ToolError("Samsung's Tizen CLI wasn't found. Install it (docs/INSTALL.md, step 2), "
                        "or set TIZEN_HOME to the folder you installed it in.")
    return exe


def need_sdb():
    exe = sdb_exe()
    if not exe:
        raise ToolError("sdb wasn't found. Install Samsung's Tizen CLI (docs/INSTALL.md, step 2), "
                        "or set TIZEN_HOME to the folder you installed it in.")
    return exe


def connect(ip):
    out = run([need_sdb(), "connect", f"{ip}:26101"], quiet=True)
    if "connected" not in out.lower() or "failed" in out.lower():
        raise ToolError(f"sdb couldn't connect to the TV: {out}\nIs Developer Mode on, with this computer's "
                        "address as Host PC IP, and was the TV restarted after turning it on?")
    return f"{ip}:26101"


def duid(ip):
    target = connect(ip)
    out = run([need_sdb(), "-s", target, "shell", "0", "getduid"], quiet=True).strip()
    if not re.fullmatch(r"[A-Za-z0-9]{6,}", out):
        raise ToolError(f"Unexpected device ID from the TV: {out!r}")
    return out


# ---- certificate --------------------------------------------------------------

def password():
    """The certificate password, made once and kept in ~/.quiet-home-secrets (never in the repo)."""
    if not os.path.exists(PASSWORD_FILE):
        os.makedirs(SECRETS, exist_ok=True)
        if not WINDOWS:
            os.chmod(SECRETS, 0o700)
        alphabet = string.ascii_letters + string.digits
        value = "".join(secrets.choice(alphabet) for _ in range(20)) + "Aa1"
        fd = os.open(PASSWORD_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(f"TIZEN_CERTIFICATE_PASSWORD={value}\n")
    with open(PASSWORD_FILE) as f:
        for line in f:
            if line.startswith("TIZEN_CERTIFICATE_PASSWORD="):
                return line.split("=", 1)[1].strip()
    raise ToolError(f"{PASSWORD_FILE} has no TIZEN_CERTIFICATE_PASSWORD line.")


def make_certificate(ip, country, new_tv=False):
    """Samsung author + distributor certificates for this TV, registered as the signing profile.

    The author certificate is made once and never replaced: every update must be signed
    with the same one. The distributor certificate lists the TV's device ID; pass
    new_tv=True to remake it for a different TV.
    """
    tizen = need_tizen()
    node = shutil.which("node")
    if not node:
        raise ToolError("Node.js wasn't found. Install it from nodejs.org (docs/INSTALL.md).")
    cli = os.path.join(skills_dir(), "common", "lib", "cli", "cert-manager-cli.js")
    ca = os.path.join(skills_dir(), "common", "assets", "samsung-tv-ca", "vd_tizen_dev_public2.crt")
    if not os.path.exists(cli):
        raise ToolError(f"Samsung's certificate tool isn't at {cli}. Clone it (docs/INSTALL.md, step 3) "
                        "or set TIZEN_SKILLS.")
    device = duid(ip)
    print(f"TV device ID: {device}")
    pw = password()
    folder = cert_dir()
    author, distributor = os.path.join(folder, "author.p12"), os.path.join(folder, "distributor.p12")

    if os.path.exists(author):
        print(f"Keeping the existing author certificate: {author}")
    else:
        print("Making the author certificate. A Samsung sign-in opens in your browser (5 minutes to finish).")
        run([node, cli, "generate-samsung-author", "--profile-name", profile(), "--identity", "Quiet Home",
             "--country", country.upper(), "--password-file", PASSWORD_FILE])
    if os.path.exists(distributor) and not new_tv:
        print(f"Keeping the existing distributor certificate: {distributor}")
    else:
        run([node, cli, "generate-samsung-distributor", "--profile-name", profile(), "--duid-list", device,
             "--privilege", "Public", "--password-file", PASSWORD_FILE])

    shutil.copy2(ca, folder)
    # The tizen CLI takes the password as an argument; it is masked in what's printed here.
    run([tizen, "security-profiles", "add", "-n", profile(), "-A", "-a", author, "-p", pw,
         "-d", distributor, "-dp", pw, "-dc", os.path.join(folder, os.path.basename(ca))], secret=pw)
    run([tizen, "cli-config", "profiles.path=" + os.path.join(tizen_data(), "profile", "profiles.xml")])
    print(f"\nSigning profile '{profile()}' is ready. Back up {author} and {PASSWORD_FILE}: "
          "updates must be signed with the same author certificate.")


# ---- build / install -----------------------------------------------------------

def build():
    tizen = need_tizen()
    result = os.path.join(LAUNCHER, ".buildResult")
    shutil.rmtree(result, ignore_errors=True)
    try:
        run([tizen, "build-web", "-e", ".*", "-e", "*.md", "-e", "wallpapers/manifest.json", "--", LAUNCHER])
        run([tizen, "package", "-t", "wgt", "-s", profile(), "--", result])
        wgts = sorted((os.path.join(result, f) for f in os.listdir(result) if f.endswith(".wgt")),
                      key=os.path.getmtime)
        if not wgts:
            raise ToolError("tizen package made no .wgt (is the signing profile set up? python tv.py cert)")
        os.makedirs(DIST, exist_ok=True)
        shutil.copy2(wgts[-1], os.path.join(DIST, WGT))
    finally:
        shutil.rmtree(result, ignore_errors=True)
    print(f"Built dist/{WGT}")


def install(ip):
    tizen = need_tizen()
    if not os.path.exists(os.path.join(DIST, WGT)):
        raise ToolError("Nothing to install yet; the build step makes dist/" + WGT)
    target = connect(ip)
    run([tizen, "install-permit", "-s", target])
    run([tizen, "install", "-s", target, "-n", WGT, "--", DIST])
    run([tizen, "run", "-s", target, "-p", APP_ID])


def uninstall(ip):
    run([need_tizen(), "uninstall", "-s", connect(ip), "-p", PKG_ID])


if __name__ == "__main__":
    # Quick check of what was found: python tools/tizen.py
    print("Tizen SDK :", tizen_home())
    print("tizen CLI :", tizen_exe())
    print("sdb       :", sdb_exe())
    print("data      :", tizen_data())
    print("skills    :", skills_dir(), "(found)" if os.path.isdir(skills_dir()) else "(not found)")
    print("profile   :", profile(), "->", cert_dir())
    sys.exit(0)
