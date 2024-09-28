import discord
from discord.ext import commands
import requests
import random
from data import interaction_data

class InteractionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        content = message.content.split()
        
        if len(content) < 2:
            return
        
        command = content[0].lstrip(self.bot.command_prefix)
        user_mention = content[1]
        
        if command in interaction_data and message.mentions:
            user = message.mentions[0] 
            response = requests.get(url=interaction_data[command][0])
            
            if response.status_code != 200:
                await message.reply("Failed to fetch data.")
                return

            data = response.json()
            txt = random.choice(interaction_data[command][1])
            embed = discord.Embed(
                description=f"{message.author.name} {txt} {user.name}",
                color=discord.Color.dark_grey()
            )
            embed.set_image(url=data['results'][0]['url'])
            embed.set_footer(text=f"Anime: {data['results'][0]['anime_name']}")
            
            await message.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionsCog(bot))
