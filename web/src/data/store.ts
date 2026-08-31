import {
  MeetingState,
  Commitment,
  TranscriptLine,
  LiveAction,
  ScreenContext,
  Minutes,
  Clarification,
  AuditSpan,
} from './types';


// Initial seeded transcript matching demo meeting
const initialTranscript: TranscriptLine[] = [
  { id: 'tl-1', speaker: 'You', text: "First, I'll send Priya a recap email summarizing what we agreed today and the next steps.", ts: '02:06' },
  { id: 'tl-2', speaker: 'You', text: 'Second, Matthew, can you research competitor pricing for the Pro tier, comparing Notion and Linear?', ts: '02:07' },
  { id: 'tl-3', speaker: 'Matthew', text: 'Will do. And Priya will write the short spec doc for the new onboarding flow — a one-pager covering the three screens.', ts: '02:08' },
  { id: 'tl-4', speaker: 'You', text: "Great. I'll schedule the design review for this Thursday at 3 PM.", ts: '02:09' },
  { id: 'tl-5', speaker: 'You', text: "Matthew, please post an update in the launch channel on Slack so the team knows we're on track.", ts: '02:10' },
  { id: 'tl-6', speaker: 'Priya', text: 'Sure. I need to order new laptops for the two new hires this week.', ts: '02:11' },
  { id: 'tl-7', speaker: 'You', text: "Yes — and I'll update the pricing page copy on the website before Friday; it still shows the old numbers and the 2023 copyright.", ts: '02:12' },
  { id: 'tl-8', speaker: 'Priya', text: "Honestly the dashboard UI looks a little dated, but that's just my opinion, nothing to action.", ts: 'now', isLive: true },
];

