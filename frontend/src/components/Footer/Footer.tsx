import { useI18n } from '../../i18n';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="bg-slate-800 border-t border-slate-700">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between text-sm text-slate-400">
          <div className="text-xl font-['Pacifico'] text-primary">{t.common.tools}</div>
          <p>{t.footer.copyright}</p>
        </div>
      </div>
    </footer>
  );
}
