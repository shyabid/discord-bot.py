
import discord
from typing import Optional
from discord import app_commands
import typing
from utils import create_autocomplete_from_list as autocomplete
import psutil 
import time 
start_time = time.time()

class BotGroup(app_commands.Group):
    @app_commands.command(
        name='ping',
        description="Returns with a Pong!"
    )
    async def ping(self,interaction: discord.Interaction):
        await interaction.response.send_message(f"pong")
        
    @app_commands.command(
        name="say",
        description="say something through the bot",
    )
    @app_commands.describe(
        message="put a message to send",
        channel="the channel to send the message in"
    )
    async def sayCmd(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        
        if channel is None:
            channel = interaction.channel

        await interaction.response.send_message(f"messange sent in <#{channel.id}>!", ephemeral=True)
        await channel.send(message)
    
        
    @app_commands.command(
        name="presence",
        description="Change the presence of the bot"
    )
    @app_commands.describe(
        type="Type of status (playing, watching, streaming, listening)",
        status="The status message to set"
    )
    @app_commands.autocomplete(type=autocomplete(['watching', 'playing', 'listening', 'streaming', 'custom']))
    async def presence(
        self,
        interaction: discord.Interaction,
        type: str,
        status: str
    ):
        activity = None

        if type == 'playing':
            activity = discord.Game(name=status)
        elif type == 'watching':
            activity = discord.Activity(type=discord.ActivityType.watching, name=status)
        elif type == 'listening':
            activity = discord.Activity(type=discord.ActivityType.listening, name=status)
        elif type == 'streaming':
            activity = discord.Streaming(name=status, url="https://twitch.tv/mystream")

        elif type == 'custom' or type is None:
            activity = discord.CustomActivity(name=status)
            
        if activity:
            await interaction.client.change_presence(activity=activity)
            await interaction.response.send_message(f"Presence changed to {type} '{status}' status.")
        else:
            await interaction.response.send_message("Invalid type. Please choose 'playing', 'watching', 'streaming', or 'listening'.")

    @app_commands.command(
        name="status",
        description="Set the current bot status"
    )
    @app_commands.describe(
        type="Type of status"
    )
    @app_commands.autocomplete(type=autocomplete(["online", "idle", "dnd", "invisible"]))
    async def status(
        self,
        interaction: discord.Interaction,
        type: str
    ):
        status_mapping = {
            'online': discord.Status.online,
            'idle': discord.Status.idle,
            'dnd': discord.Status.dnd,
            'invisible': discord.Status.offline
        }
        
        status_new = status_mapping.get(type)
        if status_new and status_new != "streaming":
            await interaction.client.change_presence(status=status_new)
            await interaction.response.send_message(f"Status changed to {type}.")
    
    @app_commands.command(
        name="suggest",
        description="Suggest new features or report bugs to the dev"
    )
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        try:
            bot_owner = await interaction.client.fetch_user(876869802948452372) 
            await bot_owner.send(f"New suggestion by: <@{interaction.user.id}>\n```{suggestion}```")
            await interaction.response.send_message(f"Suggestion received: {suggestion}")
        except discord.Forbidden:
            await interaction.response.send_message("I cannot send a DM to the bot owner.")
        except discord.HTTPException as e:
            await interaction.response.send_message("Failed to send the suggestion. Please try again later.")
            print(f"Error sending DM: {e}")
        except Exception as e:
            await interaction.response.send_message("An unexpected error occurred.")
            print(f"Unexpected error: {e}")

    @app_commands.command(
        name="stats",
        description="Displays the bot's stats"
    )
    async def stats(self, interaction: discord.Interaction):
        try:
            latency = round(interaction.client.latency * 1000, 2)
            ram_usage = psutil.Process().memory_info().rss / (1024 * 1024)  

            uptime = time.time() - start_time
            uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

            embed = discord.Embed(title="Bot Stats", color=discord.Color.dark_theme())
            embed.add_field(name="Latency", value=f"{latency} ms", inline=True)
            embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB", inline=True)
            embed.add_field(name="Uptime", value=uptime_str, inline=True) 
            embed.add_field(name="Version", value="1.0.0", inline=True)  

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")
            print(f"Error in stats command: {e}")