// Initial seeded live actions matching meeting-view.html
const initialActions: LiveAction[] = [
  {
    id: 'act-1',
    itemId: 'ai-1',
    category: 'email',
    title: 'Send Priya a recap email summarizing the agreement and next steps',
    assignee: 'You',
    status: 'needs_approval',
    reasoning: 'Heard "I\'ll send Priya a recap email" → sending is irreversible, so I drafted it and I\'m holding for your OK.',
    requiresApproval: true,
    artifact: 'Subject: Recap — today\'s decisions & next steps\n\nHi Priya,\n\nQuick recap of what we agreed today and the next steps...',
    relatedMemory: [
      { text: 'Leadership confirmed the Pro tier at $29/user — please include it in the pricing recap.', meetingTitle: 'Email from Priya', date: 'Aug 13', kind: 'email' },
    ],
  },
  {
    id: 'act-2',
    itemId: 'ai-2',
    category: 'research',
    title: 'Research competitor pricing (Notion and Linear) for the Pro tier',
    assignee: 'Matthew',
    status: 'done',
    reasoning: 'Heard "research competitor pricing… comparing Notion and Linear" → ran a grounded web search.',
    requiresApproval: false,
    artifact:
      '### Competitor Pricing — Notion vs. Linear (Pro tiers)\n\n' +
      '| Metric | Notion Plus | Notion Business | Linear Standard |\n' +
      '| :-- | :-- | :-- | :-- |\n' +
      '| **Annual** | $10/user/mo | $20/user/mo | $8/user/mo |\n' +
      '| **Monthly** | $12/user/mo | $24/user/mo | $10/user/mo |\n' +
      '| **AI** | Trial only | Full AI | Agent automations |\n\n' +
      '### Key takeaways\n' +
      '* Notion Plus and Linear are close at the entry tier.\n' +
      '* Linear is seat-based; Notion bundles more at Business.\n' +
      '===SOURCES===\n' +
      'Notion Pricing | https://www.notion.com/pricing\n' +
      'Linear Pricing | https://linear.app/pricing\n' +
      'Pricing comparison 2026 | https://example.com/notion-vs-linear',
    relatedMemory: [
      { text: 'Decided the Pro tier will launch at $29 per user per month, matching Linear.', meetingTitle: 'Pricing Strategy', date: 'Aug 12', kind: 'decision' },
    ],
  },
  {
    id: 'act-3',
    itemId: 'ai-3',
    category: 'doc',
    title: 'Write a short spec doc for the new onboarding flow',
    assignee: 'Priya',
    status: 'done',
    reasoning: 'Heard "write a short spec doc for the new onboarding flow" → generated a one-pager in Google Docs.',
    requiresApproval: false,
    artifact: 'Title: Onboarding Flow — One-Pager\n\nThree screens: sign-up, workspace setup, invite teammates.',
    relatedMemory: [
      { text: 'Onboarding will be sign-up, workspace setup, and invite teammates — three screens total.', meetingTitle: 'UX Review', date: 'Aug 5', kind: 'transcript' },
    ],
  },
  {
    id: 'act-4',
    itemId: 'ai-4',
    category: 'calendar',
    title: 'Schedule the design review for this Thursday at 3 PM',
    assignee: 'You',
    status: 'done',
    reasoning: 'Extracted time from "schedule the design review for this Thursday at 3 PM" → created the event.',
    requiresApproval: false,
    artifact: 'Event: Design Review\nTime: Thursday 3:00 PM\nAttendees: You, Design',
  },
  {
    id: 'act-5',
    itemId: 'ai-5',
    category: 'slack',
    title: 'Post an update in the launch channel on Slack',
    assignee: 'Matthew',
    status: 'done',
    reasoning: 'Heard "post an update in the launch channel on Slack" → posted to #under-study.',
    requiresApproval: false,
    artifact: 'Target: #under-study\nMessage: On track for launch — pricing, onboarding, and design review all in motion.',
    relatedMemory: [
      { text: 'Committed to shipping the public launch by the end of the month.', meetingTitle: 'Launch Planning', date: 'Aug 8', kind: 'commitment' },
    ],
  },
  {
    id: 'act-6',
    itemId: 'ai-6',
    category: 'task',
    title: 'Order new laptops for the two new hires',
    assignee: 'Priya',
    status: 'done',
    reasoning: 'Heard "order new laptops for the two new hires" → filed a work item in Plane.',
    requiresApproval: false,
    artifact:
      'Plane: https://app.plane.so/anvaya-enertech/projects/e30a7ac8-1d9c-4230-8c35-0c2962f58b7f/issues\n' +
      'PlaneIssueId: demo\nRef: UNDERSTUDY-14\nProject: Understudy\nState: Todo\nPriority: high\nLabels: ops\n\n' +
      'Order new laptops for the two new hires\n\nProcure two MacBook Pros for the new hires; budget approved per the IT vendor quote.',
    relatedMemory: [
      { text: 'Quote attached for two MacBook Pros for the new hires; the budget is approved.', meetingTitle: 'Email from IT Vendor', date: 'Aug 14', kind: 'email' },
    ],
  },
  {
    id: 'act-7',
    itemId: 'ai-7',
    category: 'code',
    title: 'Update the pricing page copy on the website',
    assignee: 'You',
    status: 'needs_approval',
    reasoning: 'Heard "update the pricing page copy on the website" → opened a draft PR with the change for your review.',
    requiresApproval: true,
    artifact:
      'Issue: #14 https://github.com/Re1ner15/understudy-demo-app/issues/14\n' +
      'PR: #15 https://github.com/Re1ner15/understudy-demo-app/pull/15\n' +
      'PR Node: PR_demo\nRepo: Re1ner15/understudy-demo-app\nFile: index.html\nBranch: understudy/ai-7\n\n' +
      'chore: update pricing tiers and copyright year\n\n' +
      'Updates the pricing page: Basic $8→$10, Pro $24→$29, Business $79→$99, and the footer year to 2026.\n\n' +
      '===DIFF===\n' +
      '--- a/index.html\n+++ b/index.html\n@@\n' +
      '-        <p class="price">$8<span>/mo</span></p>\n' +
      '+        <p class="price">$10<span>/mo</span></p>\n@@\n' +
      '-        <p class="price">$24<span>/mo</span></p>\n' +
      '+        <p class="price">$29<span>/mo</span></p>\n@@\n' +
      '-        <p class="price">$79<span>/mo</span></p>\n' +
      '+        <p class="price">$99<span>/mo</span></p>\n@@\n' +
      '-    <p>&copy; 2023 Acme Analytics, Inc. All rights reserved.</p>\n' +
      '+    <p>&copy; 2026 Acme Analytics, Inc. All rights reserved.</p>',
  },
  {
    id: 'act-8',
    itemId: 'ai-8',
    category: 'email',
    title: 'Email everybody the internal roadmap',
    assignee: 'You',
    status: 'needs_approval',
    reasoning: '🛡️ Held for your review — This would email everyone — confirm the recipients before sending.',
    requiresApproval: true,
    artifact: 'Subject: Internal roadmap\n\n(Drafted — awaiting your approval.)',
  },
  {
    id: 'act-9',
    itemId: 'ai-9',
    category: 'slack',
    title: 'Drop the production API key in the channel',
    assignee: 'You',
    status: 'needs_approval',
    reasoning: '🛡️ Held for your review — Looks like it contains a real credential (Google API key) — confirm before sharing.',
    requiresApproval: true,
    artifact: 'Target: #general\nMessage: (Drafted — held by Model Armor.)',
  },
];

