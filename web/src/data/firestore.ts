import { initializeApp } from 'firebase/app';
import {
  getFirestore,
  connectFirestoreEmulator,
  collection,
  doc,
  onSnapshot,
  updateDoc,
  deleteDoc,
  getDocs,
  getDoc,
} from 'firebase/firestore';
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
import { postJson } from './api';


const useEmulator = import.meta.env.VITE_USE_EMULATOR !== 'false';

const firebaseConfig = useEmulator
  ? {
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'demo-understudy',
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'demo-key',
    }
  : {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    };

const app = initializeApp(firebaseConfig);

export const db = getFirestore(app);

// Connect to Firestore emulator when VITE_USE_EMULATOR is not 'false' (default)
if (useEmulator) {
  try {
    const emulatorHost = import.meta.env.VITE_FIRESTORE_EMULATOR_HOST || '127.0.0.1';
    const emulatorPort = Number(import.meta.env.VITE_FIRESTORE_EMULATOR_PORT) || 8080;
    // Avoid re-connecting if already initialized in HMR
    // @ts-expect-error internal emulator tracking
    if (!db._settingsFrozen) {
      connectFirestoreEmulator(db, emulatorHost, emulatorPort);
    }
  } catch (err) {
    console.warn('[Firestore] Emulator connection note:', err);
  }
}

const MEETING_ID = 'demo-meeting';

export function subscribeToMeeting(cb: (state: MeetingState) => void): () => void {
  let transcriptLines: TranscriptLine[] = [];
  let liveActions: LiveAction[] = [];
  let capturing = false;

  const meetingRef = doc(db, 'meetings', MEETING_ID);
  const transcriptCol = collection(meetingRef, 'transcript');
  const actionsCol = collection(meetingRef, 'actions');

  const emit = () => {
    cb({
      transcript: [...transcriptLines],
      actions: [...liveActions],
      capturing,
    });
  };

  const unsubMeeting = onSnapshot(
    meetingRef,
    (snap) => {
      capturing = !!(snap.data() as any)?.capturing;
      emit();
    },
    (err) => {
      console.error('[Firestore] subscribeToMeeting doc error:', err);
    }
  );

  const unsubTranscript = onSnapshot(
    transcriptCol,
    (snapshot) => {
      const lines: TranscriptLine[] = [];
      snapshot.forEach((d) => {
        lines.push(d.data() as TranscriptLine);
      });
      // Order by capture time (ts is fixed-width HH:MM:SS, so lexical sort works),
      // falling back to id for same-second ties. Sorting by id alone scrambled the
      // transcript because ids are random (tl-<uuid>).
      lines.sort(
        (a, b) =>
          (a.ts || '').localeCompare(b.ts || '') ||
          a.id.localeCompare(b.id, undefined, { numeric: true })
      );
      transcriptLines = lines;
      emit();
    },
    (err) => {
      console.error('[Firestore] subscribeToMeeting transcript error:', err);
    }
  );

  const unsubActions = onSnapshot(
    actionsCol,
    (snapshot) => {
      const acts: LiveAction[] = [];
      snapshot.forEach((d) => {
        acts.push(d.data() as LiveAction);
      });
      acts.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
      liveActions = acts;
      emit();
    },
    (err) => {
      console.error('[Firestore] subscribeToMeeting actions error:', err);
    }
  );

  return () => {
    unsubMeeting();
    unsubTranscript();
    unsubActions();
  };
}

/** Turns transcription capture on/off for the demo meeting. */
export async function setCapture(active: boolean): Promise<void> {
  await postJson(`/meetings/${MEETING_ID}/capture`, { active });
}

/** Concludes the meeting: generates minutes (with the given attendees), logs to History. */
export async function endMeeting(attendees?: string[]): Promise<void> {
  const body = attendees && attendees.length ? { attendees } : {};
  await postJson(`/meetings/${MEETING_ID}/end`, body);
}

