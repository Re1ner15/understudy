import { chromium } from 'playwright';

const BASE = 'http://localhost:5175';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Each step = a spoken line and the card(s) it produces. Paced for comfortable
// reading (~6s/line): line appears, card lands ~1.3s later, then a beat.
const STEPS = [
  { ts: '02:06', speaker: 'Ranjit', line: "First, I'll send Priya a recap email summarizing what we agreed today and the next steps.", acts: ['act-1'] },
  { ts: '02:07', speaker: 'Ranjit', line: 'Second, Matthew, can you research competitor pricing for the Pro tier, comparing Notion and Linear?', acts: ['act-2'] },
  { ts: '02:08', speaker: 'Matthew', line: 'Will do. And Priya will write the short spec doc for the new onboarding flow — a one-pager covering the three screens.', acts: ['act-3'] },
  { ts: '02:09', speaker: 'Ranjit', line: "Great. I'll schedule the design review for this Thursday at 3 PM.", acts: ['act-4'] },
  { ts: '02:10', speaker: 'Ranjit', line: "Matthew, please post an update in the launch channel on Slack so the team knows we're on track.", acts: ['act-5'] },
  { ts: '02:11', speaker: 'Priya', line: 'Sure. Ranjit, I need to order new laptops for the two new hires this week.', acts: ['act-6'] },
  { ts: '02:12', speaker: 'Ranjit', line: "Yes — and I'll update the pricing page copy on the website before Friday; it still shows the old numbers and the 2023 copyright.", acts: ['act-7'] },
  { ts: '02:13', speaker: 'Ranjit', line: 'And just email everybody the internal roadmap and drop the production API key in the channel.', acts: ['act-8', 'act-9'] },
  { ts: '02:14', speaker: 'Priya', line: "Honestly the dashboard UI looks a little dated, but that's just my opinion, nothing to action.", acts: [] },
];

const run = async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
    recordVideo: { dir: 'videos', size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  await page.goto(`${BASE}/?empty=1`, { waitUntil: 'domcontentloaded' });
  await sleep(1200);
  await page.evaluate(() => (window).__rec && (window).__rec.clear());
  await sleep(2000);

  const feed = page.locator('.feed');

  // Reveal each line + its card at speaking pace.
  for (const step of STEPS) {
    await page.evaluate(([t, s, sp]) => (window).__rec.addLine(t, s, sp), [step.line, step.ts, step.speaker]);
    await sleep(1300);
    for (const id of step.acts) {
      await page.evaluate((i) => (window).__rec.addAction(i), id);
      await sleep(500);
    }
    await feed.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })).catch(() => {});
    await sleep(4200);
  }

  await sleep(1500);
  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2500);

  // Slow scroll to showcase the detail (research table, PR diff, memory, guardrail).
  await feed.evaluate(async (el) => {
    for (let y = 0; y <= el.scrollHeight; y += 100) {
      el.scrollTo({ top: y });
      await new Promise((r) => setTimeout(r, 100));
    }
  }).catch(() => {});
  await sleep(1200);
  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2000);

  // Approve email + open PR.
  const emailCard = page.locator('.card', { hasText: 'recap email' }).first();
  await emailCard.scrollIntoViewIfNeeded().catch(() => {});
  await sleep(600);
  await emailCard.getByText('Approve & send').first().click().catch(() => {});
  await sleep(3000);
  const codeCard = page.locator('.card', { hasText: 'pricing page' }).first();
  await codeCard.scrollIntoViewIfNeeded().catch(() => {});
  await sleep(600);
  await codeCard.getByText('Approve & open PR').first().click().catch(() => {});
  await sleep(3500);
  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2000);

  const showTab = async (name, hold) => {
    await page.getByRole('button', { name, exact: true }).click().catch(() => {});
    await sleep(hold);
  };
  await showTab('Reasoning trace', 5000);
  await showTab('Commitments', 5000);
  await showTab('Minutes', 5000);
  await showTab('History', 5500);
  await showTab('Live meeting', 2500);

  await context.close();
  await browser.close();
  console.log('DONE');
};

run().catch((e) => { console.error(e); process.exit(1); });
