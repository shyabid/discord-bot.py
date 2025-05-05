import discord
from discord import app_commands
from typing import Optional, Dict, Any, Union, DefaultDict, Literal, List
from utils import create_autocomplete_from_list as autocomplete
from utils import PaginationView
import sqlite3 
import csv
import shutil
import io
import asyncio
import random
import string
import psutil
import subprocess
from discord.ext import commands
from datetime import timedelta
import platform
import datetime
import aiohttp
import random
from bot import Morgana
from discord.ext import tasks
import time
import re
import os
import json
import pytz


class RawDatabaseView(discord.ui.View):
    """A paginated view for displaying detailed/raw database records."""
    def __init__(self, data, author_id, timeout=180):
        super().__init__(timeout=timeout)
        self.data = data
        self.author_id = author_id
        self.page = 0
        self.max_pages = max(1, len(data))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use this pagination.", ephemeral=True)
            return False
        return True
        
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await interaction.response.edit_message(embed=self.get_embed())
        
    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.max_pages - 1, self.page + 1)
        await interaction.response.edit_message(embed=self.get_embed())
        
    def get_embed(self):
        if not self.data:
            return discord.Embed(
                title="Database Records", 
                description="No data found.",
                color=discord.Color.red()
            )
        
        record = self.data[self.page]
        
        embed = discord.Embed(
            title=f"Record {self.page + 1}/{self.max_pages}",
            color=discord.Color.blue()
        )
        
        # Format record fields
        for key, value in record.items():
            # Format the value for display
            if isinstance(value, (dict, list)):
                value = f"```json\n{json.dumps(value, indent=2)}\n```"
            elif value is None:
                value = "NULL"
                
            embed.add_field(name=key, value=str(value)[:1024], inline=False)
            
        return embed

class DatabaseView(discord.ui.View):
    """A paginated view for displaying simplified database records in a table format."""
    def __init__(self, data, headers, author_id, timeout=180):
        super().__init__(timeout=timeout)
        self.data = data
        self.headers = headers
        self.author_id = author_id
        self.page = 0
        self.per_page = 10
        self.max_pages = max(1, (len(data) + self.per_page - 1) // self.per_page)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use this pagination.", ephemeral=True)
            return False
        return True
        
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await interaction.response.edit_message(embed=self.get_embed())
        
    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.max_pages - 1, self.page + 1)
        await interaction.response.edit_message(embed=self.get_embed())
        
    def get_embed(self):
        start = self.page * self.per_page
        end = min(start + self.per_page, len(self.data))
        
        embed = discord.Embed(
            title="Database Records", 
            description=f"Page {self.page + 1}/{self.max_pages}",
            color=discord.Color.dark_grey()
        )
        
        if not self.data:
            embed.description += "\nNo data found."
            return embed
            
        rows = []
        for i, row in enumerate(self.data[start:end], start=start+1):
            row_str = " | ".join([f"{val}" for val in row])
            rows.append(f"{i}. {row_str}")
            
        embed.add_field(name="Headers", value=" | ".join(self.headers), inline=False)
        embed.add_field(name="Data", value="```\n" + "\n".join(rows) + "\n```", inline=False)
        return embed

class DeleteConfirmation(discord.ui.View):
    """Confirmation view for data deletion."""
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.confirmed = False
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
            return False
        return True
        
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
start_time: float = time.time()


with open('config.json') as f:
    config = json.load(f)

