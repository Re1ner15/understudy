import React from 'react';

interface AvatarProps {
  name?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({ name, size = 'md', className = '' }) => {
  const initial = name ? name.trim().charAt(0).toUpperCase() : '·';
  
  const lower = name?.toLowerCase() || '';
  let bgColor = '#8b8b98';
  if (lower.includes('you')) {
    bgColor = '#0f9d6b'; // emerald — the user
  } else if (lower.includes('guest')) {
    bgColor = '#7c6bd6'; // violet — remote party
  } else if (initial === 'A' || lower.includes('alex')) {
    bgColor = '#4b8ff0';
  } else if (initial === 'S' || lower.includes('sam')) {
    bgColor = '#e0794e';
  }

  const dimensions = {
    sm: { width: '16px', height: '16px', fontSize: '8.5px' },
    md: { width: '26px', height: '26px', fontSize: '11px' },
    lg: { width: '28px', height: '28px', fontSize: '11.5px' },
  }[size];

  return (
    <div
      className={`avatar ${className}`}
      style={{
        width: dimensions.width,
        height: dimensions.height,
        borderRadius: '50%',
        backgroundColor: bgColor,
        display: 'grid',
        placeItems: 'center',
        color: '#ffffff',
        fontSize: dimensions.fontSize,
        fontWeight: 650,
        flex: 'none',
        lineHeight: 1,
      }}
    >
      {initial}
    </div>
  );
};
