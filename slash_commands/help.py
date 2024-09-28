import requests 
from discord import app_commands
import discord 
from utils.slash_tools import autocomplete_DICT



@app_commands.describe(
    command="Get help for a specific command"
)
async def helpcmd(interaction: discord.Interaction, command: str = None):
    if command is None:
        embed = discord.Embed(title="Help")
        await interaction.response.send_message(embed=embed)
        