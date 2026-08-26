import React from 'react';

interface PasswordStrengthMeterProps {
  password: string;
}

export default function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  const getStrength = (pwd: string): number => {
    if (!pwd) return 0;

    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(pwd)) score++;

    return Math.min(score, 5);
  };

  const strength = getStrength(password);

  const getStrengthLabel = (s: number) => {
    if (s <= 2) return { text: '弱', color: 'text-danger', bg: 'bg-accent-danger' };
    if (s <= 4) return { text: '中', color: 'text-accent-warning', bg: 'bg-accent-warning' };
    return { text: '强', color: 'text-success', bg: 'bg-accent-success' };
  };

  const { text, color, bg } = getStrengthLabel(strength);

  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-ink-muted">密码强度</span>
        <span className={color}>{text}</span>
      </div>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded-full transition-colors ${
              level <= strength ? bg : 'bg-surface-2'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
