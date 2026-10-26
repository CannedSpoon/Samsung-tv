#!/usr/bin/env python3
# Copied from Glass Home (github.com/victaphu/glass-home-samsung-tv, MIT); unchanged apart from this line.
"""Use an iPhone on the same Wi-Fi as a camera pointed at the TV.

Serves one page over HTTPS with a self-signed certificate (iOS only allows
camera access on secure pages). Open https://<this-mac>:8443 in Safari on the
iPhone, accept the certificate warning, tap Start and aim the back camera at
the TV. The page uploads a frame about once a second; the newest frame is kept
as photos/live/latest.jpg.

  phonecam.py serve             run the server (Ctrl-C to stop)
  phonecam.py snap OUT.jpg      wait for a frame taken after now (+ --settle
                                seconds for TV animations), then copy it to OUT
"""
import argparse
import http.server
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time

TV_IP = os.environ.get("TV_IP", "8.8.8.8")  # only used to pick the LAN interface
PORT = 8443
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIVE = os.path.join(ROOT, "photos", "live")
LATEST = os.path.join(LIVE, "latest.jpg")
CERT_DIR = os.path.join(ROOT, "state", "phonecam-cert")

PAGE = """<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TV camera</title>
<style>
 body{margin:0;background:#000;color:#fff;font:17px -apple-system,system-ui,sans-serif}
 video{width:100vw;height:100vh;object-fit:contain;display:block}
 #bar{position:fixed;left:0;right:0;bottom:0;padding:14px 16px calc(14px + env(safe-area-inset-bottom));
      background:rgba(0,0,0,.65)}
 button{font:600 20px -apple-system,system-ui,sans-serif;padding:12px 22px;border-radius:12px;border:0}
</style></head><body>
<video id="v" playsinline muted autoplay></video>
<div id="bar"><button id="go">Start camera</button>
 <div id="s">Aim the back camera at the TV, then tap Start.</div></div>
<script>
const v = document.getElementById('v'), s = document.getElementById('s'), go = document.getElementById('go');
let sent = 0;
async function keepAwake() {
  try { await navigator.wakeLock.request('screen'); } catch (e) {}
}
async function start() {
  go.disabled = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: false, video: {
      facingMode: {ideal: 'environment'}, width: {ideal: 1920}, height: {ideal: 1080}}});
    v.srcObject = stream;
    await v.play();
    await keepAwake();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') keepAwake();
    });
    go.style.display = 'none';
    loop();
  } catch (e) {
    s.textContent = 'Camera error: ' + e.name + ' ' + e.message;
    go.disabled = false;
  }
}
async function loop() {
  const c = document.createElement('canvas');
  for (;;) {
    if (v.videoWidth) {
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext('2d').drawImage(v, 0, 0);
      const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.82));
      try {
        await fetch('/frame', {method: 'POST', body: blob});
        sent++;
        s.textContent = 'Sending to the Mac: ' + sent + ' frames (' + c.width + 'x' + c.height +
          '). Keep this page open and the phone still.';
      } catch (e) {
        s.textContent = 'Upload failed, retrying: ' + e.message;
      }
    }
    await new Promise(r => setTimeout(r, 1000));
  }
}
go.onclick = start;
</script></body></html>"""


def mac_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((TV_IP, 9))  # no packet is sent; this just picks the LAN interface
        return s.getsockname()[0]
    finally:
        s.close()


def ensure_cert(ip):
    os.makedirs(CERT_DIR, exist_ok=True)
    cert, key = os.path.join(CERT_DIR, "cert.pem"), os.path.join(CERT_DIR, "key.pem")
    if os.path.exists(cert) and os.path.exists(key):
        return cert, key
    conf = os.path.join(CERT_DIR, "openssl.cnf")
    with open(conf, "w") as f:
        f.write("[req]\ndistinguished_name=dn\n[dn]\n[san]\n"
                f"subjectAltName=IP:{ip}\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
                    "-keyout", key, "-out", cert, "-days", "30", "-subj", f"/CN={ip}",
                    "-config", conf, "-extensions", "san"], check=True, capture_output=True)
    os.chmod(key, 0o600)
    return cert, key


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/frame":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 < n < 20_000_000:
            self.send_error(400)
            return
        data = self.rfile.read(n)
        tmp = LATEST + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, LATEST)  # readers never see a half-written frame
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def serve():
    os.makedirs(LIVE, exist_ok=True)
    ip = mac_ip()
    cert, key = ensure_cert(ip)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"Open https://{ip}:{PORT} in Safari on the iPhone", flush=True)
    httpd.serve_forever()


def snap(out, settle, timeout):
    after = time.time() + settle
    deadline = after + timeout
    while time.time() < deadline:
        try:
            if os.path.getmtime(LATEST) > after:
                shutil.copyfile(LATEST, out)
                print(out)
                return
        except FileNotFoundError:
            pass
        time.sleep(0.2)
    sys.exit("No fresh frame from the iPhone. Is the camera page open and the phone awake?")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve")
    s = sub.add_parser("snap")
    s.add_argument("out")
    s.add_argument("--settle", type=float, default=1.2, help="seconds to let the TV finish animating")
    s.add_argument("--timeout", type=float, default=15)
    a = p.parse_args()
    if a.cmd == "serve":
        serve()
    else:
        snap(a.out, a.settle, a.timeout)


if __name__ == "__main__":
    main()
