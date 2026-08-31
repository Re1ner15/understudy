import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errors = []; p.on('console', m=>{if(m.type()==='error')errors.push(m.text().slice(0,120));});
const r = await p.goto('https://understudy-web-259946930410.asia-south1.run.app', { waitUntil:'domcontentloaded' });
await p.waitForTimeout(9000);
const t = (await p.locator('body').innerText()).replace(/\s+/g,' ');
const has = s => t.includes(s);
console.log('HTTP', r.status());
console.log('generic persona -> "You":', has('You'), '| "Ranjit" gone:', !has('Ranjit'), '| Matthew:', has('Matthew'), '| Priya:', has('Priya'));
console.log('real actions -> pricing PR:', has('pricing page'), '| guardrail held:', has('production API key')||has('Held for your review'), '| research:', has('Research competitor pricing'));
console.log('tabs:', ['Live meeting','Commitments','Minutes','Reasoning trace','History'].every(has));
console.log('console errors:', errors.length? errors.slice(0,4):'none');
// exercise a real backend call via the page origin (CORS): fetch commitments count through firestore already proven; test approve endpoint reachability
await p.screenshot({ path: `${process.env.HOME}/Downloads/Understudy-Hosted-Generic.png` });
await b.close();
