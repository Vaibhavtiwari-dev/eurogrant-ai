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
  }

  debug(...args: unknown[]) {
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[DEBUG]', ...args);
    }
  }
}

export const logger = new Logger();
