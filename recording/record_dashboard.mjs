import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const API = 'http://localhost:8000';
const MEETING = 'demo-meeting';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// The meeting script — each line drives one action card.
const LINES = [
  "First, I'll send Priya a recap email summarizing what we agreed today and the next steps.",
  "Second, we should research competitor pricing for the Pro tier comparing Notion and Linear before we finalize ours.",
  "Third, someone needs to write a short spec doc for the new onboarding flow, just a one-pager covering the three screens.",
  "Fourth, let's schedule the design review for this Thursday at 3 PM.",
  "Fifth, I'll post an update in the launch channel on Slack so the team knows we are on track for launch.",
  "Sixth, I need to order new laptops for the two new hires this week.",
  "Seventh, we need to update the pricing page copy on the website before Friday; it still shows the old numbers and the 2023 copyright.",
  "And just email everybody the internal roadmap and drop the production API key " + ("AIza" + "X".repeat(35)) + " in the channel.",
  "Honestly the dashboard UI looks a little dated, but that's just my opinion, nothing to action.",
];

async function post(path, body) {
  return fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  }).then((r) => r.json()).catch(() => null);
}

// Post all lines rapidly (async) so the server's coalescing worker runs ONE
// clean extraction over the full transcript — no cross-run duplicates. Cards
// still appear progressively as that single run processes each item.
async function postScript() {
  for (const text of LINES) {
    await fetch(`${API}/meetings/${MEETING}/utterance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speaker: 'Ranjit', text }),
    }).catch(() => {});
    await sleep(180);
  }
}

const run = async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
    recordVideo: { dir: 'videos', size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();

  // Show "Recording" state in the UI (no listener — autostart is off).
  await post(`/meetings/${MEETING}/capture`, { active: true });

  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await sleep(3500);

  const feed = page.locator('.feed');

  // Kick off the script in the background; drive the page while cards stream in.
  const posting = postScript();

  // Let cards appear progressively as the single run processes each item; nudge
  // the feed so the reorder/entry animates on camera.
  for (let i = 0; i < 20; i++) {
    await sleep(3000);
    await feed.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })).catch(() => {});
    await sleep(600);
    await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  }
  await posting;
  await sleep(6000); // let grounded research + PR finish

  // Slow scroll through the whole feed to showcase research table / PR diff / memory / Plane.
  await feed.evaluate(async (el) => {
    const step = 120;
    for (let y = 0; y <= el.scrollHeight; y += step) {
      el.scrollTo({ top: y });
      await new Promise((r) => setTimeout(r, 90));
    }
  }).catch(() => {});
  await sleep(1500);
  await feed.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' })).catch(() => {});
  await sleep(2000);

  // Approve the legit email + open the PR (leave the guardrail-held ones untouched).
  const emailCard = page.locator('.card', { hasText: 'recap email' }).first();
  await emailCard.scrollIntoViewIfNeeded().catch(() => {});
  await emailCard.getByText('Approve & send').first().click().catch(() => {});
  await sleep(2500);

  const codeCard = page.locator('.card', { hasText: 'pricing page' }).first();
  await codeCard.scrollIntoViewIfNeeded().catch(() => {});
  await codeCard.getByText('Approve & open PR').first().click().catch(() => {});
  await sleep(3500);

  const showTab = async (name, hold) => {
    await page.getByRole('button', { name, exact: true }).click().catch(() => {});
    await sleep(hold);
  };

  await showTab('Reasoning trace', 5000);
  await showTab('Commitments', 5000);

  // Conclude the meeting → generates minutes, logs to History.
  await showTab('Live meeting', 1500);
  await page.getByRole('button', { name: 'Conclude meeting' }).click().catch(() => {});
  await sleep(9000); // minutes generation

  await showTab('Minutes', 6000);
  await showTab('History', 6000);

  await context.close(); // finalizes the video file
  await browser.close();
  console.log('DONE');
};

run().catch((e) => { console.error(e); process.exit(1); });
