import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const { chromium } = createRequire(import.meta.url)('playwright');
const out = process.argv[2];
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
await ctx.route('https://api.open-meteo.com/**', (r) => r.fulfill({ contentType: 'application/json',
  body: JSON.stringify({ current: { temperature_2m: 18.4, weather_code: 2 }, daily: { temperature_2m_max: [21.2], temperature_2m_min: [11.6] } }) }));
await ctx.route('https://i.ytimg.com/**', (r) => r.fulfill({ contentType: 'image/jpeg', body: readFileSync('launcher/wallpapers/unsplash-forest.jpg') }));
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('requestfailed', (r) => { if (!/config\.local|local-key/.test(r.url())) errors.push('failed: ' + r.url()); });
await page.goto('http://localhost:8080/');
await page.waitForTimeout(2500);
console.log('tiles:', (await page.$$eval('#strip .tile', (t) => t.map((x) => x.className.replace('tile', '').trim() + ':' + (x.textContent || '(mark)')))).join(' | '));
await page.screenshot({ path: out + '/tiles-home.png' });
for (const n of [1, 2]) { await page.keyboard.press('ArrowRight'); }
await page.waitForTimeout(450);                         // mid-sweep on Stremio
await page.screenshot({ path: out + '/tiles-sweep.png', clip: { x: 0, y: 700, width: 1920, height: 380 } });
for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowRight');
await page.waitForTimeout(1500);
await page.screenshot({ path: out + '/tiles-end.png', clip: { x: 0, y: 700, width: 1920, height: 380 } });
console.log('focused at end:', await page.textContent('#label'));
console.log(errors.length ? errors.join('\n') : 'no page errors or failed requests');
await browser.close();
