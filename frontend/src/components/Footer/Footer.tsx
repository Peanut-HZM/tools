import { useI18n } from '../../i18n';

export default function Footer() {
  const { t } = useI18n();
  
  const toolCategories = [
    t.footer.links.textTools,
    t.footer.links.convertTools,
    t.footer.links.calcTools,
    t.footer.links.designTools
  ];
  
  const supportLinks = [
    t.footer.links.help,
    t.footer.links.feedback,
    t.footer.links.api,
    t.footer.links.docs
  ];
  
  const aboutLinks = [
    t.footer.links.intro,
    t.footer.links.team,
    t.footer.links.contact,
    t.footer.links.jobs
  ];

  return (
    <footer className="bg-slate-800 border-t border-slate-700">
      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="text-xl font-['Pacifico'] text-primary mb-4">{t.common.logo}</div>
            <p className="text-slate-400 text-sm">
              {t.footer.desc}
            </p>
          </div>
          <div>
            <h4 className="font-semibold mb-4">{t.footer.toolCategories}</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {toolCategories.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">{t.footer.support}</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {supportLinks.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">{t.footer.about}</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              {aboutLinks.map((link) => (
                <li key={link}>
                  <a href="#" className="hover:text-white transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-700 mt-8 pt-8 text-center text-sm text-slate-400">
          <p>{t.footer.copyright}</p>
        </div>
      </div>
    </footer>
  );
}
