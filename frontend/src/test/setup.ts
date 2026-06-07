// Vitest global setup — extends matchers (toBeInTheDocument, etc.) and
// stubs out browser APIs that jsdom does not implement but our code touches.
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// IntersectionObserver is used by framer-motion; jsdom lacks it.
if (typeof globalThis.IntersectionObserver === 'undefined') {
  globalThis.IntersectionObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
    root = null;
    rootMargin = '';
    thresholds = [];
  } as unknown as typeof IntersectionObserver;
}

// matchMedia is used by Tailwind dark-mode detection and framer-motion's
// useReducedMotion. jsdom returns `false` for every media query by default.
if (typeof window !== 'undefined' && typeof window.matchMedia === 'undefined') {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
