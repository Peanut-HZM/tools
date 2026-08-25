import { useI18n } from '../../i18n';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="bg-surface-1 border-t border-border">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between text-sm text-ink-faint">
          <div className="text-xl font-['Pacifico'] bg-gradient-to-br from-accent to-accent-secondary bg-clip-text text-transparent">{t.common.tools}</div>
          <p>{t.footer.copyright}</p>
        </div>
      </div>
    </footer>
  );
}
