import * as Sentry from '@sentry/sveltekit';

Sentry.init({
  dsn: 'https://8b80ac8943da9fc1eacbb1f0988af9a9@o4511631765209088.ingest.de.sentry.io/4511631781134416',

  tracesSampleRate: 1.0,

  // Enable logs to be sent to Sentry
  enableLogs: true,

  // uncomment the line below to enable Spotlight (https://spotlightjs.com)
  // spotlight: import.meta.env.DEV,
});