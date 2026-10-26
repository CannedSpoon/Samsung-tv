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

  // Resolves to the dock entries that are installed, in config order, each
  // with its app id added. Exact ids are tried first; the full app list (slower)
  // is only read when some entry still needs a name match.
  P.resolveApps = function (defs) {
    var found = defs.map(function (def) {
      for (var i = 0; i < def.ids.length; i++) {
        var info = byId(def.ids[i], MOCK);
        if (info) return info.id;
      }
      return null;
    });
    var needsList = found.some(function (id, i) { return !id && defs[i].names.length; });
    return (needsList ? allApps() : Promise.resolve([])).then(function (list) {
      var taken = {};
      found.forEach(function (id) { if (id) taken[id] = true; });
      var apps = list.filter(function (a) { return a && a.id && a.show !== false; });
      defs.forEach(function (def, i) {
        for (var p = 0; p < def.names.length && !found[i]; p++) {
          var re = new RegExp(def.names[p]);
          for (var j = 0; j < apps.length; j++) {
            if (taken[apps[j].id] || !re.test(norm(apps[j].name))) continue;
            found[i] = apps[j].id;
            taken[apps[j].id] = true;
            break;
          }
        }
      });
      var out = [];
      defs.forEach(function (def, i) {
        if (found[i]) out.push({ label: def.label, color: def.color, accent: def.accent, id: found[i] });
      });
      return out;
    });
  };

  // Opens an installed app; falls back to an app-control launch.
  P.launch = function (id) {
    if (!tz) return new Promise(function (resolve) { setTimeout(function () { resolve('preview'); }, 150); });
    return new Promise(function (resolve, reject) {
      function viaAppControl(firstError) {
        try {
          tz.application.launchAppControl(
            new tz.ApplicationControl('http://tizen.org/appcontrol/operation/default', null, null, null, null),
            id, function () { resolve('appcontrol'); }, function (e) { reject(e || firstError); });
        } catch (e) { reject(e); }
      }
      try { tz.application.launch(id, function () { resolve('launch'); }, viaAppControl); } catch (e) { viaAppControl(e); }
    });
  };

  QH.platform = P;
}());
