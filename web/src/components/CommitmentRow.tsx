import React from 'react';
import { Commitment } from '../data/types';
import { Avatar } from './Avatar';
import { escalateCommitment, unblockCommitment, reviewCommitment } from '../data';

interface CommitmentRowProps {
  commitment: Commitment;
}

export const CommitmentRow: React.FC<CommitmentRowProps> = ({ commitment }) => {
  const isAlert = commitment.status === 'overdue' || commitment.status === 'blocked' || commitment.status === 'needs_approval';
  const isDone = commitment.status === 'done';

  const getStatusIcon = () => {
    switch (commitment.status) {
      case 'overdue':
      case 'open':
        return (
          <div
            className="stat-ico open"
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              border: `2px solid ${commitment.status === 'overdue' ? 'var(--red)' : 'var(--faint)'}`,
            }}
          />
        );
      case 'in_progress':
        return (
          <div
            className="stat-ico prog"
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              border: '2px solid var(--run)',
              borderRightColor: 'transparent',
            }}
          />
        );
      case 'blocked':
        return (
          <div
            className="stat-ico block"
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              background: 'var(--amber-soft)',
              color: 'var(--amber)',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M12 9v4M12 17h.01" />
              <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
            </svg>
          </div>
        );
      case 'needs_approval':
        return (
          <div
            className="stat-ico appr"
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              background: 'var(--amber-soft)',
              color: 'var(--amber)',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2 2 7v7c0 5 4 8 10 8s10-3 10-8V7z" />
            </svg>
          </div>
        );
      case 'done':
        return (
          <div
            className="stat-ico done"
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              background: 'var(--done)',
              color: '#ffffff',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <path d="m5 13 4 4L19 7" />
            </svg>
          </div>
        );
    }
  };

  const getDueClass = () => {
    if (commitment.status === 'overdue') return 'due over';
    if (commitment.due === 'today' || commitment.due === 'this morning') return 'due soon';
    return 'due';
  };

  const getDueStyle = () => {
    if (commitment.status === 'overdue') return { color: 'var(--red)', fontWeight: 650 };
    if (commitment.due === 'today' || commitment.due === 'this morning') return { color: 'var(--amber)', fontWeight: 600 };
    return { color: isDone ? 'var(--faint)' : 'var(--muted)' };
  };

  const renderFollowUp = () => {
    const follow = commitment.followUp;
    if (!follow) return null;

    return (
      <div
        className="follow"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          justifyContent: 'flex-end',
          fontSize: '12px',
          color: isDone ? 'var(--faint)' : 'var(--muted)',
        }}
      >
        {follow.nudgeCount ? (
          <span className="nudge" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--accent)', fontWeight: 600 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a7 7 0 0 0-7 7c0 3-1 4-2 5h18c-1-1-2-2-2-5a7 7 0 0 0-7-7z" />
            </svg>
            {follow.note}
          </span>
        ) : follow.nextNudge ? (
          <span className="nudge" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: 'var(--accent)', fontWeight: 600 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a7 7 0 0 0-7 7c0 3-1 4-2 5h18c-1-1-2-2-2-5a7 7 0 0 0-7-7z" />
            </svg>
            {follow.note}
          </span>
        ) : (
          <span className={isDone ? 'done-txt' : ''}>{follow.note}</span>
        )}

        {follow.actionType === 'escalate' && (
          <button
            className="fbtn red"
            onClick={() => escalateCommitment(commitment.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '6px 11px',
              borderRadius: '8px',
              border: '1px solid var(--red-bd)',
              background: 'var(--panel)',
              color: 'var(--red)',
              cursor: 'pointer',
            }}
          >
            Escalate
          </button>
        )}

        {follow.actionType === 'unblock' && (
          <button
            className="fbtn"
            onClick={() => unblockCommitment(commitment.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '6px 11px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
              background: 'var(--panel)',
              color: 'var(--txt)',
              cursor: 'pointer',
            }}
          >
            Unblock
          </button>
        )}

        {follow.actionType === 'review' && (
          <button
            className="fbtn amber"
            onClick={() => reviewCommitment(commitment.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '6px 11px',
              borderRadius: '8px',
              border: '1px solid var(--amber)',
              background: 'var(--amber)',
              color: '#ffffff',
              cursor: 'pointer',
            }}
          >
            Review &amp; send
          </button>
        )}
      </div>
    );
  };

  return (
    <div
      className={`row ${isAlert ? 'alert' : ''}`}
      style={{
        display: 'grid',
        gridTemplateColumns: '26px 1fr 130px 210px',
        gap: '14px',
        alignItems: 'center',
        background: isAlert ? 'var(--red-soft)' : 'var(--panel)',
        border: `1px solid ${isAlert ? 'var(--red-bd)' : 'var(--line)'}`,
        borderRadius: '12px',
        padding: '13px 16px',
        boxShadow: 'var(--card-sh)',
      }}
    >
      {getStatusIcon()}

      <div className="rmain">
        <div
          className={`ttl ${isDone ? 'done-txt' : ''}`}
          style={{
            fontWeight: 600,
            lineHeight: 1.3,
            color: isDone ? 'var(--faint)' : 'var(--txt)',
          }}
        >
          {commitment.title}
        </div>
        <div
          className="meta"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginTop: '4px',
            fontSize: '12px',
            color: 'var(--faint)',
          }}
        >
          <Avatar name={commitment.assignee} size="sm" />
          <span>{commitment.assignee || 'unassigned'}</span>
          <span
            className="mtg"
            style={{
              color: 'var(--muted)',
              background: 'var(--chip)',
              padding: '1px 7px',
              borderRadius: '6px',
            }}
          >
            {commitment.sourceMeeting}
          </span>
          <span>{commitment.sourceDate}</span>
        </div>
      </div>

      <div className={getDueClass()} style={{ fontSize: '12.5px', ...getDueStyle() }}>
        {commitment.due || 'no due date'}
      </div>

      {renderFollowUp()}
    </div>
  );
};
