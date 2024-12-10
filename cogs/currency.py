from discord.ext import commands
from discord import app_commands
import discord

class Currency(commands.Cog):
    """The description for Currency goes here."""

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db["currency_data"] 
   

    
async def setup(bot):
    await bot.add_cog(Currency(bot))
