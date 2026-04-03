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
    if (s <= 2) return { text: '弱', color: 'text-red-400', bg: 'bg-red-500' };
    if (s <= 4) return { text: '中', color: 'text-yellow-400', bg: 'bg-yellow-500' };
    return { text: '强', color: 'text-emerald-400', bg: 'bg-emerald-500' };
  };

  const { text, color, bg } = getStrengthLabel(strength);

  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">密码强度</span>
        <span className={color}>{text}</span>
      </div>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded-full transition-colors ${
              level <= strength ? bg : 'bg-slate-700'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