class Botto(commands.Cog):
    """A core module providing essential bot management and database utilities. Features include status management, bot statistics, performance monitoring, and comprehensive database operations for server administrators. Get detailed insights about the bot's operation and manage server-specific data with ease."""
    
    def __init__(self, bot: Morgana):
        self.bot = bot
        self._process = psutil.Process()
        self.bot.start_time = start_time
        self.status_task.start()
        self.db_path = "database.db"
        self.table_cache = {}
        self.load_database_schema()
        
    @commands.command()
    async def sync(self, ctx):
        sync1 = await self.bot.tree.clear_commands(guild=ctx.guild)
        sync2 = await self.bot.tree.sync(guild=ctx.guild)
        
        
        await ctx.reply(str(sync1) + "\n" + str(sync2))
        
    @tasks.loop(seconds=10)
    async def status_task(self):
        """Task to rotate bot status messages."""
        try:
            activity_type, message = random.choice(self.bot.status_messages)
            formatted_message = message.format(
                guild_count=len(self.bot.guilds),
                member_count=sum(g.member_count for g in self.bot.guilds),
                channel_count=sum(len(g.channels) for g in self.bot.guilds),
                user_count=len([member for guild in self.bot.guilds for member in guild.members]),
                role_count=sum(len(g.roles) for g in self.bot.guilds),
                emoji_count=sum(len(g.emojis) for g in self.bot.guilds),
                command_count=len(list(self.bot.walk_commands()))
            )
            
            if activity_type == "custom":
                await self.bot.change_presence(activity=discord.CustomActivity(name=formatted_message))
                return

            activity_types = {
                "playing": discord.ActivityType.playing,
                "watching": discord.ActivityType.watching,
                "listening": discord.ActivityType.listening,
                "streaming": discord.ActivityType.streaming
            }

            activity = discord.Activity(
                type=activity_types[activity_type],
                name=formatted_message
            )
            
        
            await self.bot.change_presence(activity=activity)

        except Exception as e:
            print(f"Error in status_`task: {e}")

    @status_task.before_loop
    async def before_status_task(self):
        """Wait for the bot to be ready before starting the task."""
        await self.bot.wait_until_ready()
    @status_task.before_loop
    async def before_status_task(self):
        """Wait for the bot to be ready before starting the task."""
        await self.bot.wait_until_ready()
        
    async def _get_system_stats(self) -> Dict[str, Any]:
        stats = {
            'ram_usage': self._process.memory_info().rss / (1024 * 1024),
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'disk_usage': psutil.disk_usage('/'),
            'total_members': sum(g.member_count for g in self.bot.guilds),
            'total_channels': sum(len(g.channels) for g in self.bot.guilds),
            'total_roles': sum(len(g.roles) for g in self.bot.guilds),
            'total_emojis': sum(len(g.emojis) for g in self.bot.guilds),
            'voice_clients': len(self.bot.voice_clients),
            'uptime': time.time() - self.bot.start_time
        }
        return stats

    @commands.hybrid_group(
        name="bot",
        description="Bot-related commands",
        invoke_without_command=True
    )
    async def grbt(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    @commands.command(name="status")
    async def status_command(self, ctx: commands.Context, status: str, activity: str, *, text: str):
        await self.status(ctx, status, activity, text)
    
    @grbt.command(
        name="status",
        description="Change the status of the bot"
    )
    @app_commands.describe(
        status="The status to set (online, idle, dnd, invisible)"
    )
    async def status(self, ctx: commands.Context, status: Literal['online', 'idle', 'dnd', 'invisible'], activity: str, *, text: str):
        await ctx.defer()
        
        if not ctx.author.id == config["owner"]:
            raise commands.MissingPermissions(["bot_owner"])
        
        status_mapping = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.invisible
        }
        
        discord_status = status_mapping.get(status.lower())
        
        await ctx.reply(f"Bot status changed to {status} with {activity} '{text}' activity.")
    
    @commands.command(name="suggest")
    async def suggestion_command(self, ctx: commands.Context, suggestion: str):
        await self.suggest(ctx, suggestion)

    @grbt.command(
        name="suggest",
        description="Suggest new features or report bugs to the dev"
    )
    @app_commands.describe(
        suggestion="Your suggestion or bug report"
    )
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        await ctx.defer()
        
        try:
            bot_owner = await self.bot.fetch_user(config["owner"])
            
            embed = discord.Embed(
                title="New Suggestion/Bug Report",
                description=suggestion,
                color=discord.Color.green()
            )
            embed.set_author(
                name=str(ctx.author),
                icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None
            )
            embed.add_field(name="User ID", value=ctx.author.id, inline=True)
            embed.add_field(name="Guild", value=f"{ctx.guild.name} (ID: {ctx.guild.id})", inline=True)
            embed.add_field(name="Channel", value=f"{ctx.channel.name} (ID: {ctx.channel.id})", inline=True)
            embed.add_field(name="Timestamp", value=discord.utils.format_dt(ctx.message.created_at, style='F'), inline=False)
            
            await bot_owner.send(embed=embed)
            
            thank_you = "Thank you for your suggestion! The developers have been notified."
            await ctx.reply(thank_you)
            
        except Exception as e:
            await self._handle_error(ctx, e, "sending suggestion")

    @commands.command(name="stats", aliases=["statistics", "about"])
    async def stats_command(self, ctx: commands.Context):
        await self.stats(ctx)

    @grbt.command(
        name="stats",
        description="Displays comprehensive bot statistics, performance metrics, and system information"
    )
    async def stats(self, ctx: commands.Context):
        await ctx.defer()
    
        start_time = time.perf_counter()
        sys_stats = await self._get_system_stats()
        
        uptime = sys_stats['uptime']
        uptime_str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        
        all_commands = list(self.bot.walk_commands())
        parent_commands = len([cmd for cmd in all_commands if not cmd.parent])
        
        top_commands = self.bot.db.get_top_commands(5)
        top_commands_str = ", ".join(f"`{cmd} ({count})`" for cmd, count in top_commands)
        
        commit_description = await self._fetch_commits()
        
        embed = discord.Embed(
            title=f"{self.bot.user.name} Statistics",
            description=(
                f"**Latest Changes**\n{commit_description}\n\n"
                f"**Uptime:** {uptime_str}\n"
                f"**Latency:** {round(self.bot.latency * 1000, 2)}ms\n"
                f"**Commands:** {parent_commands}"
            ),
            color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="Resource Usage",
            value=f"OS: {platform.system()} {platform.release()}\n"
                f"RAM: {sys_stats['ram_usage']:.2f} MB\n"
                f"CPU: {sys_stats['cpu_usage']:.2f}%\n"
                f"Disk: {sys_stats['disk_usage'].percent}%",
            inline=True
        )

        embed.add_field(
            name="Maintaining",
            value=f"{len(self.bot.guilds):,} Servers\n"
                f"{sys_stats['total_members']:,} Users\n"
                f"{sys_stats['total_channels']:,} Channels\n"
                f"{sys_stats['total_roles']:,} Roles",
            inline=True
        )

        embed.add_field(
            name="Versions",
            value=f"Python: {platform.python_version()}\n"
                f"Discord.py: {discord.__version__}",
            inline=True
        )

        embed.add_field(
            name="Top Used Commands",
            value=f"\n{top_commands_str}",
            inline=False
        )

        end_time = time.perf_counter()
        embed.set_footer(text=f"Stats generated in {(end_time - start_time)*1000:.2f} ms")

        await ctx.reply(embed=embed)
            
    async def _fetch_commits(self) -> str:
        """Fetch the latest commits from local git repository."""
        try:
            # Check if running from a git repository
            git_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.git')
            if not os.path.exists(git_dir):
                return "Not running from a git repository"
                
            # Use git commands to get commit history
            git_cmd = ["git", "log", "-3", "--pretty=format:%h§%s§%an§%ar"]
            
            process = await asyncio.create_subprocess_exec(
                *git_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return "Failed to fetch commit data"
                
            commit_list = []
            commits = stdout.decode().split('\n')
            
            for commit in commits:
                if not commit:
                    continue
                sha, message, author, date = commit.split('§')
                commit_list.append(f"`{sha}` - {author} - {message} ({date})")
                
            return "\n".join(commit_list)
                
        except Exception as e:
            return f"Failed to fetch commit data: {str(e)}"
    
    
    
    @commands.command(name="changepfp")
    async def changepfp(self, ctx: commands.Context, url: str):
        
        if not ctx.author.id == config["owner"]:
            raise commands.MissingPermissions(["bot_owner"])

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    avatar_bytes = await response.read()
                    await self.bot.user.edit(avatar=avatar_bytes)


    def load_database_schema(self):
        """Load database schema for autocomplete functionality."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [column[1] for column in cursor.fetchall()]
                self.table_cache[table_name] = columns
                
            conn.close()
        except Exception as e:
            print(f"Error loading database schema: {e}")
    
    async def table_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for table names in the database."""
        tables = list(self.table_cache.keys())
        return [
            app_commands.Choice(name=table, value=table)
            for table in tables
            if current.lower() in table.lower()
        ][:25]  # Discord limits to 25 choices
    
    async def field_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for field names based on the selected table."""
        table = interaction.namespace.table
        if not table or table not in self.table_cache:
            return []
            
        fields = self.table_cache[table]
        return [
            app_commands.Choice(name=field, value=field)
            for field in fields
            if current.lower() in field.lower()
        ][:25]
    
    async def execute_query(self, query: str, params: list = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as dictionaries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                results = cursor.fetchall()
                conn.close()
                return [dict(row) for row in results]
            else:
                conn.commit()
                rows_affected = cursor.rowcount
                conn.close()
                return {"rows_affected": rows_affected}
        except Exception as e:
            conn.close()
            raise e

    @app_commands.command(name="tables", description="List all tables in the database")
    async def list_tables(self, interaction: discord.Interaction):
        """Show all available tables in the database."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            tables = list(self.table_cache.keys())
            
            if not tables:
                await interaction.followup.send("No tables found in the database.", ephemeral=True)
                return
                
            # Create embeds with table information
            embeds = []
            tables_per_page = 10
            
            for i in range(0, len(tables), tables_per_page):
                page_tables = tables[i:i+tables_per_page]
                embed = discord.Embed(
                    title="Database Tables",
                    description="All the types of information that the bot stores in its database.",
                    color=discord.Color.blue()
                )
                
                for table in page_tables:
                    fields = ", ".join(f"`{table}`" for table in self.table_cache[table])
                    embed.add_field(name=table, value=fields, inline=False)
                    
                embeds.append(embed)
            
            if len(embeds) > 1:
                paginator = PaginationView(embeds, interaction.user)
                await interaction.followup.send(embed=embeds[0], view=paginator, ephemeral=True)
                paginator.message = await interaction.original_response()
            else:
                await interaction.followup.send(embed=embeds[0], ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"Error retrieving tables: {str(e)}", ephemeral=True)
    
    db_group = app_commands.Group(
        name="db", 
        description="Database management commands", 
        default_permissions=discord.Permissions(administrator=True)
    )
    
    @db_group.command(name="view", description="View data from a specific table")
    @app_commands.autocomplete(table=table_autocomplete)
    @app_commands.describe(
        table="Table to retrieve data from",
        filter_field="Field to filter on (optional)",
        filter_value="Value to filter by (optional)",
        view_type="Simple tabular view or detailed record view",
        limit="Maximum number of records to retrieve",
        query="Custom SQL WHERE clause (advanced, overrides filter options)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view_data(
        self, 
        interaction: discord.Interaction, 
        table: str,
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None,
        view_type: Literal["Simple", "Detailed", "Raw"] = "Simple",
        limit: Optional[int] = 100,
        query: Optional[str] = None
    ):
        """View data from a database table with optional filtering and advanced query options."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if table has guild_id column for per-guild isolation
            has_guild_id = 'guild_id' in self.table_cache.get(table, [])
            
            # Build query
            if query:
                # Custom SQL query - developer mode
                base_query = f"SELECT * FROM {table} WHERE {query}"
                params = []
            else:
                # Standard filter query
                base_query = f"SELECT * FROM {table}"
                params = []
                
                where_clauses = []
                
                # Add guild isolation if applicable
                if has_guild_id:
                    where_clauses.append("guild_id = ?")
                    params.append(interaction.guild.id)
                    
                # Add user filter if provided
                if filter_field and filter_value is not None:
                    where_clauses.append(f"{filter_field} = ?")
                    params.append(filter_value)
                
                # Combine where clauses if any
                if where_clauses:
                    base_query += f" WHERE {' AND '.join(where_clauses)}"
            
            # Add limit
            base_query += f" LIMIT {limit}"
            
            # Get total count without limit
            count_query = base_query.replace("SELECT *", "SELECT COUNT(*) as count").split("LIMIT")[0]
            count_result = await self.execute_query(count_query, params)
            total_count = count_result[0]["count"] if count_result else 0
            
            # Execute main query
            results = await self.execute_query(base_query, params)
            
            if not results:
                await interaction.followup.send(f"No data found in table '{table}'", ephemeral=True)
                return
            
            if view_type == "Raw":
                # Raw JSON output for developers
                json_data = json.dumps(results, indent=2, default=str)
                
                if len(json_data) > 1900:
                    # If too large, send as file
                    file = discord.File(
                        fp=io.StringIO(json_data),
                        filename=f"{table}_data.json"
                    )
                    await interaction.followup.send(
                        f"Data from '{table}' ({len(results)} records):",
                        file=file,
                        ephemeral=True
                    )
                else:
                    # Send as code block
                    await interaction.followup.send(
                        f"Data from '{table}' ({len(results)} records):\n```json\n{json_data}\n```", 
                        ephemeral=True
                    )
            elif view_type == "Simple":
                # Extract headers and data for simplified view
                headers = list(results[0].keys())
                data_rows = [list(row.values()) for row in results]
                
                view = DatabaseView(data_rows, headers, interaction.user.id)
                # Developer enhancements
                query_info = f"Query: `{base_query.replace('?', '%s') % tuple(str(p) for p in params)}`"
                embed = view.get_embed()
                embed.add_field(name="Query Information", value=query_info, inline=False)
                embed.add_field(name="Total Records", value=f"{total_count} (showing {len(results)})", inline=False)
                
                await interaction.followup.send(
                    embed=embed, 
                    view=view, 
                    ephemeral=True
                )
            else:
                # Detailed view showing complete record information
                view = RawDatabaseView(results, interaction.user.id)
                embed = view.get_embed()
                query_info = f"Query: `{base_query.replace('?', '%s') % tuple(str(p) for p in params)}`"
                embed.add_field(name="Query Information", value=query_info, inline=False)
                
                await interaction.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(f"Error retrieving data: {str(e)}", ephemeral=True)
    
    @db_group.command(name="export", description="Export table data to a file")
    @app_commands.autocomplete(table=table_autocomplete)
    @app_commands.describe(
        table="Table to export (leave empty to export all tables)",
        format="Export file format",
        filter_field="Field to filter on (optional)",
        filter_value="Value to filter by (optional)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def export_data(
        self,
        interaction: discord.Interaction,
        table: Optional[str] = None,
        format: Literal["csv", "json", "db"] = "csv",
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None
    ):
        """Export database data to a file in various formats."""
        await interaction.response.defer(ephemeral=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if not table:
                # Export all tables
                if format == "db":
                    # Create a copy of the entire database
                    temp_db_path = f"temp_export_{interaction.guild.id}_{timestamp}.db"
                    
                    # Create a new database connection
                    conn = sqlite3.connect(temp_db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Attach the source database
                    cursor.execute(f"ATTACH DATABASE ? AS source", [self.db_path])
                    
                    # Copy each table's schema and data that belongs to this guild
                    for table_name in self.table_cache.keys():
                        # Check if the table has guild_id column
                        has_guild_id = 'guild_id' in self.table_cache.get(table_name, [])
                        
                        # Copy schema
                        cursor.execute(f"CREATE TABLE IF NOT EXISTS main.{table_name} AS SELECT * FROM source.{table_name} WHERE 0=1")
                        
                        # Copy data with guild restrictions if applicable
                        if has_guild_id:
                            cursor.execute(f"INSERT INTO main.{table_name} SELECT * FROM source.{table_name} WHERE guild_id = ?", 
                                        [interaction.guild.id])
                        else:
                            # For tables without guild_id, just copy structure - no data for security
                            pass
                    
                    # Detach and close
                    cursor.execute("DETACH DATABASE source")
                    conn.commit()
                    conn.close()
                    
                    # Send file
                    with open(temp_db_path, 'rb') as f:
                        file = discord.File(f, filename=f"guild_{interaction.guild.id}_export_{timestamp}.db")
                        await interaction.followup.send("Database export complete. Contains only data associated with this guild.", file=file, ephemeral=True)
                        
                    # Clean up temp file
                    os.remove(temp_db_path)
                    return
                
                # For JSON/CSV - export all tables to a zip file with one file per table
                import zipfile
                zip_filename = f"guild_{interaction.guild.id}_export_{timestamp}.zip"
                
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    for table_name in self.table_cache.keys():
                        # Check if table has guild_id for per-guild isolation
                        has_guild_id = 'guild_id' in self.table_cache.get(table_name, [])
                        
                        # Skip tables without guild_id for security
                        if not has_guild_id:
                            continue
                            
                        # Get data for this guild
                        query = f"SELECT * FROM {table_name} WHERE guild_id = ?"
                        results = await self.execute_query(query, [interaction.guild.id])
                        
                        if not results:
                            continue  # Skip empty tables
                        
                        # Create in-memory file
                        if format == "json":
                            # Export as JSON
                            json_data = json.dumps(results, indent=2, default=str)
                            zipf.writestr(f"{table_name}.json", json_data)
                        else:
                            # Export as CSV
                            if not results:
                                continue
                                
                            csv_file = io.StringIO()
                            writer = csv.DictWriter(csv_file, fieldnames=results[0].keys())
                            writer.writeheader()
                            writer.writerows(results)
                            zipf.writestr(f"{table_name}.csv", csv_file.getvalue())
                
                # Send zip file
                with open(zip_filename, 'rb') as f:
                    file = discord.File(f, filename=zip_filename)
                    await interaction.followup.send(f"Exported all tables with guild data to {format.upper()} format.", file=file, ephemeral=True)
                    
                # Clean up
                os.remove(zip_filename)
            else:
                # Export single table
                # Check if table has guild_id for per-guild isolation
                has_guild_id = 'guild_id' in self.table_cache.get(table, [])
                
                # Build query with appropriate filters
                query = f"SELECT * FROM {table}"
                params = []
                
                where_clauses = []
                
                # Add guild isolation if applicable
                if has_guild_id:
                    where_clauses.append("guild_id = ?")
                    params.append(interaction.guild.id)
                    
                # Add user filter if provided
                if filter_field and filter_value is not None:
                    where_clauses.append(f"{filter_field} = ?")
                    params.append(filter_value)
                
                # Combine where clauses if any
                if where_clauses:
                    query += f" WHERE {' AND '.join(where_clauses)}"
                    
                # Execute query
                results = await self.execute_query(query, params)
                
                if not results:
                    await interaction.followup.send(f"No data found in table '{table}' with the specified filters.", ephemeral=True)
                    return
                
                # Create appropriate file format
                if format == "json":
                    # JSON format
                    json_data = json.dumps(results, indent=2, default=str)
                    filename = f"{table}_{timestamp}.json"
                    file = discord.File(fp=io.StringIO(json_data), filename=filename)
                    await interaction.followup.send(
                        f"Exported {len(results)} records from '{table}' to JSON.", 
                        file=file,
                        ephemeral=True
                    )
                elif format == "csv":
                    # CSV format
                    csv_data = io.StringIO()
                    writer = csv.DictWriter(csv_data, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)
                    
                    filename = f"{table}_{timestamp}.csv"
                    file = discord.File(fp=io.StringIO(csv_data.getvalue()), filename=filename)
                    await interaction.followup.send(
                        f"Exported {len(results)} records from '{table}' to CSV.", 
                        file=file,
                        ephemeral=True
                    )
                else:
                    # DB format (SQLite)
                    temp_db_path = f"temp_export_{interaction.guild.id}_{timestamp}.db"
                    
                    # Create a new database with just this table
                    conn = sqlite3.connect(temp_db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Get table schema
                    source_conn = sqlite3.connect(self.db_path)
                    source_cursor = source_conn.cursor()
                    source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE name = ?", [table])
                    table_schema = source_cursor.fetchone()[0]
                    source_conn.close()
                    
                    # Create table
                    cursor.execute(table_schema)
                    
                    # Convert results to tuples for insertion
                    columns = list(results[0].keys())
                    values = []
                    for row in results:
                        values.append(tuple(row[col] for col in columns))
                    
                    # Insert data
                    placeholders = ", ".join(["?"] * len(columns))
                    cursor.executemany(
                        f"INSERT INTO {table} VALUES ({placeholders})",
                        values
                    )
                    
                    conn.commit()
                    conn.close()
                    
                    # Send file
                    with open(temp_db_path, 'rb') as f:
                        file = discord.File(f, filename=f"{table}_{timestamp}.db")
                        await interaction.followup.send(
                            f"Exported {len(results)} records from '{table}' to SQLite database.", 
                            file=file,
                            ephemeral=True
                        )
                        
                    # Clean up
                    os.remove(temp_db_path)
                    
        except Exception as e:
            await interaction.followup.send(f"Error exporting data: {str(e)}", ephemeral=True)
            
    @db_group.command(name="import", description="Import data from a file into a table")
    @app_commands.autocomplete(table=table_autocomplete)
    @app_commands.describe(
        table="Table to import data into",
        file="File containing data to import (CSV or JSON)",
        mode="How to handle existing data",
        validate_types="Validate data types against schema"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def import_data(
        self,
        interaction: discord.Interaction,
        table: str,
        file: discord.Attachment,
        mode: Literal["append", "replace"] = "append",
        validate_types: bool = True
    ):
        """Import data from a file into a database table."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if table exists
            if table not in self.table_cache:
                await interaction.followup.send(f"Table '{table}' does not exist.", ephemeral=True)
                return
                
            # Check if table has guild_id for per-guild isolation
            has_guild_id = 'guild_id' in self.table_cache.get(table, [])
            if not has_guild_id:
                await interaction.followup.send(
                    f"Cannot import into table '{table}' as it does not support guild isolation (missing guild_id column).", 
                    ephemeral=True
                )
                return
                
            # Check file extension
            filename = file.filename.lower()
            if filename.endswith('.csv'):
                file_type = 'csv'
            elif filename.endswith('.json'):
                file_type = 'json'
            else:
                await interaction.followup.send(
                    "Invalid file format. Please upload a CSV or JSON file.", 
                    ephemeral=True
                )
                return
                
            # Download file
            file_content = await file.read()
            
            # Parse file
            records = []
            if file_type == 'csv':
                content_str = file_content.decode('utf-8')
                csv_reader = csv.DictReader(content_str.splitlines())
                records = list(csv_reader)
                
                # Convert string values to appropriate types
                for record in records:
                    for key, value in record.items():
                        if value.lower() == 'null' or value == '':
                            record[key] = None
                        elif value.lower() == 'true':
                            record[key] = 1
                        elif value.lower() == 'false':
                            record[key] = 0
                        elif value.isdigit():
                            record[key] = int(value)
                        elif re.match(r'^-?\d+(\.\d+)?$', value):
                            record[key] = float(value)
            else:
                content_str = file_content.decode('utf-8')
                records = json.loads(content_str)
                
            # Validate required fields
            if not records:
                await interaction.followup.send("No records found in the file.", ephemeral=True)
                return
                
            # Get schema information for validation
            schema_info = {}
            if validate_types:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table})")
                for col in cursor.fetchall():
                    name, type_info = col[1], col[2]
                    schema_info[name] = type_info
                conn.close()
                
            # Force guild_id for all records
            for record in records:
                record['guild_id'] = interaction.guild.id
                
            # Validate types if requested
            if validate_types:
                invalid_records = []
                for i, record in enumerate(records):
                    for field, value in record.items():
                        if field not in schema_info:
                            invalid_records.append((i, f"Field '{field}' does not exist in the table schema"))
                            continue
                            
                        field_type = schema_info[field].upper()
                        
                        # Skip NULL values
                        if value is None:
                            continue
                            
                        # Validate based on SQLite type affinities
                        if 'INTEGER' in field_type:
                            if not isinstance(value, int) and not (isinstance(value, str) and value.isdigit()):
                                invalid_records.append((i, f"Field '{field}' should be INTEGER, got {type(value).__name__}"))
                        elif 'REAL' in field_type or 'FLOAT' in field_type:
                            if not isinstance(value, (int, float)) and not (isinstance(value, str) and re.match(r'^-?\d+(\.\d+)?$', value)):
                                invalid_records.append((i, f"Field '{field}' should be REAL, got {type(value).__name__}"))
                        elif 'BLOB' in field_type:
                            # BLOB can be any data
                            pass
                        elif 'TEXT' in field_type:
                            # Ensure it's a string
                            if not isinstance(value, str):
                                record[field] = str(value)
                
                if invalid_records:
                    error_msg = "Validation failed with the following errors:\n"
                    for i, err in invalid_records[:10]:
                        error_msg += f"- Record {i+1}: {err}\n"
                    
                    if len(invalid_records) > 10:
                        error_msg += f"... and {len(invalid_records) - 10} more errors."
                        
                    await interaction.followup.send(error_msg, ephemeral=True)
                    return
            
            # If replace mode, clear existing data for this guild
            if mode == "replace":
                delete_query = f"DELETE FROM {table} WHERE guild_id = ?"
                await self.execute_query(delete_query, [interaction.guild.id])
                
            # Insert records
            columns = list(records[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            insert_query = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                for record in records:
                    values = [record.get(col) for col in columns]
                    cursor.execute(insert_query, values)
                    
                conn.commit()
                await interaction.followup.send(
                    f"Successfully imported {len(records)} records into '{table}'.", 
                    ephemeral=True
                )
            except sqlite3.Error as e:
                conn.rollback()
                await interaction.followup.send(
                    f"Database error during import: {str(e)}", 
                    ephemeral=True
                )
            finally:
                conn.close()
                
        except Exception as e:
            await interaction.followup.send(f"Error importing data: {str(e)}", ephemeral=True)
    
    class DropTableConfirmation(discord.ui.View):
        def __init__(self, author_id):
            super().__init__(timeout=60)
            self.author_id = author_id
            self.confirmed = False
            
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
                return False
            return True
            
        @discord.ui.button(label="Confirm Drop", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = True
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = False
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
    
    @db_group.command(name="drop", description="Drop all data from a table for this guild")
    @app_commands.autocomplete(table=table_autocomplete)
    @app_commands.describe(table="Table to drop data from")
    @app_commands.checks.has_permissions(administrator=True)
    async def drop_table(
        self,
        interaction: discord.Interaction,
        table: str
    ):
        """Drop all data from a table for this guild (preserves table structure)."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if table exists
            if table not in self.table_cache:
                await interaction.followup.send(f"Table '{table}' does not exist.", ephemeral=True)
                return
                
            # Check if table has guild_id for per-guild isolation
            has_guild_id = 'guild_id' in self.table_cache.get(table, [])
            if not has_guild_id:
                await interaction.followup.send(
                    f"Cannot drop data from table '{table}' as it does not support guild isolation (missing guild_id column).", 
                    ephemeral=True
                )
                return
                
            # Get count of records that will be deleted
            count_query = f"SELECT COUNT(*) as count FROM {table} WHERE guild_id = ?"
            count_result = await self.execute_query(count_query, [interaction.guild.id])
            
            if count_result[0]["count"] == 0:
                await interaction.followup.send(f"No records found in '{table}' for this guild.", ephemeral=True)
                return
                
            # Ask for confirmation
            embed = discord.Embed(
                title="⚠️ Confirm Table Data Drop",
                description=f"You are about to delete ALL {count_result[0]['count']} record(s) from '{table}' for this guild.\n\n"
                            f"This action cannot be undone!",
                color=discord.Color.red()
            )
            
            view = self.DropTableConfirmation(interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            await view.wait()
            
            if view.confirmed:
                delete_query = f"DELETE FROM {table} WHERE guild_id = ?"
                delete_result = await self.execute_query(delete_query, [interaction.guild.id])
                
                await interaction.followup.send(
                    f"Successfully dropped {delete_result['rows_affected']} record(s) from '{table}' for this guild.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("Table drop cancelled.", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"Error dropping table data: {str(e)}", ephemeral=True)
    
    class ResetDatabaseConfirmation(discord.ui.View):
        def __init__(self, author_id):
            super().__init__(timeout=60)
            self.author_id = author_id
            self.confirmed = False
            self.confirmation_phrase = None
            
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
                return False
            return True
            
        @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Require a typed confirmation
            if not self.confirmation_phrase:
                # Generate random confirmation phrase


                self.confirmation_phrase = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                
                await interaction.response.send_message(
                    f"⚠️ **EXTREME CAUTION!** ⚠️\n\n"
                    f"To confirm database reset for this guild, please type the following phrase:\n"
                    f"`{self.confirmation_phrase}`",
                    ephemeral=True
                )
                return
            
            # We should never reach here directly - the message callback handles this
            pass
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = False
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
    
    @db_group.command(name="reset", description="Reset all guild data in the database (EXTREME CAUTION)")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_database(
        self,
        interaction: discord.Interaction
    ):
        """Reset ALL data for this guild across all tables (EXTREME CAUTION)."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Count affected tables and records
            affected_tables = []
            total_records = 0
            
            for table_name, fields in self.table_cache.items():
                if 'guild_id' in fields:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name} WHERE guild_id = ?"
                    count_result = await self.execute_query(count_query, [interaction.guild.id])
                    record_count = count_result[0]["count"]
                    
                    if record_count > 0:
                        affected_tables.append((table_name, record_count))
                        total_records += record_count
            
            if not affected_tables:
                await interaction.followup.send("No guild data found to reset.", ephemeral=True)
                return
                
            # Ask for confirmation
            embed = discord.Embed(
                title="⚠️ EXTREME CAUTION: Database Reset ⚠️",
                description=f"You are about to delete ALL {total_records} record(s) across {len(affected_tables)} table(s) for guild '{interaction.guild.name}'.\n\n"
                            f"**THIS ACTION CANNOT BE UNDONE!**\n\n"
                            f"This will remove ALL bot data for your server including configurations, user data, statistics, and all other saved information.",
                color=discord.Color.dark_red()
            )
            
            # Add field listing affected tables
            table_list = "\n".join(f"• {table} ({count} records)" for table, count in affected_tables)
            embed.add_field(name="Affected Tables", value=table_list, inline=False)
            
            view = self.ResetDatabaseConfirmation(interaction.user.id)
            confirm_message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Set up a message listener for the confirmation phrase
            def check(message):
                return (
                    message.author.id == interaction.user.id 
                    and message.channel.id == interaction.channel.id
                    and view.confirmation_phrase 
                    and message.content == view.confirmation_phrase
                )
                
            try:
                # Wait for confirmation message
                confirmation_msg = await self.bot.wait_for('message', check=check, timeout=60)
                
                # Proceed with reset
                deleted_counts = []
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                try:
                    for table_name, _ in affected_tables:
                        cursor.execute(f"DELETE FROM {table_name} WHERE guild_id = ?", [interaction.guild.id])
                        deleted_counts.append((table_name, cursor.rowcount))
                        
                    conn.commit()
                    
                    # Format results
                    results = "\n".join(f"• {table}: {count} records deleted" for table, count in deleted_counts)
                    
                    await confirmation_msg.reply(
                        f"Database reset complete for guild '{interaction.guild.name}'.\n\n"
                        f"Reset summary:\n{results}",
                        ephemeral=True
                    )
                except sqlite3.Error as e:
                    conn.rollback()
                    await confirmation_msg.reply(f"Database error during reset: {str(e)}", ephemeral=True)
                finally:
                    conn.close()
                    
            except asyncio.TimeoutError:
                await interaction.followup.send("Database reset cancelled (confirmation timeout).", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"Error during database reset: {str(e)}", ephemeral=True)

        
async def setup(bot):
    await bot.add_cog(Botto(bot))
