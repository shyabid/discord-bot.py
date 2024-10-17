from discord.ext import commands
import discord
import os
import re
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Literal
)

class Auto(commands.Cog):
    def __init__(
        self, 
        bot: commands.Bot
    ) -> None:
        self.bot: commands.Bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        guild_id: str = str(message.guild.id)
        content: str = message.content.lower()

        loop = self.bot.loop

        # Auto-reaction
        autoreact_data: Dict[str, Any] = await loop.run_in_executor(
            None, lambda: self.bot.db[guild_id]["autoreact"].find_one() or {}
        )
        for trigger, data in autoreact_data.items():
            if isinstance(data, dict) and 'emojis' in data and 'type' in data:
                if self.check_trigger(content, trigger, data['type']):
                    for emoji in data['emojis']:
                        try:
                            await message.add_reaction(emoji)
                        except discord.errors.HTTPException:
                            custom_emoji: Optional[discord.Emoji] = discord.utils.get(
                                message.guild.emojis, 
                                name=emoji.strip(':')
                            )
                            if custom_emoji:
                                await message.add_reaction(custom_emoji)

        # Auto-respond
        autorespond_data: Dict[str, Any] = await loop.run_in_executor(
            None, lambda: self.bot.db[guild_id]["autorespond"].find_one() or {}
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

    @commands.hybrid_group(
        name="autoreact", 
        description="Manage auto-reactions",
    )
    @commands.has_permissions(manage_guild=True)
    async def autoreact(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            create_aliases = ["create", "add", "make", "+", "c", "mk"]
            delete_aliases = ["del", "delete", "rm", "-", "remove"]
            list_aliases = ["list", "ls", "show", "-c"]
            
            args = ctx.message.content.split()[1:]
            action = args[0].lower() if args else "create"
            
            if action in create_aliases or action not in (delete_aliases + list_aliases):
                subcommand = self.react_create
                if action in create_aliases:
                    args = args[1:]
            elif action in delete_aliases:
                subcommand = self.react_delete
                args = args[1:]  
            elif action in list_aliases:
                subcommand = self.react_list
                args = args[1:]
            else:
                await ctx.send("Invalid subcommand. Use `?help autoreact` for more information.")
                return

            if subcommand == self.react_create:
                trigger_types = ["startswith", "contains", "exact", "endswith"]
                trigger_type = next((arg for arg in args if arg in trigger_types), "contains")
                if trigger_type in args:
                    args.remove(trigger_type)
                
                trigger_response = " ".join(args)
                if "|" in trigger_response:
                    await subcommand(ctx, trigger_reply=trigger_response, type=trigger_type)
                else:
                    raise commands.BadArgument("Please seperate the trigger and response with a ` | `")
                    return
            elif subcommand == self.react_delete:

                trigger = " ".join(args)
                await subcommand(ctx, trigger=trigger)
            else:
                await subcommand(ctx)

    @commands.hybrid_group(
        name="autoreply", 
        description="Manage auto-responses",
        aliases=["ar"]
    )
    @commands.has_permissions(manage_guild=True)
    async def autoreply(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            create_aliases = ["create", "add", "make", "+", "c", "mk"]
            delete_aliases = ["del", "delete", "rm", "-", "remove"]
            list_aliases = ["list", "ls", "show", "-c"]
            
            args = ctx.message.content.split()[1:]
            action = args[0].lower() if args else "create"
            
            if action in create_aliases or action not in (delete_aliases + list_aliases):
                subcommand = self.reply_create
                if action in create_aliases:
                    args = args[1:]
            elif action in delete_aliases:
                subcommand = self.reply_delete
                args = args[1:] 
            elif action in list_aliases:
                subcommand = self.reply_list
                args = args[1:] 
            else:
                await ctx.send("Invalid subcommand. Use `?help autoreply` for more information.")
                return

            if subcommand == self.reply_create:
                trigger_types = ["startswith", "contains", "exact", "endswith"]
                trigger_type = next((arg for arg in args if arg in trigger_types), "contains")
                if trigger_type in args:
                    args.remove(trigger_type)
                
                trigger_response = " ".join(args)
                if "|" in trigger_response:
                    await subcommand(ctx, trigger_reply=trigger_response, type=trigger_type)
                else:
                    raise commands.BadArgument("Please seperate the trigger and response with a ` | `")
                    return
            elif subcommand == self.reply_delete:
                trigger = " ".join(args)
                await subcommand(ctx, trigger=trigger)
            else:
                await subcommand(ctx)

            
    @autoreact.command(
        name="create", 
        description="Create a new auto-reaction"
    )
    @commands.has_permissions(manage_guild=True)
    async def react_create(
        self, 
        ctx: commands.Context, 
        type: Optional[Literal["startswith", "contains", "exact", "endswith"]] = "contains", 
        *, 
        trigger_emojis: str
    ) -> None:
        """
        Create a new auto-reaction.

        **Examples:**
        ?autoreact create hello there | :smile: :wave:
        ?autoreact create startswith "hello there" | :smile: :wave:
        ?autoreact create contains hello there | ":smile: :wave:"
        """
        guild_id: str = str(ctx.guild.id)
        autoreact_data: Dict[str, Any] = (
            self.bot.db[guild_id]["autoreact"].find_one() or {}
        )
        
        if '|' not in trigger_emojis:
            raise commands.BadArgument("Please separate the trigger and emojis with a ` | `.")

        
        trigger_part, emojis_part = map(str.strip, trigger_emojis.split('|', 1))
        
        # Handle triggers with or without quotes
        if trigger_part.startswith('"') and trigger_part.endswith('"'):
            trigger = trigger_part[1:-1]
        else:
            trigger = trigger_part
        
        # Split emojis by space
        emoji_list: List[str] = emojis_part.strip('"').split()
        
        autoreact_data[trigger.lower()] = {
            "emojis": emoji_list, 
            "type": type
        }
        self.bot.db[guild_id]["autoreact"].update_one(
            {}, 
            {"$set": autoreact_data}, 
            upsert=True
        )
        await ctx.send(f"Auto-reaction created for trigger: `{trigger}`")

    @autoreact.command(
        name="delete", 
        description="Delete an auto-reaction"
    )
    @commands.has_permissions(manage_guild=True)
    async def react_delete(
        self, 
        ctx: commands.Context, 
        trigger: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autoreact_doc = self.bot.db[guild_id]["autoreact"].find_one()
        
        if not autoreact_doc:
            await ctx.send("No auto-reactions set up.")
            return

        autoreact_data: Dict[str, Any] = autoreact_doc

        for stored_trigger, reaction_data in autoreact_data.items():
            if stored_trigger != "_id":  
                if (
                    (reaction_data['type'] == 'startswith' and stored_trigger.startswith(trigger.lower())) or
                    (reaction_data['type'] == 'contains' and trigger.lower() in stored_trigger) or
                    (reaction_data['type'] == 'exact' and trigger.lower() == stored_trigger) or
                    (reaction_data['type'] == 'endswith' and stored_trigger.endswith(trigger.lower()))
                ):
                    del autoreact_data[stored_trigger]
                    self.bot.db[guild_id]["autoreact"].update_one(
                        {"_id": autoreact_doc["_id"]}, 
                        {"$unset": {stored_trigger: ""}}, 
                        upsert=True
                    )
                    await ctx.send(f"Auto-reaction deleted for trigger: `{stored_trigger}`")
                    return

        await ctx.send(f"No auto-reaction found for trigger: `{trigger}`")


    @autoreact.command(
        name="list", 
        description="List all auto-reactions"
    )
    @commands.has_permissions(manage_guild=True)
    async def react_list(self, ctx: commands.Context) -> None:
        guild_id: str = str(ctx.guild.id)
        autoreact_data: Dict[str, Any] = (
            self.bot.db[guild_id]["autoreact"].find_one() or {}
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

    @autoreply.command(
        name="create", 
        description="Create a new auto-response"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_create(
        self, 
        ctx: commands.Context, 
        type: Optional[Literal["startswith", "contains", "exact", "endswith"]] = "contains", 
        *, 
        trigger_reply: str
    ) -> None:
        """
        Create a new auto-response.

        **Examples:**
        ?autoreply create hello there | welcome to the server please check out the rules
        ?autoreply create startswith "hello there" | Welcome to the server please check out the rules
        ?autoreply create exact hello | Welcome exactly to the server!
        ?autoreply create endswith goodbye | Farewell message
        """
        guild_id: str = str(ctx.guild.id)
        autorespond_data: Dict[str, Any] = (
            self.bot.db[guild_id]["autorespond"].find_one() or {}
        )
        
        if '|' not in trigger_reply:
            raise commands.BadArgument("Please separate the trigger and reply with a ` | `.")
        
        trigger_part, reply_part = map(str.strip, trigger_reply.split('|', 1))
        
        # Handle triggers with or without quotes
        if trigger_part.startswith('"') and trigger_part.endswith('"'):
            trigger = trigger_part[1:-1]
        else:
            trigger = trigger_part
        
        if not trigger:
            await ctx.send("Trigger cannot be empty.")
            return
        if not reply_part:
            await ctx.send("Reply cannot be empty.")
            return
        
        autorespond_data[trigger.lower()] = {
            "reply": reply_part, 
            "type": type
        }
        self.bot.db[guild_id]["autorespond"].update_one(
            {}, 
            {"$set": autorespond_data}, 
            upsert=True
        )
        await ctx.send(f"Auto-response created for trigger: `{trigger}`")
    
    
    
    @autoreply.command(
        name="delete", 
        description="Delete an auto-response"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_delete(
        self, 
        ctx: commands.Context, 
        trigger: str
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        autorespond_doc = self.bot.db[guild_id]["autorespond"].find_one()
        
        if not autorespond_doc:
            await ctx.send("No auto-responses set up.")
            return

        autorespond_data: Dict[str, Any] = autorespond_doc

        for stored_trigger, response_data in autorespond_data.items():
            if stored_trigger != "_id":  
                if (
                    (response_data['type'] == 'startswith' and stored_trigger.startswith(trigger.lower())) or
                    (response_data['type'] == 'contains' and trigger.lower() in stored_trigger) or
                    (response_data['type'] == 'exact' and trigger.lower() == stored_trigger) or
                    (response_data['type'] == 'endswith' and stored_trigger.endswith(trigger.lower()))
                ):
                    del autorespond_data[stored_trigger]
                    self.bot.db[guild_id]["autorespond"].update_one(
                        {"_id": autorespond_doc["_id"]}, 
                        {"$unset": {stored_trigger: ""}}, 
                        upsert=True
                    )
                    await ctx.send(f"Auto-response deleted for trigger: `{stored_trigger}`")
                    return

        await ctx.send(f"No auto-response found for trigger: `{trigger}`")

    @autoreply.command(
        name="list", 
        description="List all auto-responses"
    )
    @commands.has_permissions(manage_guild=True)
    async def reply_list(self, ctx: commands.Context) -> None:
        guild_id: str = str(ctx.guild.id)
        autorespond_data: Dict[str, Any] = (
            self.bot.db[guild_id]["autorespond"].find_one() or {}
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


async def setup(
    bot: commands.Bot
) -> None:
    await bot.add_cog(Auto(bot))
