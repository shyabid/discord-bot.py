from discord.ext import commands
from discord import app_commands
import discord
import os
import re
from typing import Optional, Literal, List

class Auto(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot: return
        if not message.guild: return

        content = message.content.lower()
        guild_id = message.guild.id

        for emojis in self.bot.db.get_matching_reactions(guild_id, content):
            for emoji in emojis:
                try: await message.add_reaction(emoji)
                except discord.errors.HTTPException:
                    custom_emoji = discord.utils.get(message.guild.emojis, name=emoji.strip(':'))
                    if custom_emoji: await message.add_reaction(custom_emoji)

        for response in self.bot.db.get_matching_responses(guild_id, content):
            await message.channel.send(response)

    def is_emoji(self, s: str) -> bool:
        return s.startswith(':') and s.endswith(':') or len(s) == 1

    @commands.hybrid_group(
        name="autoreact", 
        description="Manage auto-reactions"
    )
    @commands.has_permissions(manage_guild=True)
    async def autoreact(self, ctx: commands.Context) -> None:
        """Configure automated emoji reactions for specified trigger words or phrases. 
        Provides comprehensive management of reaction triggers using pattern matching."""
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Avaliable subcommands: `create`, `delete`, `list`")
        
    @autoreact.command(
        name="create", 
        description="Create a new auto-reaction"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        type="The type of trigger",
        trigger_emojis="The trigger and emojis to react with, separated by a ` | `"
    )
    async def react_create(
        self, 
        ctx: commands.Context, 
        type: Optional[Literal["startswith", "contains", "exact", "endswith"]] = "contains", 
        *, 
        trigger_emojis: str
    ) -> None:
        """Establish a new automated emoji reaction trigger. Supports multiple emojis and pattern matching types.
        Accepts standard Unicode emojis and custom server emojis. Format: trigger | emoji1 emoji2"""
        if '|' not in trigger_emojis:
            raise commands.BadArgument("Please separate the trigger and emojis with a ` | `.")

        trigger_part, emojis_part = map(str.strip, trigger_emojis.split('|', 1))
        
        trigger = trigger_part.strip('"')
        emoji_list = emojis_part.strip('"').split()
        
        if not all(self.is_emoji(emoji) or emoji.encode('utf-8').decode('utf-8') == emoji for emoji in emoji_list):
            raise commands.BadArgument("Please provide valid emoji(s).")
        
        self.bot.db.add_auto_reaction(ctx.guild.id, trigger, emoji_list, type)
        await ctx.reply(f"Auto-reaction created for trigger: `{trigger}`")

    @autoreact.command(
        name="delete", 
        description="Delete an auto-reaction"
    )
    @app_commands.describe(
        trigger="The trigger to delete"
    )
    @commands.has_permissions(manage_guild=True)
    async def react_delete(
        self, 
        ctx: commands.Context, 
        *, 
        trigger: str
    ) -> None:
        """Remove an existing automated reaction trigger from the server configuration.
        Requires exact trigger phrase match for deletion."""
        if self.bot.db.remove_auto_reaction(ctx.guild.id, trigger):
            await ctx.reply(f"Auto-reaction deleted for trigger: `{trigger}`")
        else:
            await ctx.reply(f"No auto-reaction found for trigger: `{trigger}`")

    @autoreact.command(
        name="list", 
        description="List all auto-reactions"
    )
    @commands.has_permissions(manage_guild=True)
    async def react_list(self, ctx: commands.Context) -> None:
        """Display all configured auto-reaction triggers for the server.
        Presents triggers in an organized embed format for easy viewing."""
        reactions = self.bot.db.get_auto_reactions(ctx.guild.id)
        if reactions:

            description = ""
            for trigger, type_, emojis in reactions:
                description + f"`{trigger}`, "
            
            embed = discord.Embed(
                title="Auto-reactions",
                description=description,
                color=discord.Color.dark_grey()
            )
        
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("No auto-reactions set up.")

    @commands.hybrid_group(
        name="autoreply", 
        description="Manage auto-responses",
        aliases=["ar"]
    )
    @commands.has_permissions(manage_guild=True)
    async def autoreply(self, ctx: commands.Context) -> None:
        """Configure automated message responses for specified trigger words or phrases.
        Provides comprehensive management of response triggers using pattern matching."""
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Avaliable subcommands: `create`, `delete`, `list`")
            

    @autoreply.command(
        name="create", 
        description="Create a new auto-response"
    )
    @app_commands.describe(
        type="The type of trigger",
        trigger_reply="The trigger and reply, separated by a ` | `"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_create(
        self, 
        ctx: commands.Context, 
        type: Optional[Literal["startswith", "contains", "exact", "endswith"]] = "contains", 
        *, 
        trigger_reply: str
    ) -> None:
        """Establish a new automated message response trigger. Supports multiple response types
        and pattern matching configurations. Format: trigger | response message"""
        if '|' not in trigger_reply:
            raise commands.BadArgument("Please separate the trigger and reply with a ` | `.")
        
        trigger_part, reply_part = map(str.strip, trigger_reply.split('|', 1))
        
        trigger = trigger_part.strip('"')
        
        if not trigger or not reply_part:
            await ctx.reply("Both trigger and reply must not be empty.")
            return
        
        self.bot.db.add_auto_response(ctx.guild.id, trigger, reply_part, type)
        await ctx.reply(f"Auto-response created for trigger: `{trigger}`")

    @autoreply.command(
        name="delete", 
        description="Delete an auto-response"
    )
    @app_commands.describe(
        trigger="The trigger to delete"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_delete(
        self, 
        ctx: commands.Context, 
        *, 
        trigger: str
    ) -> None:
        """Remove an existing automated response trigger from the server configuration.
        Requires exact trigger phrase match for deletion."""
        if self.bot.db.remove_auto_response(ctx.guild.id, trigger):
            await ctx.reply(f"Auto-response deleted for trigger: `{trigger}`")
        else:
            await ctx.reply(f"No auto-response found for trigger: `{trigger}`")

    @autoreply.command(
        name="list", 
        description="List all auto-responses"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_list(self, ctx: commands.Context) -> None:
        """Display all configured auto-response triggers for the server.
        Presents triggers in an organized embed format for easy viewing."""
        responses = self.bot.db.get_auto_responses(ctx.guild.id)
        if responses:
            
            description = ""
            for trigger, type_, response in responses:
                description + f"`{trigger}`, "
            
            embed = discord.Embed(
                title="Auto-responses",
                description=description,
                color=discord.Color.dark_grey()
            )
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("No auto-responses set up.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Auto(bot))
