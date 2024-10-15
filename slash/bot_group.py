import discord
from discord import app_commands
from typing import Optional, Dict, Any, Union
from utils import create_autocomplete_from_list as autocomplete
import psutil
from discord.ext import commands
from datetime import datetime, timedelta
import time
import traceback

start_time: float = time.time()

class BotGroup(app_commands.Group):
    @app_commands.command(
        name='ping',
        description="Returns with a Pong!"
    )
    async def ping(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.send_message("pong")
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        
    @app_commands.command(
        name="say",
        description="say something through the bot",
    )
    @app_commands.describe(
        message="put a message to send",
        channel="the channel to send the message in"
    )
    async def sayCmd(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        try:
            if channel is None:
                channel = interaction.channel

            await interaction.response.send_message(f"message sent in <#{channel.id}>!", ephemeral=True)
            await channel.send(message)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(
        name="status",
        description="Change the status and presence of the bot"
    )
    @app_commands.describe(
        status_type="Type of status (online, idle, dnd, invisible)",
        activity_type="Type of activity (playing, watching, streaming, listening, custom)",
        activity_message="The activity message to set"
    )
    @app_commands.autocomplete(
        status_type=autocomplete(["online", "idle", "dnd", "invisible"]),
        activity_type=autocomplete(['watching', 'playing', 'listening', 'streaming', 'custom'])
    )
    async def bot_status(
        self,
        interaction: discord.Interaction,
        status_type: str,
        activity_type: str,
        activity_message: str
    ) -> None:
        try:
            status_mapping: Dict[str, discord.Status] = {
                'online': discord.Status.online,
                'idle': discord.Status.idle,
                'dnd': discord.Status.dnd,
                'invisible': discord.Status.invisible
            }
            
            activity_mapping: Dict[str, Union[discord.Game, discord.Activity, discord.Streaming, discord.CustomActivity]] = {
                'playing': discord.Game(name=activity_message),
                'watching': discord.Activity(type=discord.ActivityType.watching, name=activity_message),
                'listening': discord.Activity(type=discord.ActivityType.listening, name=activity_message),
                'streaming': discord.Streaming(name=activity_message, url="https://twitch.tv/mystream"),
                'custom': discord.CustomActivity(name=activity_message)
            }
            
            status: Optional[discord.Status] = status_mapping.get(status_type.lower())
            activity: Optional[Union[discord.Game, discord.Activity, discord.Streaming, discord.CustomActivity]] = activity_mapping.get(activity_type.lower())
            
            if status is None or activity is None:
                await interaction.response.send_message("Invalid status or activity type.", ephemeral=True)
                return
            
            await interaction.client.change_presence(status=status, activity=activity)
            await interaction.response.send_message(f"Bot status changed to {status_type} with {activity_type} '{activity_message}' activity.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            interaction.client.logger.error(f"Error in bot_status command: {traceback.format_exc()}")

    @app_commands.command(
        name="suggest",
        description="Suggest new features or report bugs to the dev"
    )
    async def suggest(self, interaction: discord.Interaction, suggestion: str) -> None:
        try:
            bot_owner: discord.User = await interaction.client.fetch_user(876869802948452372)
            await bot_owner.send(f"New suggestion by: <@{interaction.user.id}>\n```{suggestion}```")
            await interaction.response.send_message(f"Suggestion received: {suggestion}")
        except discord.Forbidden:
            await interaction.response.send_message("I cannot send a DM to the bot owner.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message("Failed to send the suggestion. Please try again later.", ephemeral=True)
            interaction.client.logger.error(f"Error sending DM: {e}")
        except Exception as e:
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
            interaction.client.logger.error(f"Unexpected error in suggest command: {traceback.format_exc()}")

    @app_commands.command(
        name="stats",
        description="Displays the bot's stats"
    )
    async def stats(self, interaction: discord.Interaction) -> None:
        try:
            latency: float = round(interaction.client.latency * 1000, 2)
            ram_usage: float = psutil.Process().memory_info().rss / (1024 * 1024)

            uptime: float = time.time() - start_time
            uptime_str: str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

            embed: discord.Embed = discord.Embed(title="Bot Stats", color=discord.Color.dark_theme())
            embed.add_field(name="Latency", value=f"{latency} ms", inline=True)
            embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB", inline=True)
            embed.add_field(name="Uptime", value=uptime_str, inline=True)
            embed.add_field(name="Version", value="1.0.0", inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            interaction.client.logger.error(f"Error in stats command: {traceback.format_exc()}")
    