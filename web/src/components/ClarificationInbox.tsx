import React, { useState } from 'react';
import { Clarification } from '../data/types';

interface ClarificationInboxProps {
  clarifications: Clarification[];
  onAnswer: (id: string, answer: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ClarificationInbox: React.FC<ClarificationInboxProps> = ({
  clarifications,
  onAnswer,
  isOpen,
  onClose,
}) => {
  const [filter, setFilter] = useState<'all' | 'open' | 'answered'>('open');
  const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const openCount = clarifications.filter((c) => c.status === 'open').length;
  const filtered = clarifications.filter((c) => {
    if (filter === 'open') return c.status === 'open';
    if (filter === 'answered') return c.status === 'answered';
    return true;
  });

  const handleInputChange = (id: string, val: string) => {
    setDraftAnswers((prev) => ({ ...prev, [id]: val }));
  };

  const handleAnswerSubmit = (id: string, text?: string) => {
    const answer = text !== undefined ? text : (draftAnswers[id] || '').trim();
    if (!answer) return;
    setSubmittingId(id);
    onAnswer(id, answer);
    setTimeout(() => {
      setSubmittingId(null);
      setDraftAnswers((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }, 150);
  };

  return (
    <>
      {/* Backdrop overlay */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 90,
          background: 'rgba(0, 0, 0, 0.18)',
          backdropFilter: 'blur(1px)',
        }}
      />

      {/* Popover Card */}
      <div
        className="clarification-inbox"
        style={{
          position: 'fixed',
          top: '62px',
          right: '22px',
          width: '420px',
          maxHeight: 'calc(100vh - 84px)',
          background: 'var(--panel)',
          border: '1px solid var(--line)',
          borderRadius: '14px',
          boxShadow: '0 16px 48px rgba(0,0,0,0.14), 0 2px 8px rgba(0,0,0,0.06)',
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.15s ease-out',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 18px',
            borderBottom: '1px solid var(--line)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--chip)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '26px',
                height: '26px',
                borderRadius: '7px',
                background: openCount > 0 ? 'var(--amber-bg)' : 'var(--panel)',
                border: openCount > 0 ? '1px solid var(--amber-bd)' : '1px solid var(--line)',
                display: 'grid',
                placeItems: 'center',
                color: openCount > 0 ? 'var(--amber)' : 'var(--muted)',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div>
              <h3 style={{ fontSize: '13.5px', fontWeight: 650, color: 'var(--txt)', lineHeight: 1.2 }}>
                Clarifications Inbox
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--muted)' }}>
                {openCount === 1 ? '1 open question' : `${openCount} open questions`} needing input
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--faint)',
              padding: '4px',
              borderRadius: '6px',
              display: 'grid',
              placeItems: 'center',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Tab switcher */}
        <div
          style={{
            display: 'flex',
            gap: '6px',
            padding: '8px 14px',
            borderBottom: '1px solid var(--line)',
            background: 'var(--panel)',
          }}
        >
          <button
            onClick={() => setFilter('open')}
            style={{
              background: filter === 'open' ? 'var(--chip)' : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: filter === 'open' ? 650 : 500,
              color: filter === 'open' ? 'var(--txt)' : 'var(--muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            Open
            {openCount > 0 && (
              <span
                style={{
                  background: 'var(--amber)',
                  color: '#fff',
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '10px',
                }}
              >
                {openCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setFilter('answered')}
            style={{
              background: filter === 'answered' ? 'var(--chip)' : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: filter === 'answered' ? 650 : 500,
              color: filter === 'answered' ? 'var(--txt)' : 'var(--muted)',
              cursor: 'pointer',
            }}
          >
            Answered
          </button>
          <button
            onClick={() => setFilter('all')}
            style={{
              background: filter === 'all' ? 'var(--chip)' : 'transparent',
              border: 'none',
              borderRadius: '6px',
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: filter === 'all' ? 650 : 500,
              color: filter === 'all' ? 'var(--txt)' : 'var(--muted)',
              cursor: 'pointer',
            }}
          >
            All ({clarifications.length})
          </button>
        </div>

        {/* List of items */}
        <div
          style={{
            overflowY: 'auto',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            maxHeight: '480px',
          }}
        >
          {filtered.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '36px 16px',
                color: 'var(--muted)',
                fontSize: '12.5px',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'var(--done-soft)',
                  color: 'var(--done)',
                  display: 'grid',
                  placeItems: 'center',
                  margin: '0 auto 8px',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p style={{ fontWeight: 600, color: 'var(--txt)' }}>No open questions</p>
              <p style={{ fontSize: '11.5px', color: 'var(--faint)', marginTop: '3px' }}>
                Agent has sufficient context for autonomous execution.
              </p>
            </div>
          ) : (
            filtered.map((item) => {
              const isOpenItem = item.status === 'open';
              const draftVal = draftAnswers[item.id] || '';

              return (
                <div
                  key={item.id}
                  style={{
                    background: isOpenItem ? 'var(--panel)' : 'var(--chip)',
                    border: `1px solid ${isOpenItem ? 'var(--line)' : 'var(--line)'}`,
                    borderLeft: isOpenItem
                      ? `3px solid ${item.priority === 'high' ? 'var(--amber)' : 'var(--accent)'}`
                      : '3px solid var(--done)',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    boxShadow: isOpenItem ? 'var(--card-sh)' : 'none',
                  }}
                >
                  {/* Top meta */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '.04em',
                          color: isOpenItem
                            ? item.priority === 'high'
                              ? 'var(--amber)'
                              : 'var(--accent)'
                            : 'var(--done)',
                          background: isOpenItem
                            ? item.priority === 'high'
                              ? 'var(--amber-soft)'
                              : 'var(--accent-soft)'
                            : 'var(--done-soft)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        {isOpenItem ? `${item.priority || 'normal'} priority` : 'Answered'}
                      </span>
                      {item.askedBy && (
                        <span style={{ fontSize: '11px', color: 'var(--faint)' }}>
                          from {item.askedBy}
                        </span>
                      )}
                    </div>

                    <span style={{ fontSize: '11px', color: 'var(--faint)', fontVariantNumeric: 'tabular-nums' }}>
                      {item.ts}
                    </span>
                  </div>

                  {/* Question */}
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--txt)', lineHeight: 1.4 }}>
                    {item.question}
                  </div>

                  {/* Context quote */}
                  {item.context && (
                    <div
                      style={{
                        fontSize: '11.5px',
                        color: 'var(--muted)',
                        background: 'var(--chip)',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        borderLeft: '2px solid var(--line)',
                        lineHeight: 1.4,
                      }}
                    >
                      <span style={{ fontWeight: 600, color: 'var(--faint)' }}>Context: </span>
                      "{item.context}"
                    </div>
                  )}

                  {/* If Answered */}
                  {!isOpenItem && item.answer && (
                    <div
                      style={{
                        fontSize: '12px',
                        color: 'var(--txt)',
                        background: 'var(--panel)',
                        border: '1px solid var(--line)',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '6px',
                      }}
                    >
                      <span style={{ color: 'var(--done)', marginTop: '1px', flexShrink: 0 }}>✓</span>
                      <div>
                        <span style={{ fontWeight: 600 }}>Answer: </span>
                        {item.answer}
                      </div>
                    </div>
                  )}

                  {/* If Open: Interactive options & input */}
                  {isOpenItem && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '2px' }}>
                      {/* Suggested options chips */}
                      {item.options && item.options.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {item.options.map((opt, idx) => (
                            <button
                              key={idx}
                              onClick={() => handleAnswerSubmit(item.id, opt)}
                              disabled={submittingId === item.id}
                              style={{
                                background: 'var(--chip)',
                                border: '1px solid var(--line)',
                                borderRadius: '6px',
                                padding: '5px 9px',
                                fontSize: '11.5px',
                                fontWeight: 550,
                                color: 'var(--txt)',
                                cursor: 'pointer',
                                textAlign: 'left',
                                transition: 'all 0.15s ease',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = 'var(--accent)';
                                e.currentTarget.style.background = 'var(--accent-soft)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = 'var(--line)';
                                e.currentTarget.style.background = 'var(--chip)';
                              }}
                            >
                              {opt}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Freeform input + submit */}
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <input
                          type="text"
                          placeholder="Type custom response..."
                          value={draftVal}
                          onChange={(e) => handleInputChange(item.id, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && draftVal.trim()) {
                              handleAnswerSubmit(item.id);
                            }
                          }}
                          style={{
                            flex: 1,
                            padding: '6px 10px',
                            fontSize: '12px',
                            border: '1px solid var(--line)',
                            borderRadius: '6px',
                            background: 'var(--panel)',
                            color: 'var(--txt)',
                            outline: 'none',
                          }}
                        />
                        <button
                          onClick={() => handleAnswerSubmit(item.id)}
                          disabled={!draftVal.trim() || submittingId === item.id}
                          style={{
                            padding: '6px 12px',
                            fontSize: '12px',
                            fontWeight: 600,
                            borderRadius: '6px',
                            border: '1px solid var(--accent)',
                            background: draftVal.trim() ? 'var(--accent)' : 'var(--chip)',
                            color: draftVal.trim() ? '#ffffff' : 'var(--faint)',
                            cursor: draftVal.trim() ? 'pointer' : 'default',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
};
