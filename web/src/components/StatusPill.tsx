import React from 'react';
import { ToolStatus } from '../data/types';

interface StatusPillProps {
  status: ToolStatus;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, className = '' }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'done':
        return {
          label: 'Done',
          className: 'done',
          style: { color: 'var(--done)', background: 'var(--done-soft)' },
          icon: (
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <path d="m5 13 4 4L19 7" />
            </svg>
          ),
        };
      case 'running':
        return {
          label: 'Running',
          className: 'run',
          style: { color: 'var(--run)', background: 'var(--run-soft)' },
          icon: <span className="d" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor', animation: 'blink 1.1s steps(2) infinite' }} />,
        };
      case 'needs_approval':
        return {
          label: 'Needs approval',
          className: 'appr',
          style: { color: 'var(--amber)', background: 'var(--amber-soft)' },
          icon: <span className="d" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />,
        };
      case 'queued':
        return {
          label: 'Queued',
          className: 'queue',
          style: { color: 'var(--faint)', background: 'var(--chip)' },
          icon: <span className="d" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />,
        };
      case 'error':
        return {
          label: 'Error',
          className: 'error',
          style: { color: 'var(--red)', background: 'var(--red-soft)' },
          icon: <span className="d" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <span
      className={`pill ${config.className} ${className}`}
      style={{
        fontSize: '11px',
        fontWeight: 650,
        padding: '4px 9px',
        borderRadius: '20px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        whiteSpace: 'nowrap',
        ...config.style,
      }}
    >
      {config.icon}
      {config.label}
    </span>
  );
};
