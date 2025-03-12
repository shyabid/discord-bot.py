-- Command usage statistics
CREATE TABLE IF NOT EXISTS command_statistics (
    command_name TEXT UNIQUE,
    usage_count INTEGER DEFAULT 0
);

-- Guild prefix settings
CREATE TABLE IF NOT EXISTS guild_prefixes (
    guild_id TEXT PRIMARY KEY,
    prefixes TEXT NOT NULL
);

-- AFK status tracking
CREATE TABLE IF NOT EXISTS afk_status (
    user_id INTEGER,
    guild_id INTEGER,
    reason TEXT NOT NULL,
    since TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_id INTEGER,
    PRIMARY KEY (user_id, guild_id)
);

-- Create aliases table
CREATE TABLE IF NOT EXISTS aliases (
    guild_id INTEGER,
    alias TEXT,
    command TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, alias)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_aliases_lookup ON aliases(guild_id, alias); 

-- Create auto-reaction table
CREATE TABLE IF NOT EXISTS auto_reactions (
    guild_id INTEGER,
    trigger TEXT,
    type TEXT NOT NULL CHECK(type IN ('startswith', 'contains', 'exact', 'endswith')),
    emojis TEXT NOT NULL,  -- JSON array of emoji strings
    PRIMARY KEY (guild_id, trigger)
);

