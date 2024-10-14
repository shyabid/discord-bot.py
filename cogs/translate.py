
from discord.ext import commands
import requests
from discord import app_commands
import aiohttp
import discord

async def translate_ctx_menu(interaction: discord.Interaction, message: discord.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/translate?to=en&text={message.content}") as response:
            if response.status == 200:
                translated = (await response.json()).get("translated")
                await interaction.response.send_message(f"` traslation: ` {translated}")
            else:
                await interaction.response.send_message("Error contacting the translation service.")

class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(
        name="translate",
        description="Translate text from one language to another",
        aliases=["t", "tl"]
    )
    async def translate(self, ctx, text=None):
            if text is None:
                if ctx.message.reference:
                    message = await ctx.fetch_message(ctx.message.reference.message_id)
                    text = message.content
                else:
                    await ctx.reply("Please provide text or reply to a message to translate.")
                    return
            try: 
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.popcat.xyz/translate?to=en&text={text}") as response:
                        if response.status == 200:
                            translation = (await response.json()).get('translated')
                            if translation:
                                await ctx.reply(f"` traslation: ` {translation}")
                            else:
                                await ctx.reply("Translation failed.")
                        else:
                            await ctx.reply("Error while contacting the translation service.")
            except Exception as e:
                await ctx.reply("An error occurred while translating.")

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.reply("pong")
    
async def setup(bot):
    await bot.add_cog(Translate(bot))
    