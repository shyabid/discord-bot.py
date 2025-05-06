CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    UNIQUE(guild_id, name)
);

CREATE TABLE IF NOT EXISTS tag_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    alias_name TEXT NOT NULL,
    original_tag_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, alias_name),
    FOREIGN KEY (guild_id, original_tag_name) REFERENCES tags(guild_id, name) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tags_guild ON tags(guild_id);
CREATE INDEX IF NOT EXISTS idx_tags_owner ON tags(owner_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tag_aliases_guild ON tag_aliases(guild_id);
CREATE INDEX IF NOT EXISTS idx_tag_aliases_original ON tag_aliases(original_tag_name);

-- Create trigger to auto-update modified_at timestamp using simpler syntax
CREATE TRIGGER IF NOT EXISTS update_tag_modified_time 
AFTER UPDATE ON tags
WHEN OLD.content != NEW.content
BEGIN
    UPDATE tags SET modified_at = CURRENT_TIMESTAMP WHERE tag_id = NEW.tag_id;
END;