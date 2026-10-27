/*
 * Quiet Home - settings. Edit this file, rebuild, reinstall.
 *
 * Dock apps, in order. Each is found at start-up by the Tizen app IDs listed
 * (fast and exact), then by a case-insensitive match on the app's name
 * ("+" reads as " plus", other punctuation is dropped, so "Disney+" is
 * "disney plus"). Apps that aren't installed are left out of the dock.
 * `python3 tv.py apps` lists the real IDs on your TV.
 *
 * Tiles show the app's mark on a background like its own icon (js/brands.js,
 * matched by name). An app with no brand there shows the icon the TV reports
 * for it, or its name on `color`.
 */
(function () {
  'use strict';
  window.QH = window.QH || {};
  window.QH.config = {
    apps: [
      { label: 'YouTube', color: '#1f1f1f', accent: '#ff0033',
        ids: ['9Ur5IzDKqV.TizenYouTube', 'com.samsung.tv.cobalt-yt'], names: ['^youtube$'] },
      { label: 'Prime Video', color: '#0f2a3d', accent: '#1399ff',
        ids: ['org.tizen.primevideo', 'org.tizen.ignition'],
        names: ['^prime video$', '^amazon prime video$', '\\bprime video\\b'] },
      { label: 'Stremio', color: '#2a1a4a', accent: '#8a5cf6',
        ids: [], names: ['^stremio$', '\\bstremio\\b'] },
      { label: 'TV Plus', color: '#13202e', accent: '#00c2ff',
        ids: ['com.samsung.tv.tvplus', 'com.samsung.tv.tvPlusDeeplinker'],
        names: ['^samsung tv plus$', '^tv plus$'] },
      // The full-screen FrameX TV app in apps/framex: python tv.py install framex
      { label: 'FrameX TV', color: '#1b1d24', accent: '#9b85ff',
        ids: ['FrameXTV01.App'], names: ['^framex tv$'] }
    ],

    // Website tiles, after the apps. They open in the TV's own browser
    // ("Internet"), which handles the remote's pointer and video best. E.g.
    //   { label: 'BOM radar', url: 'https://www.bom.gov.au/', color: '#16181d', accent: '#e8e8ea' }
    sites: [],

    // Always last in the dock: Samsung's own home screen, which is the way back
    // to the TV's settings and sources. Don't remove it.
    samsungHome: { label: 'Smart Hub', id: 'com.samsung.tv.csfs' },

    photoIntervalMs: 60000,   // how often the photo changes
    fadeMs: 1800,             // crossfade length
    drift: true,              // slow zoom on each photo; false on a slow TV
    locale: '',               // date/time format, e.g. 'en-GB'; empty uses the TV's

    // HDMI tiles for whatever is plugged in, after the apps. Name them with
    // `python tv.py hdmi 1 "PlayStation"`. 'switch+viewer' switches the TV to the
    // input and opens Samsung's TV viewer; 'switch' only switches.
    inputs: { enabled: true, names: {}, showUnplugged: false, method: 'switch+viewer' },

    // After this long without a button press, only the photos and the clock show.
    // The first press just wakes the screen.
    screensaver: { enabled: true, afterMs: 3 * 60 * 1000 },

    // Darker photos in the evening, by the TV's clock (24-hour).
    night: { enabled: true, from: '21:00', to: '06:00', dim: 0.45 },

    // Weather under the date, from Open-Meteo (free, no account). Off until you
    // set a place: `python tv.py weather "Your town"`. The only internet use.
    weather: { enabled: false, place: '', latitude: 0, longitude: 0, unit: 'celsius', refreshMs: 30 * 60 * 1000 },

    // The + tile: the address and password of the TV's own website, where a
    // phone on your Wi-Fi uploads photos and adds YouTube or website shortcuts.
    photoWebsite: { enabled: true, port: 8090 },

    // Number keys 1-9 on the remote open that dock tile straight away.
    quickKeys: true,

    longPressMs: 700           // hold OK this long for the Move / Hide menu
  };
}());
