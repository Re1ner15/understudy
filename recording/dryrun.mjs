import { chromium } from 'playwright';
const URL = 'https://understudy-web-259946930410.asia-south1.run.app';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [], failed = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0,160)); });
page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0,160)));
page.on('requestfailed', r => failed.push(`${r.failure()?.errorText} ${r.url().slice(0,90)}`));
const t0 = Date.now();
const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
console.log('HTTP', resp.status(), '| load', ((Date.now()-t0)/1000).toFixed(1)+'s');
await page.waitForTimeout(7000); // let the SPA hydrate + Firestore connect
const title = await page.title();
const bodyText = (await page.locator('body').innerText().catch(()=> '')).replace(/\s+/g,' ').slice(0, 400);
const tabs = {};
for (const t of ['Live meeting','Commitments','Minutes','Reasoning trace','History']) {
  tabs[t] = await page.getByText(t, { exact: false }).count().catch(()=>0);
}
await page.screenshot({ path: `${process.env.HOME}/Downloads/Understudy-DryRun-Hosted.png` });
await browser.close();
console.log('title:', title);
console.log('nav tabs found:', JSON.stringify(tabs));
console.log('body preview:', bodyText);
console.log('console errors:', errors.length ? errors.slice(0,8) : 'none');
console.log('failed requests:', failed.length ? failed.slice(0,8) : 'none');
