import React from 'react';

interface LogoProps {
  size?: number;
  showWordmark?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const Logo: React.FC<LogoProps> = ({
  size = 20,
  showWordmark = false,
  className,
  style,
}) => {
  return (
    <div
      className={`logo ${className || ''}`.trim()}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        lineHeight: 1,
        ...style,
      }}
    >
      <img
        src="/understudy-mark.svg"
        alt="Understudy"
        width={size}
        height={size}
        style={{
          width: `${size}px`,
          height: `${size}px`,
          display: 'block',
          flexShrink: 0,
        }}
      />
      {showWordmark && (
        <span
          style={{
            fontWeight: 650,
            letterSpacing: '-0.02em',
            color: 'var(--txt)',
            userSelect: 'none',
          }}
        >
          Understudy
        </span>
      )}
    </div>
  );
};
