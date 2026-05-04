CREATE TABLE `custom_beans` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`bean_data` text NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
ALTER TABLE `user` ADD `is_beta_allowed` integer DEFAULT false NOT NULL;--> statement-breakpoint
ALTER TABLE `user` ADD `beta_enabled` integer DEFAULT false NOT NULL;