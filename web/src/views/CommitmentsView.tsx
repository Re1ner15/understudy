import React, { useState, useEffect } from 'react';
import { subscribeToCommitments } from '../data';
import { Commitment } from '../data/types';
import { StatTile } from '../components/StatTile';
import { CommitmentRow } from '../components/CommitmentRow';

export const CommitmentsView: React.FC = () => {
  const [commitments, setCommitments] = useState<Commitment[]>([]);

  useEffect(() => {
    const unsubscribe = subscribeToCommitments((items) => {
      setCommitments(items);
    });
    return unsubscribe;
  }, []);

  const needsAttentionItems = commitments.filter(
    (c) => c.status === 'overdue' || c.status === 'blocked' || c.status === 'needs_approval'
  );
  const inProgressItems = commitments.filter((c) => c.status === 'in_progress' || c.status === 'open');
  const doneItems = commitments.filter((c) => c.status === 'done');
  const nudgesSent = commitments.reduce((sum, c) => sum + (c.followUp?.nudgeCount ?? 0), 0);

  return (
    <div
      className="page"
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 26px 40px',
      }}
    >
      {/* Page header */}
      <div
        className="phead"
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '14px',
          marginBottom: '20px',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '22px',
              fontWeight: 680,
              letterSpacing: '-.02em',
            }}
          >
            Commitments
          </h1>
          <div
            className="sub"
            style={{
              color: 'var(--muted)',
              fontSize: '13.5px',
              paddingBottom: '2px',
            }}
          >
            Everything Understudy is tracking to done — across every meeting
          </div>
        </div>

        <div
          className="filters"
          style={{
            marginLeft: 'auto',
            display: 'flex',
            gap: '8px',
          }}
        >
          <span
            className="fchip"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12.5px',
              color: 'var(--muted)',
              background: 'var(--panel)',
              border: '1px solid var(--line)',
              padding: '6px 11px',
              borderRadius: '8px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            All meetings{' '}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '12px', height: '12px' }}>
              <path d="m6 9 6 6 6-6" />
            </svg>
          </span>
          <span
            className="fchip"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12.5px',
              color: 'var(--muted)',
              background: 'var(--panel)',
              border: '1px solid var(--line)',
              padding: '6px 11px',
              borderRadius: '8px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            This week{' '}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '12px', height: '12px' }}>
              <path d="m6 9 6 6 6-6" />
            </svg>
          </span>
          <span
            className="fchip"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12.5px',
              color: 'var(--muted)',
              background: 'var(--panel)',
              border: '1px solid var(--line)',
              padding: '6px 11px',
              borderRadius: '8px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Everyone{' '}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '12px', height: '12px' }}>
              <path d="m6 9 6 6 6-6" />
            </svg>
          </span>
        </div>
      </div>

      {/* Stats bar */}
      <div
        className="stats"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '14px',
          marginBottom: '26px',
        }}
      >
        <StatTile value={needsAttentionItems.length} label="Need attention" variant="attn" />
        <StatTile value={inProgressItems.length} label="In progress" variant="normal" />
        <StatTile value={doneItems.length} label="Done" variant="normal" />
        <StatTile value={nudgesSent} label="Auto-nudges sent" variant="eng" />
      </div>

      {/* Section 1: Needs attention */}
      <div className="sec" style={{ marginBottom: '26px' }}>
        <div
          className="sech"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '9px',
            marginBottom: '11px',
            padding: '0 2px',
          }}
        >
          <span className="dotc" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--red)' }} />
          <span className="t" style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 700, color: 'var(--faint)' }}>
            Needs attention
          </span>
          <span className="cnt" style={{ fontSize: '12px', color: 'var(--faint)', background: 'var(--chip)', padding: '1px 8px', borderRadius: '10px' }}>
            {needsAttentionItems.length}
          </span>
        </div>
        <div className="rows" style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
          {needsAttentionItems.map((item) => (
            <CommitmentRow key={item.id} commitment={item} />
          ))}
        </div>
      </div>

      {/* Section 2: In progress */}
      <div className="sec" style={{ marginBottom: '26px' }}>
        <div
          className="sech"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '9px',
            marginBottom: '11px',
            padding: '0 2px',
          }}
        >
          <span className="dotc" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--run)' }} />
          <span className="t" style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 700, color: 'var(--faint)' }}>
            In progress
          </span>
          <span className="cnt" style={{ fontSize: '12px', color: 'var(--faint)', background: 'var(--chip)', padding: '1px 8px', borderRadius: '10px' }}>
            {inProgressItems.length}
          </span>
        </div>
        <div className="rows" style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
          {inProgressItems.map((item) => (
            <CommitmentRow key={item.id} commitment={item} />
          ))}
        </div>
      </div>

      {/* Section 3: Recently done */}
      <div className="sec" style={{ marginBottom: '26px' }}>
        <div
          className="sech"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '9px',
            marginBottom: '11px',
            padding: '0 2px',
          }}
        >
          <span className="dotc" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--done)' }} />
          <span className="t" style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 700, color: 'var(--faint)' }}>
            Recently done
          </span>
          <span className="cnt" style={{ fontSize: '12px', color: 'var(--faint)', background: 'var(--chip)', padding: '1px 8px', borderRadius: '10px' }}>
            {doneItems.length}
          </span>
        </div>
        <div className="rows" style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
          {doneItems.map((item) => (
            <CommitmentRow key={item.id} commitment={item} />
          ))}
        </div>
      </div>
    </div>
  );
};