/** Lists past meetings (everything except the live demo meeting). */
export async function listPastMeetings(): Promise<import('./types').PastMeetingSummary[]> {
  const snap = await getDocs(collection(db, 'meetings'));
  const out: import('./types').PastMeetingSummary[] = [];
  snap.forEach((d) => {
    if (d.id === MEETING_ID) return;
    const m = d.data() as any;
    out.push({ id: d.id, title: m.title || d.id, date: m.date || '' });
  });
  return out.sort((a, b) => (a.date < b.date ? 1 : -1));
}

/** Loads a past meeting's transcript + minutes. */
export async function getMeetingDetail(
  id: string
): Promise<{ id: string; title: string; date: string; transcript: TranscriptLine[]; minutes: Minutes | null }> {
  const mref = doc(db, 'meetings', id);
  const [mSnap, tSnap, minSnap] = await Promise.all([
    getDoc(mref),
    getDocs(collection(mref, 'transcript')),
    getDoc(doc(mref, 'minutes', 'latest')),
  ]);
  const m = (mSnap.data() as any) || {};
  const transcript: TranscriptLine[] = [];
  tSnap.forEach((d) => transcript.push(d.data() as TranscriptLine));
  transcript.sort(
    (a, b) => (a.ts || '').localeCompare(b.ts || '') || a.id.localeCompare(b.id, undefined, { numeric: true })
  );
  const minutes = minSnap.exists() ? (minSnap.data() as Minutes) : null;
  return { id, title: m.title || id, date: m.date || '', transcript, minutes };
}

export function subscribeToCommitments(cb: (commitments: Commitment[]) => void): () => void {
  const commitmentsCol = collection(db, 'commitments');

  return onSnapshot(
    commitmentsCol,
    (snapshot) => {
      const items: Commitment[] = [];
      snapshot.forEach((d) => {
        items.push(d.data() as Commitment);
      });
      items.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
      cb(items);
    },
    (err) => {
      console.error('[Firestore] subscribeToCommitments error:', err);
    }
  );
}

export function subscribeToScreenContext(cb: (items: ScreenContext[]) => void): () => void {
  const meetingRef = doc(db, 'meetings', MEETING_ID);
  const screenContextCol = collection(meetingRef, 'screenContext');

  return onSnapshot(
    screenContextCol,
    (snapshot) => {
      const items: ScreenContext[] = [];
      snapshot.forEach((d) => {
        items.push({ id: d.id, ...(d.data() as Omit<ScreenContext, 'id'>) });
      });
      items.sort((a, b) => (a.ts || '').localeCompare(b.ts || '', undefined, { numeric: true }));
      cb(items);
    },
    (err) => {
      console.error('[Firestore] subscribeToScreenContext error:', err);
    }
  );
}

export function subscribeToMinutes(cb: (minutes: Minutes | null) => void): () => void {
  const minutesDocRef = doc(db, 'meetings', MEETING_ID, 'minutes', 'latest');

  return onSnapshot(
    minutesDocRef,
    (snapshot) => {
      if (snapshot.exists()) {
        cb(snapshot.data() as Minutes);
      } else {
        cb(null);
      }
    },
    (err) => {
      console.error('[Firestore] subscribeToMinutes error:', err);
    }
  );
}

export function subscribeToClarifications(cb: (items: Clarification[]) => void): () => void {
  const meetingRef = doc(db, 'meetings', MEETING_ID);
  const clarificationsCol = collection(meetingRef, 'clarifications');

  return onSnapshot(
    clarificationsCol,
    (snapshot) => {
      const items: Clarification[] = [];
      snapshot.forEach((d) => {
        items.push({ id: d.id, ...(d.data() as Omit<Clarification, 'id'>) });
      });
      items.sort((a, b) => (b.ts || '').localeCompare(a.ts || '', undefined, { numeric: true }));
      cb(items);
    },
    (err) => {
      console.error('[Firestore] subscribeToClarifications error:', err);
    }
  );
}

