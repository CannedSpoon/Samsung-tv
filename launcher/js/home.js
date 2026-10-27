/*
 * Quiet Home - the screen: clock, rotating photos, the dock and remote keys.
 * Plain DOM, no frameworks. Timers stop while another app is in front.
 */
(function () {
  'use strict';
  var QH = window.QH;
  var cfg = QH.config;
  var platform = QH.platform;
  var KEY = { LEFT: 37, RIGHT: 39, ENTER: 13, BACK: 10009, ESC: 27, BACKSPACE: 8 };

  var $ = function (id) { return document.getElementById(id); };
  var dock = $('dock');
  var tiles = [];
  var focus = 0;
  var busy = false;

  // ---- stage: lay out at 1920x1080 and scale to the screen ----------------
  function fit() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    $('stage').style.transform = 'scale(' + s + ')';
  }
  window.addEventListener('resize', fit);
  fit();

  // ---- clock ---------------------------------------------------------------
  var clockTimer = null;
  function tick() {
    var now = new Date();
    var loc = cfg.locale || undefined;
    $('time').textContent = now.toLocaleTimeString(loc, { hour: 'numeric', minute: '2-digit' });
    $('date').textContent = now.toLocaleDateString(loc, { weekday: 'long', day: 'numeric', month: 'long' });
    clockTimer = setTimeout(tick, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()) + 50);
  }

  // ---- photos --------------------------------------------------------------
  var layers = [$('bg-a'), $('bg-b')];
  var front = 0;
  var order = QH.wallpapers.slice();
  for (var i = order.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = order[i]; order[i] = order[j]; order[j] = t;
  }
  var next = 0;
  var photoTimer = null;
  document.documentElement.style.setProperty('--fade', cfg.fadeMs + 'ms');
  document.documentElement.style.setProperty('--drift', (cfg.photoIntervalMs + cfg.fadeMs) + 'ms');
  if (!cfg.drift) document.body.classList.add('no-drift');

  // Loads and decodes the image before it is shown, so the crossfade never
  // stutters on a half-decoded photo.
  function load(src) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.onload = function () {
        if (img.decode) img.decode().then(function () { resolve(src); }, function () { resolve(src); });
        else resolve(src);
      };
      img.onerror = reject;
      img.src = src;
    });
  }

  function showNext() {
    var photo = order[next];
    next = (next + 1) % order.length;
    load(photo.file).then(function (src) {
      var back = layers[1 - front];
      back.style.backgroundImage = 'url("' + src + '")';
      back.classList.remove('shown');
      void back.offsetWidth; // restart the drift animation
      back.classList.add('shown');
      layers[front].classList.remove('shown');
      front = 1 - front;
      $('caption').textContent = photo.title;
    }, function () { /* skip a photo that fails to load */ }).then(schedulePhoto);
  }
  function schedulePhoto() {
    clearTimeout(photoTimer);
    if (!document.hidden) photoTimer = setTimeout(showNext, cfg.photoIntervalMs);
  }

  // ---- dock ----------------------------------------------------------------
  function tile(app, extraClass) {
    var el = document.createElement('div');
    el.className = 'tile' + (extraClass ? ' ' + extraClass : '');
    el.style.setProperty('--tile', app.color || 'rgba(255,255,255,.14)');
    el.style.setProperty('--accent', app.accent || '#fff');
    var name = document.createElement('span');
    name.className = 'name';
    name.textContent = app.label;
    el.appendChild(name);
    el.appIds = app.ids;
    el.label = app.label;
    return el;
  }

  function render(apps) {
    dock.innerHTML = '';
    tiles = apps.map(function (a) { return tile(a); });
    var home = cfg.samsungHome;
    tiles.push(tile({ label: home.label, ids: [home.id] }, 'system'));
    tiles.forEach(function (el) { dock.appendChild(el); });
    if (!apps.length) $('hint').textContent = 'None of the dock apps were found. Edit js/config.js.';
    setFocus(Math.min(focus, tiles.length - 1));
  }

  function setFocus(i) {
    if (tiles[focus]) tiles[focus].classList.remove('focus');
    focus = i;
    tiles[focus].classList.add('focus');
    $('label').textContent = tiles[focus].label;
  }

  function open() {
    var el = tiles[focus];
    if (busy || !el) return;
    busy = true;
    el.classList.add('opening');
    platform.launch(el.appIds).then(null, function (e) {
      // Show the TV's reason and the ids tried, so a wrong id can be fixed in js/config.js.
      $('hint').textContent = 'Couldn’t open ' + el.label + ' (' + el.appIds.join(', ') + ': ' +
        ((e && (e.message || e.name)) || 'error') + ')';
      setTimeout(function () { $('hint').textContent = ''; }, 10000);
    }).then(function () {
      busy = false;
      el.classList.remove('opening');
    });
  }

  document.addEventListener('keydown', function (e) {
    var k = e.keyCode;
    if (k === KEY.LEFT && focus > 0) setFocus(focus - 1);
    else if (k === KEY.RIGHT && focus < tiles.length - 1) setFocus(focus + 1);
    else if (k === KEY.ENTER) open();
    else if (k !== KEY.BACK && k !== KEY.ESC && k !== KEY.BACKSPACE) return;
    // Back does nothing on a home screen: there is nowhere to go back to.
    e.preventDefault();
  });

  // ---- pause while hidden --------------------------------------------------
  document.addEventListener('visibilitychange', function () {
    clearTimeout(clockTimer);
    if (document.hidden) { clearTimeout(photoTimer); return; }
    tick();
    schedulePhoto();
  });

  tick();
  showNext();
  platform.resolveApps(cfg.apps).then(render);
}());
