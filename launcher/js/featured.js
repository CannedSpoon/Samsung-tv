/*
 * Quiet Home - Featured: popular films and series on your services, for the
 * background slideshow, with each title's logo and where to watch it.
 *
 * Data from TMDB (themoviedb.org; free API key, set with `python tv.py
 * featured KEY`). Where to watch comes from TMDB's watch providers, which are
 * JustWatch data. Both are credited on screen while Featured shows. For each
 * provider in config, one "discover" request per type lists what's popular on
 * it in your region; then one request per title fetches its logo. Kept for a
 * day, so the TV asks again at most daily.
 */
(function () {
  'use strict';
  var QH = window.QH;
  var cfg = QH.config.featured;
  var API = 'https://api.themoviedb.org/3';
  var IMG = 'https://image.tmdb.org/t/p/';
  var CACHE = 'qh.featured.v1';
  var DAY = 24 * 3600 * 1000;

  // TMDB takes a v3 key as ?api_key=, or a v4 read token (starts "eyJ") as a header.
  function get(path) {
    return new Promise(function (resolve) {
      var key = cfg.apiKey || '';
      var bearer = /^eyJ/.test(key);
      var url = API + path + (bearer ? '' : (path.indexOf('?') < 0 ? '?' : '&') + 'api_key=' + encodeURIComponent(key));
      var x = new XMLHttpRequest();
      try {
        x.open('GET', url, true);
        if (bearer) x.setRequestHeader('Authorization', 'Bearer ' + key);
        x.timeout = 10000;
        x.onload = function () {
          try { resolve(x.status === 200 ? JSON.parse(x.responseText) : null); } catch (e) { resolve(null); }
        };
        x.onerror = x.ontimeout = function () { resolve(null); };
        x.send();
      } catch (e) { resolve(null); }
    });
  }

  function discover(type, provider) {
    return get('/discover/' + type + '?watch_region=' + cfg.region + '&with_watch_providers=' + provider.tmdb.join('|') +
      '&with_watch_monetization_types=flatrate%7Cfree%7Cads&sort_by=popularity.desc&include_adult=false' +
      '&language=' + encodeURIComponent(cfg.language) + '&page=1').then(function (d) {
      return ((d && d.results) || []).filter(function (r) { return r.backdrop_path; }).map(function (r) {
        return { id: r.id, type: type, provider: provider, r: r };
      });
    });
  }

  // The title's logo: in the TV's language, else English, else any; PNGs first.
  function logo(item) {
    var lang = String(cfg.language).split('-')[0];
    return get('/' + item.type + '/' + item.id + '/images?include_image_language=' + lang + ',en,null').then(function (d) {
      var logos = (d && d.logos) || [];
      logos.sort(function (a, b) {
        function rank(l) { return (l.iso_639_1 === lang ? 0 : l.iso_639_1 === 'en' ? 1 : 2) * 10 - (l.file_path.slice(-4) === '.png' ? 1 : 0); }
        return rank(a) - rank(b) || (b.vote_average || 0) - (a.vote_average || 0);
      });
      return logos.length ? IMG + 'w500' + logos[0].file_path : null;
    });
  }

  function slide(item, logoUrl) {
    var r = item.r;
    var date = r.release_date || r.first_air_date || '';
    return {
      slide: true,
      file: IMG + 'w1280' + r.backdrop_path,
      title: r.title || r.name || '',
      logo: logoUrl,
      kind: item.type === 'tv' ? 'Series' : 'Film',
      year: date.slice(0, 4),
      rating: r.vote_average ? Math.round(r.vote_average * 10) / 10 : null,
      overview: r.overview || '',
      provider: item.provider.label,
      app: item.provider.app
    };
  }

  function signature() {
    return [cfg.apiKey, cfg.region, cfg.language, cfg.max, cfg.types.join(),
      JSON.stringify(cfg.providers)].join('|');
  }

  QH.featured = {
    enabled: function () { return !!(cfg.enabled && cfg.apiKey && cfg.providers.length); },

    // Resolves to the slides (possibly from the day's cache), or [] when unavailable.
    load: function () {
      if (!this.enabled()) return Promise.resolve([]);
      var cached = QH.platform.store.get(CACHE);
      if (cached && cached.sig === signature() && Date.now() - cached.at < DAY && cached.slides.length) {
        return Promise.resolve(cached.slides);
      }
      var jobs = [];
      cfg.providers.forEach(function (p) { cfg.types.forEach(function (t) { jobs.push(discover(t, p)); }); });
      return Promise.all(jobs).then(function (lists) {
        // Take the lists in turn (each provider, films and series), so no one
        // provider or type fills the slideshow; skip titles already taken.
        var seen = {};
        var picked = [];
        for (var i = 0; picked.length < cfg.max; i++) {
          var any = false;
          for (var j = 0; j < lists.length && picked.length < cfg.max; j++) {
            var item = lists[j][i];
            if (!item) continue;
            any = true;
            if (seen[item.type + item.id]) continue;
            seen[item.type + item.id] = true;
            picked.push(item);
          }
          if (!any) break;
        }
        return Promise.all(picked.map(logo)).then(function (logos) {
          var slides = picked.map(function (item, k) { return slide(item, logos[k]); });
          if (slides.length) QH.platform.store.set(CACHE, { sig: signature(), at: Date.now(), slides: slides });
          else if (cached && cached.sig === signature()) return cached.slides;   // offline: yesterday's
          return slides;
        });
      });
    }
  };
}());
