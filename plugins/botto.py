import discord
from discord import app_commands
from typing import Optional, Dict, Any, Union, DefaultDict, Literal
from utils import create_autocomplete_from_list as autocomplete
import psutil
from discord.ext import commands
from datetime import datetime, timedelta
import platform
import aiohttp
import random
from bot import Morgana
from discord.ext import tasks
import time
import traceback
from collections import defaultdict
import os
import json
import pytz
json

start_time: float = time.time()


with open('config.json') as f:
    config = json.load(f)

class Botto(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot
        self._process = psutil.Process()
        self.bot.start_time = start_time
        self.status_task.start() 
    
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
            print(f"Error in status_task: {e}")

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
        """Fetch the latest commits from GitHub."""
        repo_url = "https://api.github.com/repos/Empester/discord-bot.py/commits"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(repo_url) as response:
                    if response.status == 200:
                        commit_data = await response.json()
                        commit_list = []
                        for commit in commit_data[:3]:
                            sha = commit['sha'][:7]
                            message = commit['commit']['message'].split('\n')[0][:50]
                            author = commit['commit']['author']['name']
                            utc_time = datetime.fromisoformat(commit['commit']['author']['date'].rstrip('Z'))
                            local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(config["timezone"]))
                            date = discord.utils.format_dt(local_time, style='R')
                            
                            commit_url = commit['html_url']
                            author_url = commit['author']['html_url'] if commit['author'] else None
                            
                            sha_link = f"[`{sha}`]({commit_url})"
                            author_link = f"[{author}]({author_url})" if author_url else author
                            
                            commit_list.append(f"{sha_link} - {author_link} - {message} ({date})")

                        return "\n".join(commit_list)
        except Exception:
            return "Failed to fetch commit data."
        
        return "No commit data available."

    
    @commands.command(name="changepfp")
    async def changepfp(self, ctx: commands.Context, url: str):
        
        if not ctx.author.id == config["owner"]:
            raise commands.MissingPermissions(["bot_owner"])

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    avatar_bytes = await response.read()
                    await self.bot.user.edit(avatar=avatar_bytes)
        
        
async def setup(bot):
    await bot.add_cog(Botto(bot))
