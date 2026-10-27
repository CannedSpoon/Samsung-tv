// Glass Home service - image sniffing.  Node 12 API only.
'use strict';

function isJpegStart(buf) {
  return !!buf && buf.length >= 3 && buf[0] === 0xFF && buf[1] === 0xD8 && buf[2] === 0xFF;
}

// Walks the JPEG marker segments up to the first SOFn and returns its size.
// Returns null when the data is not a structurally plausible JPEG.
function jpegSize(buf) {
  if (!isJpegStart(buf)) return null;
  var i = 2;
  while (i + 1 < buf.length) {
    if (buf[i] !== 0xFF) return null;
    var marker = buf[i + 1];
    if (marker === 0xFF) { i += 1; continue; }                          // fill byte
    if (marker === 0x01 || (marker >= 0xD0 && marker <= 0xD8)) { i += 2; continue; }
    if (marker === 0xD9 || marker === 0xDA) return null;                // EOI / SOS before a frame header
    if (i + 4 > buf.length) return null;
    var len = buf.readUInt16BE(i + 2);
    if (len < 2) return null;
    var isSof = marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC;
    if (isSof) {
      if (i + 9 > buf.length) return null;
      var h = buf.readUInt16BE(i + 5);
      var w = buf.readUInt16BE(i + 7);
      return (w > 0 && h > 0) ? { width: w, height: h } : null;
    }
    i += 2 + len;
  }
  return null;
}

function pngSize(buf) {
  if (buf.length < 24) return null;
  if (buf.readUInt32BE(0) !== 0x89504E47 || buf.readUInt32BE(4) !== 0x0D0A1A0A) return null;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

function gifSize(buf) {
  if (buf.length < 10 || buf.toString('ascii', 0, 4) !== 'GIF8') return null;
  return { width: buf.readUInt16LE(6), height: buf.readUInt16LE(8) };
}

function icoSize(buf) {
  if (buf.length < 22 || buf.readUInt16LE(0) !== 0 || buf.readUInt16LE(2) !== 1) return null;
  var n = buf.readUInt16LE(4);
  var best = 0;
  for (var i = 0; i < n && 6 + i * 16 + 16 <= buf.length; i++) {
    var w = buf[6 + i * 16] || 256;
    if (w > best) best = w;
  }
  return best ? { width: best, height: best } : null;
}

function webpSize(buf) {
  if (buf.length < 30 || buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WEBP') return null;
  var chunk = buf.toString('ascii', 12, 16);
  if (chunk === 'VP8X') return { width: 1 + buf.readUIntLE(24, 3), height: 1 + buf.readUIntLE(27, 3) };
  if (chunk === 'VP8 ') return { width: buf.readUInt16LE(26) & 0x3FFF, height: buf.readUInt16LE(28) & 0x3FFF };
  if (chunk === 'VP8L') {
    var b = buf.readUInt32LE(21);
    return { width: (b & 0x3FFF) + 1, height: ((b >> 14) & 0x3FFF) + 1 };
  }
  return { width: 0, height: 0 };
}

// True when `s` (lower-case, trimmed) starts like an SVG document: an optional
// <?xml ...> declaration, any comments, an optional <!doctype svg ...> (and
// comments after it), then "<svg" followed by a space or '>'.
// One left-to-right pass: `i` only moves forward and every indexOf starts at
// `i`, so the cost is linear in the length of `s`. (This used to be a regular
// expression, /^(<\?xml[^>]*>\s*)?(<!--[\s\S]*?-->\s*)*.../, which backtracked
// exponentially: 26 empty comments took about 3 s.)
function looksLikeSvg(s) {
  var i = 0;
  var n = s.length;
  function skipSpace() { while (i < n && /\s/.test(s.charAt(i))) i += 1; }
  function isAt(word) { return s.slice(i, i + word.length) === word; }
  function skipPast(word) {                    // false if `word` does not occur again
    var k = s.indexOf(word, i);
    if (k < 0) return false;
    i = k + word.length;
    skipSpace();
    return true;
  }
  function skipComments() {
    while (isAt('<!--')) {
      i += 4;
      if (!skipPast('-->')) return false;
    }
    return true;
  }
  skipSpace();
  if (isAt('<?xml') && !skipPast('>')) return false;
  if (!skipComments()) return false;
  if (isAt('<!doctype svg') && !(skipPast('>') && skipComments())) return false;
  return isAt('<svg') && /[\s>]/.test(s.charAt(i + 4));
}

// Returns { ext, type, width, height } for the image formats a TV can show,
// or null for anything else (HTML error pages served as icons, etc.).
function sniff(buf) {
  if (!buf || buf.length < 4) return null;
  var s;
  if ((s = pngSize(buf))) return { ext: 'png', type: 'image/png', width: s.width, height: s.height };
  if (isJpegStart(buf)) {
    s = jpegSize(buf) || { width: 0, height: 0 };
    return { ext: 'jpg', type: 'image/jpeg', width: s.width, height: s.height };
  }
  if ((s = gifSize(buf))) return { ext: 'gif', type: 'image/gif', width: s.width, height: s.height };
  if ((s = webpSize(buf))) return { ext: 'webp', type: 'image/webp', width: s.width, height: s.height };
  if ((s = icoSize(buf))) return { ext: 'ico', type: 'image/x-icon', width: s.width, height: s.height };
  var head = buf.slice(0, 512).toString('utf8').replace(/^\uFEFF/, '').trim().toLowerCase();
  if (looksLikeSvg(head)) return { ext: 'svg', type: 'image/svg+xml', width: 512, height: 512 };
  return null;
}

module.exports = { isJpegStart: isJpegStart, jpegSize: jpegSize, sniff: sniff, looksLikeSvg: looksLikeSvg };
