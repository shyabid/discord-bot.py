import discord
from discord import app_commands
from typing import Optional, Dict, Any, Union
from utils import create_autocomplete_from_list as autocomplete
import psutil
from discord.ext import commands
from datetime import datetime, timedelta
import platform
import aiohttp
import time
import traceback

start_time: float = time.time()
class Botto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="bot",
        description="Bot-related commands",
        invoke_without_command=True
    )
    async def grbt(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @grbt.command(
        name='ping',
        description="Returns with a Pong!"
    )
    async def ping(self, ctx: commands.Context):
        start_time = time.perf_counter()
        message = await ctx.reply("Pinging...")
        end_time = time.perf_counter()
        
        websocket_latency = self.bot.latency * 1000
        message_latency = (end_time - start_time) * 1000
        total_latency = websocket_latency + message_latency
        
        await message.edit(content=f"Pong! 🏓\n"
                                    f"Bot Processing Time: {message_latency:.2f}ms\n"
                                    f"WebSocket Latency: {websocket_latency:.2f}ms\n"
                                    f"Total Latency: {total_latency:.2f}ms")
    @grbt.command(
        name="say",
        description="say something through the bot"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        message="The message to send",
        channel="The channel to send the message in (optional)"
    )
    async def say(self, ctx: commands.Context, message: str, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel
        await channel.send(message)
        await ctx.reply(f"message sent in {channel.mention}!", ephemeral=True)
    
    @commands.command(name="status")
    async def status_command(self, ctx: commands.Context, status: str, activity: str, *, text: str):
        await self.status(ctx, status, activity, text)
    
    @grbt.command(
        name="status",
        description="Change the status and presence of the bot"
    )
    @app_commands.describe(
        status="The status to set (online, idle, dnd, invisible)",
        activity="The activity type (playing, watching, listening, streaming, custom)",
        text="The text to display for the activity"
    )
    async def status(self, ctx: commands.Context, status: str, activity: str, *, text: str):
        if not ctx.author.id == 876869802948452372: raise commands.MissingPermissions(["bot_owner"])
        
        status_mapping = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.invisible
        }
        
        activity_mapping = {
            'playing': discord.Game(name=text),
            'watching': discord.Activity(type=discord.ActivityType.watching, name=text),
            'listening': discord.Activity(type=discord.ActivityType.listening, name=text),
            'streaming': discord.Streaming(name=text, url="https://twitch.tv/mystream"),
            'custom': discord.CustomActivity(name=text)
        }
        
        discord_status = status_mapping.get(status.lower())
        discord_activity = activity_mapping.get(activity.lower())
        
        if discord_status is None or discord_activity is None:
            await ctx.reply("Invalid status or activity type.", ephemeral=True)
            return
        
        await self.bot.change_presence(status=discord_status, activity=discord_activity)
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
        bot_owner = await self.bot.fetch_user(876869802948452372)
        
        embed = discord.Embed(
            title="New Suggestion/Bug Report",
            description=suggestion,
            color=discord.Color.green()
        )
        embed.set_author(name=f"{ctx.author.name}#{ctx.author.discriminator}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.add_field(name="User ID", value=ctx.author.id, inline=True)
        embed.add_field(name="Guild", value=f"{ctx.guild.name} (ID: {ctx.guild.id})", inline=True)
        embed.add_field(name="Channel", value=f"{ctx.channel.name} (ID: {ctx.channel.id})", inline=True)
        embed.add_field(name="Timestamp", value=discord.utils.format_dt(ctx.message.created_at, style='F'), inline=False)
        
        await bot_owner.send(embed=embed)
        
        thank_embed = discord.Embed(
            title="Thank You for Your Feedback!",
            description="Your suggestion has been sent to the bot developer. We appreciate your input!",
            color=discord.Color.dark_grey()
        )
        thank_embed.add_field(name="Your Suggestion", value=suggestion[:1024] + "..." if len(suggestion) > 1024 else suggestion)
        
        await ctx.reply(embed=thank_embed)

    @commands.command(name="stats", aliases=["statistics", "about"])
    async def stats_command(self, ctx: commands.Context):
        await self.stats(ctx)

    @grbt.command(
        name="stats",
        description="Displays comprehensive bot statistics, performance metrics, and system information"
    )
    async def stats(self, ctx: commands.Context):
        await ctx.defer()
        try:
            start_time = time.perf_counter()
            latency = round(self.bot.latency * 1000, 2)
            if not hasattr(self.bot, 'start_time'):
                self.bot.start_time = time.time()

            uptime = time.time() - self.bot.start_time
            uptime_str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
            process = psutil.Process()
            ram_usage = process.memory_info().rss / (1024 * 1024)
            cpu_usage = psutil.cpu_percent()
            disk_usage = psutil.disk_usage('/')

            all_commands = list(self.bot.walk_commands())
            parent_commands = len([cmd for cmd in all_commands if not cmd.parent])

            total_members = sum(guild.member_count for guild in self.bot.guilds)
            total_channels = sum(len(guild.channels) for guild in self.bot.guilds)
            total_roles = sum(len(guild.roles) for guild in self.bot.guilds)
            total_emojis = sum(len(guild.emojis) for guild in self.bot.guilds)
            voice_clients = len(self.bot.voice_clients)

            repo_url = "https://api.github.com/repos/shyabid/discord-bot.py/commits"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(repo_url) as response:
                    if response.status == 200:
                        commit_data = await response.json()
                        commit_list = []
                        for commit in commit_data[:3]:
                            sha = commit['sha'][:7]
                            message = commit['commit']['message'].split('\n')[0][:50]  # Truncate message to 50 chars
                            author = commit['commit']['author']['name']
                            date = discord.utils.format_dt(datetime.fromisoformat(commit['commit']['author']['date'].rstrip('Z')), style='R')
                            
                            commit_url = commit['html_url']
                            author_url = commit['author']['html_url'] if commit['author'] else None
                            
                            sha_link = f"[`{sha}`]({commit_url})"
                            author_link = f"[{author}]({author_url})" if author_url else author
                            
                            commit_list.append(f"{sha_link} - {author_link} - {message} ({date})")

                        commit_description = "\n".join(commit_list)
                    else:
                        commit_description = "Failed to fetch commit data."

            embed = discord.Embed(
                title=f"{self.bot.user.name} Statistics",
                description=(
                    f"**Latest Changes**\n{commit_description}\n\n"
                    f"**Uptime:** {uptime_str}\n"
                    f"**Latency:** {latency}ms\n"
                    f"**Commands:** {parent_commands}"
                ),
                color=discord.Color.dark_grey()
            )

            embed.add_field(
                name="Resource Usage",
                value=f"OS: {platform.system()} {platform.release()}\n"
                    f"RAM: {ram_usage:.2f} MB\n"
                    f"CPU: {cpu_usage:.2f}%\n"
                    f"Disk: {disk_usage.percent}%",
                inline=True
            )

            embed.add_field(
                name="Maintaining",
                value=f"{len(self.bot.guilds):,} Servers\n"
                    f"{total_members:,} Users\n"
                    f"{total_channels:,} Channels\n"
                    f"{total_roles:,} Roles",
                inline=True
            )

            embed.add_field(
                name="Versions",
                value=f"Python: {platform.python_version()}\n"
                    f"Discord.py: {discord.__version__}",
                inline=True
            )   

            end_time = time.perf_counter()
            embed.set_footer(text=f"Stats generated in {(end_time - start_time)*1000:.2f} ms")

            await ctx.reply(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An unexpected error occurred while fetching bot statistics: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Error Type", value=type(e).__name__, inline=True)
            error_embed.add_field(name="Error Details", value=str(e)[:1024], inline=True)
            
            tb_string = ''.join(traceback.format_tb(e.__traceback__))
            error_embed.add_field(name="Traceback", value=f"```py\n{tb_string[:1024]}\n```", inline=False)

            await ctx.reply(embed=error_embed)

    @grbt.command(name="sync", description="Sync application commands for a specific guild")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context, guild_id: str):
        try:
            guild_id = int(guild_id)
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                await ctx.reply(f"Error: Could not find a guild with ID {guild_id}")
                return
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
            await ctx.reply(f"Successfully synced application commands for guild: {guild.name} (ID: {guild.id})")

        except ValueError:
            await ctx.reply("Error: Invalid guild ID. Please provide a valid integer ID.")
        except Exception as e:
            await ctx.reply(f"An error occurred while syncing: {str(e)}")


async def setup(bot):
    await bot.add_cog(Botto(bot))
