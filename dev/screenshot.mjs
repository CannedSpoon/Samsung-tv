// Renders the preview at 1920x1080 and saves docs/screenshots/home.png.
// Needs `node dev/preview.mjs` running and Playwright installed.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright'); // resolves a global install too
import { mkdir } from 'node:fs/promises';

const url = process.env.URL || 'http://localhost:8080/';
const out = new URL('../docs/screenshots/', import.meta.url).pathname;
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(url);
await page.waitForTimeout(2500);
await page.screenshot({ path: out + 'home.png' });
console.log('focused:', await page.textContent('#label'), '| tiles:', await page.$$eval('.tile', (t) => t.map((x) => x.textContent).join(', ')));
await browser.close();
if (errors.length) { console.error('page errors:\n' + errors.join('\n')); process.exit(1); }
