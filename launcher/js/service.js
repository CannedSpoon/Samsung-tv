/*
 * Quiet Home - client for the TV's own photo website (service/, Glass Home's
 * service). Adapted from Glass Home's js/data.js
 * (github.com/victaphu/glass-home-samsung-tv, MIT).
 *
 * Talks to http://127.0.0.1:<port> with the package's local key (js/local-key.js,
 * made per install by tv.py, never in git). The website password is never
 * stored by the app: it is shown only while the service reports it.
 */
(function () {
  'use strict';
  var QH = window.QH;
  var cfg = QH.config.photoWebsite;
  var tz = typeof window.tizen !== 'undefined' ? window.tizen : null;
  var base = 'http://127.0.0.1:' + cfg.port;
  var key = window.GH_LOCAL_KEY || '';
  var CACHE = 'qh.website.v1';
  var state = QH.platform.store.get(CACHE);
  var password = null;   // { id, plain }: memory only

  // XMLHttpRequest rather than fetch: fetch isn't allowed from the app's file:// page.
  function request(method, path, body) {
    return new Promise(function (resolve) {
      var x = new XMLHttpRequest();
      var url = base + path + (path.indexOf('?') >= 0 ? '&' : '?') + 'k=' + encodeURIComponent(key);
      function done(status) {
        var data = null;
        try { data = x.responseText ? JSON.parse(x.responseText) : null; } catch (e) { data = null; }
        resolve({ status: status, data: data });
      }
      try {
        x.open(method, url, true);
        x.timeout = 6000;
        if (body) x.setRequestHeader('Content-Type', 'application/json');
        x.onload = function () { done(x.status); };
        x.onerror = x.ontimeout = function () { done(0); };
        x.send(body ? JSON.stringify(body) : null);
      } catch (e) { resolve({ status: 0, data: null }); }
    });
  }

  var S = { online: false };

  // Starts the service (it keeps running after the app is closed; after a TV
  // restart the app starts it again).
  S.start = function () {
    if (!tz || !cfg.enabled) return;
    var id = 'QuietHome1.Photos';
    try { id = tz.application.getCurrentApplication().appInfo.packageId + '.Photos'; } catch (e) { /* default */ }
    try {
      tz.application.launchAppControl(new tz.ApplicationControl('http://tizen.org/appcontrol/operation/service'),
        id, function () {}, function () { try { tz.application.launch(id); } catch (e) { /* shown as offline */ } });
    } catch (e) { /* shown as offline */ }
  };

  S.cached = function () { return state; };

  // Resolves to true when the state changed (new photos or shortcuts).
  S.refresh = function () {
    if (!cfg.enabled || !key) return Promise.resolve(false);
    var since = password && state && state.rev ? '?rev=' + state.rev : '';
    return request('GET', '/local/state' + since).then(function (r) {
      S.online = r.status === 200 && !!r.data;
      if (!S.online) return false;
      if (r.data.same) { state.lan = r.data.lan; return false; }
      if (r.data.password && r.data.password.plain) password = { id: r.data.password.id, plain: r.data.password.plain };
      state = r.data;
      var slim = JSON.parse(JSON.stringify(state));
      if (slim.password) slim.password.plain = null;
      QH.platform.store.set(CACHE, slim);
      return true;
    });
  };

  S.photos = function () {
    return ((state && state.photos) || []).map(function (p) {
      return { file: base + p.url + '?k=' + encodeURIComponent(key), title: '', user: true, id: p.id };
    });
  };

  // A file the service serves (e.g. a website shortcut's icon), with the key.
  S.media = function (path) { return base + path + '?k=' + encodeURIComponent(key); };

  S.shortcuts = function () { return (state && state.shortcuts) || []; };

  // What the + panel shows: { url, password, note }.
  S.panel = function () {
    if (!cfg.enabled) return { note: 'The photo website is off (photoWebsite in js/config.js).' };
    if (!key) return { note: 'This build has no local key. Reinstall with python tv.py install.' };
    if (!S.online) return { note: 'The photo website is starting… (if this stays, the TV may not support it).' };
    var pw = state && state.password;
    var shown = pw && password && password.id === pw.id ? password.plain : null;
    return {
      url: state && state.lan && state.lan.url,
      password: shown,
      note: shown ? '' : 'Choose New password to show a password here.'
    };
  };

  S.newPassword = function () {
    return request('POST', '/local/password', {}).then(function (r) {
      if (r.status !== 200 || !r.data || !r.data.plain) throw new Error('service');
      password = { id: r.data.id, plain: r.data.plain };
      if (state) state.password = { id: r.data.id, generated: true };
    });
  };

  S.removeShortcut = function (id) {
    return request('DELETE', '/local/shortcuts/' + encodeURIComponent(id)).then(function (r) {
      if (r.status !== 200) throw new Error('service');
      if (state) state.shortcuts = (state.shortcuts || []).filter(function (s) { return s.id !== id; });
    });
  };

  QH.service = S;
}());
