import discord
from discord.ext import commands
import requests
import random
from data import interaction_data
from utils import find_member

class InteractionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        content = message.content.split()
        if not content:
            return
            
        prefixes = await self.bot.get_prefix(message)
        
        if isinstance(prefixes, str):
            prefixes = [prefixes]
            
        command = None
        for prefix in prefixes:
            if content[0].startswith(prefix):
                command = content[0][len(prefix):] 
                break
                
        if not command: 
            return
        if command in interaction_data:
            if len(content) < 2:
                await message.reply("Mention a user or provide their name/id to interact with")
                return
            
            user = None
            
            if message.mentions:
                user = message.mentions[0]
            else:
                user = await find_member(message.guild, content[1])
                
            if not user:
                await message.reply("Couldn't find that user!")
                return
            
            response = requests.get(url=interaction_data[command][0])
            
            if response.status_code != 200:
                await message.reply("Failed to fetch data.")
                return

            data = response.json()
            txt = random.choice(interaction_data[command][1])
            embed = discord.Embed(
                description=f"{message.author.mention} {txt} {user.mention}",
                color=discord.Color.dark_grey()
            )
            embed.set_image(url=data['results'][0]['url'])
            embed.set_footer(text=f"Anime: {data['results'][0]['anime_name']}")
            
            await message.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionsCog(bot))