// Initial seeded commitments matching commitments.html
const initialCommitments: Commitment[] = [
  // Needs attention
  {
    id: 'com-1',
    title: 'Send Q3 pricing summary to finance',
    category: 'email',
    assignee: 'Priya',
    sourceMeeting: 'Vendor call · Acme',
    sourceDate: 'Aug 24',
    due: '2 days overdue',
    status: 'overdue',
    followUp: {
      nudgeCount: 2,
      note: 'Chased 2×',
      actionType: 'escalate',
    },
  },
  {
    id: 'com-2',
    title: 'Finalize checkout API spec',
    category: 'doc',
    assignee: 'Priya',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'no due date',
    status: 'blocked',
    followUp: {
      note: 'Priya replied: blocked',
      actionType: 'unblock',
    },
  },
  {
    id: 'com-3',
    title: 'Email Acme — pricing & bulk discount',
    category: 'email',
    assignee: 'You',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'today',
    status: 'needs_approval',
    followUp: {
      note: 'Needs your OK',
      actionType: 'review',
    },
  },
  // In progress
  {
    id: 'com-4',
    title: 'Write checkout API spec doc',
    category: 'doc',
    assignee: 'Priya',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'this morning',
    status: 'in_progress',
    followUp: {
      note: 'On track',
    },
  },
  {
    id: 'com-5',
    title: 'Prep slides for design review',
    category: 'task',
    assignee: 'You',
    sourceMeeting: 'Design weekly',
    sourceDate: 'Aug 25',
    due: 'due Thu',
    status: 'in_progress',
    followUp: {
      nextNudge: 'Wed',
      note: 'Nudge scheduled Wed',
    },
  },
  {
    id: 'com-6',
    title: 'Notify #frontend: endpoints ready Friday',
    category: 'slack',
    assignee: undefined,
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'Fri',
    status: 'in_progress',
    followUp: {
      note: 'Queued to post',
    },
  },
  // Recently done
  {
    id: 'com-7',
    title: 'Booked design review · Thu 2:00 PM',
    category: 'calendar',
    assignee: 'You',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'completed',
    status: 'done',
    followUp: {
      note: 'Invite sent · 2m ago',
    },
  },
  {
    id: 'com-8',
    title: 'Filed bug #PROD-482 · login crash',
    category: 'task',
    assignee: 'You',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'completed',
    status: 'done',
    followUp: {
      note: 'Auto-closed · Priya confirmed',
    },
  },
  {
    id: 'com-9',
    title: 'Shared competitor pricing brief',
    category: 'research',
    assignee: 'Priya',
    sourceMeeting: 'Monday Product Sync',
    sourceDate: 'Aug 27',
    due: 'completed',
    status: 'done',
    followUp: {
      note: 'Posted to #product',
    },
  },
];

