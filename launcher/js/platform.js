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
    var found = defs.map(function (def) {
      return def.ids.filter(function (id) { return !!byId(id, MOCK); });
    });
    var needsList = found.some(function (ids, i) { return !ids.length && defs[i].names.length; });
    return (needsList ? allApps() : Promise.resolve([])).then(function (list) {
      var taken = {};
      found.forEach(function (ids) { ids.forEach(function (id) { taken[id] = true; }); });
      var apps = list.filter(function (a) { return a && a.id && a.show !== false; });
      defs.forEach(function (def, i) {
        for (var p = 0; p < def.names.length && !found[i].length; p++) {
          var re = new RegExp(def.names[p]);
          for (var j = 0; j < apps.length; j++) {
            if (taken[apps[j].id] || !re.test(norm(apps[j].name))) continue;
            found[i] = [apps[j].id];
            taken[apps[j].id] = true;
            break;
          }
        }
      });
      var out = [];
      defs.forEach(function (def, i) {
        if (found[i].length) out.push({ label: def.label, color: def.color, accent: def.accent, ids: found[i] });
      });
      return out;
    });
  };

  // Opens one app id: a plain launch, then an app-control launch.
  function launchOne(id) {
    return new Promise(function (resolve, reject) {
      function viaAppControl(firstError) {
        try {
          tz.application.launchAppControl(
            new tz.ApplicationControl('http://tizen.org/appcontrol/operation/default', null, null, null, null),
            id, function () { resolve(id); }, function (e) { reject(e || firstError); });
        } catch (e) { reject(e); }
      }
      try { tz.application.launch(id, function () { resolve(id); }, viaAppControl); } catch (e) { viaAppControl(e); }
    });
  }

  // Opens the first of `ids` that the TV will open. Rejects with the last error.
  P.launch = function (ids) {
    if (!tz) return new Promise(function (resolve) { setTimeout(function () { resolve('preview'); }, 150); });
    var i = 0;
    function next(err) {
      if (i >= ids.length) return Promise.reject(err || new Error('no app id'));
      return launchOne(ids[i++]).then(null, next);
    }
    return next();
  };

  QH.platform = P;
}());
