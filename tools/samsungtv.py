"""Talk to a Samsung Tizen TV on the home network. Standard library only.

- Discovery: SSDP, then a scan of the local /24 for the TV's REST API (port 8001).
- Device info: GET http://<tv>:8001/api/v2/ (no prompt on the TV).
- Remote keys: Samsung's local remote-control WebSocket (TLS, port 8002). The
  first connection shows an Allow prompt on the TV; the returned token is kept
  in state/token. The WebSocket code is adapted from Glass Home's
  tools/tvremote.py (github.com/victaphu/glass-home-samsung-tv, MIT).
- sdb: Samsung's debug bridge, for the read-only `0 getduid` and
  `0 vd_applist` (Developer Mode only).
"""
import base64
import concurrent.futures
import ipaddress
import json
import os
import shutil
import socket
import ssl
import struct
import subprocess
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
TOKEN_FILE = os.path.join(STATE, "token")
CLIENT_NAME = "Quiet Home setup"


# ---- discovery ---------------------------------------------------------------

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # no packet is sent; this only picks the LAN interface
        return s.getsockname()[0]
    finally:
        s.close()


def device_info(ip, timeout=2.0):
    """The TV's /api/v2/ answer, or None if `ip` isn't a Samsung TV."""
    try:
        with urllib.request.urlopen(f"http://{ip}:8001/api/v2/", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    device = data.get("device") if isinstance(data, dict) else None
    if not isinstance(device, dict) or "Samsung" not in str(data.get("type", "")) + str(device.get("type", "")):
        return None
    return data


def ssdp_candidates(wait=3.0):
    msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\n"
           "MX: 2\r\nST: urn:samsung.com:device:RemoteControlReceiver:1\r\n\r\n").encode()
    found = set()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        s.settimeout(0.5)
        s.sendto(msg, ("239.255.255.250", 1900))
        end = time.time() + wait
        while time.time() < end:
            try:
                _, addr = s.recvfrom(4096)
                found.add(addr[0])
            except socket.timeout:
                continue
    except OSError:
        pass
    finally:
        s.close()
    return found


def port_open(ip, port, timeout=0.4):
    try:
        with socket.create_connection((str(ip), port), timeout=timeout):
            return True
    except OSError:
        return False


def discover(subnet=None, log=print):
    """Returns [(ip, info)] for every Samsung TV found."""
    candidates = ssdp_candidates()
    if subnet is None:
        subnet = ipaddress.ip_network(local_ip() + "/24", strict=False)
    else:
        subnet = ipaddress.ip_network(subnet, strict=False)
    log(f"Scanning {subnet} for Samsung TVs (port 8001)...")
    hosts = list(subnet.hosts()) or [subnet.network_address]
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        for ip, ok in zip(hosts, pool.map(lambda h: port_open(h, 8001), hosts)):
            if ok:
                candidates.add(str(ip))
    found = []
    for ip in sorted(candidates, key=lambda a: ipaddress.ip_address(a)):
        info = device_info(ip)
        if info:
            found.append((ip, info))
    return found


# ---- REST ----------------------------------------------------------------------

