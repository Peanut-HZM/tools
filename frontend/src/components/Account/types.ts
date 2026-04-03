export type AccountSection = 'basic' | 'security' | 'preferences';

export interface NavItem {
  id: AccountSection;
  label: string;
  icon: React.ReactNode;
  description?: string;
}
