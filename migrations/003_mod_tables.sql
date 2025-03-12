CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    modlog_channel_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_guild_config_modlog ON guild_config(modlog_channel_id);

-- Create moderation case history
CREATE TABLE IF NOT EXISTS mod_cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('ban', 'kick', 'timeout', 'unban', 'untimeout')),
    reason TEXT,
    duration INTEGER, -- For timeout cases
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mod_cases_guild ON mod_cases(guild_id);
CREATE INDEX IF NOT EXISTS idx_mod_cases_target ON mod_cases(target_id);
