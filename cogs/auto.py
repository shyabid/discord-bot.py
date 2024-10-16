from discord.ext import commands
import discord
from db import db
import os
import re
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Literal
)
from urllib.parse import urlparse

class Auto(commands.Cog):
    def __init__(
        self, 
        bot: commands.Bot
    ) -> None:
        self.bot: commands.Bot = bot

    @commands.hybrid_group(
        name="auto", 
        description="Manage auto-reactions and auto-responses"
    )
    @commands.has_permissions(manage_guild=True)
    async def auto(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Please specify a subcommand. Use `?help auto` for more information."
            )

    @auto.group(
        name="reaction", 
        description="Manage auto-reactions"
    )
    @commands.has_permissions(manage_guild=True)
    async def auto_reaction(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Please specify a subcommand. Use `?help auto reaction` for more information."
            )

    @auto.group(
        name="respond", 
        description="Manage auto-responses"
    )
    @commands.has_permissions(manage_guild=True)
    async def auto_respond(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Please specify a subcommand. Use `?help auto respond` for more information."
            )
    
    @auto_reaction.command(
        name="create", 
        description="Create a new auto-reaction"
    )
    @commands.has_permissions(manage_guild=True)
    async def reaction_create(
        self, 
        ctx: commands.Context, 
        type: Literal["startswith", "contains", "exact", "endswith"], 
        trigger: str, 
        emojis: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autoreact_data: Dict[str, Any] = (
            db[guild_id]["autoreact"].find_one() or {}
        )
        
        if trigger.startswith('"') and trigger.endswith('"'):
            trigger = trigger[1:-1] 
        elif ' ' in trigger:
            await ctx.send(
                "Trigger must be one word unless enclosed in quotes."
            )
            return
        
        emoji_list: List[str] = emojis.split()
        autoreact_data[trigger] = {
            "emojis": emoji_list, 
            "type": type
        }
        db[guild_id]["autoreact"].update_one(
            {}, 
            {"$set": autoreact_data}, 
            upsert=True
        )
        await ctx.send(f"Auto-reaction created for trigger: {trigger}")

    @auto_respond.command(
        name="create", 
        description="Create a new auto-response"
    )
    @commands.has_permissions(manage_guild=True)
    async def respond_create(
        self, 
        ctx: commands.Context, 
        type: Literal["startswith", "contains", "exact", "endswith"], 
        trigger: str, 
        reply: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autorespond_data: Dict[str, Any] = (
            db[guild_id]["autorespond"].find_one() or {}
        )
        
        if trigger.startswith('"') and trigger.endswith('"'):
            trigger = trigger[1:-1]  
        elif ' ' in trigger:
            await ctx.send(
                "Trigger must be one word unless enclosed in quotes."
            )
            return
        
        autorespond_data[trigger] = {
            "reply": reply, 
            "type": type
        }
        db[guild_id]["autorespond"].update_one(
            {}, 
            {"$set": autorespond_data}, 
            upsert=True
        )
        await ctx.send(f"Auto-response created for trigger: {trigger}")

    @auto_reaction.command(
        name="delete", 
        description="Delete an auto-reaction"
    )
    @commands.has_permissions(manage_guild=True)
    async def reaction_delete(
        self, 
        ctx: commands.Context, 
        trigger: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autoreact_data: Dict[str, Any] = (
            db[guild_id]["autoreact"].find_one() or {}
        )
        if trigger in autoreact_data:
            del autoreact_data[trigger]
            db[guild_id]["autoreact"].update_one(
                {}, 
                {"$set": autoreact_data}, 
                upsert=True
            )
            await ctx.send(f"Auto-reaction deleted for trigger: {trigger}")
        else:
            await ctx.send(f"No auto-reaction found for trigger: {trigger}")

    @auto_respond.command(
        name="delete", 
        description="Delete an auto-response"
    )
    @commands.has_permissions(manage_guild=True)
    async def respond_delete(
        self, 
        ctx: commands.Context, 
        trigger: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autorespond_data: Dict[str, Any] = (
            db[guild_id]["autorespond"].find_one() or {}
        )
        if trigger in autorespond_data:
            del autorespond_data[trigger]
            db[guild_id]["autorespond"].update_one(
                {}, 
                {"$set": autorespond_data}, 
                upsert=True
            )
            await ctx.send(f"Auto-response deleted for trigger: {trigger}")
        else:
            await ctx.send(f"No auto-response found for trigger: {trigger}")

    @auto_reaction.command(
        name="list", 
        description="List all auto-reactions"
    )
    @commands.has_permissions(manage_guild=True)
    async def reaction_list(self, ctx: commands.Context) -> None:
        guild_id: str = str(ctx.guild.id)
        autoreact_data: Dict[str, Any] = (
            db[guild_id]["autoreact"].find_one() or {}
        )
        if autoreact_data:
            trigger_list: List[str] = [
                f"`{trigger}`" for trigger in autoreact_data.keys()
            ]
            formatted_triggers: str = ", ".join(trigger_list)
            embed: discord.Embed = discord.Embed(
                title="Auto-reactions",
                description=formatted_triggers,
                color=discord.Color.dark_grey()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No auto-reactions set up.")

    @auto_respond.command(
        name="list", 
        description="List all auto-responses"
    )
    @commands.has_permissions(manage_guild=True)
    async def respond_list(self, ctx: commands.Context) -> None:
        guild_id: str = str(ctx.guild.id)
        autorespond_data: Dict[str, Any] = (
            db[guild_id]["autorespond"].find_one() or {}
        )
        if autorespond_data:
            trigger_list: List[str] = [
                f"`{trigger}`" for trigger in autorespond_data.keys()
            ]
            formatted_triggers: str = ", ".join(trigger_list)
            embed: discord.Embed = discord.Embed(
                title="Auto-responses",
                description=formatted_triggers,
                color=discord.Color.dark_grey()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No auto-responses set up.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        guild_id: str = str(message.guild.id)
        content: str = message.content.lower()
        # Auto-reaction
        autoreact_data: Dict[str, Any] = (
            db[guild_id]["autoreact"].find_one() or {}
        )
        for trigger, data in autoreact_data.items():
            if isinstance(data, dict) and 'emojis' in data and 'type' in data:
                if self.check_trigger(content, trigger, data['type']):
                    for emoji in data['emojis']:
                        try:
                            await message.add_reaction(emoji)
                        except discord.errors.HTTPException:
                            custom_emoji: Optional[discord.Emoji] = (
                                discord.utils.get(
                                    message.guild.emojis, 
                                    name=emoji.strip(':')
                                )
                            )
                            if custom_emoji:
                                await message.add_reaction(custom_emoji)

        autorespond_data: Dict[str, Any] = (
            db[guild_id]["autorespond"].find_one() or {}
        )
        for trigger, data in autorespond_data.items():
            if isinstance(data, dict) and 'reply' in data and 'type' in data:
                if self.check_trigger(content, trigger, data['type']):
                    await message.channel.send(data['reply'])

    def check_trigger(
        self, 
        content: str, 
        trigger: str, 
        trigger_type: str
    ) -> bool:
        if trigger_type == "startswith":
            return content.startswith(trigger.lower())
        elif trigger_type == "contains":
            return trigger.lower() in content
        elif trigger_type == "exact":
            return content == trigger.lower()
        elif trigger_type == "endswith":
            return content.endswith(trigger.lower())
        return False
    
    def is_emoji(self, s: str) -> bool:
        return s.startswith(':') and s.endswith(':') or len(s) == 1

    def get_missing_param(
        self, 
        action: str, 
        args: List[str]
    ) -> str:
        if action in ["create", "add", "make", "+", "c", "mk"]:
            if len(args) == 0:
                return "trigger"
            elif len(args) == 1:
                return "response or emoji"
        elif action in ["del", "delete", "rm", "-", "remove"]:
            if len(args) == 0:
                return "trigger"
        return "None"

async def setup(
    bot: commands.Bot
) -> None:
    await bot.add_cog(Auto(bot))
