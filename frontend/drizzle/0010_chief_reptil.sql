CREATE TABLE `page_feedback` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`entity_slug` text,
	`entity_url_path` text,
	`entity_name` text,
	`page_url` text NOT NULL,
	`page_title` text,
	`fields` text DEFAULT '[]' NOT NULL,
	`message` text NOT NULL,
	`reporter_user_id` text,
	`reporter_email` text,
	`reporter_user_agent` text,
	`reporter_ip` text,
	`status` text DEFAULT 'new' NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`reporter_user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `page_feedback_kind_status_idx` ON `page_feedback` (`kind`,`status`);--> statement-breakpoint
CREATE INDEX `page_feedback_entity_idx` ON `page_feedback` (`entity_slug`,`kind`);