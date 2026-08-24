import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并 Tailwind 类名工具。
 * 支持 clsx 的条件类 + tailwind-merge 去重。
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
