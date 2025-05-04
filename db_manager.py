import sqlite3
import os
import time
import json
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

class DBManager:
    def __init__(self):
        self.connection = sqlite3.connect("database.db")
        self._cursor = self.connection.cursor()
        self.execute("PRAGMA foreign_keys = ON")
        self.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.commit()
        
        try:
            self.execute("SELECT COUNT(*) FROM migrations WHERE name = 'schema'")
            if self.fetchone()[0] == 0:
                print("Applying base schema...")
                with open("schema.sql", "r", encoding='utf-8') as f:
                    schema = f.read()
                    statements = []
                    current_statement = []
                    in_trigger = False
                    
                    for line in schema.split('\n'):
                        line = line.strip()
                        if not line or line.startswith('--'):
                            continue
                            
                        if 'CREATE TRIGGER' in line:
                            in_trigger = True
                            
                        if in_trigger:
                            current_statement.append(line)
                            if line == 'END;':
                                statements.append('\n'.join(current_statement))
                                current_statement = []
                                in_trigger = False
                        else:
                            current_statement.append(line)
                            if line.endswith(';'):
                                statements.append('\n'.join(current_statement))
                                current_statement = []
                                
                    for statement in statements:
                        if statement.strip():
                            self.execute(statement.strip())
                            
                self.execute("INSERT INTO migrations (name) VALUES (?)", ("schema",))
                self.commit()
                print("Base schema applied successfully")
                
            # Then apply all migrations in order
            migrations_dir = "migrations"
            if not os.path.exists(migrations_dir):
                os.makedirs(migrations_dir)
                print(f"Created migrations directory: {migrations_dir}")
            
            applied = set(self._get_applied_migrations())
            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
            
            for filename in migration_files:
                migration_name = filename[:-4]  # Remove .sql extension
                if migration_name in applied:
                    continue
                    
                print(f"Applying migration: {migration_name}")
                try:
                    filepath = os.path.join(migrations_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        migration_sql = f.read()
                        for statement in migration_sql.split(';'):
                            if statement.strip():
                                self.execute(statement.strip())
                    
                    self.execute("INSERT INTO migrations (name) VALUES (?)", (migration_name,))
                    self.commit()
                    print(f"Successfully applied migration: {migration_name}")
                except Exception as e:
                    print(f"Failed to apply migration {filename}: {e}")
                    raise
                    
        except Exception as e:
            print(f"Error during database initialization: {e}")
            raise

    def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        try:
            self.execute("SELECT name FROM migrations ORDER BY id")
            return [row[0] for row in self.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting applied migrations: {e}")
            return []

    def _apply_migrations(self) -> None:
        """Apply any pending migrations."""
        applied = set(self._get_applied_migrations())
        migrations_dir = "migrations"
        
        if not os.path.exists(migrations_dir):
            os.makedirs(migrations_dir)
            print(f"Created migrations directory: {migrations_dir}")
            return
            
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        if not migration_files:
            print("No migration files found")
            return
            
        for filename in migration_files:
            migration_name = filename[:-4]  # Remove .sql extension
            if migration_name in applied:
                continue
                
            print(f"Applying migration: {migration_name}")
            try:
                with open(os.path.join(migrations_dir, filename), 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                    for statement in migration_sql.split(';'):
                        if statement.strip():
                            try:
                                self.execute(statement)
                            except sqlite3.Error as e:
                                print(f"Error in migration {filename}, statement: {statement.strip()}\nError: {e}")
                                raise
                
                self.execute("INSERT INTO migrations (name) VALUES (?)", (migration_name,))
                self.commit()
                print(f"Successfully applied migration: {migration_name}")
            except Exception as e:
                print(f"Failed to apply migration {filename}: {e}")
                raise

    def execute(self, query: str, params=()) -> sqlite3.Cursor:
        """Execute a SQL query with parameters.
        
        Args:
            query (str): The SQL query to execute
            params (tuple|dict): Query parameters (either tuple or dict)
        """
        try:
            # If params is not already a tuple/list, convert it
            if not isinstance(params, (tuple, list)):
                params = (params,)
            self._cursor.execute(query, params)
            return self._cursor
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print(f"Table missing error: {e}. Try restarting the bot to apply migrations.")
            raise


    def execute_and_commit(self, query: str, params=()) -> sqlite3.Cursor:
        """Execute a SQL query with parameters and commit the changes.
        
        Args:
            query (str): The SQL query to execute
            params (tuple|list|dict): Query parameters
            
        Returns:
            sqlite3.Cursor: Database cursor
        """
        self.execute(query, params)
        self.commit()
        return self._cursor
    
    def fetchone(self) -> Optional[tuple]: return self._cursor.fetchone()
    def fetchall(self) -> List[tuple]: return self._cursor.fetchall()
    def commit(self) -> None: self.connection.commit()
    def close(self) -> None: self.connection.close()
    
    def count_up_command(self, command_name: str) -> None:
        self.execute("INSERT OR IGNORE INTO command_statistics (command_name) VALUES (?)", (command_name,))
        self.execute("UPDATE command_statistics SET usage_count = usage_count + 1 WHERE command_name = ?", (command_name,))
        self.commit()

    def get_command_usage(self, command_name: str) -> int:
        self.execute("SELECT usage_count FROM command_statistics WHERE command_name = ?", (command_name,))
        result = self.fetchone()
        return result[0] if result else 0

    def get_top_commands(self, limit: int = 5) -> List[Tuple[str, int]]:
        self.execute("""
            SELECT command_name, usage_count 
            FROM command_statistics 
            ORDER BY usage_count DESC 
            LIMIT ?
        """, (limit,))
        return self.fetchall()

    def get_guild_prefixes(self, guild_id: str) -> List[str]:
        self.execute("SELECT prefixes FROM guild_prefixes WHERE guild_id = ?", (guild_id,))
        result = self.fetchone()
        if not result:
            self.execute_and_commit("INSERT OR REPLACE INTO guild_prefixes (guild_id, prefixes) VALUES (?, ?)",(guild_id, json.dumps(["?"])))
            return ["?"]
        return json.loads(result[0])

    def set_guild_prefixes(self, guild_id: str, prefixes: List[str]) -> None:
        self.execute_and_commit("INSERT OR REPLACE INTO guild_prefixes (guild_id, prefixes) VALUES (?, ?)", (guild_id, json.dumps(prefixes)))

    def set_afk(self, user_id: int, guild_id: int, reason: str) -> None:
        self.execute_and_commit("INSERT OR REPLACE INTO afk_status (user_id, guild_id, reason, since, last_message_id) VALUES (?, ?, ?, datetime('now'), NULL)",(user_id, guild_id, reason))

    def remove_afk(self, user_id: int, guild_id: int) -> Optional[Tuple[str, float]]:
        self.execute("SELECT reason, strftime('%s', since) FROM afk_status WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        data = self.fetchone()
        if data: self.execute_and_commit("DELETE FROM afk_status WHERE user_id = ? AND guild_id = ?",(user_id, guild_id))
        return data

    def get_afk(self, user_id: int, guild_id: int) -> Optional[Tuple[str, float]]:
        self.execute("SELECT reason, strftime('%s', since) FROM afk_status WHERE user_id = ? AND guild_id = ?",(user_id, guild_id))
        return self.fetchone()

    def set_last_afk_message(self, user_id: int, guild_id: int, message_id: int) -> None:
        self.execute_and_commit("UPDATE afk_status SET last_message_id = ? WHERE user_id = ? AND guild_id = ?",(message_id, user_id, guild_id))

    def get_last_afk_message(self, user_id: int, guild_id: int) -> Optional[int]:
        self.execute("SELECT last_message_id FROM afk_status WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        result = self.fetchone(); return result[0] if result else None

    def add_alias(self, guild_id: int, alias: str, command: str, created_by: int) -> None:
        self.execute_and_commit( "INSERT OR REPLACE INTO aliases (guild_id, alias, command, created_by) VALUES (?, ?, ?, ?)",(guild_id, alias, command, created_by))

    def remove_alias(self, guild_id: int, alias: str) -> bool:
        self.execute_and_commit("DELETE FROM aliases WHERE guild_id = ? AND alias = ?", (guild_id, alias)); return self._cursor.rowcount > 0

    def reset_aliases(self, guild_id: int) -> None:
        self.execute_and_commit("DELETE FROM aliases WHERE guild_id = ?", (guild_id,))

    def get_alias(self, guild_id: int, alias: str) -> Optional[Tuple[str, int]]:
        self.execute("SELECT command, created_by FROM aliases WHERE guild_id = ? AND alias = ?", (guild_id, alias)); return self.fetchone()

    def get_all_aliases(self, guild_id: int) -> List[Tuple[str, str]]:
        self.execute("SELECT alias, command FROM aliases WHERE guild_id = ? ORDER BY alias", (guild_id,))
        return self.fetchall()

    def add_auto_reaction(self, guild_id: int, trigger: str, emojis: List[str], trigger_type: str) -> None: 
        self.execute_and_commit("INSERT OR REPLACE INTO auto_reactions (guild_id, trigger, type, emojis) VALUES (?, ?, ?, ?)", (guild_id, trigger.lower(), trigger_type, json.dumps(emojis)))

    def remove_auto_reaction(self, guild_id: int, trigger: str) -> bool:
        self.execute_and_commit("DELETE FROM auto_reactions WHERE guild_id = ? AND trigger = ?", (guild_id, trigger.lower()))
        return self._cursor.rowcount > 0

    def get_auto_reactions(self, guild_id: int) -> List[Tuple[str, str, List[str]]]:
        self.execute("SELECT trigger, type, emojis FROM auto_reactions WHERE guild_id = ?", (guild_id,))
        results = self.fetchall()
        return [(trigger, type_, json.loads(emojis)) for trigger, type_, emojis in results]

    def get_matching_reactions(self, guild_id: int, content: str) -> List[List[str]]:
        self.execute("SELECT type, emojis, trigger FROM auto_reactions WHERE guild_id = ?", (guild_id,))
        matching_emojis = []
        content = content.lower()
        for type_, emojis, trigger in self.fetchall():
            trigger = trigger.lower()
            if (
                (type_ == "startswith" and content.startswith(trigger)) or (type_ == "contains" and trigger in content) or
                (type_ == "exact" and content == trigger) or (type_ == "endswith" and content.endswith(trigger))
            ): matching_emojis.append(json.loads(emojis))
        return matching_emojis

    def add_auto_response(self, guild_id: int, trigger: str, response: str, trigger_type: str) -> None:
        self.execute_and_commit(
            "INSERT OR REPLACE INTO auto_responses (guild_id, trigger, type, response) VALUES (?, ?, ?, ?)",
            (guild_id, trigger.lower(), trigger_type, response)
        )

    def remove_auto_response(self, guild_id: int, trigger: str) -> bool:
        self.execute_and_commit("DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?", (guild_id, trigger.lower()))
        return self._cursor.rowcount > 0

    def get_auto_responses(self, guild_id: int) -> List[Tuple[str, str, str]]:
        self.execute("SELECT trigger, type, response FROM auto_responses WHERE guild_id = ?", (guild_id,))
        return self.fetchall()

    def get_matching_responses(self, guild_id: int, content: str) -> List[str]:
        self.execute("SELECT type, response, trigger FROM auto_responses WHERE guild_id = ?", (guild_id,))
        matching_responses = []; content = content.lower()
        for type_, response, trigger in self.fetchall():
            trigger = trigger.lower()
            if (
                (type_ == "startswith" and content.startswith(trigger)) or (type_ == "contains" and trigger in content) or
                (type_ == "exact" and content == trigger) or (type_ == "endswith" and content.endswith(trigger))
            ): matching_responses.append(response)
        return matching_responses

    # Leveling Methods
    def get_user_level_data(self, guild_id: int, user_id: int) -> tuple:
        self.execute("""
            SELECT xp, level, last_xp_time FROM user_levels 
            WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id))
        result = self.fetchone(); return result if result else (0, 0, 0)

    def update_user_level(self, guild_id: int, user_id: int, xp: int, level: int) -> None:
        self.execute_and_commit(
            """INSERT OR REPLACE INTO user_levels (guild_id, user_id, xp, level, last_xp_time)
            VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, xp, level, time.time())
        )
    def get_guild_leaderboard(self, guild_id: int, limit: int = 10) -> List[tuple]:
        self.execute("""
            SELECT user_id, xp, level FROM user_levels 
            WHERE guild_id = ? 
            ORDER BY xp DESC LIMIT ?
        """, (guild_id, limit))
        return self.fetchall()
    
    def get_user_rank(self, user_id: int, guild_id: int) -> int:
        """
        Get the user's rank in the guild based on XP.
        Returns an integer representing their position (1 = highest XP)
        """
        self.execute("""
            WITH RankedUsers AS (
                SELECT 
                    user_id,
                    RANK() OVER (ORDER BY xp DESC) as rank_num
                FROM user_levels
                WHERE guild_id = ?
            )
            SELECT rank_num
            FROM RankedUsers
            WHERE user_id = ?
        """, (guild_id, user_id))
        
        result = self.fetchone()
        return result[0] if result else 0

    
    def reset_user_level(self, guild_id: int, user_id: int) -> None:
        self.execute_and_commit("DELETE FROM user_levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))

    def set_level_reward(self, guild_id: int, level: int, role_id: Optional[int]) -> None:
        if role_id:
            self.execute_and_commit("""
                INSERT OR REPLACE INTO level_rewards (guild_id, level, role_id)
                VALUES (?, ?, ?)
            """, (guild_id, level, role_id))
        else: self.execute_and_commit("DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (guild_id, level))

    def get_level_rewards(self, guild_id: int) -> List[tuple]:
        self.execute("""
            SELECT level, role_id FROM level_rewards 
            WHERE guild_id = ? ORDER BY level ASC
        """, (guild_id,)); return self.fetchall()

    def get_level_reward(self, guild_id: int, level: int) -> Optional[int]:
        self.execute("SELECT role_id FROM level_rewards WHERE guild_id = ? AND level = ?", (guild_id, level))
        result = self.fetchone()
        return result[0] if result else None

    def set_levelup_channel(self, guild_id: int, channel_id: Optional[int]) -> None:
        if channel_id:
            self.execute_and_commit("""
                INSERT OR REPLACE INTO guild_leveling_settings 
                (guild_id, levelup_channel_id) VALUES (?, ?)
            """, (guild_id, channel_id))
        else:
            self.execute_and_commit("""
                UPDATE guild_leveling_settings 
                SET levelup_channel_id = NULL 
                WHERE guild_id = ?
            """, (guild_id,))

    def get_levelup_channel(self, guild_id: int) -> Optional[int]:
        """Get levelup channel ID"""
        self.execute("SELECT levelup_channel_id FROM guild_leveling_settings", (guild_id,))
        result = self.fetchone()
        return result[0] if result else None

    def add_reminder(self, user_id: int, guild_id: int, channel_id: int, message_id: int, message: str, reminder_time: int) -> int:
        self.execute_and_commit("""
            INSERT INTO reminders (user_id, guild_id, channel_id, message_id, message, reminder_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, guild_id, channel_id, message_id, message, reminder_time))
        return self._cursor.lastrowid

    def get_user_reminders(self, user_id: int, guild_id: int) -> List[tuple]:
        self.execute("""
            SELECT id, message, reminder_time, channel_id, message_id 
            FROM reminders 
            WHERE user_id = ? AND guild_id = ?
            ORDER BY reminder_time ASC
        """, (user_id, guild_id))
        return self.fetchall()

    def clear_user_reminders(self, user_id: int, guild_id: int) -> int:
        self.execute_and_commit("DELETE FROM reminders WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        return self._cursor.rowcount

    def remove_reminder(self, reminder_id: int) -> bool:
        self.execute_and_commit("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        return self._cursor.rowcount > 0

    def get_pending_reminders(self) -> List[tuple]:
        current_time = int(time.time())
        self.execute("""
            SELECT id, user_id, guild_id, channel_id, message_id, message
            FROM reminders 
            WHERE reminder_time <= ?
            ORDER BY reminder_time ASC
        """, (current_time,))
        return self.fetchall()

    def execute_query(self, query: str, params=(), fetch_one=False, fetch_all=False):
        try:
            cursor = self.execute(query, params)
            if fetch_one:
                result = cursor.fetchone()
                return dict(zip([col[0] for col in cursor.description], result)) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in results]
            return cursor
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def get_user_balance(self, user_id: int) -> float:
        query = "SELECT balance FROM user_balances WHERE user_id = ?"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return float(result["balance"]) if result else 0.0

    def update_user_balance(self, user_id: int, amount: float, transaction_type: str = None, description: str = None, guild_id: int = None) -> None:
        """Update user's balance"""
        with self.connection as conn:
            cur = conn.cursor()
            # First ensure the user exists
            cur.execute("INSERT OR IGNORE INTO user_balances (user_id, balance) VALUES (?, 0.0)", (user_id,))
            
            # Update balance with basic fields
            cur.execute("UPDATE user_balances SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            
            # Log transaction if requested
            if transaction_type and guild_id:
                cur.execute(
                    "INSERT INTO user_transactions (user_id, guild_id, amount, type, description) VALUES (?, ?, ?, ?, ?)",
                    (user_id, guild_id, amount, transaction_type, description)
                )

    def get_user_streak(self, user_id: int) -> tuple:
        query = "SELECT streak_count, highest_streak FROM user_balances WHERE user_id = ?"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return (result["streak_count"], result["highest_streak"]) if result else (0, 0)

    def update_user_streak(self, user_id: int, increment: bool = True) -> None:
        with self.connection as conn:
            cur = conn.cursor()
            if increment:
                cur.execute("UPDATE user_balances SET streak_count = streak_count + 1, highest_streak = MAX(highest_streak, streak_count + 1) WHERE user_id = ?", (user_id,))
            else:
                cur.execute("UPDATE user_balances SET streak_count = 0 WHERE user_id = ?", (user_id,))

    def get_economy_settings(self, guild_id: int) -> dict:
        query = "SELECT * FROM economy_settings WHERE guild_id = ?"
        result = self.execute_query(query, (guild_id,), fetch_one=True)
        return result or {"guild_id": guild_id, "daily_min": 2.0, "daily_max": 5.0, "message_reward": 0.1, "streak_bonus_multiplier": 0.1, "max_streak_bonus": 7}

    def update_economy_settings(self, guild_id: int, settings: dict) -> None:
        query = "INSERT OR REPLACE INTO economy_settings (guild_id, daily_min, daily_max, message_reward, streak_bonus_multiplier, max_streak_bonus) VALUES (?, ?, ?, ?, ?, ?)"
        self.execute_and_commit(query, (guild_id, settings["daily_min"], settings["daily_max"], settings["message_reward"], settings["streak_bonus_multiplier"], settings["max_streak_bonus"]))

    def create_trade(self, seller_id: int, buyer_id: int, item_id: int, price: float) -> int:
        query = "INSERT INTO item_trades (seller_id, buyer_id, item_id, price) VALUES (?, ?, ?, ?)"
        self.execute_and_commit(query, (seller_id, buyer_id, item_id, price))
        return self._cursor.lastrowid

    def complete_trade(self, trade_id: int) -> bool:
        query = "UPDATE item_trades SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE trade_id = ? AND status = 'pending'"
        self.execute_and_commit(query, (trade_id,))
        return self._cursor.rowcount > 0

    def cancel_trade(self, trade_id: int) -> bool:
        query = "UPDATE item_trades SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP WHERE trade_id = ? AND status = 'pending'"
        self.execute_and_commit(query, (trade_id,))
        return self._cursor.rowcount > 0

    def get_user_trades(self, user_id: int, status: str = None) -> list:
        query = "SELECT t.*, si.name as item_name FROM item_trades t JOIN shop_items si ON t.item_id = si.item_id WHERE (t.seller_id = ? OR t.buyer_id = ?)"
        params = [user_id, user_id]
        if status:
            query += " AND t.status = ?"
            params.append(status)
        query += " ORDER BY t.created_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    def get_user_inventory(self, user_id: int) -> list:
        query = "SELECT inventory FROM user_balances WHERE user_id = ?"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return json.loads(result["inventory"]) if result and result["inventory"] else []

    def add_to_inventory(self, user_id: int, item_id: int) -> None:
        inventory = self.get_user_inventory(user_id)
        inventory.append(item_id)
        query = "UPDATE user_balances SET inventory = ? WHERE user_id = ?"
        self.execute_and_commit(query, (json.dumps(inventory), user_id))

    def remove_from_inventory(self, user_id: int, item_id: int) -> bool:
        inventory = self.get_user_inventory(user_id)
        if item_id in inventory:
            inventory.remove(item_id)
            query = "UPDATE user_balances SET inventory = ? WHERE user_id = ?"
            self.execute_and_commit(query, (json.dumps(inventory), user_id))
            return True
        return False

    def get_user_achievements(self, user_id: int) -> list:
        query = "SELECT * FROM user_achievements WHERE user_id = ? ORDER BY unlocked_at DESC"
        return self.execute_query(query, (user_id,), fetch_all=True)

    def update_achievement_progress(self, user_id: int, achievement_id: str, progress: int) -> None:
        query = """INSERT INTO user_achievements (user_id, achievement_id, progress) VALUES (?, ?, ?)
                  ON CONFLICT(user_id, achievement_id) DO UPDATE SET progress = ?, unlocked_at = CASE WHEN progress < ? THEN CURRENT_TIMESTAMP ELSE unlocked_at END"""
        self.execute_and_commit(query, (user_id, achievement_id, progress, progress, progress))

    def get_user_transaction_history(self, user_id: int, limit: int = 50, transaction_type: str = None) -> list:
        query = "SELECT * FROM user_transactions WHERE user_id = ?"
        params = [user_id]
        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self.execute_query(query, tuple(params), fetch_all=True)

    def get_user_stats(self, user_id: int) -> dict:
        stats = {
            "balance": self.get_user_balance(user_id),
            "mgems": self.get_user_mgems(user_id),
            "total_earned": 0,
            "total_spent": 0,
            "streak_count": 0,
            "highest_streak": 0,
            "inventory_count": 0,
            "trades_completed": 0,
            "achievements_unlocked": 0
        }
        query = """SELECT ub.total_earned, ub.total_spent, ub.streak_count, ub.highest_streak,
                  (SELECT COUNT(*) FROM json_each(ub.inventory)) as inventory_count,
                  (SELECT COUNT(*) FROM item_trades WHERE (seller_id = ? OR buyer_id = ?) AND status = 'completed') as trades_completed,
                  (SELECT COUNT(*) FROM user_achievements WHERE user_id = ? AND progress > 0) as achievements_unlocked
                  FROM user_balances ub WHERE ub.user_id = ?"""
        result = self.execute_query(query, (user_id, user_id, user_id, user_id), fetch_one=True)
        if result:
            stats.update({k: v for k, v in result.items() if v is not None})
        return stats

    def update_quiz_stats(self, user_id: int, correct: bool, category: str) -> None:
        """Update quiz statistics for a user"""
        with self.connection as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO quiz_stats (user_id, total_quizzes, correct_answers)
                VALUES (?, 1, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                total_quizzes = total_quizzes + 1,
                correct_answers = correct_answers + ?
            """, (user_id, int(correct), int(correct)))

            cur.execute("""
                INSERT INTO quiz_category_stats (user_id, category, total_attempts, correct_answers)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, category) DO UPDATE SET
                total_attempts = total_attempts + 1,
                correct_answers = correct_answers + ?
            """, (user_id, category, int(correct), int(correct)))

    def get_quiz_user_stats(self, user_id: int) -> tuple:
        """Get user's quiz statistics"""
        with self.connection as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT total_quizzes, correct_answers FROM quiz_stats WHERE user_id = ?",
                (user_id,)
            )
            overall_stats = cur.fetchone()

            cur.execute(
                "SELECT category, total_attempts, correct_answers FROM quiz_category_stats WHERE user_id = ?",
                (user_id,)
            )
            category_stats = cur.fetchall()

            return overall_stats, category_stats

    def get_quiz_leaderboard(self, limit: int = 10) -> list:
        """Get quiz leaderboard data"""
        with self.connection as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, total_quizzes, correct_answers 
                FROM quiz_stats 
                ORDER BY correct_answers DESC
                LIMIT ?
            """, (limit,))
            return cur.fetchall()

    def get_welcomer_settings(self, guild_id: int) -> dict:
        """Get welcomer settings for a guild"""
        cur = self.execute("""
            SELECT * FROM welcomer_settings WHERE guild_id = ?
        """, (guild_id,))
        settings = cur.fetchone()
        
        if not settings:
            return None
            
        # Get buttons
        cur = self.execute("""
            SELECT label, url FROM welcomer_buttons 
            WHERE guild_id = ?
        """, (guild_id,))
        buttons = cur.fetchall()
        
        result = {
            'enabled': bool(settings[1]),
            'channel_id': settings[2],
            'message': settings[3],
            'title': settings[4],
            'description': settings[5],
            'color': settings[6],
            'footer': {
                'text': settings[7],
                'icon_url': settings[8]
            },
            'author': {
                'name': settings[9],
                'url': settings[10],
                'icon_url': settings[11]
            },
            'thumbnail_url': settings[12],
            'image_url': settings[13]
        }
        
        if buttons:
            result['buttons'] = [{'label': b[0], 'url': b[1]} for b in buttons]
            
        return result

    def update_welcomer_settings(self, guild_id: int, settings: dict) -> None:
        """Update welcomer settings for a guild"""
        with self.connection as conn:
            cur = conn.cursor()
            
            # First ensure guild exists in settings
            cur.execute("""
                INSERT OR IGNORE INTO welcomer_settings (guild_id)
                VALUES (?)
            """, (guild_id,))
            
            # Update settings
            cur.execute("""
                UPDATE welcomer_settings SET
                enabled = ?,
                channel_id = ?,
                message = ?,
                title = ?,
                description = ?,
                color = ?,
                footer_text = ?,
                footer_icon_url = ?,
                author_name = ?,
                author_url = ?,
                author_icon_url = ?,
                thumbnail_url = ?,
                image_url = ?,
                updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (
                settings.get('enabled', False),
                settings.get('channel_id'),
                settings.get('message'),
                settings.get('title'),
                settings.get('description'),
                settings.get('color'),
                settings.get('footer', {}).get('text'),
                settings.get('footer', {}).get('icon_url'),
                settings.get('author', {}).get('name'),
                settings.get('author', {}).get('url'),
                settings.get('author', {}).get('icon_url'),
                settings.get('thumbnail_url'),
                settings.get('image_url'),
                guild_id
            ))
            
            # Handle buttons
            if 'buttons' in settings:
                # Clear existing buttons
                cur.execute("DELETE FROM welcomer_buttons WHERE guild_id = ?", (guild_id,))
                # Add new buttons
                for button in settings['buttons']:
                    cur.execute("""
                        INSERT INTO welcomer_buttons (guild_id, label, url)
                        VALUES (?, ?, ?)
                    """, (guild_id, button['label'], button['url']))

    def get_shop_data(self, guild_id: int) -> dict:
        """Get shop data for a guild"""
        query = "SELECT * FROM shop_data WHERE guild_id = ?"
        result = self.execute_query(query, (guild_id,), fetch_one=True)
        if result:
            result["items"] = json.loads(result["items"])
            return result
        return {"guild_id": guild_id, "channel_id": None, "message_id": None, "items": []}

    def save_shop_data(self, guild_id: int, data: dict) -> None:
        """Save shop data for a guild"""
        items = json.dumps(data["items"]) if isinstance(data["items"], list) else data["items"]
        query = """INSERT OR REPLACE INTO shop_data (guild_id, channel_id, message_id, items)
                   VALUES (?, ?, ?, ?)"""
        self.execute_and_commit(query, (guild_id, data["channel_id"], data["message_id"], items))

    def get_expired_temp_roles(self) -> list:
        """Get all expired temporary roles"""
        query = "SELECT * FROM temp_roles WHERE removal_time <= CURRENT_TIMESTAMP"
        return self.execute_query(query, fetch_all=True)

    def remove_temp_role(self, user_id: int, guild_id: int, role_id: int) -> None:
        """Remove a temporary role"""
        query = "DELETE FROM temp_roles WHERE user_id = ? AND guild_id = ? AND role_id = ?"
        self.execute_and_commit(query, (user_id, guild_id, role_id))

    def update_item_stock(self, item_id: int, amount: int) -> None:
        """Update item stock"""
        query = "UPDATE shop_items SET stock = stock + ? WHERE item_id = ?"
        self.execute_and_commit(query, (amount, item_id))

    def update_shop_revenue(self, guild_id: int, amount: float) -> None:
        """Update shop revenue for a guild"""
        query = """INSERT INTO shop_stats (guild_id, total_revenue) 
                   VALUES (?, ?) 
                   ON CONFLICT(guild_id) DO UPDATE SET total_revenue = total_revenue + ?"""
        self.execute_and_commit(query, (guild_id, amount, amount))

    def log_purchase(self, user_id: int, guild_id: int, item_id: int, order_id: str, price: float) -> None:
        """Log a purchase"""
        query = """INSERT INTO user_purchases (user_id, guild_id, item_id, order_id, price_paid)
                   VALUES (?, ?, ?, ?, ?)"""
        self.execute_and_commit(query, (user_id, guild_id, item_id, order_id, price))

    def get_top_balances(self, guild_id: int, limit: int = 10) -> list:
        """Get top balances in a guild"""
        query = """SELECT user_id, balance FROM user_balances 
                   ORDER BY balance DESC LIMIT ?"""
        return self.execute_query(query, (limit,), fetch_all=True)

    def get_user_mgems(self, user_id: int) -> int:
        """Get user's mgem balance"""
        query = "SELECT mgems FROM user_balances WHERE user_id = ?"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return result["mgems"] if result else 0

    def update_user_mgems(self, user_id: int, amount: int) -> None:
        """Update user's mgem balance"""
        query = """INSERT INTO user_balances (user_id, mgems) 
                   VALUES (?, ?) 
                   ON CONFLICT(user_id) DO UPDATE SET mgems = mgems + ?"""
        self.execute_and_commit(query, (user_id, amount, amount))

    def get_last_daily_claim(self, user_id: int) -> Optional[datetime]:
        """Get user's last daily claim time"""
        query = "SELECT last_daily_claim FROM user_balances WHERE user_id = ?"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return datetime.fromisoformat(result["last_daily_claim"]) if result and result["last_daily_claim"] else None

    def update_daily_claim(self, user_id: int) -> None:
        """Update user's last daily claim time"""
        query = """INSERT INTO user_balances (user_id, last_daily_claim) 
                   VALUES (?, CURRENT_TIMESTAMP) 
                   ON CONFLICT(user_id) DO UPDATE SET last_daily_claim = CURRENT_TIMESTAMP"""
        self.execute_and_commit(query, (user_id,))

    def get_user_purchases(self, user_id: int) -> list:
        """Get all purchases made by a user"""
        query = """
            SELECT up.*, si.name, si.code, si.type, si.role_id, si.time_limit
            FROM user_purchases up
            JOIN shop_items si ON up.item_id = si.item_id
            WHERE up.user_id = ?
            ORDER BY up.purchased_at DESC
        """
        return self.execute_query(query, (user_id,), fetch_all=True)

    def save_shop_item(self, guild_id: int, item: dict) -> int:
        """Save a shop item and return its ID"""
        query = """
            INSERT INTO shop_items (
                guild_id, code, type, name, price, stock,
                max_per_user, role_id, time_limit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            guild_id,
            item["code"],
            item["type"],
            item["name"],
            item["price"],
            item["stock"],
            item.get("max_per_user"),
            item.get("role_id"),
            item.get("time_limit")
        )
        self.execute_and_commit(query, params)
        return self._cursor.lastrowid

    def get_shop_item_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get a shop item by its code"""
        query = """
            SELECT * FROM shop_items 
            WHERE code = ?
        """
        return self.execute_query(query, (code,), fetch_one=True)

    # Waifu System Methods
    def save_waifu_card(self, user_id: int, waifu: dict, serial: str) -> None:
        """Save a waifu card to the database"""
        query = """
            INSERT INTO waifu_cards (
                serial_number, owner_id, waifu_id, name, 
                rarity, rank, level
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
        """
        params = (
            serial,
            user_id,
            waifu['id'],
            waifu['name'],
            waifu['rarity_tier'],
            waifu.get('popularity_rank')
        )
        self.execute_and_commit(query, params)

    def get_next_serial(self, rarity: str) -> str:
        """Get the next serial number for a rarity tier"""
        query = """
            INSERT INTO waifu_serials (rarity, count) 
            VALUES (?, 1)
            ON CONFLICT(rarity) DO UPDATE 
            SET count = count + 1
            RETURNING count
        """
        result = self.execute_query(query, (rarity,), fetch_one=True)
        count = result['count'] if result else 1
        return f"{rarity}-{count:06d}"

    def get_user_cards(self, user_id: int, rarity: str = None, locked: bool = None) -> List[Dict]:
        """Get all cards owned by a user with optional filters"""
        query = "SELECT * FROM waifu_cards WHERE owner_id = ?"
        params = [user_id]
        
        if rarity:
            query += " AND rarity = ?"
            params.append(rarity)
        if locked is not None:
            query += " AND locked = ?"
            params.append(locked)
            
        query += " ORDER BY obtained_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    def get_card_by_serial(self, serial: str) -> Optional[Dict]:
        """Get a card by its serial number"""
        query = "SELECT * FROM waifu_cards WHERE serial_number = ?"
        return self.execute_query(query, (serial,), fetch_one=True)

    def update_card_owner(self, serial: str, new_owner_id: int) -> bool:
        """Update the owner of a card"""
        query = """
            UPDATE waifu_cards 
            SET owner_id = ?, locked = FALSE 
            WHERE serial_number = ? AND locked = FALSE
        """
        result = self.execute_and_commit(query, (new_owner_id, serial))
        return result.rowcount > 0

    def toggle_card_lock(self, serial: str, owner_id: int, locked: bool) -> bool:
        """Lock or unlock a card"""
        query = "UPDATE waifu_cards SET locked = ? WHERE serial_number = ? AND owner_id = ?"
        result = self.execute_and_commit(query, (locked, serial, owner_id))
        return result.rowcount > 0

    def delete_card(self, serial: str, owner_id: int) -> bool:
        """Delete a card (used when selling)"""
        query = "DELETE FROM waifu_cards WHERE serial_number = ? AND owner_id = ? AND locked = FALSE"
        result = self.execute_and_commit(query, (serial, owner_id))
        return result.rowcount > 0

    def create_trade(self, offerer_id: int, offeree_id: int, offerer_card: str, 
                    offeree_card: str, guild_id: int) -> Optional[int]:
        """Create a new trade offer"""
        # First verify cards are available and not locked
        verify_query = """
            SELECT COUNT(*) as valid_cards
            FROM waifu_cards wc1
            JOIN waifu_cards wc2 ON 1=1
            WHERE wc1.serial_number = ? 
            AND wc1.owner_id = ?
            AND NOT wc1.locked
            AND wc2.serial_number = ?
            AND wc2.owner_id = ?
            AND NOT wc2.locked
        """
        result = self.execute_query(
            verify_query, 
            (offerer_card, offerer_id, offeree_card, offeree_id),
            fetch_one=True
        )
        
        if not result or result['valid_cards'] == 0:
            return None
            
        # Create the trade
        query = """
            INSERT INTO waifu_trades (
                offerer_id, offeree_id, offerer_card, 
                offeree_card, guild_id
            ) VALUES (?, ?, ?, ?, ?)
            RETURNING trade_id
        """
        result = self.execute_query(
            query, 
            (offerer_id, offeree_id, offerer_card, offeree_card, guild_id),
            fetch_one=True
        )
        return result['trade_id'] if result else None

    def get_pending_trades(self, user_id: int = None, guild_id: int = None) -> List[Dict]:
        """Get pending trades with optional filters"""
        query = "SELECT * FROM waifu_trades WHERE status = 'pending'"
        params = []
        
        if user_id:
            query += " AND (offerer_id = ? OR offeree_id = ?)"
            params.extend([user_id, user_id])
        if guild_id:
            query += " AND guild_id = ?"
            params.append(guild_id)
            
        query += " ORDER BY created_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    def update_trade_status(self, trade_id: int, status: str) -> bool:
        """Update the status of a trade"""
        query = """
            UPDATE waifu_trades 
            SET status = ?, completed_at = CASE 
                WHEN ? IN ('completed', 'cancelled', 'failed') THEN CURRENT_TIMESTAMP 
                ELSE NULL 
            END
            WHERE trade_id = ?
        """
        result = self.execute_and_commit(query, (status, status, trade_id))
        return result.rowcount > 0

    def update_card_level(self, serial: str, level: int) -> bool:
        """Update a card's level"""
        query = "UPDATE waifu_cards SET level = ? WHERE serial_number = ?"
        result = self.execute_and_commit(query, (level, serial))
        return result.rowcount > 0

    def update_card_rarity(self, serial: str, new_rarity: str) -> bool:
        """Update a card's rarity (for upgrades)"""
        query = """
            UPDATE waifu_cards 
            SET rarity = ?, level = 1 
            WHERE serial_number = ?
        """
        result = self.execute_and_commit(query, (new_rarity, serial))
        return result.rowcount > 0
    def get_waifu_leaderboard_stats(self) -> List[Dict]:
        """Get waifu leaderboard statistics efficiently using SQL"""
        query = """
            WITH card_values AS (
                SELECT 
                    wc.owner_id,
                    wc.rarity,
                    wc.rank,
                    wc.serial_number,
                    wc.name,
                    wc.level,
                    wc.locked,
                    CASE 
                        WHEN wc.rarity = 'SS' THEN 3000 - (COALESCE(wc.rank, 0) * 5)
                        WHEN wc.rarity = 'S' THEN 1000 - (COALESCE(wc.rank, 0) * 2)
                        WHEN wc.rarity = 'A' THEN 100 - (COALESCE(wc.rank, 0) * 0.1)
                        WHEN wc.rarity = 'B' THEN 30 - (COALESCE(wc.rank, 0) * 0.05)
                        WHEN wc.rarity = 'C' THEN 10 - (COALESCE(wc.rank, 0) * 0.02)
                        WHEN wc.rarity = 'D' THEN 3 - (COALESCE(wc.rank, 0) * 0.01)
                        ELSE 0 
                    END as card_value
                FROM waifu_cards wc
                WHERE NOT EXISTS (
                    SELECT 1 FROM waifu_trades wt 
                    WHERE wt.status = 'pending'
                    AND (wt.offerer_card = wc.serial_number OR wt.offeree_card = wc.serial_number)
                )
            )
            SELECT 
                cv.owner_id,
                COUNT(*) as total_cards,
                GROUP_CONCAT(cv.rarity) as cards_by_tier,
                SUM(cv.card_value) as total_value,
                MAX(CASE WHEN cv.rarity = 'SS' THEN 1 ELSE 0 END) as has_ss,
                COUNT(DISTINCT cv.rarity) as unique_tiers,
                GROUP_CONCAT(json_object(
                    'serial', cv.serial_number,
                    'name', cv.name,
                    'rarity', cv.rarity,
                    'level', cv.level,
                    'locked', cv.locked,
                    'value', cv.card_value
                )) as inventory
            FROM card_values cv
            GROUP BY cv.owner_id
            ORDER BY total_value DESC, has_ss DESC, unique_tiers DESC
            LIMIT 5
        """
        return self.execute_query(query, fetch_all=True)

    def get_card_stats(self, user_id: int = None, guild_id: int = None) -> Dict:
        """Get card statistics with optional filters"""
        query = """
            SELECT 
                COUNT(*) as total_cards,
                SUM(CASE WHEN locked THEN 1 ELSE 0 END) as locked_cards,
                AVG(level) as avg_level,
                MAX(level) as max_level,
                COUNT(DISTINCT rarity) as unique_rarities,
                GROUP_CONCAT(DISTINCT rarity) as rarities,
                MIN(obtained_at) as first_card_date,
                MAX(obtained_at) as last_card_date
            FROM waifu_cards wc
            LEFT JOIN waifu_trades wt ON wc.serial_number IN (wt.offerer_card, wt.offeree_card)
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND wc.owner_id = ?"
            params.append(user_id)
        if guild_id:
            query += " AND wt.guild_id = ?"
            params.append(guild_id)
            
        return self.execute_query(query, tuple(params), fetch_one=True)

    # Waifu Trading Methods
    def get_pending_trades_for_user(self, user_id: int, other_user_id: Optional[int] = None) -> List[dict]:
        """Get pending trades for a user"""
        query = """
            SELECT t.*, 
                   wc1.name as offerer_card_name,
                   wc2.name as offeree_card_name
            FROM waifu_trades t
            JOIN waifu_cards wc1 ON t.offerer_card = wc1.serial_number
            JOIN waifu_cards wc2 ON t.offeree_card = wc2.serial_number
            WHERE t.status = 'pending'
            AND (t.offerer_id = ? OR t.offeree_id = ?)
        """
        params = [user_id, user_id]
        
        if other_user_id:
            query += " AND (t.offerer_id = ? OR t.offeree_id = ?)"
            params.extend([other_user_id, other_user_id])
            
        query += " ORDER BY t.created_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    def process_trade(self, trade_id: int, action: str) -> bool:
        """Process a trade (accept/decline/cancel)"""
        if action not in ['completed', 'declined', 'cancelled']:
            return False
            
        with self.connection as conn:
            cur = conn.cursor()
            try:
                # Update trade status
                cur.execute("""
                    UPDATE waifu_trades 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE trade_id = ? AND status = 'pending'
                    RETURNING offerer_id, offeree_id, offerer_card, offeree_card
                """, (action, trade_id))
                
                trade = cur.fetchone()
                if not trade:
                    return False
                    
                if action == 'completed':
                    # Swap card ownership
                    cur.executemany("""
                        UPDATE waifu_cards
                        SET owner_id = ?
                        WHERE serial_number = ?
                    """, [
                        (trade[1], trade[2]),  # Give offerer's card to offeree
                        (trade[0], trade[3])   # Give offeree's card to offerer
                    ])
                    
                return True
                
            except sqlite3.Error:
                return False

    def create_trade_offer(self, offerer_id: int, offeree_id: int, offerer_card: str, 
                          offeree_card: str, guild_id: int) -> Optional[int]:
        """Create a new trade offer"""
        # Verify cards are available and not locked
        verify_query = """
            SELECT COUNT(*) as count
            FROM waifu_cards wc1, waifu_cards wc2
            WHERE wc1.serial_number = ? AND wc1.owner_id = ? AND NOT wc1.locked
            AND wc2.serial_number = ? AND wc2.owner_id = ? AND NOT wc2.locked
        """
        result = self.execute_query(verify_query, 
            (offerer_card, offerer_id, offeree_card, offeree_id), 
            fetch_one=True
        )
        
        if not result or result['count'] == 0:
            return None
            
        self.execute("""
            INSERT INTO waifu_trades (offerer_id, offeree_id, offerer_card, offeree_card, guild_id, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (offerer_id, offeree_id, offerer_card, offeree_card, guild_id))
        
        self.commit()
        return self._cursor.lastrowid

    def get_trade_by_id(self, trade_id: int) -> Optional[dict]:
        """Get trade by ID"""
        return self.execute_query("""
            SELECT * FROM waifu_trades WHERE trade_id = ?
        """, (trade_id,), fetch_one=True)

    def get_card_value_stats(self) -> List[dict]:
        """Get card value statistics for leaderboard"""
        return self.execute_query("""
            SELECT 
                owner_id,
                COUNT(*) as total_cards,
                GROUP_CONCAT(rarity) as cards_by_tier,
                SUM(
                    CASE 
                        WHEN rarity = 'SS' THEN 3000 - (rank * 5)
                        WHEN rarity = 'S' THEN 1000 - (rank * 2)
                        WHEN rarity = 'A' THEN 100 - (rank * 0.1)
                        WHEN rarity = 'B' THEN 30 - (rank * 0.05)
                        WHEN rarity = 'C' THEN 10 - (rank * 0.02)
                        WHEN rarity = 'D' THEN 3 - (rank * 0.01)
                        ELSE 0 
                    END
                ) as total_value
            FROM waifu_cards
            GROUP BY owner_id
            ORDER BY total_value DESC
            LIMIT 5
        """, fetch_all=True)

    def add_temp_channel(self, channel_id: int, guild_id: int, owner_id: int, 
                        control_message_id: int, text_channel_id: int, name: str) -> None:
        """Add temporary channel to database"""
        self.execute_and_commit("""
            INSERT INTO temp_channels 
            (channel_id, guild_id, owner_id, control_message_id, text_channel_id, name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (channel_id, guild_id, owner_id, control_message_id, text_channel_id, name))
        
        
    def remove_temp_channel(self, channel_id: int) -> None:
        self.execute_and_commit(
            "DELETE FROM temp_channels WHERE channel_id = ?",
            (channel_id,)
        )
    
    def get_temp_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        self.execute("""
            SELECT channel_id, owner_id, control_message_id, text_channel_id 
            FROM temp_channels 
            WHERE guild_id = ?
        """, (guild_id,))
        return [
            {
                "channel_id": row[0],
                "owner_id": row[1],
                "control_message_id": row[2],
                "text_channel_id": row[3]
            }
            for row in self.fetchall()
        ]


    def get_template_channel(self, guild_id: int) -> Optional[int]:
        """Get template channel ID for a guild"""
        self.execute("""
            SELECT channel_id FROM tempvc_config 
            WHERE guild_id = ? AND enabled = 1
        """, (guild_id,))
        result = self.fetchone()
        return result[0] if result else None

    def set_template_channel(self, guild_id: int, channel_id: int) -> None:
        """Set template channel for a guild"""
        self.execute("""
            INSERT OR REPLACE INTO tempvc_config 
            (guild_id, channel_id, enabled) 
            VALUES (?, ?, 1)
        """, (guild_id, channel_id))
        self.commit()

    def toggle_tempvc(self, guild_id: int, enabled: bool) -> None:
        self.execute_and_commit(
            "UPDATE tempvc_config SET enabled = ? WHERE guild_id = ?",
            (enabled, guild_id)
        )

    def is_tempvc_enabled(self, guild_id: int) -> bool:
        self.execute(
            "SELECT enabled FROM tempvc_config WHERE guild_id = ?",
            (guild_id,)
        )
        result = self.fetchone()
        return bool(result[0]) if result else False

    # Moderation Methods
    def set_modlog(self, guild_id: int, channel_id: int) -> None:
        """Set moderation log channel for a guild"""
        self.execute_and_commit("""
            INSERT INTO guild_config (guild_id, modlog_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) 
            DO UPDATE SET modlog_channel_id = ?, updated_at = CURRENT_TIMESTAMP
        """, (guild_id, channel_id, channel_id))

    def get_modlog(self, guild_id: int) -> Optional[int]:
        """Get moderation log channel ID for a guild"""
        result = self.execute_query(
            "SELECT modlog_channel_id FROM guild_config WHERE guild_id = ?",
            (guild_id,),
            fetch_one=True
        )
        return result["modlog_channel_id"] if result else None

    def add_mod_case(
        self,
        guild_id: int,
        moderator_id: int,
        target_id: int,
        action: str,
        reason: Optional[str] = None,
        duration: Optional[int] = None
    ) -> int:
        """Add a moderation case and return its ID"""
        result = self.execute_query("""
            INSERT INTO mod_cases (
                guild_id, moderator_id, target_id,
                action, reason, duration
            ) VALUES (?, ?, ?, ?, ?, ?)
            RETURNING case_id
        """, (guild_id, moderator_id, target_id, action, reason, duration),
        fetch_one=True)
        
        return result["case_id"]

    def get_mod_cases(
        self,
        guild_id: int,
        target_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get moderation cases for a guild/user"""
        query = "SELECT * FROM mod_cases WHERE guild_id = ?"
        params = [guild_id]
        
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        return self.execute_query(query, tuple(params), fetch_all=True)
