import React, { useState } from 'react';

interface AvatarProps {
  src?: string;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  name,
  size = 'md',
  className = ''
}) => {
  const [error, setError] = useState(false);

  const getInitials = (n: string) => {
    const parts = n.trim().split(/\s+/);
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return n.substring(0, 2).toUpperCase();
  };

  const sizes = {
    xs: 'h-6 w-6 text-[10px]',
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
    xl: 'h-16 w-16 text-lg',
  };

  const initials = getInitials(name);

  // Generate background color based on name string length for variance
  const colors = [
    'bg-indigo-600 text-white',
    'bg-emerald-600 text-white',
    'bg-rose-600 text-white',
    'bg-cyan-600 text-white',
    'bg-amber-600 text-white',
    'bg-violet-600 text-white'
  ];
  const colorIndex = (name.length + initials.charCodeAt(0)) % colors.length;
  const fallbackColor = colors[colorIndex];

  return (
    <div className={`relative inline-flex items-center justify-center rounded-full overflow-hidden font-semibold border border-slate-200 dark:border-zinc-800 ${sizes[size]} ${className}`}>
      {src && !error ? (
        <img
          src={src}
          alt={name}
          onError={() => setError(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <div className={`h-full w-full flex items-center justify-center ${fallbackColor}`}>
          {initials}
        </div>
      )}
    </div>
  );
};
