from logger import log
from bot import Bot
import asyncio
from fastapi import FastAPI

# will make a dhasboard and controller + bot status logs here with either FasAPI or Flask

bot = Bot()
async def main():
    await bot.start()
    
asyncio.run(main())