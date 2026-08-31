import React, { useState, useEffect } from 'react';
import { Logo } from '../components/Logo';
import { subscribeToMeeting, approveAction, skipAction, subscribeToClarifications, answerClarification, setCapture } from '../data';
import { MeetingState, Clarification } from '../data/types';

export const CompanionView: React.FC = () => {
  const [meetingState, setMeetingState] = useState<MeetingState>({
    transcript: [],
    actions: [],
  });
  const [clarifications, setClarifications] = useState<Clarification[]>([]);
  const [seconds, setSeconds] = useState(134);
  const [isCollapsed, setIsCollapsed] = useState<boolean>(true);

  // Scoped transparency for /companion route only
  useEffect(() => {
    document.documentElement.classList.add('companion-mode');
    document.body.classList.add('companion-mode');
    return () => {
      document.documentElement.classList.remove('companion-mode');
      document.body.classList.remove('companion-mode');
    };
  }, []);

  useEffect(() => {
    const unsubMeeting = subscribeToMeeting((state) => {
      setMeetingState(state);
    });
    const unsubClar = subscribeToClarifications((items) => {
      setClarifications(items);
    });
    return () => {
      unsubMeeting();
      unsubClar();
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const runningAction = meetingState.actions.find((a) => a.status === 'running');
  const pendingActions = meetingState.actions.filter((a) => a.status === 'needs_approval');
  const pendingAction = pendingActions[0];
  const doneActions = meetingState.actions.filter((a) => a.status === 'done');
  const totalActions = meetingState.actions.length;

  const pendingCount = pendingActions.length;
  const isMeetingActive = totalActions > 0 || meetingState.transcript.length > 0;

  return (
    <div
      className="companion-root"
      style={{
        margin: '8px',
        display: 'inline-block',
        width: 'fit-content',
        height: 'fit-content',
        fontFamily: 'Inter, -apple-system, "SF Pro Text", system-ui, sans-serif',
        userSelect: 'none',
      }}
    >
      {isCollapsed ? (
        /* COLLAPSED STATE: ~56px rounded-square Understudy logo chip */
        <div
          className="companion-chip"
          onClick={() => setIsCollapsed(false)}
          title="Open Understudy Companion"
          style={{
            width: '56px',
            height: '56px',
            background: 'var(--panel, #ffffff)',
            border: '1px solid var(--line, #e3e6df)',
            borderRadius: '14px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            position: 'relative',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.04)';
            e.currentTarget.style.boxShadow = '0 10px 28px rgba(0,0,0,0.16), 0 3px 8px rgba(0,0,0,0.08)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)';
          }}
        >
          <img
            src="/understudy-mark.svg"
            alt="Understudy"
            width={34}
            height={34}
            style={{ display: 'block', borderRadius: '8px' }}
          />

          {/* Badge: numeric count if needs_approval, else live pulse dot if meeting active, else none */}
          {pendingCount > 0 ? (
            <div
              className="badge-count"
              style={{
                position: 'absolute',
                top: '-5px',
                right: '-5px',
                minWidth: '18px',
                height: '18px',
                padding: '0 5px',
                borderRadius: '9px',
                background: 'var(--amber, #b7791f)',
                color: '#ffffff',
                fontSize: '11px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '2px solid var(--panel, #ffffff)',
                boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
                lineHeight: 1,
              }}
            >
              {pendingCount}
            </div>
          ) : isMeetingActive ? (
            <div
              className="badge-live-pulse"
              style={{
                position: 'absolute',
                top: '-2px',
                right: '-2px',
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent, #0f9d6b)',
                border: '2px solid var(--panel, #ffffff)',
                animation: 'pulse-emerald 1.8s infinite',
              }}
            />
          ) : null}
        </div>
      ) : (
        /* EXPANDED STATE: Full companion card */
        <div
          className="companion"
          style={{
            width: '340px',
            background: 'var(--panel, #ffffff)',
            border: '1px solid var(--line, #e3e6df)',
            borderRadius: '16px',
            boxShadow: '0 12px 40px rgba(0,0,0,.15), 0 2px 8px rgba(0,0,0,.08)',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            className="ch"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 14px',
              borderBottom: '1px solid var(--line, #e3e6df)',
            }}
          >
            <Logo size={16} showWordmark style={{ fontSize: '13.5px' }} />
            <button
              className="live"
              onClick={() => setCapture(!meetingState.capturing)}
              title={meetingState.capturing ? 'Pause capture (stop transcribing)' : 'Start recording'}
              style={{
                marginLeft: 'auto',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11.5px',
                fontWeight: 600,
                padding: '4px 9px',
                borderRadius: '999px',
                cursor: 'pointer',
                border: `1px solid ${meetingState.capturing ? 'rgba(239,83,80,0.5)' : 'var(--line, #e6e9e4)'}`,
                background: meetingState.capturing ? 'rgba(239,83,80,0.08)' : 'var(--chip, #f1f3ee)',
                color: meetingState.capturing ? '#ef5350' : 'var(--muted, #61665d)',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              <span
                className="rec"
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: meetingState.capturing ? '#ef5350' : 'var(--faint, #969c90)',
                  animation: meetingState.capturing ? 'pulse 1.6s infinite' : 'none',
                }}
              />
              {meetingState.capturing ? formatTime(seconds) : 'Paused'}
            </button>
            <div
              className="min"
              onClick={() => setIsCollapsed(true)}
              title="Minimize to icon"
              style={{
                width: '22px',
                height: '22px',
                borderRadius: '6px',
                display: 'grid',
                placeItems: 'center',
                color: 'var(--faint, #969c90)',
                marginLeft: '4px',
                cursor: 'pointer',
                transition: 'background 0.15s ease, color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--chip, #f1f3ee)';
                e.currentTarget.style.color = 'var(--txt, #191c18)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--faint, #969c90)';
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M5 12h14" />
              </svg>
            </div>
          </div>

          {/* Now-working row */}
          {runningAction ? (
            <div
              className="now"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 14px',
                background: 'var(--run-soft, #3b82f614)',
              }}
            >
              <span
                className="spin"
                style={{
                  width: '15px',
                  height: '15px',
                  borderRadius: '50%',
                  border: '2px solid var(--run, #3b82f6)',
                  borderRightColor: 'transparent',
                  animation: 'spin .8s linear infinite',
                  flex: 'none',
                }}
              />
              <span className="t" style={{ fontSize: '13px', color: 'var(--txt, #191c18)' }}>
                {runningAction.category === 'email' && (
                  <>Drafting <b>email to Acme</b>…</>
                )}
                {runningAction.category === 'doc' && (
                  <>Drafting <b>API spec doc</b>…</>
                )}
                {runningAction.category === 'slack' && (
                  <>Posting <b>#frontend notification</b>…</>
                )}
                {runningAction.category !== 'email' && runningAction.category !== 'doc' && runningAction.category !== 'slack' && (
                  <>Working on <b>{runningAction.title}</b>…</>
                )}
              </span>
            </div>
          ) : (
            <div
              className="now"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px 14px',
                background: 'var(--chip, #f1f3ee)',
              }}
            >
              <span style={{ fontSize: '13px', color: 'var(--muted, #61665d)' }}>Listening for live commitments…</span>
            </div>
          )}

          {/* Recent list */}
          <div className="recent" style={{ padding: '6px 14px 10px' }}>
            {meetingState.actions.length > 0 ? (
              meetingState.actions.slice(0, 4).map((a) => (
                <div
                  key={a.id}
                  className="r"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '9px',
                    padding: '6px 0',
                    fontSize: '12.5px',
                    color: 'var(--muted, #61665d)',
                  }}
                >
                  <span
                    className="ic"
                    style={{
                      width: '16px',
                      height: '16px',
                      flex: 'none',
                      display: 'grid',
                      placeItems: 'center',
                      color: a.status === 'done' ? 'var(--done, #16a34a)' : 'var(--faint, #969c90)',
                    }}
                  >
                    {a.status === 'done' ? (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                        <path d="m5 13 4 4L19 7" />
                      </svg>
                    ) : (
                      '•'
                    )}
                  </span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.title}
                  </span>
                  <span
                    className="tm"
                    style={{
                      marginLeft: 'auto',
                      fontSize: '11px',
                      color: 'var(--faint, #969c90)',
                    }}
                  >
                    {a.status === 'done' ? 'now' : a.status}
                  </span>
                </div>
              ))
            ) : (
              <>
                <div
                  className="r"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '9px',
                    padding: '6px 0',
                    fontSize: '12.5px',
                    color: 'var(--muted, #61665d)',
                  }}
                >
                  <span
                    className="ic done"
                    style={{
                      width: '16px',
                      height: '16px',
                      flex: 'none',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--done, #16a34a)',
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="m5 13 4 4L19 7" />
                    </svg>
                  </span>
                  <span>
                    Booked <b>design review</b> · Thu 2pm
                  </span>
                  <span className="tm" style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--faint, #969c90)' }}>
                    now
                  </span>
                </div>
                <div
                  className="r"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '9px',
                    padding: '6px 0',
                    fontSize: '12.5px',
                    color: 'var(--muted, #61665d)',
                  }}
                >
                  <span
                    className="ic done"
                    style={{
                      width: '16px',
                      height: '16px',
                      flex: 'none',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--done, #16a34a)',
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="m5 13 4 4L19 7" />
                    </svg>
                  </span>
                  <span>
                    <b>Research brief</b> ready
                  </span>
                  <span className="tm" style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--faint, #969c90)' }}>
                    now
                  </span>
                </div>
                <div
                  className="r"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '9px',
                    padding: '6px 0',
                    fontSize: '12.5px',
                    color: 'var(--muted, #61665d)',
                  }}
                >
                  <span
                    className="ic queue"
                    style={{
                      width: '16px',
                      height: '16px',
                      flex: 'none',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--faint, #969c90)',
                    }}
                  >
                    •
                  </span>
                  <span>
                    Notify <b>#frontend</b> · queued
                  </span>
                  <span className="tm" style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--faint, #969c90)' }}>
                    Fri
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Approval box */}
          {pendingAction && (
            <div
              className="appr"
              style={{
                margin: '2px 12px 12px',
                padding: '11px 12px',
                background: 'var(--amber-bg, #faf1dd)',
                border: '1px solid var(--amber-bd, #d9a03e66)',
                borderRadius: '11px',
              }}
            >
              <div
                className="lab"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--amber, #b7791f)',
                  textTransform: 'uppercase',
                  letterSpacing: '.04em',
                  marginBottom: '6px',
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2 2 7v7c0 5 4 8 10 8s10-3 10-8V7z" />
                </svg>
                Needs your OK
              </div>
              <div
                className="q"
                style={{
                  fontSize: '13px',
                  color: 'var(--txt, #191c18)',
                  fontWeight: 550,
                  marginBottom: '9px',
                }}
              >
                {pendingAction.title || 'Approve action'}
              </div>
              <div className="btns" style={{ display: 'flex', gap: '7px' }}>
                <button
                  className="btn primary"
                  onClick={() => approveAction(pendingAction.id)}
                  style={{
                    flex: 1,
                    fontSize: '12.5px',
                    fontWeight: 650,
                    padding: '7px 0',
                    borderRadius: '8px',
                    border: '1px solid var(--accent, #0f9d6b)',
                    background: 'var(--accent, #0f9d6b)',
                    color: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  Approve &amp; send
                </button>
                <button
                  className="btn"
                  onClick={() => skipAction(pendingAction.id)}
                  style={{
                    flex: 1,
                    fontSize: '12.5px',
                    fontWeight: 650,
                    padding: '7px 0',
                    borderRadius: '8px',
                    border: '1px solid var(--line, #e3e6df)',
                    background: '#ffffff',
                    color: 'var(--txt, #191c18)',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* Clarification prompt box */}
          {clarifications.filter((c) => c.status === 'open').length > 0 && (() => {
            const openClar = clarifications.filter((c) => c.status === 'open')[0];
            return (
              <div
                className="clar-box"
                style={{
                  margin: '2px 12px 12px',
                  padding: '11px 12px',
                  background: 'var(--panel, #ffffff)',
                  border: '1px solid var(--accent, #0f9d6b)',
                  borderLeft: '3px solid var(--accent, #0f9d6b)',
                  borderRadius: '11px',
                  boxShadow: 'var(--card-sh)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'var(--accent, #0f9d6b)',
                    textTransform: 'uppercase',
                    letterSpacing: '.04em',
                    marginBottom: '5px',
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  Clarification Needed
                  {clarifications.filter((c) => c.status === 'open').length > 1 && (
                    <span
                      style={{
                        marginLeft: 'auto',
                        fontSize: '10px',
                        color: 'var(--muted, #61665d)',
                        fontWeight: 600,
                      }}
                    >
                      1 of {clarifications.filter((c) => c.status === 'open').length}
                    </span>
                  )}
                </div>

                <div
                  style={{
                    fontSize: '12.5px',
                    color: 'var(--txt, #191c18)',
                    fontWeight: 600,
                    marginBottom: '8px',
                    lineHeight: 1.35,
                  }}
                >
                  {openClar.question}
                </div>

                {openClar.options && openClar.options.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    {openClar.options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => answerClarification(openClar.id, opt)}
                        style={{
                          padding: '6px 10px',
                          fontSize: '11.5px',
                          fontWeight: 600,
                          borderRadius: '6px',
                          border: '1px solid var(--line, #e3e6df)',
                          background: 'var(--chip, #f1f3ee)',
                          color: 'var(--txt, #191c18)',
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'all 0.15s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = 'var(--accent, #0f9d6b)';
                          e.currentTarget.style.background = 'var(--accent-soft)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = 'var(--line, #e3e6df)';
                          e.currentTarget.style.background = 'var(--chip, #f1f3ee)';
                        }}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                ) : (
                  <button
                    onClick={() => answerClarification(openClar.id, 'Confirmed')}
                    style={{
                      width: '100%',
                      padding: '6px 0',
                      fontSize: '12px',
                      fontWeight: 650,
                      borderRadius: '6px',
                      border: '1px solid var(--accent, #0f9d6b)',
                      background: 'var(--accent, #0f9d6b)',
                      color: '#ffffff',
                      cursor: 'pointer',
                    }}
                  >
                    Confirm &amp; Proceed
                  </button>
                )}
              </div>
            );
          })()}

          {/* Footer */}
          <div
            className="cf"
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '10px 14px',
              borderTop: '1px solid var(--line, #e3e6df)',
              fontSize: '12px',
              color: 'var(--muted, #61665d)',
            }}
          >
            <span>
              {totalActions} actions · {doneActions.length} done
            </span>
            <a
              href={`${window.location.origin}/`}
              target="_blank"
              rel="noreferrer"
              style={{
                marginLeft: 'auto',
                color: 'var(--accent, #0f9d6b)',
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              Open dashboard →
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

