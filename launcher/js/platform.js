/*
 * Quiet Home - the Tizen calls: find the dock apps and launch them.
 * Off the TV (a desktop browser) it uses a mock app list, so the layout can
 * be previewed. App matching and the launch fallback follow Glass Home
 * (github.com/victaphu/glass-home-samsung-tv, MIT).
 */
(function () {
  'use strict';
  var QH = window.QH;
  var tz = typeof window.tizen !== 'undefined' ? window.tizen : null;
  var P = { isTV: !!tz };

  // "Disney+" -> "disney plus"
  function norm(name) {
    return String(name || '').toLowerCase().replace(/\+/g, ' plus ').replace(/[^a-z0-9]+/g, ' ').trim();
  }

  var MOCK = [
    { id: 'org.tizen.netflix-app', name: 'Netflix' },
    { id: '9Ur5IzDKqV.TizenYouTube', name: 'YouTube' },
    { id: 'org.tizen.primevideo', name: 'Prime Video' },
    { id: 'MCmYXNxgcu.DisneyPlus', name: 'Disney+' },
    { id: 'Stremio0001.Stremio', name: 'Stremio' },
    { id: 'com.samsung.tv.tvplus', name: 'Samsung TV Plus' },
    { id: 'FrameXTV01.App', name: 'FrameX TV' },
    { id: 'com.samsung.tv.csfs', name: 'Smart Hub' }
  ];

  function byId(id, list) {
    if (tz) {
      try { var info = tz.application.getAppInfo(id); return info && info.id ? info : null; } catch (e) { return null; }
    }
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function allApps() {
    if (!tz) return Promise.resolve(MOCK);
    return new Promise(function (resolve) {
      var done = false;
      function finish(list) { if (!done) { done = true; resolve(list || []); } }
      setTimeout(function () { finish([]); }, 4000);
      try { tz.application.getAppsInfo(finish, function () { finish([]); }); } catch (e) { finish([]); }
    });
  }

  // Resolves to the dock entries that are installed, in config order. Each gets
  // `ids`: every listed id that is installed (some apps, like Samsung TV Plus,
  // have more than one and only one of them opens on a given TV), else the
  // first app whose name matches. The full app list (slower) is only read when
  // some entry has no installed id.
  P.resolveApps = function (defs) {
    var icons = [];
    var found = defs.map(function (def, i) {
      return def.ids.filter(function (id) {
        var info = byId(id, MOCK);
        if (info && !icons[i]) icons[i] = info.iconPath || null;
        return !!info;
      });
    });
    var needsList = found.some(function (ids, i) { return (!ids.length || defs[i].searchAll) && defs[i].names.length; });
    return (needsList ? allApps() : Promise.resolve([])).then(function (list) {
      var taken = {};
      found.forEach(function (ids) { ids.forEach(function (id) { taken[id] = true; }); });
      var apps = list.filter(function (a) { return a && a.id && a.show !== false; });
      defs.forEach(function (def, i) {
        // searchAll: also try every installed app whose name matches, after the
        // listed ids (for apps whose id differs between TV models and years).
        if (def.searchAll) {
          apps.forEach(function (a) {
            var hit = def.names.some(function (n) { return new RegExp(n).test(norm(a.name)); });
            if (hit && found[i].indexOf(a.id) < 0) {
              found[i].push(a.id);
              if (!icons[i]) icons[i] = a.iconPath || null;
            }
          });
        }
        for (var p = 0; p < def.names.length && !found[i].length; p++) {
          var re = new RegExp(def.names[p]);
          for (var j = 0; j < apps.length; j++) {
            if (taken[apps[j].id] || !re.test(norm(apps[j].name))) continue;
            found[i] = [apps[j].id];
            icons[i] = apps[j].iconPath || null;
            taken[apps[j].id] = true;
            break;
          }
        }
      });
      var out = [];
      defs.forEach(function (def, i) {
        // fallback: tried last, and only when the app itself was found.
        if (found[i].length && def.fallback) {
          def.fallback.forEach(function (id) { if (found[i].indexOf(id) < 0 && byId(id, MOCK)) found[i].push(id); });
        }
        if (found[i].length) {
          out.push({ label: def.label, color: def.color, accent: def.accent, ids: found[i], icon: iconUrl(icons[i]) });
        }
      });
      return out;
    });
  };

  // The TV reports icons as file paths; some apps report none or a poor one,
  // so tiles only use this when js/brands.js has no mark for the app.
  function iconUrl(path) {
    if (!path) return null;
    var s = String(path);
    if (/^(file|https?|data):/i.test(s)) return s;
    return s.charAt(0) === '/' ? 'file://' + s : s;
  }

  // Resolves true once another app has actually come in front of this one
  // (this page is hidden), false if that hasn't happened within `ms`. Some
  // system apps (Samsung TV Plus on 2020 TVs) accept a launch and then don't
  // appear, so a launch only counts once this confirms it.
  function cameForward(ms) {
    return new Promise(function (resolve) {
      if (document.hidden) { resolve(true); return; }
      var done = false;
      function finish(v) {
        if (done) return;
        done = true;
        document.removeEventListener('visibilitychange', check);
        clearTimeout(timer);
        resolve(v);
      }
      function check() { if (document.hidden) finish(true); }
      var timer = setTimeout(function () { finish(false); }, ms);
      document.addEventListener('visibilitychange', check);
    });
  }

  var SILENT = 'accepted but didn\u2019t come on screen';

  // Opens one app id: a plain launch, or an app-control launch if the plain one
  // is refused; counted only once the app is really on screen. An app that
  // accepts the launch and stays hidden is given up on (no second method).
  function launchOne(id) {
    function attempt(start) {
      return new Promise(function (resolve, reject) {
        try { start(resolve, reject); } catch (e) { reject(e); }
      }).then(function () {
        return cameForward(3500).then(function (ok) {
          if (!ok) throw new Error(SILENT);
          return id;
        });
      });
    }
    return attempt(function (ok, fail) { tz.application.launch(id, ok, fail); }).then(null, function (first) {
      if (first && first.message === SILENT) throw first;
      return attempt(function (ok, fail) {
        tz.application.launchAppControl(
          new tz.ApplicationControl('http://tizen.org/appcontrol/operation/default', null, null, null, null),
          id, ok, fail);
      }).then(null, function (e) { throw e || first; });
    });
  }

  // Opens the first of `ids` that the TV will open; resolves with that id, or
  // rejects with the last error. The id that worked is remembered (under
  // `remember`) and tried first next time, so a slow search happens once.
  P.launch = function (ids, remember) {
    if (!tz) return new Promise(function (resolve) { setTimeout(function () { resolve('preview'); }, 150); });
    var key = remember ? 'qh.works.' + remember : null;
    var known = key && P.store.get(key);
    if (known && ids.indexOf(known) > 0) ids = [known].concat(ids.filter(function (x) { return x !== known; }));
    var i = 0;
    function next(err) {
      if (i >= ids.length) return Promise.reject(err || new Error('no app id'));
      return launchOne(ids[i++]).then(function (id) {
        if (key && id !== known) P.store.set(key, id);
        return id;
      }, next);
    }
    return next();
  };

  var VIEW = 'http://tizen.org/appcontrol/operation/view';

  function viewRequest(appId, uri) {
    return new Promise(function (resolve, reject) {
      try {
        tz.application.launchAppControl(new tz.ApplicationControl(VIEW, uri, null, null, null), appId,
          function () { resolve('view'); }, reject);
      } catch (e) { reject(e); }
    });
  }

  // A YouTube shortcut: the plain watch URL handed to the YouTube app, the form
  // Glass Home found to work from a cold start. Opens YouTube's home if refused.
  P.openYouTube = function (shortcut, youtubeIds) {
    var url = window.GHYouTube ? window.GHYouTube.canonicalUrl(shortcut) : shortcut.url;
    if (!tz) return Promise.resolve('preview ' + url);
    if (!youtubeIds || !youtubeIds.length) return Promise.reject(new Error('YouTube is not installed'));
    return viewRequest(youtubeIds[0], url).then(null, function () { return P.launch(youtubeIds); });
  };

  // A website shortcut, in the TV's own browser ("Internet").
  P.openUrl = function (url) {
    if (!tz) return Promise.resolve('preview ' + url);
    return viewRequest('org.tizen.browser', url).then(null, function () { return viewRequest(null, url); });
  };

  // Lets the number keys reach the page (arrows, OK and Back always do).
  P.registerKeys = function (names) {
    if (!tz || !tz.tvinputdevice) return;
    names.forEach(function (n) { try { tz.tvinputdevice.registerKey(n); } catch (e) { /* not on this remote */ } });
  };

  // Small settings kept on the TV (dock order, hidden tiles), in localStorage.
  P.store = {
    get: function (k) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked */ } }
  };

  QH.platform = P;
}());
