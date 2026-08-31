import { chromium } from 'playwright';
import { pathToFileURL } from 'url';
import path from 'path';
import fs from 'fs';

const svgPath = path.resolve('docs/architecture.svg');
const svg = fs.readFileSync(svgPath, 'utf8');
const m = svg.match(/width="(\d+)"\s+height="(\d+)"/);
const W = m ? parseInt(m[1]) : 1200;
const H = m ? parseInt(m[2]) : 1180;

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0}html,body{width:${W}px;height:${H}px;background:#f6f7f4}
</style></head><body>${svg}</body></html>`;
const tmp = path.resolve('recording/_arch.html');
fs.writeFileSync(tmp, html);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' });
await page.waitForTimeout(200);
const outputs = [path.resolve('docs/architecture.png'), `${process.env.HOME}/Downloads/Understudy-architecture.png`];
for (const out of outputs) { await page.screenshot({ path: out, clip: { x: 0, y: 0, width: W, height: H } }); }
await browser.close();
fs.unlinkSync(tmp);
console.log('WROTE', outputs.join(' , '), `(${W}x${H} @2x)`);
