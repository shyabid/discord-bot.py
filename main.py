from logger import log
from bot import Bot
import asyncio
from fastapi import FastAPI

# will make a dhasboard and controller + bot status logs here with either FasAPI or Flask

async def main():
    bot = Bot()
    await bot.start()
    
asyncio.run(main())