export type ActionCategory = 'email' | 'calendar' | 'doc' | 'research' | 'task' | 'slack' | 'code';

export type ToolStatus = 'queued' | 'running' | 'done' | 'needs_approval' | 'error';

export type CommitmentStatus = 'open' | 'in_progress' | 'blocked' | 'done' | 'needs_approval' | 'overdue';

export interface TranscriptLine {
  id: string;
  speaker: string;
  text: string;
  ts: string;
  isLive?: boolean;
}

export interface ActionItem {
  id: string;
  text: string;
  category: ActionCategory;
  assignee?: string;
  due?: string;
  sourceQuote: string;
  confidence: number;
}

export interface LiveAction {
  id: string;
  itemId: string;
  category: ActionCategory;
  title: string;
  assignee?: string;
  status: ToolStatus;
  reasoning: string;
  artifact?: string;
  requiresApproval: boolean;
  relatedMemory?: Array<{ text: string; meetingTitle: string; date: string; kind?: string; score?: number }>;
}

export interface FollowUpInfo {
  nudgeCount?: number;
  lastNudge?: string;
  nextNudge?: string;
  note?: string;
  actionType?: 'escalate' | 'unblock' | 'review';
}

export interface Commitment {
  id: string;
  title: string;
  category: ActionCategory;
  assignee?: string;
  sourceMeeting: string;
  sourceDate: string;
  due?: string;
  status: CommitmentStatus;
  followUp?: FollowUpInfo;
  artifact?: string;
}

export interface MeetingState {
  transcript: TranscriptLine[];
  actions: LiveAction[];
  capturing?: boolean;
}

export interface PastMeetingSummary {
  id: string;
  title: string;
  date: string;
}

export type ScreenContextKind = 'slide' | 'website' | 'doc' | 'code' | 'app' | 'other';

export interface ScreenContext {
  id?: string;
  kind: ScreenContextKind;
  summary: string;
  keyPoints: string[];
  ts: string;
}

export interface TopicNote {
  heading: string;
  notes: string;
}

export interface MinutesActionItem {
  id: string;
  text: string;
  category: ActionCategory | string;
  assignee?: string | null;
  due?: string | null;
}

export interface Minutes {
  title: string;
  date: string;
  attendees: string[];
  topics: TopicNote[];
  decisions: string[];
  materialsShown: string[];
  actionItems: MinutesActionItem[];
}

export type ClarificationStatus = 'open' | 'answered' | 'dismissed';

export interface Clarification {
  id: string;
  question: string;
  context?: string;
  itemId?: string;
  askedBy?: string;
  options?: string[];
  answer?: string;
  status: ClarificationStatus;
  ts: string;
  answeredAt?: string;
  priority?: 'high' | 'normal' | 'low';
}

export type AuditSpanStatus = 'done' | 'running' | 'error' | 'queued';

export type AuditCategory =
  | 'orchestrator'
  | 'llm'
  | 'tool'
  | 'transcription'
  | 'screen'
  | 'scanner';

export interface AuditSpan {
  id: string;
  name: string;
  category: AuditCategory;
  status: AuditSpanStatus;
  startTime: string;
  endTime?: string;
  latencyMs: number;
  parentId?: string;
  model?: string;
  inputSummary?: string;
  outputSummary?: string;
  reasoning?: string;
  tokens?: {
    prompt?: number;
    completion?: number;
    total?: number;
  };
  metadata?: Record<string, any>;
}