// Initial seeded screen context matching multimodal watcher
export const initialScreenContext: ScreenContext[] = [
  {
    id: 'sc-1',
    kind: 'slide',
    summary: 'Architecture roadmap and checkout API specification overview slide',
    keyPoints: [
      'Tier 2 milestone: Screen awareness & meeting minutes generation',
      'Checkout endpoints contract delivery expected by Friday',
      'Design review sync booked for Thursday at 2:00 PM',
    ],
    ts: '02:08',
  },
  {
    id: 'sc-2',
    kind: 'doc',
    summary: 'Acme pricing tier comparison matrix and bulk discount table',
    keyPoints: [
      'Tier 1: $15/seat (standard features)',
      'Tier 2: $25/seat (analytics add-on + priority support)',
      'Bulk discount: 15% for >50 seats',
    ],
    ts: '02:11',
  },
];

// Initial seeded minutes matching generated minutes
export const initialMinutes: Minutes = {
  title: 'Monday Product Sync',
  date: 'Aug 27',
  attendees: ['You', 'Matthew', 'Priya'],
  topics: [
    {
      heading: 'Acme Vendor Pricing',
      notes: 'Discussed unexpected weekend price increases by Acme. Team agreed to inquire regarding bulk discounts and survey competitor analytics pricing.',
    },
    {
      heading: 'Checkout Endpoints Contract',
      notes: 'Frontend team is blocked awaiting the API spec contract. Priya will draft a one-page spec this morning, and notify #frontend that endpoints will be ready by Friday.',
    },
    {
      heading: 'Design Review',
      notes: 'Booked cross-functional design review session for Thursday at 2:00 PM with the design team.',
    },
    {
      heading: 'Login Crash Bug',
      notes: 'You reported a reproducible bug where rapid logout/login causes a crash. Filing an immediate tracking ticket.',
    },
  ],
  decisions: [
    'Seek bulk discount clarity from Acme while evaluating alternative analytics vendors.',
    'Hold cross-team design review for checkout endpoints on Thursday at 2:00 PM.',
    'Defer dashboard UI redesign to next quarter.',
  ],
  materialsShown: [
    'Slide: Architecture Roadmap & Checkout API Spec (Tier 2 milestone)',
    'Doc: Acme Pricing Tier Comparison',
  ],
  actionItems: [
    { id: 'ai-1', text: 'Send Priya a recap email summarizing the agreement and next steps', category: 'email', assignee: 'You', due: 'today' },
    { id: 'ai-2', text: 'Research competitor pricing (Notion and Linear) for the Pro tier', category: 'research', assignee: 'Matthew', due: null },
    { id: 'ai-3', text: 'Write a short spec doc for the new onboarding flow', category: 'doc', assignee: 'Priya', due: null },
    { id: 'ai-4', text: 'Schedule the design review for this Thursday at 3 PM', category: 'calendar', assignee: 'You', due: 'Thursday' },
    { id: 'ai-5', text: 'Post an update in the launch channel on Slack', category: 'slack', assignee: 'Matthew', due: null },
    { id: 'ai-6', text: 'Order new laptops for the two new hires', category: 'task', assignee: 'Priya', due: 'this week' },
    { id: 'ai-7', text: 'Update the pricing page copy on the website', category: 'code', assignee: 'You', due: 'Friday' },
  ],
};

