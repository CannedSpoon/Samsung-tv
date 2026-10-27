/*
 * Quiet Home - weather under the date, from Open-Meteo (open-meteo.com, free,
 * no key; data CC BY 4.0, credited on screen). Off until a place is set with
 * `python tv.py weather "Your town"`. The last answer is kept, so the TV shows
 * something straight away after a restart.
 */
(function () {
  'use strict';
  var QH = window.QH;
  var cfg = QH.config.weather;
  var CACHE = 'qh.weather.v1';

  // WMO weather codes, shortened.
  var CODES = [[0, 'Clear'], [1, 'Mostly clear'], [2, 'Partly cloudy'], [3, 'Cloudy'], [45, 'Fog'], [48, 'Fog'],
    [51, 'Drizzle'], [53, 'Drizzle'], [55, 'Drizzle'], [56, 'Freezing drizzle'], [57, 'Freezing drizzle'],
    [61, 'Light rain'], [63, 'Rain'], [65, 'Heavy rain'], [66, 'Freezing rain'], [67, 'Freezing rain'],
    [71, 'Light snow'], [73, 'Snow'], [75, 'Heavy snow'], [77, 'Snow'], [80, 'Showers'], [81, 'Showers'],
    [82, 'Heavy showers'], [85, 'Snow showers'], [86, 'Snow showers'], [95, 'Thunderstorm'], [96, 'Thunderstorm'],
    [99, 'Thunderstorm']];
  function describe(code) {
    for (var i = 0; i < CODES.length; i++) if (CODES[i][0] === code) return CODES[i][1];
    return '';
  }

  function url() {
    return 'https://api.open-meteo.com/v1/forecast?latitude=' + cfg.latitude + '&longitude=' + cfg.longitude +
      '&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min' +
      '&timezone=auto&forecast_days=1&temperature_unit=' + (cfg.unit === 'fahrenheit' ? 'fahrenheit' : 'celsius');
  }

  function get() {
    return new Promise(function (resolve) {
      var x = new XMLHttpRequest();
      try {
        x.open('GET', url(), true);
        x.timeout = 10000;
        x.onload = function () {
          try { resolve(x.status === 200 ? JSON.parse(x.responseText) : null); } catch (e) { resolve(null); }
        };
        x.onerror = x.ontimeout = function () { resolve(null); };
        x.send();
      } catch (e) { resolve(null); }
    });
  }

  // "18° Partly cloudy · 21° / 12° · Melbourne", or '' when unknown.
  function text(data) {
    if (!data || !data.current) return '';
    var c = data.current;
    var d = data.daily || {};
    var parts = [Math.round(c.temperature_2m) + '° ' + describe(c.weather_code)];
    if (d.temperature_2m_max && d.temperature_2m_min) {
      parts.push(Math.round(d.temperature_2m_max[0]) + '° / ' + Math.round(d.temperature_2m_min[0]) + '°');
    }
    if (cfg.place) parts.push(cfg.place);
    return parts.join('  ·  ');
  }

  var timer = null;
  QH.weather = {
    enabled: function () { return !!(cfg.enabled && (cfg.latitude || cfg.longitude)); },
    // Calls show(text) now (from the cache) and after every refresh.
    start: function (show) {
      if (!this.enabled()) return;
      var cached = QH.platform.store.get(CACHE);
      if (cached && cached.lat === cfg.latitude && cached.lon === cfg.longitude) show(text(cached.data));
      function refresh() {
        clearTimeout(timer);
        if (document.hidden) return;
        get().then(function (data) {
          if (data) {
            QH.platform.store.set(CACHE, { lat: cfg.latitude, lon: cfg.longitude, data: data });
            show(text(data));
          }
          timer = setTimeout(refresh, cfg.refreshMs);
        });
      }
      refresh();
      document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
    }
  };
}());
