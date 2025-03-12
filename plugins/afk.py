import discord
from discord.ext import commands
from discord import app_commands
from utils import format_seconds
from datetime import datetime
import time
from typing import Optional
from bot import Morgana

class Afk(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: 
            return
            
        last_afk_message = self.bot.db.get_last_afk_message(message.author.id, message.guild.id)
        if last_afk_message and message.id == last_afk_message: return
        if message.content.startswith(f"{self.bot.command_prefix}afk"): return
        
        afk_data = self.bot.db.get_afk(message.author.id, message.guild.id)
        if afk_data:
            reason, since = afk_data
            time_diff = int(time.time() - float(since))
            formatted_time = format_seconds(time_diff)
            
            self.bot.db.remove_afk(message.author.id, message.guild.id)
            await message.channel.send(
                f"{message.author.mention}, welcome back! You were AFK for `{formatted_time}`"
            )
            
        for mention in message.mentions:
            afk_data = self.bot.db.get_afk(mention.id, message.guild.id)
            if afk_data:
                reason, since = afk_data
                await message.reply(
                    f"{mention.display_name} is AFK: {reason} (since <t:{int(since)}:R>)"
                )

    @commands.hybrid_command(
        name="afk",
        description="Set your status to AFK"
    )
    @app_commands.describe(reason="The reason for going AFK")
    async def set_afk(self, ctx: commands.Context, *, reason: Optional[str] = None) -> None:
        await ctx.defer()
        if not ctx.guild:
            return await ctx.reply("This command can only be used in a server.")

        reason = reason or "AFK"
        
        if self.bot.db.get_afk(ctx.author.id, ctx.guild.id):
            return await ctx.reply("You are already set as AFK.")
        
        self.bot.db.set_afk(ctx.author.id, ctx.guild.id, reason)
        self.bot.db.set_last_afk_message(ctx.author.id, ctx.guild.id, ctx.message.id)
        await ctx.reply(f"I've set your AFK: {reason}")

async def setup(bot: Morgana):
    await bot.add_cog(Afk(bot))
