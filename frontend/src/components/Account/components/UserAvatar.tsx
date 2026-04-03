import React from 'react';
import { User } from 'lucide-react';

interface UserAvatarProps {
  username?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function UserAvatar({ username, size = 'md', className = '' }: UserAvatarProps) {
  const sizeClasses = {
    sm: 'w-10 h-10 text-sm',
    md: 'w-16 h-16 text-base',
    lg: 'w-24 h-24 text-2xl',
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div
      className={`${sizeClasses[size]} rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-semibold ${className}`}
    >
      {username ? (
        getInitials(username)
      ) : (
        <User className="w-1/2 h-1/2 opacity-50" />
      )}
    </div>
  );
}
