import React from 'react';

interface StatTileProps {
  value: number | string;
  label: string;
  variant?: 'normal' | 'attn' | 'eng';
}

export const StatTile: React.FC<StatTileProps> = ({ value, label, variant = 'normal' }) => {
  let numColor = 'var(--txt)';
  if (variant === 'attn') numColor = 'var(--red)';
  if (variant === 'eng') numColor = 'var(--accent)';

  return (
    <div
      className={`stat ${variant}`}
      style={{
        background: 'var(--panel)',
        border: '1px solid var(--line)',
        borderRadius: '13px',
        padding: '15px 17px',
        boxShadow: 'var(--card-sh)',
      }}
    >
      <div
        className="n"
        style={{
          fontSize: '26px',
          fontWeight: 700,
          letterSpacing: '-.02em',
          lineHeight: 1,
          color: numColor,
        }}
      >
        {value}
      </div>
      <div
        className="l"
        style={{
          fontSize: '12.5px',
          color: 'var(--muted)',
          marginTop: '7px',
        }}
      >
        {label}
      </div>
    </div>
  );
};
