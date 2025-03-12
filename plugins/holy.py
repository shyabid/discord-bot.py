import discord 
from discord import app_commands
import random
from discord.ext import commands
import requests 
from bot import Morgana

class Holy(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot
    
    
    @commands.hybrid_group(name="holy", description="Get a verse from the Quran or Bible")
    async def holy(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Avaliable subcommands: `quran`, `bible`")
            
    @holy.command(
        name="quran",
        description="Get a quran Verse"
    )
    @app_commands.describe(
        query="Specify the chp and verse. (e.g. 2:255)"
    )
    async def quran(self, ctx, *, query: str = None):
        if query is not None and not ':' in query:
            raise commands.BadArgument("Invalid format. Use `chapter:verse` (e.g. 2:255)")
            
        if query is None:
            random_number = random.randint(1, 6236)
            url = f'https://api.alquran.cloud/v1/ayah/{random_number}/editions/quran-uthmani,en.pickthall'
        else:
            url = f'https://api.alquran.cloud/v1/ayah/{query}/editions/quran-uthmani,en.pickthall'
        
        response = requests.get(url)
        data = response.json()

        if data['code'] != 200:
            await ctx.reply(f"Could not fetch the verse. Please check the format and try again.")
            return
        
        verse = data['data'][1]
        arbic_name = data["data"][0]["surah"]["name"]
        eng_name = data["data"][0]["surah"]["englishName"]
        ayah_number = verse['numberInSurah']
        verse_text = verse['text']
        arbic = data["data"][0]["text"]
        embed = discord.Embed(
            description=f"{arbic} \n\n{verse_text}",
            color=discord.Color.dark_grey()
        )
        embed.set_author(name=f"Surah {eng_name} [{arbic_name}] Ayah {ayah_number}")

        await ctx.reply(embed=embed)
        

    @holy.command(
        name="bible",
        description="Get a Bible Verse"
    )
    @app_commands.describe(
        query="bookName chapterNum:verseNum"
    )
    async def bible(self, ctx: commands.Context, *, query:str = None):
        if query is not None and ':' not in query:
            raise commands.BadArgument("Invalid format. Use `bookName chapter:verse` (e.g. John 3:16)")
            
        if query == None:
            response = requests.get('https://bible-api.com/?random=verse')
        else:
            try:
                response = requests.get(f'https://bible-api.com/{query}')
            except Exception:
                await ctx.reply(f"Invalid format. Use `bookName chapter:verse` (e.g. John 3:16)")
                return
        
        data = response.json()
        
        print(data)
        if 'text' not in data:
            await ctx.reply(f"Could not fetch the verse. Please check the format and try again.")
            return
        
        embed = discord.Embed(
            description=data['text'],
            color=discord.Color.dark_grey()
        )
        
        embed.set_author(name=data['reference'])
        embed.set_footer(text="taken from World English Bible")
        await ctx.reply(embed=embed)

    @commands.command(name="quran")
    async def quran_command(self, ctx, *, verse = None): await self.quran(ctx, query=verse)
    
    @commands.command(name="bible")
    async def bible_command(self, ctx, *, verse  = None): await self.bible(ctx, query=verse)
    
    
async def setup(bot: Morgana) -> None:
    await bot.add_cog(Holy(bot))
                           