def rest(ip, method, path, timeout=5):
    req = urllib.request.Request(f"http://{ip}:8001{path}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def app_status(ip, app_id):
    """{'running': bool, 'visible': bool, ...} or None if the TV doesn't know the app."""
    status, body = rest(ip, "GET", f"/api/v2/applications/{app_id}")
    if status != 200:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


# ---- remote-control WebSocket ---------------------------------------------------

class WebSocket:
    """Just enough of RFC 6455 for the TV: text frames, ping/pong, close."""

    def __init__(self, ip, path, timeout=10):
        ctx = ssl.create_default_context()
        # The TV serves a self-signed certificate on the local network; there is
        # no CA to check it against. Only ever used for the TV's own address.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        raw = socket.create_connection((ip, 8002), timeout=timeout)
        self.sock = ctx.wrap_socket(raw, server_hostname=ip)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f"GET {path} HTTP/1.1\r\nHost: {ip}:8002\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("TV closed the connection during the handshake")
            head += chunk
        head, self.buf = head.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n", 1)[0].decode(errors="replace")
        if " 101 " not in status:
            raise ConnectionError(f"TV refused the WebSocket handshake: {status}")

    def _frame(self, opcode, payload):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            header = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 1 << 16:
            header = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            header = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send_json(self, obj):
        self._frame(0x1, json.dumps(obj).encode())

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("TV closed the connection")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_json(self, deadline):
        # The TV pings regularly, so enforce a hard deadline rather than relying
        # on a per-read timeout that the pings keep resetting.
        message = b""
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise socket.timeout("deadline passed")
            self.sock.settimeout(remaining)
            b1, b2 = self._read(2)
            fin, opcode, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x8:
                raise ConnectionError("TV closed the connection")
            message += payload
            if fin:
                return json.loads(message.decode("utf-8", errors="replace"))

    def close(self):
        try:
            self._frame(0x8, b"")
            self.sock.close()
        except OSError:
            pass


class Remote:
    """Connected remote control. Raises RuntimeError if the TV doesn't allow it."""

    def __init__(self, ip, wait_for_allow=45):
        name = base64.b64encode(CLIENT_NAME.encode()).decode()
        path = f"/api/v2/channels/samsung.remote.control?name={name}"
        token = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                token = f.read().strip() or None
        if token:
            path += f"&token={token}"
        self.ws = WebSocket(ip, path)
        deadline = time.time() + wait_for_allow
        while True:
            try:
                msg = self.ws.recv_json(deadline)
            except socket.timeout:
                self.ws.close()
                raise RuntimeError("No answer from the TV. Choose Allow on the TV's prompt, then retry.")
            event = msg.get("event")
            if event == "ms.channel.connect":
                new_token = (msg.get("data") or {}).get("token")
                if new_token and new_token != token:
                    os.makedirs(STATE, exist_ok=True)
                    with open(TOKEN_FILE, "w") as f:
                        f.write(new_token)
                    os.chmod(TOKEN_FILE, 0o600)
                return
            if event in ("ms.channel.unauthorized", "ms.channel.timeOut"):
                self.ws.close()
                raise RuntimeError(f"The TV refused the connection ({event}). Choose Allow on the TV, then retry.")

    def key(self, name, delay=0.6):
        name = name.upper()
        if not name.startswith("KEY_"):
            name = "KEY_" + name
        self.ws.send_json({"method": "ms.remote.control", "params": {
            "Cmd": "Click", "DataOfCmd": name, "Option": "false", "TypeOfRemote": "SendRemoteKey"}})
        time.sleep(delay)
        return name

    def installed_apps(self, wait=8):
        """Not answered on Tizen 8 and later; returns [] then."""
        self.ws.send_json({"method": "ms.channel.emit",
                           "params": {"event": "ed.installedApp.get", "to": "host"}})
        deadline = time.time() + wait
        while True:
            try:
                msg = self.ws.recv_json(deadline)
            except socket.timeout:
                return []
            if msg.get("event") == "ed.installedApp.get":
                return msg.get("data", {}).get("data", [])

    def close(self):
        self.ws.close()


# ---- sdb (Developer Mode) ------------------------------------------------------

def sdb_path():
    found = shutil.which("sdb")
    if found:
        return found
    candidate = os.path.expanduser("~/tizen-studio/tools/sdb")
    return candidate if os.path.exists(candidate) else None


def sdb(ip, *args, timeout=30):
    """Runs `sdb -s <tv>:26101 <args>`; returns (ok, output)."""
    exe = sdb_path()
    if not exe:
        return False, "sdb not found (install Samsung's Tizen SDK CLI; see docs/INSTALL.md)"
    target = f"{ip}:26101"
    subprocess.run([exe, "connect", target], capture_output=True, text=True, timeout=timeout)
    p = subprocess.run([exe, "-s", target, *args], capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr).strip()
    return p.returncode == 0 and "error" not in out.lower()[:200], out