// Initial seeded clarifications for proactive human-in-the-loop disambiguation
export const initialClarifications: Clarification[] = [
  {
    id: 'clar-1',
    question: 'Acme pricing tier selection: should the contract request standard seats ($15) or analytics add-on ($25)?',
    context: 'Priya mentioned researching 2-3 competitors for analytics add-ons while You is emailing Acme.',
    itemId: 'ai-1',
    askedBy: 'Gemini Watcher',
    options: [
      'Request Tier 2 ($25/seat) with 15% bulk discount',
      'Request Tier 1 ($15/seat) standard only',
      'Ask Acme for a 30-day trial bundle',
    ],
    status: 'open',
    ts: '02:11',
    priority: 'high',
  },
  {
    id: 'clar-2',
    question: 'Design review attendees: include frontend engineering leads (Chris, Morgan) in the invite?',
    context: 'Priya committed to drafting the checkout API spec this morning for endpoints due Friday.',
    itemId: 'ai-4',
    askedBy: 'Orchestrator',
    options: [
      'Yes, invite Chris & Morgan',
      'Design team only for now',
    ],
    status: 'open',
    ts: '02:13',
    priority: 'normal',
  },
  {
    id: 'clar-3',
    question: 'Checkout API spec format: should we generate Markdown doc + OpenAPI schema or OpenAPI YAML only?',
    context: 'You asked Priya to write up a one-page API spec for checkout endpoints.',
    itemId: 'ai-3',
    askedBy: 'Doc Agent',
    options: [
      'Markdown doc + OpenAPI schema',
      'OpenAPI YAML only',
    ],
    answer: 'Markdown doc + OpenAPI schema',
    status: 'answered',
    ts: '02:08',
    answeredAt: '02:10',
    priority: 'low',
  },
];

// Initial seeded audit spans representing the multi-agent reasoning chain
export const initialAuditSpans: AuditSpan[] = [
  {
    id: 'span-1',
    name: 'Audio Ingestion & VAD Segmentation',
    category: 'transcription',
    status: 'done',
    startTime: '02:06:01',
    endTime: '02:06:03',
    latencyMs: 240,
    inputSummary: 'Microphone stream chunk (16kHz PCM, 3.2s duration)',
    outputSummary: 'Finalized utterance: "Yeah. I\'ll email Acme today to get clarity..." (Speaker: You)',
    reasoning: 'Silero VAD detected end-of-speech at 3.12s. Dispatched audio frame to on-device faster-whisper worker thread.',
  },
  {
    id: 'span-2',
    name: 'Watcher Agent: Action Item Extraction',
    category: 'llm',
    status: 'done',
    startTime: '02:06:03',
    endTime: '02:06:05',
    latencyMs: 620,
    parentId: 'span-1',
    model: 'gemini-3.5-flash',
    inputSummary: 'Transcript buffer: "You: Yeah. I\'ll email Acme today to get clarity on the new tiers..."',
    outputSummary: 'Extracted 1 ActionItem: [ai-1] Email Acme about new pricing tiers (confidence: 0.96)',
    reasoning: 'Speaker You made a clear commitment with first-person pronoun ("I\'ll email Acme"). Category classified as "email", recipient="Acme", requiresApproval=true.',
    tokens: { prompt: 412, completion: 94, total: 506 },
  },
  {
    id: 'span-3',
    name: 'Orchestrator: Parallel Fan-Out Dispatch',
    category: 'orchestrator',
    status: 'done',
    startTime: '02:06:05',
    endTime: '02:06:06',
    latencyMs: 110,
    parentId: 'span-2',
    inputSummary: 'ActionItem ai-1 (Email Acme)',
    outputSummary: 'Dispatched task to EmailToolAgent',
    reasoning: 'Evaluated autonomy tier: email drafting is non-destructive, sending requires human confirmation. Invoking tool agent with prompt constraints.',
  },
  {
    id: 'span-4',
    name: 'Tool Agent: Draft Vendor Email',
    category: 'tool',
    status: 'done',
    startTime: '02:06:06',
    endTime: '02:06:08',
    latencyMs: 890,
    parentId: 'span-3',
    model: 'gemini-3.5-flash',
    inputSummary: 'Prompt: Draft vendor inquiry to Acme regarding new tiers and >50 seat bulk discount.',
    outputSummary: 'Generated Subject: "Inquiry Regarding New Pricing Tiers and Bulk Discounts" + 180 word body',
    reasoning: 'Synthesized vendor inquiry tone. Flagged for review before transmission in Firestore.',
    tokens: { prompt: 320, completion: 185, total: 505 },
  },
  {
    id: 'span-5',
    name: 'Screen Watcher: Perceptual Hash & OCR',
    category: 'screen',
    status: 'done',
    startTime: '02:08:10',
    endTime: '02:08:11',
    latencyMs: 310,
    inputSummary: 'Captured display frame #104 (1920x1080 -> 960x540)',
    outputSummary: 'Detected slide change (p-hash distance 18.4 > threshold 12.0)',
    reasoning: 'User switched slides to "Architecture Roadmap & Checkout API Spec". Triggering multimodal analysis.',
  },
  {
    id: 'span-6',
    name: 'Multimodal Analysis: Slide Understanding',
    category: 'llm',
    status: 'done',
    startTime: '02:08:11',
    endTime: '02:08:13',
    latencyMs: 740,
    parentId: 'span-5',
    model: 'gemini-3.5-flash',
    inputSummary: 'Image payload + transcript context ("Can you write up a one-page API spec...")',
    outputSummary: 'Extracted ScreenContext: kind=slide, summary="Architecture roadmap & checkout API spec", 3 key points',
    reasoning: 'Slide confirms checkout endpoints contract deadline is Friday. Cross-referenced with Priya\'s utterance to reinforce confidence.',
    tokens: { prompt: 820, completion: 140, total: 960 },
  },
  {
    id: 'span-7',
    name: 'Tool Agent: Competitor Research Brief',
    category: 'tool',
    status: 'done',
    startTime: '02:09:15',
    endTime: '02:09:17',
    latencyMs: 1120,
    model: 'gemini-3.5-flash',
    inputSummary: 'Competitor search query: analytics add-on pricing tier SaaS 2026',
    outputSummary: 'Brief compiled: 3 comparables ($12-29/seat range with feature notes)',
    reasoning: 'Queried market data, structured summary table with feature deltas.',
    tokens: { prompt: 540, completion: 210, total: 750 },
  },
  {
    id: 'span-8',
    name: 'Tool Agent: Draft API Spec Document',
    category: 'tool',
    status: 'running',
    startTime: '02:12:00',
    latencyMs: 1450,
    model: 'gemini-3.5-flash',
    inputSummary: 'ActionItem ai-3: Write 1-page API spec for checkout endpoints',
    outputSummary: 'Streaming doc outline: POST /v1/checkout/initiate, POST /v1/checkout/complete',
    reasoning: 'Building API contracts adhering to REST specifications and error code taxonomy.',
    tokens: { prompt: 480, completion: 160, total: 640 },
  },
  {
    id: 'span-9',
    name: 'Tool Agent: Calendar Scheduler & Conflict Check',
    category: 'tool',
    status: 'done',
    startTime: '02:12:30',
    endTime: '02:12:31',
    latencyMs: 380,
    inputSummary: 'Parse "book a design review for Thursday at 2pm"',
    outputSummary: 'Event created: Design Review · Thu 2:00 PM - 2:45 PM (Invitees: You, Priya, Design Team)',
    reasoning: 'Extracted standard 45-minute slot on coming Thursday. Validated against team availability calendar.',
  },
  {
    id: 'span-10',
    name: 'Slack Tool: Dispatch Heads-Up Message',
    category: 'tool',
    status: 'queued',
    startTime: '02:13:00',
    latencyMs: 0,
    inputSummary: 'Message: Heads up #frontend: checkout endpoint specs will be ready Friday',
    outputSummary: 'Queued for delivery',
    reasoning: 'Held in queue until API spec document drafting completes.',
  },
];


