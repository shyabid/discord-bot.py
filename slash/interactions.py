import requests 
from discord import app_commands
import discord 
from utils.slash_tools import autocomplete_DICT2
import random
from data import interaction_data


# autocomplete cant show more than 25 options at once.... the issue is real

@app_commands.describe(type="Select an interaction type",user="User to interact with")
@app_commands.autocomplete(type=autocomplete_DICT2(interaction_data))
async def interactioncmd(interaction: discord.Interaction, type: str, user: discord.User):
    response = requests.get(url=interaction_data.get(type)[0])
    
    if response.status_code != 200:
        await interaction.response.send_message("Failed to fetch data.", ephemeral=True)
        return

    data = response.json()
    
    txt = random.choice(interaction_data.get(type)[1])
    embed = discord.Embed(
        description=f"{interaction.user.global_name} {txt} {user.name}",
        color=discord.Color.dark_grey()
    )
    embed.set_image(url=data['results'][0]['url'])
    embed.set_footer(text=f"Anime: {data['results'][0]['anime_name']}")
    
    await interaction.response.send_message(embed=embed)