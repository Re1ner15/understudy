import React, { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { subscribeToMeeting, subscribeToScreenContext, setCapture, endMeeting } from '../data';
import { MeetingState, ScreenContext, ScreenContextKind } from '../data/types';
import { Avatar } from '../components/Avatar';
import { ActionCard } from '../components/ActionCard';

const ScreenContextIcon: React.FC<{ kind: ScreenContextKind }> = ({ kind }) => {
  const iconProps = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    style: { width: '12px', height: '12px' },
  };

  switch (kind) {
    case 'slide':
      return (
        <svg {...iconProps}>
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      );
    case 'website':
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      );
    case 'doc':
      return (
        <svg {...iconProps}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case 'code':
      return (
        <svg {...iconProps}>
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      );
    case 'app':
      return (
        <svg {...iconProps}>
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      );
    case 'other':
    default:
      return (
        <svg {...iconProps}>
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
        </svg>
      );
  }
};

export const MeetingView: React.FC = () => {
  const [meetingState, setMeetingState] = useState<MeetingState>({
    transcript: [],
    actions: [],
  });
  const [screenContexts, setScreenContexts] = useState<ScreenContext[]>([]);
  const [ending, setEnding] = useState(false);
  const [concluding, setConcluding] = useState(false);
  const [attendeesInput, setAttendeesInput] = useState('');
  const [micStarting, setMicStarting] = useState(false);

  useEffect(() => {
    const unsubMeeting = subscribeToMeeting((state) => {
      setMeetingState(state);
    });
    const unsubScreen = subscribeToScreenContext((items) => {
      setScreenContexts(items);
    });
    return () => {
      unsubMeeting();
      unsubScreen();
    };
  }, []);

  const pendingCount = meetingState.actions.filter((a) => a.status === 'needs_approval').length;
  const totalCount = meetingState.actions.length;

  // Ordering: not-done (needs-approval / running / queued) on top, done sinks to
  // the bottom — chronological within each group. When all are done they're
  // naturally chronological again.
  const doneRank = (s: string) => (s === 'done' || s === 'error' ? 1 : 0);
  const chrono = (id: string) => {
    const m = id.match(/(\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  };
  const sortedActions = [...meetingState.actions].sort(
    (a, b) => doneRank(a.status) - doneRank(b.status) || chrono(a.id) - chrono(b.id)
  );

  // FLIP animation: cards fade/slide in and glide smoothly when they reorder.
  const feedRef = useRef<HTMLDivElement>(null);
  const prevRects = useRef<Map<string, DOMRect>>(new Map());
  const orderKey = sortedActions.map((a) => `${a.id}:${a.status}`).join(',');
  useLayoutEffect(() => {
    const container = feedRef.current;
    if (!container) return;
    const cards = Array.from(container.querySelectorAll<HTMLElement>('[data-card-id]'));
    const newRects = new Map<string, DOMRect>();
    cards.forEach((el) => {
      const id = el.dataset.cardId as string;
      const rect = el.getBoundingClientRect();
      newRects.set(id, rect);
      const prev = prevRects.current.get(id);
      if (prev) {
        const dy = prev.top - rect.top;
        if (Math.abs(dy) > 1) {
          el.style.transition = 'none';
          el.style.transform = `translateY(${dy}px)`;
          requestAnimationFrame(() => {
            el.style.transition = 'transform 480ms cubic-bezier(0.22,1,0.36,1)';
            el.style.transform = '';
          });
        }
      } else {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-10px) scale(0.98)';
        requestAnimationFrame(() => {
          el.style.transition = 'opacity 420ms ease, transform 420ms cubic-bezier(0.22,1,0.36,1)';
          el.style.opacity = '1';
          el.style.transform = '';
        });
      }
    });
    prevRects.current = newRects;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderKey]);

  return (
    <div
      className="body"
      style={{
        display: 'grid',
        gridTemplateColumns: '38% 62%',
        flex: 1,
        minHeight: 0,
      }}
    >
      {/* Left column: Transcript */}
      <div
        className="col left"
        style={{
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          borderRight: '1px solid var(--line)',
        }}
      >
        <div
          className="colhead"
          style={{
            padding: '17px 22px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <h2
            style={{
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              color: 'var(--faint)',
              fontWeight: 650,
            }}
          >
            Transcript
          </h2>
          {(() => {
            const rec = meetingState.capturing;
            const accent = micStarting ? '#f59e0b' : rec ? '#ef4444' : 'var(--faint)';
            return (
              <button
                onClick={() => {
                  const next = !rec;
                  setCapture(next);
                  if (next) {
                    // Mic spawns on Record; warm-up (~2s to load Whisper). Show it.
                    setMicStarting(true);
                    setTimeout(() => setMicStarting(false), 2500);
                  } else {
                    setMicStarting(false);
                  }
                }}
                title={rec ? 'Pause capture (stop transcribing)' : 'Start recording — mic starts in ~2s'}
                style={{
                  marginLeft: 'auto',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '7px',
                  fontSize: '12px',
                  fontWeight: 650,
                  padding: '6px 12px',
                  borderRadius: '999px',
                  cursor: 'pointer',
                  border: `1px solid ${micStarting ? '#f59e0b' : rec ? '#ef4444' : 'var(--line)'}`,
                  background: micStarting ? 'rgba(245,158,11,0.1)' : rec ? 'rgba(239,68,68,0.08)' : 'var(--chip)',
                  color: accent,
                }}
              >
                <span
                  style={{
                    width: '9px',
                    height: '9px',
                    borderRadius: '50%',
                    background: accent,
                    animation: (rec || micStarting) ? 'pulse-emerald 1.5s infinite' : 'none',
                    display: 'inline-block',
                  }}
                />
                {micStarting ? 'Starting mic…' : rec ? 'Recording — Pause' : 'Paused — Record'}
              </button>
            );
          })()}
        </div>

        <div
          className="transcript"
          style={{
            overflowY: 'auto',
            padding: '0 22px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            flex: 1,
          }}
        >
          {meetingState.transcript.map((line) => (
            <div
              key={line.id}
              className={`line ${line.isLive ? 'now' : ''}`}
              style={{
                display: 'flex',
                gap: '11px',
                ...(line.isLive
                  ? {
                      background: 'var(--accent-soft)',
                      margin: '0 -12px',
                      padding: '9px 12px',
                      borderRadius: '10px',
                      borderLeft: '2px solid var(--accent)',
                    }
                  : {}),
              }}
            >
              <Avatar name={line.speaker} size="md" />
              <div>
                <div
                  className="who"
                  style={{
                    fontWeight: 650,
                    fontSize: '13px',
                    marginBottom: '2px',
                  }}
                >
                  {line.speaker}
                  <span
                    style={{
                      color: 'var(--faint)',
                      fontWeight: 400,
                      fontSize: '11px',
                      marginLeft: '7px',
                    }}
                  >
                    {line.ts}
                  </span>
                </div>
                <div
                  className="say"
                  style={{
                    color: line.isLive ? 'var(--txt)' : 'var(--muted)',
                    lineHeight: 1.5,
                  }}
                >
                  {line.text}
                  {line.isLive && (
                    <span
                      className="typing"
                      style={{
                        display: 'inline-block',
                        width: '7px',
                        height: '14px',
                        background: 'var(--accent)',
                        marginLeft: '3px',
                        verticalAlign: '-2px',
                        animation: 'blink 1s steps(2) infinite',
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Materials shown strip */}
        {screenContexts.length > 0 && (
          <div
            className="materials-strip"
            style={{
              borderTop: '1px solid var(--line)',
              padding: '12px 20px',
              background: 'var(--panel)',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                marginBottom: '8px',
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: 'var(--run)',
                }}
              />
              <h3
                style={{
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '.08em',
                  color: 'var(--faint)',
                  fontWeight: 700,
                }}
              >
                Materials Shown
              </h3>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: '11px',
                  color: 'var(--muted)',
                  background: 'var(--chip)',
                  padding: '1px 6px',
                  borderRadius: '8px',
                  fontWeight: 600,
                }}
              >
                {screenContexts.length}
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                maxHeight: '120px',
                overflowY: 'auto',
              }}
            >
              {screenContexts.map((item, idx) => (
                <div
                  key={item.id || idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'var(--chip)',
                    borderRadius: '8px',
                    padding: '6px 10px',
                    fontSize: '12px',
                  }}
                >
                  <div
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '5px',
                      background: 'var(--panel)',
                      border: '1px solid var(--line)',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--muted)',
                      flexShrink: 0,
                    }}
                  >
                    <ScreenContextIcon kind={item.kind} />
                  </div>
                  <span
                    style={{
                      fontWeight: 550,
                      color: 'var(--txt)',
                      flex: 1,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={item.summary}
                  >
                    {item.summary}
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      color: 'var(--faint)',
                      flexShrink: 0,
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {item.ts}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right column: Activity feed */}
      <div
        className="col right"
        style={{
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          className="colhead"
          style={{
            padding: '17px 22px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <h2
            style={{
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              color: 'var(--faint)',
              fontWeight: 650,
            }}
          >
            What Understudy is doing
          </h2>
          <span className="count" style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--muted)' }}>
            {totalCount} actions · {pendingCount} {pendingCount === 1 ? 'needs you' : 'need you'}
          </span>
          {!concluding ? (
            <button
              onClick={() => setConcluding(true)}
              disabled={ending}
              title="Generate minutes, log this meeting to History, and track its tasks in Commitments"
              style={{
                marginLeft: '12px', fontSize: '12px', fontWeight: 650, padding: '6px 13px',
                borderRadius: '8px', border: '1px solid var(--accent)',
                background: ending ? 'var(--chip)' : 'var(--accent)',
                color: ending ? 'var(--muted)' : 'var(--on-accent)',
                cursor: ending ? 'default' : 'pointer', whiteSpace: 'nowrap',
              }}
            >
              {ending ? 'Concluding…' : 'Conclude meeting'}
            </button>
          ) : (
            <div style={{ marginLeft: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                autoFocus
                value={attendeesInput}
                onChange={(e) => setAttendeesInput(e.target.value)}
                placeholder="Attendees (comma-separated)"
                style={{
                  fontSize: '12px', padding: '6px 10px', borderRadius: '8px',
                  border: '1px solid var(--line)', width: '240px', background: 'var(--panel)', color: 'var(--txt)',
                }}
                onKeyDown={(e) => { if (e.key === 'Escape') setConcluding(false); }}
              />
              <button
                onClick={async () => {
                  setEnding(true);
                  const names = attendeesInput.split(',').map((s) => s.trim()).filter(Boolean);
                  try { await endMeeting(names); } finally { setEnding(false); setConcluding(false); }
                }}
                style={{
                  fontSize: '12px', fontWeight: 650, padding: '6px 12px', borderRadius: '8px',
                  border: '1px solid var(--accent)', background: 'var(--accent)', color: 'var(--on-accent)', cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >
                {ending ? 'Concluding…' : 'Generate minutes'}
              </button>
              <button
                onClick={() => setConcluding(false)}
                style={{ fontSize: '12px', padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--line)', background: 'var(--chip)', color: 'var(--muted)', cursor: 'pointer' }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        <div
          className="feed"
          ref={feedRef}
          style={{
            overflowY: 'auto',
            padding: '0 22px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '11px',
            flex: 1,
          }}
        >
          {sortedActions.length === 0 && (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--faint)', fontSize: '13px' }}>
              Nothing in progress. Actions appear here as the meeting is captured; once you
              conclude, they move to Minutes &amp; History.
            </div>
          )}
          {sortedActions.map((action) => (
            <div key={action.id} data-card-id={action.id} style={{ willChange: 'transform, opacity' }}>
              <ActionCard action={action} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
