// Quiet Home photo website: Glass Home's service (github.com/victaphu/glass-home-samsung-tv, MIT),
// used as is apart from config.json (packageId), the site name and icons.
// Glass Home - Tizen web service entry point (app id GlassHome1.Photos).
//
// The TV app starts this service (tizen.application.launchAppControl with the
// service operation). It keeps running after the app is hidden or closed, and
// serves the photo/shortcut website on the LAN. With a public certificate it
// does not start by itself after a reboot: the app starts it again.
//
// The runtime calls onStart once and onRequest for every later launch request,
// so both just make sure the server is up. Node 12 API only.
'use strict';
var path = require('path');

var service = null;
var starting = false;

function log() {
  try {
    var args = Array.prototype.slice.call(arguments);
    console.log.apply(console, ['[GlassHome.Photos]'].concat(args));
  } catch (e) { /* logging must never throw */ }
}

function start() {
  if (service || starting) return;
  starting = true;
  try {
    var core = require('./server.js');
    var s = core.createService({ appDir: path.join(__dirname, '..'), log: log });
    s.start(function (err) {
      starting = false;
      if (err) { log('start failed: ' + (err && err.message)); return; }
      service = s;
    });
  } catch (e) {
    starting = false;
    log('fatal: ' + (e && e.stack ? e.stack : e));
  }
}

function stop() {
  var s = service;
  service = null;
  if (s) { try { s.stop(); } catch (e) { log('stop failed: ' + e.message); } }
}

module.exports.onStart = function () { start(); };
module.exports.onRequest = function () { start(); };
module.exports.onExit = function () { stop(); };
module.exports.onStop = function () { stop(); };

if (typeof process !== 'undefined' && process && typeof process.on === 'function') {
  process.on('uncaughtException', function (e) { log('uncaught: ' + (e && e.stack ? e.stack : e)); });
  process.on('unhandledRejection', function (e) { log('unhandled rejection: ' + (e && e.stack ? e.stack : e)); });
}
