import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    exclude: ['**/node_modules/**', '**/e2e/**', '**/dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: [
        'src/components/CompanyProfile.tsx',
        'src/components/DocumentList.tsx',
        'src/components/DocumentUpload.tsx',
        'src/components/dashboard/MatchedGrants.tsx',
        'src/components/dashboard/NotificationSettings.tsx',
      ],
      exclude: [
        'src/**/*.{test,spec}.{ts,tsx}',
        'src/test/**',
        'src/**/*.d.ts',
        'src/lib/api.ts',
        'src/i18n/**',
      ],
      thresholds: {
        lines: 80,
        branches: 75,
        functions: 80,
        statements: 80,
      },
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
