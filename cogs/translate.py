
from discord.ext import commands
import requests
from discord import app_commands
import aiohttp
import discord
import traceback
from typing import (
    Dict,
    List,
    Optional,
    Any
)

async def translate_ctx_menu(
    interaction: discord.Interaction, 
    message: discord.Message
) -> None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.popcat.xyz/translate?to=en&text={message.content}"
            ) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    translated: Optional[str] = data.get("translated")
                    if translated:
                        await interaction.response.send_message(embed=discord.Embed(description=f"` translation: ` {translated}", color=discord.Color.dark_grey()))
                    else:
                        await interaction.response.send_message("Translation failed: No translated text received.")
                else:
                    await interaction.response.send_message(f"Error contacting the translation service. Status code: {response.status}")
    except Exception as e:
        error_message: str = f"An error occurred during translation: {str(e)}"
        interaction.client.logger.error(f"Translation error in translate_ctx_menu: {error_message}\n{traceback.format_exc()}")
        await interaction.response.send_message(error_message)

class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
    
    @commands.command(
        name="translate",
        description="Translate text from one language to another",
        aliases=["t", "tl"]
    )
    async def translate(
        self, 
        ctx: commands.Context, 
        *, 
        text: Optional[str] = None
    ) -> None:
        """
        Translate text from one language to another.
        
        **Parameters:**
        text (optional): The text to translate. If not provided, the bot will attempt to translate the message you're replying to.

        **Example:**
        ?translate Hello, how are you?
        ?t Bonjour, comment allez-vous?
        ?tl こんにちは、お元気ですか？
        """
        try:
            if text is None:
                if ctx.message.reference:
                    referenced_message: discord.Message = await ctx.fetch_message(
                        ctx.message.reference.message_id
                    )
                    text = referenced_message.content
                else:
                    await ctx.reply("Please provide text or reply to a message to translate.")
                    return

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.popcat.xyz/translate?to=en&text={text}"
                ) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        translation: Optional[str] = data.get('translated')
                        if translation:
                            embed = discord.Embed(
                                description=f"` translation: ` {translation}", 
                                color=discord.Color.dark_grey()
                            )
                            await ctx.reply(embed=embed)
                        else:
                            await ctx.reply("Translation failed: No translated text received.")
                    else:
                        await ctx.reply(f"Error while contacting the translation service. Status code: {response.status}")
        except Exception as e:
            error_message: str = f"An error occurred while translating: {str(e)}"
            self.bot.logger.error(f"Translation error in translate command: {error_message}\n{traceback.format_exc()}")
            await ctx.reply(error_message)

    @commands.command()
    async def ping(
        self, 
        ctx: commands.Context
    ) -> None:
        try:
            await ctx.reply("pong")
        except Exception as e:
            error_message: str = f"An error occurred in ping command: {str(e)}"
            self.bot.logger.error(f"Ping command error: {error_message}\n{traceback.format_exc()}")
            await ctx.reply(error_message)
    
async def setup(
        bot: commands.Bot
) -> None:
    try:
        await bot.add_cog(Translate(bot))
        bot.logger.info("Translate cog loaded successfully")
    except Exception as e:
        error_message: str = f"Failed to add Translate cog: {str(e)}"
        bot.logger.error(f"{error_message}\n{traceback.format_exc()}")
