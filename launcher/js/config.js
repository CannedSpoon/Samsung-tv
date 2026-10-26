/*
 * Quiet Home - settings. Edit this file, rebuild, reinstall.
 *
 * Dock apps, in order. Each is found at start-up by the Tizen app IDs listed
 * (fast and exact), then by a case-insensitive match on the app's name
 * ("+" reads as " plus", other punctuation is dropped, so "Disney+" is
 * "disney plus"). Apps that aren't installed are left out of the dock.
 * `python3 tv.py apps` lists the real IDs on your TV.
 *
 * `color` is the tile colour. Tiles show the app's name, not its logo: some
 * apps report a poor icon to other apps, and plain tiles load instantly.
 */
(function () {
  'use strict';
  window.QH = window.QH || {};
  window.QH.config = {
    apps: [
      { label: 'Netflix', color: '#141414', accent: '#e50914',
        ids: ['org.tizen.netflix-app'], names: ['^netflix$', '\\bnetflix\\b'] },
      { label: 'YouTube', color: '#1f1f1f', accent: '#ff0033',
        ids: ['9Ur5IzDKqV.TizenYouTube', 'com.samsung.tv.cobalt-yt'], names: ['^youtube$'] },
      { label: 'Prime Video', color: '#0f2a3d', accent: '#1399ff',
        ids: ['org.tizen.primevideo', 'org.tizen.ignition'],
        names: ['^prime video$', '^amazon prime video$', '\\bprime video\\b'] },
      { label: 'Disney+', color: '#0b1d4d', accent: '#3fd0ff',
        ids: ['MCmYXNxgcu.DisneyPlus'], names: ['^disney plus$', '\\bdisney plus\\b'] },
      { label: 'Stremio', color: '#2a1a4a', accent: '#8a5cf6',
        ids: [], names: ['^stremio$', '\\bstremio\\b'] },
      { label: 'TV Plus', color: '#13202e', accent: '#00c2ff',
        ids: ['com.samsung.tv.tvPlusDeeplinker', 'com.samsung.tv.tvplus'],
        names: ['^samsung tv plus$', '^tv plus$'] }
    ],

    // Always last in the dock: Samsung's own home screen, which is the way back
    // to the TV's settings and sources. Don't remove it.
    samsungHome: { label: 'Smart Hub', id: 'com.samsung.tv.csfs' },

    photoIntervalMs: 60000,   // how often the photo changes
    fadeMs: 1800,             // crossfade length
    drift: true,              // slow zoom on each photo; false on a slow TV
    locale: ''                // date/time format, e.g. 'en-GB'; empty uses the TV's
  };
}());
