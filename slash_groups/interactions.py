import requests 
from discord import app_commands
import discord 
from utils.slash_tools import autocomplete_DICT

interactionUrls = {
    "lurk": "https://nekos.best/api/v2/lurk",
    "shoot": "https://nekos.best/api/v2/shoot",
    "sleep": "https://nekos.best/api/v2/sleep",
    "shrug": "https://nekos.best/api/v2/shrug",
    "stare": "https://nekos.best/api/v2/stare",
    "wave": "https://nekos.best/api/v2/wave",
    "poke": "https://nekos.best/api/v2/poke",
    "smile": "https://nekos.best/api/v2/smile",
    "peck": "https://nekos.best/api/v2/peck",
    "wink": "https://nekos.best/api/v2/wink",
    "blush": "https://nekos.best/api/v2/blush",
    "smug": "https://nekos.best/api/v2/smug",
    "tickle": "https://nekos.best/api/v2/tickle",
    "yeet": "https://nekos.best/api/v2/yeet",
    "think": "https://nekos.best/api/v2/think",
    "highfive": "https://nekos.best/api/v2/highfive",
    "feed": "https://nekos.best/api/v2/feed",
    "bite": "https://nekos.best/api/v2/bite",
    "bored": "https://nekos.best/api/v2/bored",
    "nom": "https://nekos.best/api/v2/nom",
    "yawn": "https://nekos.best/api/v2/yawn",
    "facepalm": "https://nekos.best/api/v2/facepalm",
    "cuddle": "https://nekos.best/api/v2/cuddle",
    "kick": "https://nekos.best/api/v2/kick",
    "happy": "https://nekos.best/api/v2/happy",
    "hug": "https://nekos.best/api/v2/hug",
    "baka": "https://nekos.best/api/v2/baka",
    "pat": "https://nekos.best/api/v2/pat",
    "nod": "https://nekos.best/api/v2/nod",
    "nope": "https://nekos.best/api/v2/nope",
    "kiss": "https://nekos.best/api/v2/kiss",
    "dance": "https://nekos.best/api/v2/dance",
    "punch": "https://nekos.best/api/v2/punch",
    "handshake": "https://nekos.best/api/v2/handshake",
    "slap": "https://nekos.best/api/v2/slap",
    "cry": "https://nekos.best/api/v2/cry",
    "pout": "https://nekos.best/api/v2/pout",
    "handhold": "https://nekos.best/api/v2/handhold",
    "thumbsup": "https://nekos.best/api/v2/thumbsup",
    "laugh": "https://nekos.best/api/v2/laugh"
}


@app_commands.command(name="interaction", description="Interaction commands")
@app_commands.describe(type="Select an interaction type",user="User to interact with")
@app_commands.autocomplete(type=autocomplete_DICT(interactionUrls))
async def interactioncmd(interaction: discord.Interaction, type: str, user: discord.User):
    response = requests.get(url=type)
    data = response.json()
    
    if response.status_code == 200:
        embed = discord.Embed(
            description=f"{user.mention} take this",
            color=discord.Color.dark_grey()
        )
        embed.set_image(url=data['results'][0]['url'])
        embed.set_footer(f"Anime: {data['results'][0]['anime_name']}")
        
    await interaction.response.send_embed(embed=embed)
