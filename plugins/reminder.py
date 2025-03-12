from discord.ext import commands, tasks
import discord
import asyncio
from utils import parse_time_string, format_seconds
import time
from typing import Dict, Any, List, Optional

class Reminder(commands.Cog):
    """Set reminders for yourself."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_reminders.start()

    @tasks.loop(seconds=1)
    async def check_reminders(self):
        """Check for and send due reminders"""
        try:
            reminders = self.bot.db.get_pending_reminders()
            for reminder in reminders:
                reminder_id, user_id, guild_id, channel_id, message_id, message = reminder
                
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        try:
                            original_message = await channel.fetch_message(message_id)
                            message_link = original_message.jump_url
                        except:
                            message_link = None

                        view = discord.ui.View()
                        if message_link:
                            view.add_item(discord.ui.Button(label="Go to original message", url=message_link))
                            
                        time_str = f"<t:{int(time.time())}:R>"
                        message_content = f"<@{user_id}>, You set a reminder {time_str}:\n> **{message}**"
                        
                        await channel.send(message_content, view=view)
                    else:
                        user = self.bot.get_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="Reminder", 
                                description=message, 
                                color=discord.Color.dark_grey()
                            )
                            await user.send(embed=embed)
                except Exception as e:
                    print(f"Error sending reminder: {e}")
                finally:
                    self.bot.db.remove_reminder(reminder_id)
        except Exception as e:
            print(f"Error in reminder check loop: {e}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_group(
        name="reminder", 
        aliases=["rm", "remind", "remember"], 
        invoke_without_command=True
    )
    async def reminder(self, ctx: commands.Context, duration: str, *, message: str) -> None:
        """Set a reminder. Usage: ?rm <time> <message>"""
        seconds = parse_time_string(duration)
        if seconds <= 0:
            await ctx.reply("Please provide a valid time.")
            return

        reminder_time = int(time.time()) + seconds

        reminder_id = self.bot.db.add_reminder(
            ctx.author.id,
            ctx.guild.id,
            ctx.channel.id,
            ctx.message.id,
            message,
            reminder_time
        )
        
        await ctx.reply(
            f"Okay, I'll remind you about **'{message}'** "
            f"<t:{reminder_time}:R>."
        )

    @reminder.command(name="list")
    async def list_reminders(self, ctx: commands.Context) -> None:
        """List all your active reminders."""
        reminders = self.bot.db.get_user_reminders(ctx.author.id, ctx.guild.id)
        
        if not reminders:
            await ctx.reply("You don't have any active reminders.")
            return

        embed = discord.Embed(
            title="Your Active Reminders", 
            color=discord.Color.dark_grey()
        )
        
        current_time = int(time.time())
        for reminder_id, message, reminder_time, _, _ in reminders:
            time_left = reminder_time - current_time
            embed.add_field(
                name=format_seconds(time_left), 
                value=message, 
                inline=False
            )
            
        await ctx.reply(embed=embed)

    @reminder.command(name="clear")
    async def clear_reminders(self, ctx: commands.Context) -> None:
        """Clear all your active reminders."""
        count = self.bot.db.clear_user_reminders(ctx.author.id, ctx.guild.id)
        
        if count > 0:
            await ctx.reply(f"Cleared {count} reminder(s).")
        else:
            await ctx.reply("You don't have any active reminders to clear.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reminder(bot))
