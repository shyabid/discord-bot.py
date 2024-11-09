from bot import Bot
import asyncio
import discord
from discord.ext import commands
from fastapi import FastAPI

# will make a dashboard and controller + bot status logs here with either FasAPI or Flask

bot = Bot()

async def main():
    await bot.start()
    
asyncio.run(main())
