from discord.ext import commands
import discord
import asyncio
from utils import parse_time_string, format_seconds
import time
from typing import Dict, Any, List, Optional

class Reminder(commands.Cog):
    """Set reminders for yourself."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.hybrid_group(
        name="reminder", 
        aliases=["rm", "remind"], 
        invoke_without_command=True
    )
    async def reminder(
        self, 
        ctx: commands.Context, 
        duration: str, 
        *, 
        message: str
    ) -> None:
        """Set a reminder. Usage: ?rm <time> <message>"""
        seconds: int = parse_time_string(duration)
        if seconds <= 0:
            await ctx.reply("Please provide a valid time.")
            return

        guild_id: str = str(ctx.guild.id)
        user_id: str = str(ctx.author.id)
        reminder_time: int = int(time.time()) + seconds

        reminder: Dict[str, Any] = {
            "user_id": user_id,
            "message": message,
            "time": reminder_time,
            "channel_id": ctx.channel.id,
            "message_id": ctx.message.id
        }

        self.bot.db[guild_id]["reminders"].insert_one(reminder)
        
        await ctx.reply(
            f"Okay, I'll remind you about **'{message}'** "
            f"<t:{int(time.time()) + seconds}:R>."
        )
        
        await asyncio.sleep(seconds)
        
        original_message: discord.Message = await ctx.fetch_message(
            ctx.message.id
        )
        message_link: str = original_message.jump_url

        embed: discord.Embed = discord.Embed(
            title="Reminder", 
            description=message, 
            color=discord.Color.dark_grey()
        )
        embed.add_field(
            name="Original Message", 
            value=f"[Click here]({message_link})"
        )
        
        channel = self.bot.get_channel(ctx.channel.id)
        if channel:
            await channel.send(f"{ctx.author.mention}", embed=embed)
        else:
            await ctx.author.send(embed=embed)

        self.bot.db[guild_id]["reminders"].delete_one(
            {"user_id": user_id, "time": reminder_time}
        )

    @reminder.command(name="list")
    async def list_reminders(self, ctx: commands.Context) -> None:
        """List all your active reminders."""
        guild_id: str = str(ctx.guild.id)
        user_id: str = str(ctx.author.id)
        
        reminders: List[Dict[str, Any]] = list(
            self.bot.db[guild_id]["reminders"].find({"user_id": user_id})
        )
        
        if not reminders:
            await ctx.reply("You don't have any active reminders.")
            return

        embed: discord.Embed = discord.Embed(
            title="Your Active Reminders", 
            color=discord.Color.dark_grey()
        )
        for reminder in reminders:
            time_left: int = reminder["time"] - int(time.time())
            embed.add_field(
                name=format_seconds(time_left), 
                value=reminder["message"], 
                inline=False
            )
        await ctx.reply(embed=embed)

    @reminder.command(name="clear")
    async def clear_reminders(self, ctx: commands.Context) -> None:
        """Clear all your active reminders."""
        guild_id: str = str(ctx.guild.id)
        user_id: str = str(ctx.author.id)
        
        result: Any = self.bot.db[guild_id]["reminders"].delete_many(
            {"user_id": user_id}
        )
        
        if result.deleted_count > 0:
            await ctx.reply(f"Cleared {result.deleted_count} reminder(s).")
        else:
            await ctx.reply("You don't have any active reminders to clear.")


    @commands.command()
    async def test(self, ctx: commands.Context):
        ctx.author.history

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reminder(bot))
