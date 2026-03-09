import { useI18n } from '../../i18n';
import { useState } from 'react';
import ContactModal from '../ContactModal/ContactModal';

export default function Footer() {
  const { t } = useI18n();
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);

  return (
    <>
      <footer className="bg-slate-800 border-t border-slate-700">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between space-y-4 md:space-y-0">
            {/* Logo 和简介 */}
            <div className="text-center md:text-left">
              <div className="text-xl font-['Pacifico'] text-primary mb-2">{t.common.tools}</div>
              <p className="text-slate-400 text-sm">{t.footer.desc}</p>
            </div>

            {/* 联系我们链接 */}
            <div className="flex items-center space-x-6">
              <button
                onClick={() => setIsContactModalOpen(true)}
                className="text-slate-400 hover:text-white transition-colors text-sm"
              >
                {t.footer.contactUs}
              </button>
            </div>
          </div>

          {/* 版权信息 */}
          <div className="border-t border-slate-700 mt-8 pt-8 text-center text-sm text-slate-400">
            <p>{t.footer.copyright}</p>
          </div>
        </div>
      </footer>

      {/* 联系我们弹窗 */}
      <ContactModal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
      />
    </>
  );
}
