from discord.ext import commands
import discord
from discord import app_commands
import asyncio
from typing import List, Optional, Tuple
import traceback

def to_emoji(c: int) -> str:
    return chr(0x1f1e6 + c)

class Poll(commands.Cog):
    """Create and manage polls"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot


    @commands.hybrid_command(
        name="poll",
        description="Create a quick poll with predefined options."
    )
    @app_commands.describe(
        question="The poll question",
    )
    async def poll(self, ctx: commands.Context, *, question: str) -> None:
        embed = discord.Embed(
            title=ctx.author.display_name + " asks:",
            description=question,
            color=discord.Color.dark_grey()
        )
        msg = await ctx.reply(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Poll(bot))