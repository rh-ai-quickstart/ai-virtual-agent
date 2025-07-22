import js from '@eslint/js';
import tseslint from 'typescript-eslint';

// ESLint Plugin Imports
import jsxA11yPlugin from 'eslint-plugin-jsx-a11y';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import reactRefreshPlugin from 'eslint-plugin-react-refresh';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: ['node_modules/', 'dist/', '.eslintcache', '*.log', 'src/types/index.d.ts'],
  },

  {
    files: ['**/*.js', '**/*.jsx'], // Explicitly targets JS and JSX files
    ...js.configs.recommended,
    languageOptions: {
      ...js.configs.recommended.languageOptions,
      globals: {
        ...globals.es2022,
      },
    },
    rules: {
      ...js.configs.recommended.rules,
    },
  },

  ...tseslint.configs.recommendedTypeChecked.map((config) => ({
    ...config, // Spread each original config object from recommendedTypeChecked
    // These objects should already contain `files: ['*.ts', '*.tsx', etc.]`
    // and rules that require type checking.
    ignores: ['eslint.config.js'],
    languageOptions: {
      ...(config.languageOptions || {}), // Preserve original languageOptions
      parserOptions: {
        ...(config.languageOptions?.parserOptions || {}), // Preserve original parserOptions
        project: [
          './tsconfig.app.json', // Relative to eslint.config.js (frontend/tsconfig.app.json)
          './tsconfig.node.json', // Relative to eslint.config.js (frontend/tsconfig.node.json)
        ],
        tsconfigRootDir: import.meta.dirname, // Should resolve to 'frontend/'
      },
    },
    rules: {
      ...(config.rules || {}), // Preserve original rules
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  })),

  // Additional configuration for React within TS/TSX files
  // This layers React-specific settings on top of the TypeScript setup for .ts/.tsx files.
  {
    files: ['**/*.{ts,tsx}'], // Target only TypeScript/TSX files
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      'react-refresh': reactRefreshPlugin,
      'jsx-a11y': jsxA11yPlugin,
    },
    languageOptions: {
      // Ensure JSX is enabled for TSX files
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        // Globals specific to your React components
        ...globals.browser,
      },
    },
    rules: {
      // React specific rules
      ...reactPlugin.configs.recommended.rules,
      ...reactPlugin.configs['jsx-runtime'].rules,
      ...reactHooksPlugin.configs.recommended.rules,
      ...jsxA11yPlugin.configs.recommended.rules,

      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Any other React specific rule overrides
    },
    settings: {
      react: {
        version: 'detect', // Detect React version
      },
    },
  },

  eslintPluginPrettierRecommended
);
