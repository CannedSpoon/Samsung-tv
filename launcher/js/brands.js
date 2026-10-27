/*
 * Quiet Home - how each tile looks: the app's mark (launcher/img/marks/, made by
 * dev/brands.py) on a background like the app's own icon. `match` is tested
 * against a tile's name and app ids, so HDMI tiles named "PlayStation 5" or
 * "Foxtel" get their brand too. `text` draws a typographic logo instead of a
 * mark; `size` is the mark's height as a share of the tile (wordmarks are wide
 * and thin, so they need more). Idea and several colours from Arn0 Launcher's
 * js/brands.js (github.com/NelsonEU/arn0-tv, MIT).
 */
(function () {
  'use strict';
  var B = [
    { key: 'youtube', match: /youtube|tizentube|cobalt-yt/i, mark: 'youtube', bg: '#ffffff', glow: '#ff0000', size: 46 },
    { key: 'primevideo', match: /prime ?video|primevideo|ignition/i, mark: 'primevideo',
      bg: 'linear-gradient(135deg,#0b2f4f,#1a98ff)', glow: '#1a98ff', size: 78 },
    { key: 'stremio', match: /stremio/i, mark: 'stremio', bg: 'linear-gradient(135deg,#2d2470,#7b5cf0)', glow: '#8f76ff', size: 52 },
    { key: 'framex', match: /framex/i, text: 'FrameX', bg: 'linear-gradient(135deg,#1b1d24,#3a2a6e)', glow: '#9b85ff' },
    { key: 'tvplus', match: /tv ?plus|tvplus/i, text: 'TV Plus', bg: 'linear-gradient(135deg,#071a3d,#1c5fd6)', glow: '#3b8bff' },
    { key: 'smarthub', match: /csfs|smart hub/i, mark: 'samsung', bg: 'linear-gradient(135deg,#0d1c73,#1428a0)', glow: '#3c5cff', size: 92 },
    { key: 'playstation', match: /playstation|\bps[345]\b/i, mark: 'playstation', bg: 'linear-gradient(135deg,#00205c,#0070d1)', glow: '#2b8cff', size: 56 },
    { key: 'xbox', match: /xbox/i, mark: 'xbox', bg: 'linear-gradient(135deg,#0a3a0a,#16a016)', glow: '#3fd03f', size: 54 },
    { key: 'switch', match: /switch|nintendo/i, mark: 'switch', bg: 'linear-gradient(135deg,#b3000e,#ff2a2a)', glow: '#ff4040', size: 54 },
    { key: 'foxtel', match: /foxtel/i, mark: 'foxtel', bg: 'linear-gradient(135deg,#c23c00,#eb5205)', glow: '#ff7a33', size: 80 },
    { key: 'netflix', match: /netflix/i, mark: 'netflix', bg: '#141414', glow: '#e50914', size: 56 },
    { key: 'twitch', match: /twitch/i, mark: 'twitch', bg: '#9146ff', glow: '#b38bff', size: 52 },
    { key: 'plex', match: /plex/i, mark: 'plex', bg: '#1f1f1f', glow: '#ebaf00', size: 52 },
    { key: 'spotify', match: /spotify/i, mark: 'spotify', bg: '#121212', glow: '#1ed760', size: 52 },
    { key: 'appletv', match: /apple ?tv|aria-video/i, mark: 'appletv', bg: '#1c1c1e', glow: '#ffffff', size: 52 },
    { key: 'crunchyroll', match: /crunchyroll/i, mark: 'crunchyroll', bg: '#f47521', glow: '#ff9a55', size: 52 },
    { key: 'kodi', match: /kodi/i, mark: 'kodi', bg: '#17b2e7', glow: '#6fd6ff', size: 52 },
    { key: 'tubi', match: /tubi/i, mark: 'tubi', bg: '#7408ff', glow: '#a35cff', size: 70 },
    { key: 'paramountplus', match: /paramount/i, mark: 'paramountplus', bg: '#0064ff', glow: '#4d94ff', size: 56 }
  ];

  window.QH = window.QH || {};
  window.QH.brands = {
    // The brand for a tile, or null. `text`: its name plus any app ids.
    find: function (text) {
      for (var i = 0; i < B.length; i++) if (B[i].match.test(text)) return B[i];
      return null;
    }
  };
}());
