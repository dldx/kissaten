CREATE TABLE `brew_recipes` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`data` text NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`deleted_at` integer,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `roaster_suggestion_votes` (
	`id` text PRIMARY KEY NOT NULL,
	`suggestion_id` text NOT NULL,
	`user_id` text NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`suggestion_id`) REFERENCES `roaster_suggestions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `roaster_suggestion_votes_uniq` ON `roaster_suggestion_votes` (`suggestion_id`,`user_id`);--> statement-breakpoint
CREATE TABLE `roaster_suggestions` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`name_normalized` text NOT NULL,
	`country` text,
	`website` text,
	`user_id` text NOT NULL,
	`status` text DEFAULT 'pending' NOT NULL,
	`upvote_count` integer DEFAULT 0 NOT NULL,
	`implemented_roaster_slug` text,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	`updated_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `roaster_suggestions_name_normalized_uniq` ON `roaster_suggestions` (`name_normalized`);