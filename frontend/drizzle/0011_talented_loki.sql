CREATE TABLE `email_queue` (
	`id` text PRIMARY KEY NOT NULL,
	`recipient_email` text NOT NULL,
	`recipient_name` text,
	`kind` text NOT NULL,
	`data` text DEFAULT '{}' NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`sent_at` integer
);
--> statement-breakpoint
CREATE INDEX `email_queue_recipient_status_idx` ON `email_queue` (`recipient_email`,`status`);