import * as Sentry from '@sentry/nextjs';

if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: 0.1,
  });
}

/**
 * Application logger abstraction.
 * In a real-world scenario, you might want to plug this into
 * an external logging service like Sentry, Datadog, or LogRocket.
 */
class Logger {
  info(...args: unknown[]) {
    console.info('[INFO]', ...args);
  }

  warn(...args: unknown[]) {
    console.warn('[WARN]', ...args);
  }

  error(...args: unknown[]) {
    console.error('[ERROR]', ...args);
    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      if (args[0] instanceof Error) {
        Sentry.captureException(args[0]);
      } else {
        Sentry.captureException(new Error(String(args[0])));
      }
    }
  }

  debug(...args: unknown[]) {
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[DEBUG]', ...args);
    }
  }
}

export const logger = new Logger();
