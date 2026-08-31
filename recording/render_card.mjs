import { chromium } from 'playwright';
import { pathToFileURL } from 'url';
import path from 'path';

const html = path.resolve('recording/title_card.html');
const out = process.env.OUT || `${process.env.HOME}/Desktop/Understudy-Title-Card.png`;

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 2, // crisp 2x
});
await page.goto(pathToFileURL(html).href, { waitUntil: 'networkidle' });
await page.waitForTimeout(300);
await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
await browser.close();
console.log('WROTE', out);
