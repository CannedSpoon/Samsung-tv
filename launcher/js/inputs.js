/*
 * Quiet Home - HDMI input tiles: which ports have something plugged in, and
 * switching the TV to one. Follows Arn0 Launcher's js/inputs.js
 * (github.com/NelsonEU/arn0-tv, MIT): tizen.systeminfo VIDEOSOURCE to list,
 * tizen.tvwindow.setSource to switch, then Samsung's TV viewer to show it.
 */
(function () {
  'use strict';
  var QH = window.QH;
  var tz = typeof window.tizen !== 'undefined' ? window.tizen : null;
  var VIEWER = 'org.tizen.tv-viewer';

  function withTimeout(promise, ms) {
    return new Promise(function (resolve, reject) {
      var t = setTimeout(function () { reject(new Error('timed out')); }, ms);
      promise.then(function (v) { clearTimeout(t); resolve(v); }, function (e) { clearTimeout(t); reject(e); });
    });
  }

  function sources() {
    if (!tz) {
      // Preview: two consoles plugged in.
      return Promise.resolve({ connected: [{ type: 'HDMI', number: 1 }, { type: 'HDMI', number: 2 }],
                               disconnected: [{ type: 'HDMI', number: 3 }] });
    }
    return withTimeout(new Promise(function (resolve, reject) {
      tz.systeminfo.getPropertyValue('VIDEOSOURCE', resolve, reject);
    }), 6000);
  }

  // Resolves to [{ number, connected }] for the TV's HDMI ports, in port order.
  QH.inputs = {
    list: function (showUnplugged) {
      return sources().then(function (info) {
        var ports = {};
        (info.disconnected || []).forEach(function (s) { if (s.type === 'HDMI') ports[s.number] = false; });
        (info.connected || []).forEach(function (s) { if (s.type === 'HDMI') ports[s.number] = true; });
        return Object.keys(ports).map(Number).sort(function (a, b) { return a - b; })
          .filter(function (n) { return ports[n] || showUnplugged; })
          .map(function (n) { return { number: n, connected: ports[n] }; });
      }, function () { return []; });
    },

    open: function (number, method) {
      if (!tz) return Promise.resolve('preview');
      return sources().then(function (info) {
        var all = (info.connected || []).concat(info.disconnected || []);
        var src = null;
        for (var i = 0; i < all.length; i++) if (all[i].type === 'HDMI' && all[i].number === number) src = all[i];
        if (!src) throw new Error('HDMI ' + number + ' is not reported by the TV');
        return withTimeout(new Promise(function (resolve, reject) {
          tz.tvwindow.setSource(src, resolve, reject, 'MAIN');
        }), 8000);
      }).then(function () {
        if (method === 'switch') return 'switched';
        return QH.platform.launch([VIEWER]);
      });
    }
  };
}());
