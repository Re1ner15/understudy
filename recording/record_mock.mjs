import { chromium } from 'playwright';

const BASE = 'http://localhost:5175';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const run = async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
    recordVideo: { dir: 'videos', size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();

  // Live meeting — cards animate in (FLIP entry) on load.
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await sleep(4000);

  const feed = page.locator('.feed');

  // Slow scroll through the whole feed to showcase every card + its detail
  // (research table + sources, GitHub PR diff, Plane link, memory recalls, guardrail).
  await feed.evaluate(async (el) => {
    for (let y = 0; y <= el.scrollHeight; y += 90) {
      el.scrollTo({ top: y });
      await new Promise((r) => setTimeout(r, 110));
    }
  }).catch(() => {});
  await sleep(1500);
  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2500);

  // Approve the email → it completes and glides to the bottom (reorder animation).
  const emailCard = page.locator('.card', { hasText: 'recap email' }).first();
  await emailCard.scrollIntoViewIfNeeded().catch(() => {});
  await sleep(800);
  await emailCard.getByText('Approve & send').first().click().catch(() => {});
  await sleep(3000);

  // Approve the code PR → PR marked ready, card completes and reorders.
  const codeCard = page.locator('.card', { hasText: 'pricing page' }).first();
  await codeCard.scrollIntoViewIfNeeded().catch(() => {});
  await sleep(800);
  await codeCard.getByText('Approve & open PR').first().click().catch(() => {});
  await sleep(3500);

  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2000);

  const showTab = async (name, hold) => {
    await page.getByRole('button', { name, exact: true }).click().catch(() => {});
    await sleep(hold);
  };

  await showTab('Reasoning trace', 5500);
  await showTab('Commitments', 5500);
  await showTab('Minutes', 5500);
  await showTab('History', 6000);
  await showTab('Live meeting', 2500);

  await context.close();
  await browser.close();
  console.log('DONE');
};

run().catch((e) => { console.error(e); process.exit(1); });
