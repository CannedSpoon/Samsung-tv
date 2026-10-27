// Glass Home service - address checks.  Node 12 API only (runs on the TV).
'use strict';
var os = require('os');

function parseV4(s) {
  var m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(String(s || ''));
  if (!m) return null;
  var p = [+m[1], +m[2], +m[3], +m[4]];
  for (var i = 0; i < 4; i++) if (p[i] > 255) return null;
  return p;
}

function hextets(part) {
  if (part === '') return [];
  var list = part.split(':');
  var out = [];
  for (var i = 0; i < list.length; i++) {
    if (!/^[0-9a-f]{1,4}$/.test(list[i])) return null;
    out.push(parseInt(list[i], 16));
  }
  return out;
}

// '2001:db8::1' -> [0x2001, 0xdb8, 0, 0, 0, 0, 0, 1]. Accepts one '::' and a
// dotted IPv4 tail ('::ffff:192.168.1.5'); null for anything that is not an
// IPv6 address (zones must be stripped first).
function parseV6(addr) {
  var s = String(addr || '').toLowerCase();
  if (s.length > 45 || s.indexOf(':') < 0 || !/^[0-9a-f:.]+$/.test(s)) return null;
  var tail = [];
  var dot = s.indexOf('.');
  if (dot >= 0) {
    var cut = s.lastIndexOf(':');
    if (cut > dot) return null;
    var v4 = parseV4(s.slice(cut + 1));
    if (!v4) return null;
    tail = [v4[0] * 256 + v4[1], v4[2] * 256 + v4[3]];
    s = s.slice(0, cut + 1);
    if (s.slice(-2) !== '::') s = s.slice(0, -1);
  }
  var halves = s.split('::');
  if (halves.length > 2) return null;
  var head = hextets(halves[0]);
  var rest = halves.length === 2 ? hextets(halves[1]) : [];
  if (!head || !rest) return null;
  rest = rest.concat(tail);
  var zeros = 8 - head.length - rest.length;
  if (halves.length === 2 ? zeros < 1 : zeros !== 0) return null;
  while (zeros-- > 0) head.push(0);
  return head.concat(rest);
}

// The IPv4 address inside an IPv4-mapped IPv6 address (::ffff:0:0/96), or null.
function mappedV4(w) {
  if (!w || w[0] || w[1] || w[2] || w[3] || w[4] || w[5] !== 0xffff) return null;
  return [w[6] >> 8, w[6] & 255, w[7] >> 8, w[7] & 255];
}

// An IPv4 address mapped into IPv6, in any spelling ('::ffff:192.168.1.5',
// '::ffff:c0a8:105', '0:0:0:0:0:ffff:192.168.1.5'), becomes that IPv4 address
// ('192.168.1.5'), so every check below judges it as IPv4. Also strips an IPv6
// zone ('fe80::1%wlan0').
function normalize(addr) {
  var a = String(addr || '').toLowerCase();
  var z = a.indexOf('%');
  if (z > 0) a = a.slice(0, z);
  var v4 = a.indexOf(':') >= 0 ? mappedV4(parseV6(a)) : null;
  return v4 ? v4.join('.') : a;
}

function isLoopback(addr) {
  var a = normalize(addr);
  var p = parseV4(a);
  if (p) return p[0] === 127;
  return a === '::1';
}