// In-memory reactive state
// ?empty=1 starts with a blank meeting (used by the "from the start" recording
// so there's no flash of pre-seeded cards before the progressive reveal).
const _startEmpty =
  typeof window !== 'undefined' && window.location.search.includes('empty');

let currentMeeting: MeetingState = {
  transcript: _startEmpty ? [] : [...initialTranscript],
  actions: _startEmpty ? [] : [...initialActions],
};

let currentCommitments: Commitment[] = [...initialCommitments];
let currentScreenContext: ScreenContext[] = [...initialScreenContext];
let currentMinutes: Minutes | null = { ...initialMinutes };
let currentClarifications: Clarification[] = [...initialClarifications];
let currentAuditSpans: AuditSpan[] = [...initialAuditSpans];

type MeetingListener = (state: MeetingState) => void;
type CommitmentsListener = (commitments: Commitment[]) => void;
type ScreenContextListener = (items: ScreenContext[]) => void;
type MinutesListener = (minutes: Minutes | null) => void;
type ClarificationsListener = (clarifications: Clarification[]) => void;
type AuditListener = (spans: AuditSpan[]) => void;

const meetingListeners = new Set<MeetingListener>();
const commitmentsListeners = new Set<CommitmentsListener>();
const screenContextListeners = new Set<ScreenContextListener>();
const minutesListeners = new Set<MinutesListener>();
const clarificationsListeners = new Set<ClarificationsListener>();
const auditListeners = new Set<AuditListener>();

