export type AccountSection = 'basic' | 'security' | 'preferences' | 'apiTokens';

export interface NavItem {
  id: AccountSection;
  label: string;
  icon: React.ReactNode;
  description?: string;
}
