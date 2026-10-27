// Draws the app icons (512x512): launcher/icon.png, a dock of three tiles over a
// hill at dusk, and apps/framex/icon.png, a wordmark.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b4c7e"/><stop offset="1" stop-color="#f2a65a"/></linearGradient></defs>
<rect width="512" height="512" rx="112" fill="url(#sky)"/>
<path d="M0 330 Q140 250 260 300 T512 280 V400 H0Z" fill="#1d3b2a"/>
<rect x="56" y="360" width="400" height="96" rx="36" fill="rgba(255,255,255,.28)"/>
<rect x="84" y="380" width="100" height="56" rx="14" fill="#fff"/>
<rect x="206" y="380" width="100" height="56" rx="14" fill="rgba(255,255,255,.7)"/>
<rect x="328" y="380" width="100" height="56" rx="14" fill="rgba(255,255,255,.7)"/></svg>`;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 512, height: 512 } });
await page.setContent(`<body style="margin:0;background:transparent">${svg}</body>`);
await page.screenshot({ path: new URL('../launcher/icon.png', import.meta.url).pathname, omitBackground: true });
const framex = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1b1d24"/><stop offset="1" stop-color="#3a2a6e"/></linearGradient></defs>
<rect width="512" height="512" rx="112" fill="url(#g)"/>
<text x="256" y="268" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-weight="800" font-size="128" letter-spacing="-4" fill="#fff">FrameX</text>
<text x="256" y="372" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-weight="600" font-size="72" letter-spacing="10" fill="#b9a8ff">TV</text></svg>`;
await page.setContent(`<body style="margin:0;background:transparent">${framex}</body>`);
await page.screenshot({ path: new URL('../apps/framex/icon.png', import.meta.url).pathname, omitBackground: true });
await browser.close();
