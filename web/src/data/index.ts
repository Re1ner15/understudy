import * as mockStore from './store';
import * as firestoreStore from './firestore';

export * from './types';
export * from './api';

const isFirestore = import.meta.env.VITE_DATA_SOURCE === 'firestore';

export const subscribeToMeeting = isFirestore
  ? firestoreStore.subscribeToMeeting
  : mockStore.subscribeToMeeting;

export const subscribeToCommitments = isFirestore
  ? firestoreStore.subscribeToCommitments
  : mockStore.subscribeToCommitments;

export const subscribeToScreenContext = isFirestore
  ? firestoreStore.subscribeToScreenContext
  : mockStore.subscribeToScreenContext;

export const subscribeToMinutes = isFirestore
  ? firestoreStore.subscribeToMinutes
  : mockStore.subscribeToMinutes;

export const approveAction = isFirestore
  ? firestoreStore.approveAction
  : mockStore.approveAction;

export const editAction = isFirestore
  ? firestoreStore.editAction
  : mockStore.editAction;

export const skipAction = isFirestore
  ? firestoreStore.skipAction
  : mockStore.skipAction;

export const escalateCommitment = isFirestore
  ? firestoreStore.escalateCommitment
  : mockStore.escalateCommitment;

export const unblockCommitment = isFirestore
  ? firestoreStore.unblockCommitment
  : mockStore.unblockCommitment;

export const reviewCommitment = isFirestore
  ? firestoreStore.reviewCommitment
  : mockStore.reviewCommitment;

export const subscribeToClarifications = isFirestore
  ? firestoreStore.subscribeToClarifications
  : mockStore.subscribeToClarifications;

export const subscribeToAudit = isFirestore
  ? firestoreStore.subscribeToAudit
  : mockStore.subscribeToAudit;

export const answerClarification = isFirestore
  ? firestoreStore.answerClarification
  : mockStore.answerClarification;

export const setCapture = isFirestore
  ? firestoreStore.setCapture
  : mockStore.setCapture;

export const endMeeting = isFirestore
  ? firestoreStore.endMeeting
  : mockStore.endMeeting;

export const listPastMeetings = isFirestore
  ? firestoreStore.listPastMeetings
  : mockStore.listPastMeetings;

export const getMeetingDetail = isFirestore
  ? firestoreStore.getMeetingDetail
  : mockStore.getMeetingDetail;