-- Create auto-response table
CREATE TABLE IF NOT EXISTS auto_responses (
    guild_id INTEGER,
    trigger TEXT,
    type TEXT NOT NULL CHECK(type IN ('startswith', 'contains', 'exact', 'endswith')),
    response TEXT NOT NULL,
    PRIMARY KEY (guild_id, trigger)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_auto_reactions_lookup ON auto_reactions(guild_id, trigger);
CREATE INDEX IF NOT EXISTS idx_auto_responses_lookup ON auto_responses(guild_id, trigger); 

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_afk_user_guild ON afk_status(user_id, guild_id);
CREATE INDEX IF NOT EXISTS idx_command_stats_name ON command_statistics(command_name);
CREATE INDEX IF NOT EXISTS idx_guild_prefixes_id ON guild_prefixes(guild_id);
CREATE INDEX IF NOT EXISTS idx_aliases_lookup ON aliases(guild_id, alias);

-- Leveling system tables
CREATE TABLE IF NOT EXISTS user_levels (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_xp_time REAL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_rewards (
    guild_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS guild_leveling_settings (
    guild_id INTEGER PRIMARY KEY,
    levelup_channel_id INTEGER,
    bg_color TEXT DEFAULT '010101',
    text_color TEXT DEFAULT 'ffffff',
    xp_color TEXT DEFAULT 'ffffff',
    circle_avatar INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    reminder_time INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time);

-- Economy Tables

-- Up
-- Create daily claims tracking table
CREATE TABLE IF NOT EXISTS daily_claims (
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    last_claim INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER DEFAULT 0,
    last_streak_reset INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- Down

CREATE TABLE IF NOT EXISTS economy (
    user_id INTEGER,
    guild_id INTEGER,
    balance REAL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS user_balances (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    mgems INTEGER DEFAULT 0,
    last_daily_claim TIMESTAMP,
    last_transaction_at TIMESTAMP,
    total_earned REAL DEFAULT 0.0,
    total_spent REAL DEFAULT 0.0,
    streak_count INTEGER DEFAULT 0,
    highest_streak INTEGER DEFAULT 0,
    inventory TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    code TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('item', 'role')),
    name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    max_per_user INTEGER,
    role_id INTEGER,
    time_limit TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    order_id TEXT NOT NULL UNIQUE,
    price_paid REAL NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

CREATE TABLE IF NOT EXISTS temp_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    removal_time TIMESTAMP NOT NULL,
    UNIQUE(user_id, guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS shop_stats (
    guild_id INTEGER PRIMARY KEY,
    total_revenue REAL DEFAULT 0.0
);

-- User balance table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    last_daily_claim TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_purchases_user_id ON user_purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_user_purchases_guild_id ON user_purchases(guild_id);
CREATE INDEX IF NOT EXISTS idx_shop_items_guild_id ON shop_items(guild_id);
CREATE INDEX IF NOT EXISTS idx_temp_roles_removal_time ON temp_roles(removal_time);
CREATE INDEX IF NOT EXISTS idx_temp_roles_user_guild ON temp_roles(user_id, guild_id);

-- Quiz Statistics Tables
CREATE TABLE IF NOT EXISTS quiz_stats (
    user_id INTEGER NOT NULL,
    total_quizzes INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS quiz_category_stats (
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    total_attempts INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, category)
);

CREATE INDEX IF NOT EXISTS idx_quiz_stats_user ON quiz_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_category_user ON quiz_category_stats(user_id);

-- Welcomer system tables
CREATE TABLE IF NOT EXISTS welcomer_settings (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    channel_id INTEGER,
    message TEXT,
    title TEXT,
    description TEXT,
    color TEXT,
    footer_text TEXT,
    footer_icon_url TEXT,
    author_name TEXT,
    author_url TEXT,
    author_icon_url TEXT,
    thumbnail_url TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS welcomer_buttons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    url TEXT NOT NULL,
    FOREIGN KEY (guild_id) REFERENCES welcomer_settings(guild_id) ON DELETE CASCADE
);

-- Create shop_data table
CREATE TABLE IF NOT EXISTS shop_data (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    message_id INTEGER,
    items TEXT DEFAULT '[]' -- JSON array of items
);

-- Create economy_settings table
CREATE TABLE IF NOT EXISTS economy_settings (
    guild_id INTEGER PRIMARY KEY,
    daily_min REAL DEFAULT 2.0,
    daily_max REAL DEFAULT 5.0,
    message_reward REAL DEFAULT 0.1,
    streak_bonus_multiplier REAL DEFAULT 0.1,
    max_streak_bonus INTEGER DEFAULT 7
);

-- Create user_transactions table
CREATE TABLE IF NOT EXISTS user_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Waifu System Tables
CREATE TABLE IF NOT EXISTS waifu_cards (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT UNIQUE NOT NULL,
    owner_id INTEGER NOT NULL,
    waifu_id TEXT NOT NULL,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL CHECK(rarity IN ('SS', 'S', 'A', 'B', 'C', 'D')),
    rank INTEGER,
    level INTEGER DEFAULT 1,
    locked BOOLEAN DEFAULT FALSE,
    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS waifu_serials (
    rarity TEXT PRIMARY KEY CHECK(rarity IN ('SS', 'S', 'A', 'B', 'C', 'D')),
    count INTEGER DEFAULT 0,
    last_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS waifu_trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    offerer_id INTEGER NOT NULL,
    offeree_id INTEGER NOT NULL,
    offerer_card TEXT NOT NULL,
    offeree_card TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'cancelled', 'failed')),
    guild_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (offerer_card) REFERENCES waifu_cards(serial_number),
    FOREIGN KEY (offeree_card) REFERENCES waifu_cards(serial_number)
);

-- Waifu System Indexes
CREATE INDEX IF NOT EXISTS idx_waifu_cards_owner ON waifu_cards(owner_id);
CREATE INDEX IF NOT EXISTS idx_waifu_cards_serial ON waifu_cards(serial_number);
CREATE INDEX IF NOT EXISTS idx_waifu_cards_rarity ON waifu_cards(rarity);
CREATE INDEX IF NOT EXISTS idx_waifu_cards_rank ON waifu_cards(rank);
CREATE INDEX IF NOT EXISTS idx_waifu_trades_users ON waifu_trades(offerer_id, offeree_id);
CREATE INDEX IF NOT EXISTS idx_waifu_trades_status ON waifu_trades(status);
CREATE INDEX IF NOT EXISTS idx_waifu_trades_guild ON waifu_trades(guild_id);

-- Waifu System Triggers
CREATE TRIGGER IF NOT EXISTS update_card_modified_time 
AFTER UPDATE ON waifu_cards
FOR EACH ROW
BEGIN
    UPDATE waifu_cards 
    SET last_modified_at = CURRENT_TIMESTAMP
    WHERE card_id = NEW.card_id;
END;

CREATE TRIGGER IF NOT EXISTS update_serial_generated_time
AFTER UPDATE ON waifu_serials
FOR EACH ROW
BEGIN
    UPDATE waifu_serials 
    SET last_generated_at = CURRENT_TIMESTAMP
    WHERE rarity = NEW.rarity;
END;

-- Moderation System Tables
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    modlog_channel_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mod_cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('ban', 'kick', 'timeout', 'unban', 'untimeout')),
    reason TEXT,
    duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id) ON DELETE CASCADE
);

-- Moderation System Indexes
CREATE INDEX IF NOT EXISTS idx_guild_config_modlog ON guild_config(modlog_channel_id);
CREATE INDEX IF NOT EXISTS idx_mod_cases_guild ON mod_cases(guild_id);
CREATE INDEX IF NOT EXISTS idx_mod_cases_target ON mod_cases(target_id);

-- Add tempvc tables
CREATE TABLE IF NOT EXISTS tempvc_config (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

-- Create indexes for tempvc system
CREATE INDEX IF NOT EXISTS idx_temp_channels_guild ON temp_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_temp_channels_owner ON temp_channels(owner_id);
CREATE INDEX IF NOT EXISTS idx_tempvc_config_enabled ON tempvc_config(enabled);
CREATE INDEX IF NOT EXISTS idx_temp_channel_perms ON temp_channel_permissions(channel_id, target_id);