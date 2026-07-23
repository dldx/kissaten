PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TABLE `__new_roaster_suggestion_votes` (
	`id` text PRIMARY KEY NOT NULL,
	`suggestion_id` text NOT NULL,
	`user_id` text NOT NULL,
	`notify_on_implementation` integer DEFAULT false NOT NULL,
	`created_at` integer DEFAULT (cast(unixepoch('subsecond') * 1000 as integer)) NOT NULL,
	FOREIGN KEY (`suggestion_id`) REFERENCES `roaster_suggestions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
INSERT INTO `__new_roaster_suggestion_votes`("id", "suggestion_id", "user_id", "notify_on_implementation", "created_at") SELECT "id", "suggestion_id", "user_id", "notify_on_implementation", "created_at" FROM `roaster_suggestion_votes`;--> statement-breakpoint
DROP TABLE `roaster_suggestion_votes`;--> statement-breakpoint
ALTER TABLE `__new_roaster_suggestion_votes` RENAME TO `roaster_suggestion_votes`;--> statement-breakpoint
PRAGMA foreign_keys=ON;--> statement-breakpoint
CREATE UNIQUE INDEX `roaster_suggestion_votes_uniq` ON `roaster_suggestion_votes` (`suggestion_id`,`user_id`);