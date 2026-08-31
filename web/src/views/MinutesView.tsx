import React, { useState, useEffect } from 'react';
import { subscribeToMinutes } from '../data';
import { Minutes, ActionCategory } from '../data/types';
import { Avatar } from '../components/Avatar';

const CategoryIcon: React.FC<{ category: ActionCategory | string }> = ({ category }) => {
  const iconProps = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    style: { width: '15px', height: '15px' },
  };

  switch (category) {
    case 'email':
      return (
        <svg {...iconProps}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="m3 7 9 6 9-6" />
        </svg>
      );
    case 'doc':
      return (
        <svg {...iconProps}>
          <path d="M6 2h9l5 5v15H6z" />
          <path d="M14 2v6h6M9 13h7M9 17h7" />
        </svg>
      );
    case 'calendar':
      return (
        <svg {...iconProps}>
          <rect x="3" y="4" width="18" height="17" rx="2" />
          <path d="M3 9h18M8 2v4M16 2v4" />
        </svg>
      );
    case 'research':
      return (
        <svg {...iconProps}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      );
    case 'slack':
      return (
        <svg {...iconProps}>
          <rect x="4" y="4" width="16" height="16" rx="4" />
          <path d="M9 9h6v6H9z" />
        </svg>
      );
    case 'task':
    default:
      return (
        <svg {...iconProps}>
          <path d="m9 11 3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
      );
  }
};

