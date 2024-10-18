
from discord.ext import commands
import requests
from discord import app_commands
import aiohttp
import discord
import traceback
from typing import (
    Dict,
    Literal,
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


    @commands.hybrid_command(
        name="autotranslate",
        description="Toggle automatic translation for the current channel"
    )
    @commands.has_permissions(manage_messages=True)
    async def autotranslate(
        self,
        ctx: commands.Context,
        state: Literal["on", "off"]
    ) -> None:
        """
        Toggle automatic translation for the current channel.

        **Parameters:**
        state: Either "on" or "off" to enable or disable auto-translation.

        **Example:**
        ?autotranslate on
        /autotranslate state:off
        """
        channel_id = ctx.channel.id
        guild_id = ctx.guild.id

        if state == "on":
            webhook = await ctx.channel.create_webhook(name="AutoTranslate")
            self.bot.db[str(guild_id)]["autotranslate"].update_one(
                {"channel_id": channel_id},
                {"$set": {"webhook_id": webhook.id, "webhook_token": webhook.token}},
                upsert=True
            )
            await ctx.reply("Auto-translation has been enabled for this channel.")
        else:
            webhook_data = self.bot.db[str(guild_id)]["autotranslate"].find_one({"channel_id": channel_id})
            if webhook_data:
                webhook = await self.bot.fetch_webhook(webhook_data["webhook_id"])
                await webhook.delete()
                self.bot.db[str(guild_id)]["autotranslate"].delete_one({"channel_id": channel_id})
                await ctx.reply("Auto-translation has been disabled for this channel.")
            else:
                await ctx.reply("Auto-translation was not enabled for this channel.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        guild_id = message.guild.id

        webhook_data = self.bot.db[str(guild_id)]["autotranslate"].find_one({"channel_id": channel_id})
        if not webhook_data:
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.popcat.xyz/translate?to=en&text={message.content}") as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    translation: Optional[str] = data.get('translated')
                    
                    if translation and translation.lower() != message.content.lower():
                        webhook = await self.bot.fetch_webhook(webhook_data["webhook_id"])
                        await message.delete()
                        await webhook.send(
                            content=translation,
                            username=message.author.display_name,
                            avatar_url=message.author.avatar.url if message.author.avatar else None
                        )



async def setup(
        bot: commands.Bot
) -> None:
    try:
        await bot.add_cog(Translate(bot))
        bot.logger.info("Translate cog loaded successfully")
    except Exception as e:
        error_message: str = f"Failed to add Translate cog: {str(e)}"
        bot.logger.error(f"{error_message}\n{traceback.format_exc()}")