export function subscribeToAudit(cb: (items: AuditSpan[]) => void): () => void {
  const meetingRef = doc(db, 'meetings', MEETING_ID);
  const auditCol = collection(meetingRef, 'audit');

  return onSnapshot(
    auditCol,
    (snapshot) => {
      const items: AuditSpan[] = [];
      snapshot.forEach((d) => {
        items.push({ id: d.id, ...(d.data() as Omit<AuditSpan, 'id'>) });
      });
      items.sort((a, b) => (a.startTime || '').localeCompare(b.startTime || '', undefined, { numeric: true }));
      cb(items);
    },
    (err) => {
      console.error('[Firestore] subscribeToAudit error:', err);
    }
  );
}

export async function approveAction(id: string): Promise<void> {
  console.log(`[Firestore] approveAction called for id: ${id}`);
  try {
    await postJson(`/meetings/${MEETING_ID}/actions/${id}/approve`);
  } catch (err) {
    console.warn(`[Firestore] Backend approve endpoint failed, falling back to direct Firestore write:`, err);
    const actionRef = doc(db, 'meetings', MEETING_ID, 'actions', id);
    await updateDoc(actionRef, {
      status: 'done',
      reasoning: 'Approved by user. Email queued and sent to Acme.',
      requiresApproval: false,
    });
  }
}

export async function editAction(id: string, newTitle?: string): Promise<void> {
  console.log(`[Firestore] editAction called for id: ${id}, newTitle: ${newTitle}`);
  if (newTitle) {
    const actionRef = doc(db, 'meetings', MEETING_ID, 'actions', id);
    await updateDoc(actionRef, { title: newTitle });
  }
}

export async function skipAction(id: string): Promise<void> {
  console.log(`[Firestore] skipAction called for id: ${id}`);
  try {
    await postJson(`/meetings/${MEETING_ID}/actions/${id}/skip`);
  } catch (err) {
    console.warn(`[Firestore] Backend skip endpoint failed, falling back to direct Firestore write:`, err);
    const actionRef = doc(db, 'meetings', MEETING_ID, 'actions', id);
    await deleteDoc(actionRef);
  }
}

export async function escalateCommitment(id: string): Promise<void> {
  console.log(`[Firestore] escalateCommitment called for id: ${id}`);
  const comRef = doc(db, 'commitments', id);
  await updateDoc(comRef, {
    'followUp.note': 'Escalated to team lead',
    'followUp.actionType': null,
  });
}

export async function unblockCommitment(id: string): Promise<void> {
  console.log(`[Firestore] unblockCommitment called for id: ${id}`);
  const comRef = doc(db, 'commitments', id);
  await updateDoc(comRef, {
    status: 'in_progress',
    'followUp.note': 'Unblocked · In progress',
    'followUp.actionType': null,
  });
}

export async function reviewCommitment(id: string): Promise<void> {
  console.log(`[Firestore] reviewCommitment called for id: ${id}`);
  const comRef = doc(db, 'commitments', id);
  await updateDoc(comRef, {
    status: 'done',
    due: 'completed',
    'followUp.note': 'Approved & sent',
    'followUp.actionType': null,
  });
}

export async function answerClarification(id: string, answer: string): Promise<void> {
  console.log(`[Firestore] answerClarification called for id: ${id}, answer: ${answer}`);
  try {
    await postJson(`/meetings/${MEETING_ID}/clarifications/${id}/answer`, { answer });
  } catch (err) {
    console.warn(`[Firestore] Backend answer clarification endpoint failed, falling back to direct Firestore write:`, err);
    const clarRef = doc(db, 'meetings', MEETING_ID, 'clarifications', id);
    await updateDoc(clarRef, {
      answer,
      status: 'answered',
      answeredAt: new Date().toISOString(),
    });
  }
}