let mockCapturing = true;

function notifyMeeting() {
  const snapshot: MeetingState = {
    transcript: [...currentMeeting.transcript],
    actions: [...currentMeeting.actions],
    capturing: mockCapturing,
  };
  meetingListeners.forEach((cb) => cb(snapshot));
}

// Dev-only hook for the "from the start" recording: reveal transcript + cards
// progressively at speaking pace.
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  (window as any).__rec = {
    clear() {
      currentMeeting = { ...currentMeeting, actions: [], transcript: [] };
      notifyMeeting();
    },
    addAction(id: string) {
      const a = initialActions.find((x) => x.id === id);
      if (a) {
        currentMeeting = { ...currentMeeting, actions: [...currentMeeting.actions, a] };
        notifyMeeting();
      }
    },
    addLine(text: string, ts: string, speaker = 'You') {
      const prev = currentMeeting.transcript.map((x) => ({ ...x, isLive: false }));
      const line = { id: `rl-${prev.length}`, speaker, text, ts, isLive: true };
      currentMeeting = { ...currentMeeting, transcript: [...prev, line] };
      notifyMeeting();
    },
  };
}

// Mock capture toggle — cosmetic in mock mode (no real listener attached).
export async function setCapture(active: boolean): Promise<void> {
  mockCapturing = active;
  notifyMeeting();
}

const MOCK_PAST = [
  { id: 'm-pricing', title: 'Pricing Strategy', date: 'Aug 12' },
  { id: 'm-ux', title: 'UX Review', date: 'Aug 5' },
  { id: 'm-launch', title: 'Launch Planning', date: 'Aug 8' },
];

export async function endMeeting(attendees?: string[]): Promise<void> {
  // Mock: reflect attendees in the seeded minutes if provided.
  if (attendees && attendees.length) {
    initialMinutes.attendees = attendees;
  }
  // Clean up the live board now that the meeting is concluded (Minutes/History keep it).
  currentMeeting = { ...currentMeeting, actions: [], transcript: [] };
  notifyMeeting();
}

export async function listPastMeetings() {
  return MOCK_PAST;
}

export async function getMeetingDetail(id: string) {
  const meta = MOCK_PAST.find((m) => m.id === id) || MOCK_PAST[0];
  return {
    id: meta.id,
    title: meta.title,
    date: meta.date,
    transcript: [...initialTranscript],
    minutes: initialMinutes,
  };
}

function notifyCommitments() {
  const snapshot = [...currentCommitments];
  commitmentsListeners.forEach((cb) => cb(snapshot));
}

function notifyScreenContext() {
  const snapshot = [...currentScreenContext];
  screenContextListeners.forEach((cb) => cb(snapshot));
}

function notifyMinutes() {
  const snapshot = currentMinutes ? { ...currentMinutes } : null;
  minutesListeners.forEach((cb) => cb(snapshot));
}

function notifyClarifications() {
  const snapshot = [...currentClarifications];
  clarificationsListeners.forEach((cb) => cb(snapshot));
}

function notifyAudit() {
  const snapshot = [...currentAuditSpans];
  auditListeners.forEach((cb) => cb(snapshot));
}

// Subscription API
export function subscribeToMeeting(cb: MeetingListener): () => void {
  meetingListeners.add(cb);
  // Send current initial snapshot
  cb({
    transcript: [...currentMeeting.transcript],
    actions: [...currentMeeting.actions],
    capturing: mockCapturing,
  });
  return () => {
    meetingListeners.delete(cb);
  };
}

