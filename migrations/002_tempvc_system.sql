PRAGMA foreign_keys = ON;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS temp_channel_permissions;
DROP TABLE IF EXISTS temp_channels;
DROP TABLE IF EXISTS tempvc_config;

-- Create tempvc configuration table
CREATE TABLE IF NOT EXISTS tempvc_config (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create temporary channels table
CREATE TABLE IF NOT EXISTS temp_channels (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    control_message_id INTEGER NOT NULL,
    text_channel_id INTEGER NOT NULL,
    name TEXT DEFAULT NULL,  -- Make name nullable
    user_limit INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add permissions table for temp channels
CREATE TABLE IF NOT EXISTS temp_channel_permissions (
    channel_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('user', 'role')),
    connect BOOLEAN DEFAULT TRUE,
    view_channel BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES temp_channels(channel_id) ON DELETE CASCADE,
    PRIMARY KEY (channel_id, target_id, target_type)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_temp_channels_guild ON temp_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_temp_channels_owner ON temp_channels(owner_id);
CREATE INDEX IF NOT EXISTS idx_tempvc_config_enabled ON tempvc_config(enabled);
CREATE INDEX IF NOT EXISTS idx_temp_channel_perms ON temp_channel_permissions(channel_id, target_id);