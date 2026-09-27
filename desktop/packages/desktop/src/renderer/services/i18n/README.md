# Strings (i18n)

Kel ships in English (en-US) only (D-61). There is no language setting and no other locale bundle.

- Strings live in `locales/en-US/<module>.json`; `locales/en-US/index.ts` combines them.
- `index.ts` initialises i18next synchronously with en-US. `@/common/config/i18n` resolves every
  language hint to en-US, and the main process (`process/services/i18n`) loads the same strings for
  the tray menu and dialogs.
- After changing keys, run `bun run i18n:types` to regenerate `i18n-keys.d.ts`, and
  `node scripts/check-i18n.js` to validate.

```tsx
import { useTranslation } from 'react-i18next';

const Example = () => {
  const { t } = useTranslation();
  return <h1>{t('login.brand')}</h1>;
};
```
