#!/usr/bin/env node
// Runs the photo website service (launcher/service) on 127.0.0.1:8090 with a
// throwaway data folder, so `node dev/preview.mjs` shows uploads and shortcuts
// in the browser preview. Nothing listens on the network. Ctrl-C to stop.
//   node dev/run-website.js [--data DIR]
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const app = path.join(__dirname, '..', 'launcher');
if (!fs.existsSync(path.join(app, 'js', 'local-key.js'))) {
  console.error('No launcher/js/local-key.js yet. Run once:  python3 -c "import tv; tv.prepare_launcher()"  (or python3 tv.py install)');
  process.exit(1);
}
const i = process.argv.indexOf('--data');
const data = i > 0 ? process.argv[i + 1] : fs.mkdtempSync(path.join(os.tmpdir(), 'quiet-home-site-'));
const service = require(path.join(app, 'service', 'server.js')).createService({
  appDir: app, port: 8090, hosts: ['127.0.0.1'], dataDir: data,
  advertiseUrl: 'http://127.0.0.1:8090', config: { fetchIcons: false }
});
service.start((err) => {
  if (err) { console.error(err); process.exit(1); }
  console.log('Photo website: http://127.0.0.1:8090  (data: ' + data + ')');
});
