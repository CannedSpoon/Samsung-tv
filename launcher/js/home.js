/*
 * Quiet Home - the screen: clock, rotating photos, the dock and remote keys.
 * Plain DOM, no frameworks. Timers stop while another app is in front.
 *
 * The dock holds, in this order unless you've moved them: your apps, HDMI
 * inputs with something plugged in, and shortcuts added from a phone; then +
 * (the photo website, hidden tiles) and Smart Hub, which can't be moved or
 * hidden. Hold OK on a tile to move or hide it. The long-press handling and
 * screensaver follow Glass Home (github.com/victaphu/glass-home-samsung-tv, MIT).
 */
(function () {
  'use strict';
  var QH = window.QH;
  var cfg = QH.config;
  var platform = QH.platform;
  var service = QH.service;
  var KEY = { LEFT: 37, UP: 38, RIGHT: 39, DOWN: 40, ENTER: 13, BACK: 10009, ESC: 27, BACKSPACE: 8 };
  var PREFS = 'qh.dock.v1';

  var $ = function (id) { return document.getElementById(id); };
  var body = document.body;
  var dock = $('dock');
  var strip = $('strip');

  // ---- stage: lay out at 1920x1080 and scale to the screen ----------------
  function fit() {
    var s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    $('stage').style.transform = 'scale(' + s + ')';
  }
  window.addEventListener('resize', fit);
  fit();

  // ---- hint line under the dock ---------------------------------------------
  var hintTimer = null;
  function hint(text, ms) {
    clearTimeout(hintTimer);
    $('hint').textContent = text;
    if (text) hintTimer = setTimeout(function () { $('hint').textContent = ''; }, ms || 6000);
  }

  // ---- clock and evening dimming -------------------------------------------
  var clockTimer = null;
  function minutes(hhmm) {
    var p = String(hhmm).split(':');
    return (+p[0] || 0) * 60 + (+p[1] || 0);
  }
  function dim(now) {
    var n = cfg.night;
    var on = false;
    if (n.enabled) {
      var m = now.getHours() * 60 + now.getMinutes();
      var from = minutes(n.from);
      var to = minutes(n.to);
      on = from < to ? (m >= from && m < to) : (m >= from || m < to);
    }
    $('dim').style.opacity = on ? n.dim : 0;
  }
  function tick() {
    var now = new Date();
    var loc = cfg.locale || undefined;
    $('time').textContent = now.toLocaleTimeString(loc, { hour: 'numeric', minute: '2-digit' });
    $('date').textContent = now.toLocaleDateString(loc, { weekday: 'long', day: 'numeric', month: 'long' });
    dim(now);
    clockTimer = setTimeout(tick, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()) + 50);
  }

  // ---- photos ----------------------------------------------------------------
  var layers = [$('bg-a'), $('bg-b')];
  var front = 0;
  var order = [];
  var next = 0;
  var photoTimer = null;
  var userPhotos = [];
  document.documentElement.style.setProperty('--fade', cfg.fadeMs + 'ms');
  document.documentElement.style.setProperty('--drift', (cfg.photoIntervalMs + cfg.fadeMs) + 'ms');
  if (!cfg.drift) body.classList.add('no-drift');

  function shuffle(list) {
    list = list.slice();
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = list[i]; list[i] = list[j]; list[j] = t;
    }
    return list;
  }

  // Bundled and uploaded photos, shuffled; photos just uploaded come next.
  function setPhotos(fresh) {
    var all = shuffle(QH.wallpapers.concat(userPhotos));
    if (fresh && fresh.length) {
      var ids = fresh.map(function (p) { return p.file; });
      all = fresh.concat(all.filter(function (p) { return ids.indexOf(p.file) < 0; }));
    }
    order = all;
    next = 0;
  }

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
      $('caption').textContent = photo.title || '';
    }, function () { /* skip a photo that fails to load */ }).then(schedulePhoto);
  }
  function schedulePhoto() {
    clearTimeout(photoTimer);
    if (!document.hidden) photoTimer = setTimeout(showNext, cfg.photoIntervalMs);
  }

  // ---- dock ------------------------------------------------------------------
  var apps = [];
  var ports = [];
  var items = [];
  var tiles = [];
  var focus = 0;
  var busy = false;
  var prefs = platform.store.get(PREFS) || { order: [], hidden: [] };

  function savePrefs() { platform.store.set(PREFS, prefs); }

  function inputLabel(n) { return (cfg.inputs.names && cfg.inputs.names[n]) || 'HDMI ' + n; }

  // Everything that can be in the dock, before your order and hidden tiles.
  function candidates() {
    var list = apps.map(function (a) {
      return { key: 'app:' + a.label, kind: 'app', label: a.label, color: a.color, accent: a.accent, ids: a.ids };
    });
    ports.forEach(function (p) {
      var name = inputLabel(p.number);
      list.push({ key: 'hdmi:' + p.number, kind: 'input', number: p.number, label: name,
                  title: name === 'HDMI ' + p.number ? name : name + '  (HDMI ' + p.number + ')',
                  color: '#1c222c', accent: p.connected ? '#9fb3c8' : '#4a5563' });
    });
    service.shortcuts().forEach(function (s) {
      var yt = s.type === 'youtube';
      list.push({ key: 'sc:' + s.id, kind: 'shortcut', shortcut: s, label: s.name || (yt ? 'YouTube video' : 'Website'),
                  title: (yt ? 'YouTube: ' : 'Website: ') + (s.name || s.url),
                  color: yt ? '#1f1f1f' : '#17262f', accent: yt ? '#ff0033' : '#7fd1ff' });
    });
    return list;
  }

  function rebuildDock() {
    var keep = items[focus] && items[focus].key;
    var byKey = {};
    var all = candidates();
    all.forEach(function (it) { byKey[it.key] = it; });
    var ordered = [];
    prefs.order.forEach(function (k) { if (byKey[k]) { ordered.push(byKey[k]); delete byKey[k]; } });
    all.forEach(function (it) { if (byKey[it.key]) ordered.push(it); });
    items = ordered.filter(function (it) { return prefs.hidden.indexOf(it.key) < 0; });
    items.push({ key: 'plus', kind: 'plus', label: '+', title: 'Add photos and shortcuts, hidden tiles', fixed: true });
    items.push({ key: 'home', kind: 'app', label: cfg.samsungHome.label, ids: [cfg.samsungHome.id], fixed: true });

    strip.innerHTML = '';
    tiles = items.map(function (it) {
      var el = document.createElement('div');
      el.className = 'tile' + (it.fixed ? ' system' : '') + (it.kind === 'plus' ? ' plus' : '') +
        (it.kind === 'input' ? ' input' : '');
      el.style.setProperty('--tile', it.color || 'rgba(255,255,255,.14)');
      el.style.setProperty('--accent', it.accent || '#fff');
      var name = document.createElement('span');
      name.className = 'name';
      name.textContent = it.label;
      el.appendChild(name);
      strip.appendChild(el);
      return el;
    });
    var at = 0;
    for (var i = 0; i < items.length; i++) if (items[i].key === keep) at = i;
    setFocus(keep ? at : Math.min(focus, items.length - 1));
    if (!apps.length) hint('None of the dock apps were found. Edit js/config.js.', 15000);
  }

  function setFocus(i) {
    if (tiles[focus]) tiles[focus].classList.remove('focus');
    focus = Math.max(0, Math.min(i, items.length - 1));
    tiles[focus].classList.add('focus');
    $('label').textContent = items[focus].title || items[focus].label;
    // Slide the strip so the focused tile stays in view (centred when it can be).
    var view = dock.clientWidth - 60;
    var el = tiles[focus];
    var off = Math.max(0, Math.min(el.offsetLeft + el.offsetWidth / 2 - view / 2, strip.scrollWidth - view));
    strip.style.transform = 'translateX(' + (-off) + 'px)';
  }

  function youtubeIds() {
    for (var i = 0; i < apps.length; i++) if (apps[i].label === 'YouTube') return apps[i].ids;
    return null;
  }

  function activate(it) {
    if (busy || !it) return;
    if (it.kind === 'plus') { openPanel(); return; }
    var el = tiles[focus];
    var job;
    if (it.kind === 'input') job = QH.inputs.open(it.number, cfg.inputs.method);
    else if (it.kind === 'shortcut' && it.shortcut.type === 'youtube') job = platform.openYouTube(it.shortcut, youtubeIds());
    else if (it.kind === 'shortcut') job = platform.openUrl(it.shortcut.url);
    else job = platform.launch(it.ids);
    busy = true;
    el.classList.add('opening');
    job.then(null, function (e) {
      // The TV's reason and the ids tried, so a wrong id can be fixed in js/config.js.
      var why = (e && (e.message || e.name)) || 'error';
      hint('Couldn’t open ' + it.label + (it.ids ? ' (' + it.ids.join(', ') + ': ' + why + ')' : ' (' + why + ')'), 10000);
    }).then(function () {
      busy = false;
      el.classList.remove('opening');
    });
  }

  // ---- hold OK: Move / Hide menu -------------------------------------------
  var mode = 'dock';          // 'dock' | 'menu' | 'panel'
  var menuItems = [];
  var menuFocus = 0;

  function movable(i) { return i >= 0 && i < items.length && !items[i].fixed; }

  function openMenu() {
    var it = items[focus];
    if (!movable(focus)) return;
    menuItems = [];
    if (movable(focus - 1)) menuItems.push({ label: 'Move left', run: function () { move(-1); } });
    if (movable(focus + 1)) menuItems.push({ label: 'Move right', run: function () { move(1); } });
    if (it.kind === 'shortcut') menuItems.push({ label: 'Remove shortcut', run: function () { removeShortcut(it); } });
    else menuItems.push({ label: 'Hide (show again from +)', run: function () { hide(it); } });
    menuItems.push({ label: 'Cancel', run: function () {} });
    menuFocus = 0;
    $('menu-title').textContent = it.title || it.label;
    renderList($('menu-list'), menuItems, menuFocus);
    $('menu').classList.add('open');
    body.classList.add('sheet-open');
    mode = 'menu';
  }

  function closeMenu() {
    $('menu').classList.remove('open');
    body.classList.remove('sheet-open');
    mode = 'dock';
  }

  function renderList(el, list, at) {
    el.innerHTML = '';
    list.forEach(function (x, i) {
      var b = document.createElement('div');
      b.className = 'choice' + (i === at ? ' focus' : '');
      b.textContent = x.label;
      el.appendChild(b);
    });
  }

  function move(delta) {
    var visible = items.filter(function (it) { return !it.fixed; }).map(function (it) { return it.key; });
    var i = focus;
    var t = visible[i]; visible[i] = visible[i + delta]; visible[i + delta] = t;
    prefs.order = visible.concat(prefs.order.filter(function (k) { return visible.indexOf(k) < 0; }));
    savePrefs();
    rebuildDock();
  }

  function hide(it) {
    prefs.hidden.push(it.key);
    savePrefs();
    rebuildDock();
    hint(it.label + ' is hidden. Show it again from +.');
  }

  function removeShortcut(it) {
    service.removeShortcut(it.shortcut.id).then(function () {
      rebuildDock();
      hint('Removed ' + it.label + '.');
    }, function () { hint('Couldn’t remove it: the photo website isn’t running.'); });
  }

  // ---- + panel: photo website, hidden tiles --------------------------------
  var panelActions = [];
  var panelFocus = 0;

  function renderPanel() {
    var p = service.panel();
    $('panel-url').textContent = p.url || '';
    $('panel-password').textContent = p.password ? 'Password: ' + p.password : '';
    $('panel-note').textContent = p.note || '';
    $('panel-site').style.display = cfg.photoWebsite.enabled ? '' : 'none';
    // Close first, so a stray OK doesn't make a new password (which signs phones out).
    panelActions = [{ label: 'Close', run: closePanel }];
    if (cfg.photoWebsite.enabled && service.online) {
      panelActions.push({ label: 'New password', run: function () {
        service.newPassword().then(renderPanel, function () { hint('Couldn’t make a password.'); });
      } });
    }
    if (prefs.hidden.length) {
      panelActions.push({ label: 'Show hidden tiles (' + prefs.hidden.length + ')', run: function () {
        prefs.hidden = []; savePrefs(); rebuildDock(); closePanel();
      } });
    }
    if (prefs.order.length || prefs.hidden.length) {
      panelActions.push({ label: 'Reset dock order', run: function () {
        prefs = { order: [], hidden: [] }; savePrefs(); rebuildDock(); closePanel();
      } });
    }
    panelFocus = Math.min(panelFocus, panelActions.length - 1);
    renderList($('panel-actions'), panelActions, panelFocus);
  }

  function openPanel() {
    panelFocus = 0;
    renderPanel();
    $('panel').classList.add('open');
    body.classList.add('sheet-open');
    mode = 'panel';
    refreshService();
  }

  function closePanel() {
    $('panel').classList.remove('open');
    body.classList.remove('sheet-open');
    mode = 'dock';
  }

  // ---- screensaver ------------------------------------------------------------
  var idleTimer = null;
  var asleep = false;
  var swallow = null;

  function poke() {
    clearTimeout(idleTimer);
    if (cfg.screensaver.enabled && !document.hidden) idleTimer = setTimeout(sleep, cfg.screensaver.afterMs);
  }
  function sleep() {
    if (mode === 'menu') closeMenu();
    if (mode === 'panel') closePanel();
    asleep = true;
    body.classList.add('asleep');
  }
  function wake() {
    asleep = false;
    body.classList.remove('asleep');
    poke();
  }

  // ---- keys -------------------------------------------------------------------
  var enterDown = false;
  var longTimer = null;
  var longFired = false;

  function onKeyDown(e) {
    var k = e.keyCode;
    if (asleep) {
      // The first press only wakes the screen; its key-up is ignored too.
      swallow = k;
      wake();
      e.preventDefault();
      return;
    }
    poke();
    if (k === KEY.BACK || k === KEY.ESC || k === KEY.BACKSPACE) {
      // Back closes a menu; on the home screen there is nowhere to go back to.
      if (mode === 'menu') closeMenu();
      else if (mode === 'panel') closePanel();
      e.preventDefault();
      return;
    }
    if (mode === 'menu' || mode === 'panel') {
      var list = mode === 'menu' ? menuItems : panelActions;
      var at = mode === 'menu' ? menuFocus : panelFocus;
      var prev = mode === 'menu' ? KEY.UP : KEY.LEFT;
      var nxt = mode === 'menu' ? KEY.DOWN : KEY.RIGHT;
      if (k === prev) at = Math.max(0, at - 1);
      else if (k === nxt) at = Math.min(list.length - 1, at + 1);
      else if (k === KEY.ENTER) {
        if (enterDown) return;                  // still held from opening the menu
        var chosen = list[at];
        if (mode === 'menu') closeMenu();
        chosen.run();
        e.preventDefault();
        return;
      } else return;
      if (mode === 'menu') { menuFocus = at; renderList($('menu-list'), menuItems, at); }
      else { panelFocus = at; renderList($('panel-actions'), panelActions, at); }
      e.preventDefault();
      return;
    }
    if (k === KEY.LEFT) setFocus(focus - 1);
    else if (k === KEY.RIGHT) setFocus(focus + 1);
    else if (k === KEY.ENTER) {
      if (enterDown) return;                    // auto-repeat while held
      enterDown = true;
      longFired = false;
      clearTimeout(longTimer);
      longTimer = setTimeout(function () {
        longTimer = null;
        if (!enterDown || mode !== 'dock') return;
        longFired = true;
        openMenu();
      }, cfg.longPressMs);
    } else if (cfg.quickKeys && k >= 49 && k <= 57 && items[k - 49] && !items[k - 49].fixed) {
      setFocus(k - 49);
      activate(items[focus]);
    } else return;
    e.preventDefault();
  }

  function onKeyUp(e) {
    if (swallow !== null && e.keyCode === swallow) { swallow = null; e.preventDefault(); return; }
    if (e.keyCode !== KEY.ENTER) return;
    if (!enterDown) return;
    enterDown = false;
    if (longTimer) {
      clearTimeout(longTimer);
      longTimer = null;
      if (!longFired && mode === 'dock') activate(items[focus]);
    }
    longFired = false;
  }

  document.addEventListener('keydown', onKeyDown);
  document.addEventListener('keyup', onKeyUp);

  // ---- photo website and inputs: keep in step ------------------------------
  var serviceTimer = null;
  function refreshService() {
    clearTimeout(serviceTimer);
    var before = userPhotos.map(function (p) { return p.file; });
    return service.refresh().then(function (changed) {
      if (changed) {
        userPhotos = service.photos();
        var now = userPhotos.map(function (p) { return p.file; });
        if (now.join() !== before.join()) {
          // New uploads show next (on the very first sync they just join the shuffle).
          var fresh = userPhotos.filter(function (p) { return before.indexOf(p.file) < 0; });
          setPhotos(before.length ? fresh : []);
        }
        rebuildDock();
      }
      if (mode === 'panel') renderPanel();
    }).then(function () {
      if (!document.hidden) serviceTimer = setTimeout(refreshService, 20000);
    });
  }

  function refreshInputs() {
    if (!cfg.inputs.enabled) return Promise.resolve();
    return QH.inputs.list(cfg.inputs.showUnplugged).then(function (list) {
      var changed = JSON.stringify(list) !== JSON.stringify(ports);
      ports = list;
      if (changed && apps.length) rebuildDock();
    });
  }

  // ---- pause while hidden --------------------------------------------------
  document.addEventListener('visibilitychange', function () {
    clearTimeout(clockTimer);
    if (document.hidden) {
      clearTimeout(photoTimer);
      clearTimeout(idleTimer);
      clearTimeout(serviceTimer);
      return;
    }
    tick();
    schedulePhoto();
    poke();
    refreshInputs();
    refreshService();
  });

  // For the browser preview and tests: skip to the next photo.
  QH.debug = { nextPhoto: function () { clearTimeout(photoTimer); showNext(); } };

  // ---- start -------------------------------------------------------------------
  userPhotos = service.photos();
  setPhotos();
  tick();
  showNext();
  poke();
  if (cfg.quickKeys) platform.registerKeys(['1', '2', '3', '4', '5', '6', '7', '8', '9']);
  if (QH.weather.enabled()) {
    body.classList.add('has-weather');
    QH.weather.start(function (text) { $('weather').textContent = text; });
  }
  service.start();
  Promise.all([platform.resolveApps(cfg.apps), refreshInputs()]).then(function (r) {
    apps = r[0];
    rebuildDock();
    refreshService();
  });
}());