// Loopback and the private / link-local ranges a home network uses.
function isPrivate(addr) {
  var a = normalize(addr);
  var p = parseV4(a);
  if (p) {
    return p[0] === 10 || p[0] === 127 ||
      (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
      (p[0] === 192 && p[1] === 168) ||
      (p[0] === 169 && p[1] === 254);
  }
  if (a === '::1') return true;
  return /^f[cd][0-9a-f]{2}:/.test(a) || /^fe[89ab][0-9a-f]:/.test(a);
}

function isPublicV4(p) {
  if (p[0] === 0 || p[0] === 10 || p[0] === 127) return false;
  if (p[0] === 100 && p[1] >= 64 && p[1] <= 127) return false;        // CGNAT
  if (p[0] === 169 && p[1] === 254) return false;
  if (p[0] === 172 && p[1] >= 16 && p[1] <= 31) return false;
  if (p[0] === 192 && p[1] === 168) return false;
  if (p[0] === 192 && p[1] === 0 && (p[2] === 0 || p[2] === 2)) return false;
  if (p[0] === 198 && (p[1] === 18 || p[1] === 19)) return false;
  if (p[0] === 198 && p[1] === 51 && p[2] === 100) return false;
  if (p[0] === 203 && p[1] === 0 && p[2] === 113) return false;
  if (p[0] >= 224) return false;                                       // multicast, reserved
  return true;
}

// For outbound fetches (site icons, YouTube): only public unicast addresses,
// so a shortcut can never make the TV probe the home network.
// IPv6 is parsed into numbers (not matched on its spelling) and must be global
// unicast, 2000::/3 (first group 0x2000-0x3fff). That excludes every
// non-global scope: ::, ::1, IPv4-compatible ::a.b.c.d, NAT64 64:ff9b::/96,
// unique-local fc00::/7, link-local fe80::/10, site-local fec0::/10 and
// multicast ff00::/8. Inside 2000::/3 the documentation and IETF-protocol
// blocks are refused too, and 6to4 (2002::/16) is judged by the IPv4 address
// it carries. IPv4-mapped forms were turned into IPv4 by normalize().
function isPublicUnicast(addr) {
  var a = normalize(addr);
  var p = parseV4(a);
  if (p) return isPublicV4(p);
  var w = parseV6(a);
  if (!w) return false;
  if (w[0] < 0x2000 || w[0] > 0x3fff) return false;
  if (w[0] === 0x2001 && w[1] < 0x0200) return false;                   // 2001::/23 IETF (Teredo, benchmarking, ORCHID)
  if (w[0] === 0x2001 && w[1] === 0x0db8) return false;                 // 2001:db8::/32 documentation
  if (w[0] === 0x3fff && w[1] < 0x1000) return false;                   // 3fff::/20 documentation
  if (w[0] === 0x2002) return isPublicV4([w[1] >> 8, w[1] & 255, w[2] >> 8, w[2] & 255]);   // 6to4
  return true;
}

function isIpLiteral(host) {
  var h = String(host || '');
  if (parseV4(h)) return true;
  return h.indexOf(':') >= 0 && /^[0-9a-f:.]+$/i.test(h);
}

// DNS-rebinding guard: the Host header must be an address or a local name.
function hostAllowed(hostHeader) {
  var h = String(hostHeader || '').toLowerCase().trim();
  if (!h) return false;
  if (h.charAt(0) === '[') {
    var end = h.indexOf(']');
    return end > 1 && /^[0-9a-f:.]+$/.test(h.slice(1, end));
  }
  var colon = h.indexOf(':');
  if (colon >= 0) {
    if (!/^\d{1,5}$/.test(h.slice(colon + 1))) return false;
    h = h.slice(0, colon);
  }
  if (parseV4(h)) return true;
  if (h === 'localhost') return true;
  if (/^[a-z0-9-]{1,63}$/.test(h)) return true;                        // single-label name
  return /^[a-z0-9.-]+\.(local|lan|home|home\.arpa|internal|localdomain)$/.test(h);
}

// The TV's own LAN address(es), best first.
function lanAddresses() {
  var out = [];
  var ifs;
  try { ifs = os.networkInterfaces(); } catch (e) { return out; }
  Object.keys(ifs || {}).forEach(function (name) {
    (ifs[name] || []).forEach(function (info) {
      var fam = info.family;
      if (!(fam === 'IPv4' || fam === 4) || info.internal) return;
      if (!isPrivate(info.address) || isLoopback(info.address)) return;
      var score = 0;
      if (/^(wlan|wl|eth|en)/i.test(name)) score += 10;
      if (/^(p2p|docker|br-|veth|tun|tap|virbr)/i.test(name)) score -= 20;
      if (/^192\.168\./.test(info.address)) score += 3;
      else if (/^10\./.test(info.address)) score += 2;
      else if (/^172\./.test(info.address)) score += 1;
      if (/^169\.254\./.test(info.address)) score -= 30;
      if (/^192\.168\.49\./.test(info.address)) score -= 15;          // Wi-Fi Direct group
      out.push({ name: name, address: info.address, score: score });
    });
  });
  out.sort(function (a, b) { return b.score - a.score; });
  return out;
}

module.exports = {
  parseV4: parseV4,
  parseV6: parseV6,
  normalize: normalize,
  isLoopback: isLoopback,
  isPrivate: isPrivate,
  isPublicUnicast: isPublicUnicast,
  isIpLiteral: isIpLiteral,
  hostAllowed: hostAllowed,
  lanAddresses: lanAddresses
};