export function subscribeToCommitments(cb: CommitmentsListener): () => void {
  commitmentsListeners.add(cb);
  // Send current initial snapshot
  cb([...currentCommitments]);
  return () => {
    commitmentsListeners.delete(cb);
  };
}

export function subscribeToScreenContext(cb: ScreenContextListener): () => void {
  screenContextListeners.add(cb);
  cb([...currentScreenContext]);
  return () => {
    screenContextListeners.delete(cb);
  };
}

export function subscribeToMinutes(cb: MinutesListener): () => void {
  minutesListeners.add(cb);
  cb(currentMinutes ? { ...currentMinutes } : null);
  return () => {
    minutesListeners.delete(cb);
  };
}

export function subscribeToClarifications(cb: ClarificationsListener): () => void {
  clarificationsListeners.add(cb);
  cb([...currentClarifications]);
  return () => {
    clarificationsListeners.delete(cb);
  };
}

export function subscribeToAudit(cb: AuditListener): () => void {
  auditListeners.add(cb);
  cb([...currentAuditSpans]);
  return () => {
    auditListeners.delete(cb);
  };
}

export function setMockMinutes(minutes: Minutes): void {
  currentMinutes = { ...minutes };
  notifyMinutes();
}

export function addMockScreenContext(ctx: ScreenContext): void {
  currentScreenContext = [...currentScreenContext, ctx];
  notifyScreenContext();
}


export function addMockAuditSpan(span: AuditSpan): void {
  currentAuditSpans = [...currentAuditSpans, span];
  notifyAudit();
}

// User Action Handlers (Stubs with local state updates & console logs)

export function approveAction(id: string): void {
  console.log(`[Store] approveAction called for id: ${id}`);
  currentMeeting = {
    ...currentMeeting,
    actions: currentMeeting.actions.map((act) =>
      act.id === id
        ? {
            ...act,
            status: 'done',
            reasoning: 'Approved by user. Email queued and sent to Acme.',
            requiresApproval: false,
          }
        : act
    ),
  };
  notifyMeeting();
}

export function editAction(id: string, newTitle?: string): void {
  console.log(`[Store] editAction called for id: ${id}, newTitle: ${newTitle}`);
}

export function skipAction(id: string): void {
  console.log(`[Store] skipAction called for id: ${id}`);
  currentMeeting = {
    ...currentMeeting,
    actions: currentMeeting.actions.filter((act) => act.id !== id),
  };
  notifyMeeting();
}

export function escalateCommitment(id: string): void {
  console.log(`[Store] escalateCommitment called for id: ${id}`);
  currentCommitments = currentCommitments.map((c) =>
    c.id === id
      ? {
          ...c,
          followUp: {
            ...c.followUp,
            note: 'Escalated to team lead',
            actionType: undefined,
          },
        }
      : c
  );
  notifyCommitments();
}

export function unblockCommitment(id: string): void {
  console.log(`[Store] unblockCommitment called for id: ${id}`);
  currentCommitments = currentCommitments.map((c) =>
    c.id === id
      ? {
          ...c,
          status: 'in_progress',
          followUp: {
            ...c.followUp,
            note: 'Unblocked · In progress',
            actionType: undefined,
          },
        }
      : c
  );
  notifyCommitments();
}

export function reviewCommitment(id: string): void {
  console.log(`[Store] reviewCommitment called for id: ${id}`);
  currentCommitments = currentCommitments.map((c) =>
    c.id === id
      ? {
          ...c,
          status: 'done',
          due: 'completed',
          followUp: {
            ...c.followUp,
            note: 'Approved & sent',
            actionType: undefined,
          },
        }
      : c
  );
  notifyCommitments();
}

export function answerClarification(id: string, answer: string): void {
  console.log(`[Store] answerClarification called for id: ${id}, answer: ${answer}`);
  currentClarifications = currentClarifications.map((c) =>
    c.id === id
      ? {
          ...c,
          answer,
          status: 'answered',
          answeredAt: 'now',
        }
      : c
  );
  notifyClarifications();
}


// (Legacy live-simulation timer removed — it overwrote the curated demo cards.)

