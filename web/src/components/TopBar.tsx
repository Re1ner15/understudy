import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Avatar } from './Avatar';
import { Logo } from './Logo';
import { subscribeToClarifications, answerClarification, subscribeToMeeting } from '../data';
import { Clarification } from '../data/types';
import { ClarificationInbox } from './ClarificationInbox';

export const TopBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isCommitments = location.pathname.startsWith('/commitments');
  const isMinutes = location.pathname.startsWith('/minutes');
  const isAudit = location.pathname.startsWith('/audit');
  const isHistory = location.pathname.startsWith('/history');
  const isLive = !isCommitments && !isMinutes && !isAudit && !isHistory;
  const [seconds, setSeconds] = useState(0);
  const [capturing, setCapturing] = useState(false);
  const [boardEmpty, setBoardEmpty] = useState(true);
  const [clarifications, setClarifications] = useState<Clarification[]>([]);
  const [isInboxOpen, setIsInboxOpen] = useState(false);

  useEffect(() => {
    const unsub = subscribeToClarifications((items) => {
      setClarifications(items);
    });
    return unsub;
  }, []);

  // Track recording state + whether the meeting board is empty (fresh/concluded).
  useEffect(() => {
    const unsub = subscribeToMeeting((state) => {
      setCapturing(!!state.capturing);
      setBoardEmpty(state.transcript.length === 0 && state.actions.length === 0);
    });
    return unsub;
  }, []);

  // Timer: ticks only while recording; resets to 0 when the meeting is empty
  // (fresh start or concluded); holds when paused.
  useEffect(() => {
    if (!capturing && boardEmpty) {
      setSeconds(0);
      return;
    }
    if (!capturing) return; // paused → hold
    const timer = setInterval(() => setSeconds((prev) => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [capturing, boardEmpty]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const openClarifications = clarifications.filter((c) => c.status === 'open');
  const openCount = openClarifications.length;

  return (
    <div
      className="topbar"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '18px',
        height: '54px',
        padding: '0 22px',
        borderBottom: '1px solid var(--line)',
        background: 'var(--panel)',
        flex: 'none',
        position: 'relative',
        zIndex: 50,
      }}
    >
      <div
        className="brand"
        onClick={() => navigate('/')}
        style={{
          display: 'flex',
          alignItems: 'center',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        <Logo size={18} showWordmark />
      </div>

      <div
        className="seg"
        style={{
          display: 'flex',
          background: 'var(--seg)',
          border: '1px solid var(--line)',
          borderRadius: '9px',
          padding: '3px',
        }}
      >
        <button
          className={isLive ? 'on' : ''}
          onClick={() => navigate('/')}
          style={{
            border: 0,
            background: isLive ? 'var(--panel)' : 'none',
            color: isLive ? 'var(--txt)' : 'var(--muted)',
            fontSize: '13px',
            fontWeight: 550,
            padding: '5px 13px',
            borderRadius: '6px',
            cursor: 'pointer',
            boxShadow: isLive ? 'var(--seg-sh)' : 'none',
          }}
        >
          Live meeting
        </button>
        <button
          className={isCommitments ? 'on' : ''}
          onClick={() => navigate('/commitments')}
          style={{
            border: 0,
            background: isCommitments ? 'var(--panel)' : 'none',
            color: isCommitments ? 'var(--txt)' : 'var(--muted)',
            fontSize: '13px',
            fontWeight: 550,
            padding: '5px 13px',
            borderRadius: '6px',
            cursor: 'pointer',
            boxShadow: isCommitments ? 'var(--seg-sh)' : 'none',
          }}
        >
          Commitments
        </button>
        <button
          className={isMinutes ? 'on' : ''}
          onClick={() => navigate('/minutes')}
          style={{
            border: 0,
            background: isMinutes ? 'var(--panel)' : 'none',
            color: isMinutes ? 'var(--txt)' : 'var(--muted)',
            fontSize: '13px',
            fontWeight: 550,
            padding: '5px 13px',
            borderRadius: '6px',
            cursor: 'pointer',
            boxShadow: isMinutes ? 'var(--seg-sh)' : 'none',
          }}
        >
          Minutes
        </button>
        <button
          className={isAudit ? 'on' : ''}
          onClick={() => navigate('/audit')}
          style={{
            border: 0,
            background: isAudit ? 'var(--panel)' : 'none',
            color: isAudit ? 'var(--txt)' : 'var(--muted)',
            fontSize: '13px',
            fontWeight: 550,
            padding: '5px 13px',
            borderRadius: '6px',
            cursor: 'pointer',
            boxShadow: isAudit ? 'var(--seg-sh)' : 'none',
          }}
        >
          Reasoning trace
        </button>
        <button
          className={isHistory ? 'on' : ''}
          onClick={() => navigate('/history')}
          style={{
            border: 0,
            background: isHistory ? 'var(--panel)' : 'none',
            color: isHistory ? 'var(--txt)' : 'var(--muted)',
            fontSize: '13px',
            fontWeight: 550,
            padding: '5px 13px',
            borderRadius: '6px',
            cursor: 'pointer',
            boxShadow: isHistory ? 'var(--seg-sh)' : 'none',
          }}
        >
          History
        </button>
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Clarifications Inbox Trigger Button */}
        <button
          onClick={() => setIsInboxOpen((prev) => !prev)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: '8px',
            border: openCount > 0 ? '1px solid var(--amber-bd)' : '1px solid var(--line)',
            background: openCount > 0 ? 'var(--amber-bg)' : 'var(--panel)',
            color: openCount > 0 ? 'var(--amber)' : 'var(--muted)',
            cursor: 'pointer',
            fontSize: '12.5px',
            fontWeight: 600,
            transition: 'all 0.15s ease',
            boxShadow: 'var(--card-sh)',
          }}
          title="Clarifications inbox"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <text x="12" y="17" textAnchor="middle" fontSize="14" fontWeight="700" fill="currentColor" fontFamily="-apple-system, sans-serif">?</text>
          </svg>
          <span>Clarifications</span>
          {openCount > 0 && (
            <span
              style={{
                display: 'inline-grid',
                placeItems: 'center',
                minWidth: '17px',
                height: '17px',
                padding: '0 4px',
                borderRadius: '9px',
                background: 'var(--amber)',
                color: '#ffffff',
                fontSize: '10.5px',
                fontWeight: 700,
                lineHeight: 1,
              }}
            >
              {openCount}
            </span>
          )}
        </button>

        {isLive ? (
          <div
            className="live"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              fontVariantNumeric: 'tabular-nums',
              fontSize: '13px',
              color: 'var(--txt)',
            }}
          >
            <span
              className="rec"
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: capturing ? '#ef5350' : 'var(--faint)',
                animation: capturing ? 'pulse 1.6s infinite' : 'none',
              }}
            />
            {capturing ? 'LIVE' : boardEmpty ? 'READY' : 'PAUSED'} · {formatTime(seconds)}
          </div>
        ) : (
          <div
            className="who"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '13px',
              color: 'var(--muted)',
            }}
          >
            <Avatar name={import.meta.env.VITE_USER_NAME || 'Ranjit Jail'} size="lg" />
            <span>{import.meta.env.VITE_USER_NAME || 'Ranjit Jail'}</span>
          </div>
        )}
      </div>

      {/* Clarifications Inbox Popover */}
      <ClarificationInbox
        clarifications={clarifications}
        onAnswer={answerClarification}
        isOpen={isInboxOpen}
        onClose={() => setIsInboxOpen(false)}
      />
    </div>
  );
};