export const MinutesView: React.FC = () => {
  const [minutes, setMinutes] = useState<Minutes | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const unsubscribe = subscribeToMinutes((data) => {
      setMinutes(data);
      setHasLoaded(true);
    });
    return unsubscribe;
  }, []);

  const handleCopyMarkdown = () => {
    if (!minutes) return;
    const md = `# ${minutes.title} — Meeting Minutes
**Date:** ${minutes.date}
**Attendees:** ${minutes.attendees.join(', ')}

## Decisions
${minutes.decisions.map((d) => `- ${d}`).join('\n')}

## Topics & Discussion
${minutes.topics.map((t) => `### ${t.heading}\n${t.notes}`).join('\n\n')}

## Materials Shown
${minutes.materialsShown.map((m) => `- ${m}`).join('\n')}

## Action Items
${minutes.actionItems.map((a) => `- [ ] **${a.assignee || 'Unassigned'}** (${a.category}): ${a.text}${a.due ? ` [Due: ${a.due}]` : ''}`).join('\n')}
`;
    navigator.clipboard.writeText(md).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!minutes) {
    return (
      <div
        className="page"
        style={{
          flex: 1,
          display: 'grid',
          placeItems: 'center',
          color: 'var(--muted)',
          fontSize: '14px',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: '320px' }}>
          {hasLoaded ? (
            <>
              <div style={{ fontSize: '30px', marginBottom: '10px' }}>📝</div>
              <p style={{ fontWeight: 600, color: 'var(--txt)' }}>No minutes yet</p>
              <p style={{ fontSize: '12.5px', color: 'var(--faint)', marginTop: '6px', lineHeight: 1.5 }}>
                Understudy generates the minutes when the meeting ends. Finish the
                meeting to see the summary, decisions, and action items here.
              </p>
            </>
          ) : (
            <>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  border: '2.5px solid var(--accent)',
                  borderRightColor: 'transparent',
                  animation: 'spin .8s linear infinite',
                  margin: '0 auto 14px',
                }}
              />
              <p style={{ fontWeight: 600, color: 'var(--txt)' }}>Loading meeting minutes…</p>
              <p style={{ fontSize: '12.5px', color: 'var(--faint)', marginTop: '4px' }}>
                Listening for latest meeting summary
              </p>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="page"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '28px 32px 60px',
        maxWidth: '1020px',
        width: '100%',
        margin: '0 auto',
      }}
    >
      {/* Page Header */}
      <div
        className="phead"
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '24px',
          borderBottom: '1px solid var(--line)',
          paddingBottom: '20px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '.06em',
                color: 'var(--accent)',
                background: 'var(--accent-soft)',
                padding: '3px 9px',
                borderRadius: '6px',
              }}
            >
              Minutes &amp; Summary
            </span>
            <span style={{ color: 'var(--faint)', fontSize: '13px' }}>·</span>
            <span style={{ color: 'var(--muted)', fontSize: '13px', fontWeight: 500 }}>
              {minutes.date}
            </span>
          </div>
          <h1
            style={{
              fontSize: '24px',
              fontWeight: 700,
              letterSpacing: '-.025em',
              color: 'var(--txt)',
              marginBottom: '8px',
            }}
          >
            {minutes.title}
          </h1>
          {/* Attendees Chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12.5px', color: 'var(--faint)', fontWeight: 500 }}>
              Attendees:
            </span>
            {minutes.attendees.map((attendee) => (
              <div
                key={attendee}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'var(--panel)',
                  border: '1px solid var(--line)',
                  borderRadius: '16px',
                  padding: '2px 10px 2px 3px',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--txt)',
                  boxShadow: 'var(--card-sh)',
                }}
              >
                <Avatar name={attendee} size="sm" />
                <span>{attendee}</span>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleCopyMarkdown}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '12.5px',
            fontWeight: 600,
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--line)',
            background: copied ? 'var(--accent)' : 'var(--panel)',
            color: copied ? '#ffffff' : 'var(--txt)',
            cursor: 'pointer',
            boxShadow: 'var(--card-sh)',
            transition: 'all 0.15s ease',
            flexShrink: 0,
          }}
        >
          {copied ? (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: '13px', height: '13px' }}>
                <path d="m5 13 4 4L19 7" />
              </svg>
              Copied Markdown!
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '13px', height: '13px' }}>
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy Markdown
            </>
          )}
        </button>
      </div>

      {/* Grid of Highlights: Decisions & Materials */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '20px',
          marginBottom: '26px',
        }}
      >
        {/* Decisions Reached */}
        <div
          style={{
            background: 'var(--panel)',
            border: '1px solid var(--line)',
            borderRadius: '14px',
            padding: '18px 20px',
            boxShadow: 'var(--card-sh)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '14px',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--done)',
              }}
            />
            <h2
              style={{
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '.08em',
                fontWeight: 700,
                color: 'var(--faint)',
              }}
            >
              Key Decisions Reached
            </h2>
            <span
              style={{
                marginLeft: 'auto',
                fontSize: '11px',
                color: 'var(--done)',
                background: 'var(--done-soft)',
                padding: '2px 8px',
                borderRadius: '10px',
                fontWeight: 650,
              }}
            >
              {minutes.decisions.length} agreed
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {minutes.decisions.map((decision, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '13px',
                  color: 'var(--txt)',
                  lineHeight: 1.45,
                  padding: '8px 12px',
                  background: 'var(--chip)',
                  borderRadius: '9px',
                }}
              >
                <div
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    background: 'var(--done)',
                    color: '#fff',
                    display: 'grid',
                    placeItems: 'center',
                    flexShrink: 0,
                    marginTop: '2px',
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" style={{ width: '9px', height: '9px' }}>
                    <path d="m5 13 4 4L19 7" />
                  </svg>
                </div>
                <span>{decision}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Materials Shown */}
        <div
          style={{
            background: 'var(--panel)',
            border: '1px solid var(--line)',
            borderRadius: '14px',
            padding: '18px 20px',
            boxShadow: 'var(--card-sh)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '14px',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--run)',
              }}
            />
            <h2
              style={{
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '.08em',
                fontWeight: 700,
                color: 'var(--faint)',
              }}
            >
              Materials Presented &amp; Referenced
            </h2>
            <span
              style={{
                marginLeft: 'auto',
                fontSize: '11px',
                color: 'var(--faint)',
                background: 'var(--chip)',
                padding: '2px 8px',
                borderRadius: '10px',
                fontWeight: 600,
              }}
            >
              {minutes.materialsShown.length}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {minutes.materialsShown.map((material, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '13px',
                  color: 'var(--txt)',
                  padding: '8px 12px',
                  background: 'var(--chip)',
                  borderRadius: '9px',
                }}
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '6px',
                    background: 'var(--panel)',
                    border: '1px solid var(--line)',
                    display: 'grid',
                    placeItems: 'center',
                    color: 'var(--muted)',
                    flexShrink: 0,
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '13px', height: '13px' }}>
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </div>
                <span style={{ fontWeight: 500 }}>{material}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Topics & Discussion */}
      <div style={{ marginBottom: '28px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '12px',
            padding: '0 2px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: 'var(--accent)',
            }}
          />
          <h2
            style={{
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              fontWeight: 700,
              color: 'var(--faint)',
            }}
          >
            Topics &amp; Discussion Notes
          </h2>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--faint)',
              background: 'var(--chip)',
              padding: '1px 8px',
              borderRadius: '10px',
            }}
          >
            {minutes.topics.length}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {minutes.topics.map((topic, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--panel)',
                border: '1px solid var(--line)',
                borderRadius: '12px',
                padding: '16px 20px',
                boxShadow: 'var(--card-sh)',
              }}
            >
              <h3
                style={{
                  fontSize: '15px',
                  fontWeight: 650,
                  color: 'var(--txt)',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span style={{ color: 'var(--accent)', fontSize: '13px' }}>§{idx + 1}</span>
                {topic.heading}
              </h3>
              <p
                style={{
                  fontSize: '13.5px',
                  color: 'var(--muted)',
                  lineHeight: 1.6,
                }}
              >
                {topic.notes}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Action Items */}
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '12px',
            padding: '0 2px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: 'var(--amber)',
            }}
          />
          <h2
            style={{
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              fontWeight: 700,
              color: 'var(--faint)',
            }}
          >
            Assigned Action Items
          </h2>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--faint)',
              background: 'var(--chip)',
              padding: '1px 8px',
              borderRadius: '10px',
            }}
          >
            {minutes.actionItems.length}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {minutes.actionItems.map((action, idx) => (
            <div
              key={action.id || idx}
              style={{
                display: 'grid',
                gridTemplateColumns: '32px 1fr auto auto',
                gap: '12px',
                alignItems: 'center',
                background: 'var(--panel)',
                border: '1px solid var(--line)',
                borderRadius: '12px',
                padding: '12px 16px',
                boxShadow: 'var(--card-sh)',
              }}
            >
              <div
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '8px',
                  background: 'var(--chip)',
                  border: '1px solid var(--line)',
                  display: 'grid',
                  placeItems: 'center',
                  color: 'var(--muted)',
                }}
              >
                <CategoryIcon category={action.category} />
              </div>

              <div>
                <div style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--txt)', lineHeight: 1.35 }}>
                  {action.text}
                </div>
              </div>

              <div>
                {action.assignee ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: 'var(--muted)' }}>
                    <Avatar name={action.assignee} size="sm" />
                    <span style={{ fontWeight: 550 }}>{action.assignee}</span>
                  </div>
                ) : (
                  <span style={{ fontSize: '12px', color: 'var(--faint)', fontStyle: 'italic' }}>Unassigned</span>
                )}
              </div>

              <div>
                {action.due ? (
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: 600,
                      color: action.due.toLowerCase().includes('today') ? 'var(--amber)' : 'var(--muted)',
                      background: action.due.toLowerCase().includes('today') ? 'var(--amber-soft)' : 'var(--chip)',
                      padding: '3px 9px',
                      borderRadius: '8px',
                    }}
                  >
                    {action.due}
                  </span>
                ) : (
                  <span style={{ fontSize: '11.5px', color: 'var(--faint)' }}>No due date</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
