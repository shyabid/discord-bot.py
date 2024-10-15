from bot import Bot
import asyncio
import discord
from discord.ext import commands
from fastapi import FastAPI
from utils import create_autocomplete_from_list as autocomplete, create_autocomplete_from_dict as autocomplete_DICT2

# will make a dhasboard and controller + bot status logs here with either FasAPI or Flask

bot = Bot()

async def main():
    await bot.start()
    
asyncio.run(main())
