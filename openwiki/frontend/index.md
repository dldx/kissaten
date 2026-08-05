# Files

- [Email Notifications](email-notifications.md) - Kissaten email system: nodemailer SMTP transporter, the single branded email shell in email-templates.ts, admin digest notifications, and user-facing transactional emails (magic-link OTP, beta approval, roaster-implemented to opted-in voters).
- [Feedback Data Lookup](feedback-data-lookup.md) - How to resolve page_feedback rows from the frontend SQLite database to their source coffee bean JSON files via a DuckDB↔SQLite cross-database join, plus the feedback dialog component UI that produces submissions.
- [Frontend](frontend.md) - SvelteKit 5 frontend: route structure, API client with smart search integration, tasting wizard, brew assistant, vault, local-first sync, authentication, SEO, and PWA support.
- [Local-First Sync System](sync-system.md) - Dexie (IndexedDB) to Turso/libSQL bidirectional sync architecture: four synced data types, three sync modes, SHA-256 digest verification, conflict resolution, and guest-to-user claiming.
