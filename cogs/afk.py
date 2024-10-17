import discord
from discord.ext import commands
from discord import app_commands
from utils import format_seconds
from datetime import datetime, timezone
from typing import Optional
import calendar
import time

class Afk(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: 
            return
        if message.content.startswith("?afk"): 
            return
        
        afk_data = self.bot.db[str(message.guild.id)]["afks"].find_one({"userid": message.author.id})
        
        if afk_data:
            try: 
                self.bot.db[str(message.guild.id)]["afks"].delete_one({"userid": message.author.id})
                time_then = round(afk_data['since'])
                time_now = round(time.time())
                timediff = time_now - time_then
                formated_time = format_seconds(timediff)
                await message.channel.send(f"{message.author.mention}, your AFK has been removed. You were away for `{formated_time}`")
            
            except Exception as e:
                print(f"An error occurred while removing AFK: {str(e)}")

        for mention in message.mentions:
            afk_user_data = self.bot.db[str(message.guild.id)]["afks"].find_one({"userid": mention.id})
            
            if afk_user_data:
                try:
                    embed = discord.Embed(
                        description=f"that user went AFK <t:{round(afk_user_data['since'])}:R> with reason: `{afk_user_data['reason']}`",
                        color=discord.Color.dark_grey()
                    )
                    await message.reply(embed=embed)
                except Exception as e:
                    print(f"An error occurred while sending AFK message: {str(e)}")

        
    @commands.hybrid_command(
        name="afk",
        description="Set your status to AFK"
    )
    async def set_afk(self, ctx: commands.Context, *, reason: Optional[str] = None) -> None:
        """
        Set your status to AFK with an optional reason.

        **Usage:**
        ?afk [reason]
        /afk [reason]

        **Parameters:**
        reason (str, optional): The reason for going AFK. If not provided, a default reason will be used.

        **Example:**
        ?afk Going to sleep
        ?afk
        /afk Busy with work
        /afk
        """
        reason = reason or "I'm AFK :)"
        if not ctx.guild:
            return await ctx.reply("This command can only be used in a server.")

        try:
            existing_afk = self.bot.db[str(ctx.guild.id)]["afks"].find_one({"userid": ctx.author.id})
            if existing_afk:
                await ctx.reply("You are already set as AFK.")
                return
            
            self.bot.db[str(ctx.guild.id)]["afks"].insert_one({
                "userid": ctx.author.id,
                "reason": reason,
                "since": time.time()
            })
            await ctx.reply(f"Your AFK has been set to: {reason}")
            
        except Exception as e:
            await ctx.reply(f"An error occurred while setting AFK: {str(e)}")
            
async def setup(bot):
    await bot.add_cog(Afk(bot))