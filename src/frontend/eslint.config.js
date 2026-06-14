import js from '@eslint/js';
import tseslint from 'typescript-eslint';

// Flat Config (ESLint 9). js.recommended + typescript-eslint.recommended
// fangen genau die Fehlerklasse KI-generierten Codes ab: ungenutzte
// Variablen, falsche/erfundene Signaturen, tote Pfade.
export default tseslint.config(
  { ignores: ['dist/', 'node_modules/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    // Node-Tooling-Skripte (z. B. scripts/check-types.mjs) duerfen Node-Globals nutzen.
    files: ['**/*.{js,mjs}'],
    languageOptions: { globals: { process: 'readonly', console: 'readonly' } },
  },
);
