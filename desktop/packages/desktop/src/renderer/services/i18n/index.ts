import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import { DEFAULT_LANGUAGE } from '@/common/config/i18n';
import { applyDocumentDirection } from './direction';

// D-61: Kel ships in English (en-US) only. There is no language setting and no other locale bundle;
// the strings are loaded synchronously so the first render is already in English.
import enUS from './locales/en-US/index';

i18n
  .use(initReactI18next)
  .init({
    resources: { [DEFAULT_LANGUAGE]: { translation: enUS as Record<string, unknown> } },
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: [DEFAULT_LANGUAGE],
    debug: false,
    interpolation: { escapeValue: false },
  })
  .catch((error: Error) => {
    console.error('Failed to initialize i18n:', error);
  });

applyDocumentDirection(DEFAULT_LANGUAGE);

export default i18n;
