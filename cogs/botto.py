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
    def __init__(self, bot):
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
        await ctx.send("pong")
        
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
        await ctx.send(f"message sent in {channel.mention}!", ephemeral=True)
    
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
            await ctx.send("Invalid status or activity type.", ephemeral=True)
            return
        
        await self.bot.change_presence(status=discord_status, activity=discord_activity)
        await ctx.send(f"Bot status changed to {status} with {activity} '{text}' activity.")
    
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
            color=discord.Color.blue()
        )
        thank_embed.add_field(name="Your Suggestion", value=suggestion[:1024] + "..." if len(suggestion) > 1024 else suggestion)
        
        await ctx.send(embed=thank_embed)

    @grbt.command(
        name="stats",
        description="Displays comprehensive bot statistics, performance metrics, and system information"
    )
    async def stats(self, ctx: commands.Context):
        await ctx.defer()
        try:
            start_time = time.perf_counter()
            latency = round(self.bot.latency * 1000, 2)
            process = psutil.Process()
            ram_usage = process.memory_info().rss / (1024 * 1024)
            cpu_usage = psutil.cpu_percent()
            disk_usage = psutil.disk_usage('/')

            if not hasattr(self.bot, 'start_time'):
                self.bot.start_time = time.time()

            uptime = time.time() - self.bot.start_time
            uptime_str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

            repo_url = "https://api.github.com/repos/shyabid/discord-bot.py/commits/main"
            async with aiohttp.ClientSession() as session:
                async with session.get(repo_url) as response:
                    if response.status == 200:
                        commit_data = await response.json()
                        latest_commit = commit_data['sha'][:7]
                        commit_message = commit_data['commit']['message'].split('\n')[0]
                        commit_author = f"[{commit_data['commit']['author']['name']}](https://github.com/{commit_data['commit']['author']['name']})"
                        commit_date = discord.utils.format_dt(datetime.fromisoformat(commit_data['commit']['author']['date'].rstrip('Z')), style='R')
                    else:
                        latest_commit = "Unknown"
                        commit_message = "Failed to fetch"
                        commit_author = "Unknown"
                        commit_date = "Unknown"

            all_commands = list(self.bot.walk_commands())
            parent_commands = [cmd for cmd in all_commands if not cmd.parent]
            slash_commands = len(self.bot.tree.get_commands())

            total_members = sum(guild.member_count for guild in self.bot.guilds)
            total_channels = sum(len(guild.channels) for guild in self.bot.guilds)
            total_roles = sum(len(guild.roles) for guild in self.bot.guilds)
            total_emojis = sum(len(guild.emojis) for guild in self.bot.guilds)

            voice_clients = len(self.bot.voice_clients)

            embed = discord.Embed(
                title="Comprehensive Bot Statistics",
                description=f"Running on commit [`{latest_commit}`](https://github.com/shyabid/discord-bot.py/commit/{latest_commit}): `{commit_message}` by {commit_author} {commit_date}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Latency", value=f"{latency} ms", inline=True)
            embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB", inline=True)
            embed.add_field(name="CPU Usage", value=f"{cpu_usage:.2f}%", inline=True)
            embed.add_field(name="Disk Usage", value=f"{disk_usage.percent}%", inline=True)
            embed.add_field(name="Uptime", value=uptime_str, inline=True)
            embed.add_field(name="Servers", value=f"{len(self.bot.guilds):,}", inline=True)
            embed.add_field(name="Users", value=f"{total_members:,}", inline=True)
            embed.add_field(name="Channels", value=f"{total_channels:,}", inline=True)
            embed.add_field(name="Roles", value=f"{total_roles:,}", inline=True)
            embed.add_field(name="Emojis", value=f"{total_emojis:,}", inline=True)
            embed.add_field(name="Voice Connections", value=str(voice_clients), inline=True)
            embed.add_field(name="Commands", value=f"{len(parent_commands)} ({len(all_commands)} total)", inline=True)
            embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
            embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
            embed.add_field(name="Operating System", value=f"{platform.system()} {platform.release()}", inline=True)

            end_time = time.perf_counter()
            embed.set_footer(text=f"Stats generated in {(end_time - start_time)*1000:.2f} ms")

            await ctx.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An unexpected error occurred while fetching bot statistics: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Error Type", value=type(e).__name__, inline=True)
            error_embed.add_field(name="Error Details", value=str(e), inline=True)
            error_embed.add_field(name="Traceback", value=f"```py\n{''.join(traceback.format_tb(e.__traceback__))}\n```", inline=False)
            
            await ctx.send(embed=error_embed)

    @grbt.command(name="sync", description="Sync application commands for a specific guild")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guild_id: str):
        try:
            guild_id = int(guild_id)
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                await ctx.send(f"Error: Could not find a guild with ID {guild_id}")
                return
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
            await ctx.send(f"Successfully synced application commands for guild: {guild.name} (ID: {guild.id})")

        except ValueError:
            await ctx.send("Error: Invalid guild ID. Please provide a valid integer ID.")
        except Exception as e:
            await ctx.send(f"An error occurred while syncing: {str(e)}")


async def setup(bot):
    await bot.add_cog(Botto(bot))
