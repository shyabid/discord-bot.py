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

class BotGroup(app_commands.Group):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                description=f"You are missing the permission(s) `{', '.join(error.missing_permissions)}` to execute this command!",
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            embed = discord.Embed(
                description=f"I am missing the permission(s) `{', '.join(error.missing_permissions)}` to fully perform this command!",
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = discord.Embed(
                title="Error!",
                description=f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.",
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Error!",
                description=str(error),
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        self.bot.logger.warning(f"Command error handled: {type(error).__name__}")

    @app_commands.command(
        name='ping',
        description="Returns with a Pong!"
    )
    async def ping(
        self,
        interaction: discord.Interaction
    ) -> None:
        await interaction.response.send_message("pong")
        
    @app_commands.command(
        name="say",
        description="say something through the bot"
    )
    @app_commands.describe(
        message="put a message to send",
        channel="the channel to send the message in"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sayCmd(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        if channel is None:
            channel = interaction.channel

        await interaction.response.send_message(f"message sent in <#{channel.id}>!", ephemeral=True)
        await channel.send(message)
    
    @app_commands.command(
        name="status",
        description="Change the status and presence of the bot"
    )
    @app_commands.describe(
        status="Type of status (online, idle, dnd, invisible)",
        activity="Type of activity (playing, watching, streaming, listening, custom)",
        text="The activity message to set"
    )
    @app_commands.autocomplete(
        status=autocomplete(["online", "idle", "dnd", "invisible"]),
        activity=autocomplete(['watching', 'playing', 'listening', 'streaming', 'custom'])
    )
    async def bot_status(
        self,
        interaction: discord.Interaction,
        status: str,
        activity: str,
        text: str
    ) -> None:
        if interaction.user.id != interaction.client.owner_id:
            await interaction.response.send_message("You don't have permission to change the bot's status.", ephemeral=True)
            return
        
        status_mapping: Dict[str, discord.Status] = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.invisible
        }
        
        activity_mapping: Dict[str, Union[discord.Game, discord.Activity, discord.Streaming, discord.CustomActivity]] = {
            'playing': discord.Game(name=text),
            'watching': discord.Activity(type=discord.ActivityType.watching, name=text),
            'listening': discord.Activity(type=discord.ActivityType.listening, name=text),
            'streaming': discord.Streaming(name=text, url="https://twitch.tv/mystream"),
            'custom': discord.CustomActivity(name=text)
        }
        
        discord_status: Optional[discord.Status] = status_mapping.get(status.lower())
        discord_activity: Optional[Union[discord.Game, discord.Activity, discord.Streaming, discord.CustomActivity]] = activity_mapping.get(activity.lower())
        
        if discord_status is None or discord_activity is None:
            await interaction.response.send_message("Invalid status or activity type.", ephemeral=True)
            return
        
        await interaction.client.change_presence(status=discord_status, activity=discord_activity)
        await interaction.response.send_message(f"Bot status changed to {status} with {activity} '{text}' activity.")
    
    
    @app_commands.command(
        name="suggest",
        description="Suggest new features or report bugs to the dev"
    )
    @app_commands.describe(
        suggestion="Your detailed suggestion or bug report"
    )
    async def suggest(
        self,
        interaction: discord.Interaction,
        suggestion: str
    ) -> None:
        bot_owner: discord.User = await interaction.client.fetch_user(876869802948452372)
        
        embed = discord.Embed(
            title="New Suggestion/Bug Report",
            description=suggestion,
            color=discord.Color.green()
        )
        embed.set_author(name=f"{interaction.user.name}#{interaction.user.discriminator}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="User ID", value=interaction.user.id, inline=True)
        embed.add_field(name="Guild", value=f"{interaction.guild.name} (ID: {interaction.guild.id})", inline=True)
        embed.add_field(name="Channel", value=f"{interaction.channel.name} (ID: {interaction.channel.id})", inline=True)
        embed.add_field(name="Timestamp", value=discord.utils.format_dt(interaction.created_at, style='F'), inline=False)
        
        await bot_owner.send(embed=embed)
        
        thank_embed = discord.Embed(
            title="Thank You for Your Feedback!",
            description="Your suggestion has been sent to the bot developer. We appreciate your input!",
            color=discord.Color.blue()
        )
        thank_embed.add_field(name="Your Suggestion", value=suggestion[:1024] + "..." if len(suggestion) > 1024 else suggestion)
        
        await interaction.response.send_message(embed=thank_embed, ephemeral=True)

    @app_commands.command(
        name="stats",
        description="Displays comprehensive bot statistics, performance metrics, and system information"
    )
    async def stats(
        self,
        interaction: discord.Interaction
    ) -> None:
        await interaction.response.defer(ephemeral=False)
        try:
            start_time = time.perf_counter()
            latency: float = round(interaction.client.latency * 1000, 2)
            process = psutil.Process()
            ram_usage: float = process.memory_info().rss / (1024 * 1024)
            cpu_usage: float = psutil.cpu_percent()
            disk_usage = psutil.disk_usage('/')

            uptime: float = time.time() - interaction.client.start_time if hasattr(interaction.client, 'start_time') else 0
            uptime_str: str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

            if not hasattr(interaction.client, 'start_time'):
                interaction.client.start_time = time.time()

            uptime: float = time.time() - interaction.client.start_time
            uptime_str: str = f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

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

            all_commands = list(interaction.client.walk_commands())
            parent_commands = [cmd for cmd in all_commands if not cmd.parent]
            slash_commands = len(interaction.client.tree.get_commands())

            total_members = sum(guild.member_count for guild in interaction.client.guilds)
            total_channels = sum(len(guild.channels) for guild in interaction.client.guilds)
            total_roles = sum(len(guild.roles) for guild in interaction.client.guilds)
            total_emojis = sum(len(guild.emojis) for guild in interaction.client.guilds)

            voice_clients = len(interaction.client.voice_clients)

            embed: discord.Embed = discord.Embed(
                title="Comprehensive Bot Statistics",
                description=f"Running on commit [`{latest_commit}`](https://github.com/shyabid/discord-bot.py/commit/{latest_commit}): `{commit_message}` by {commit_author} {commit_date}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Latency", value=f"{latency} ms", inline=True)
            embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB", inline=True)
            embed.add_field(name="CPU Usage", value=f"{cpu_usage:.2f}%", inline=True)
            embed.add_field(name="Disk Usage", value=f"{disk_usage.percent}%", inline=True)
            embed.add_field(name="Uptime", value=uptime_str, inline=True)
            embed.add_field(name="Servers", value=f"{len(interaction.client.guilds):,}", inline=True)
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

            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Error",
                description=f"An unexpected error occurred while fetching bot statistics: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.add_field(name="Error Type", value=type(e).__name__, inline=True)
            error_embed.add_field(name="Error Details", value=str(e), inline=True)
            error_embed.add_field(name="Traceback", value=f"```py\n{''.join(traceback.format_tb(e.__traceback__))}\n```", inline=False)
            
            await interaction.followup.send(embed=error_embed, ephemeral=True)