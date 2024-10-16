from __future__ import annotations

import os
import sys
import asyncio
import logging
import aiohttp
import discord
import datetime
import traceback

from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from collections import Counter
from discord.ext import commands
from db import db
from slash import *
from cogs.translate import translate_ctx_menu

EXTENSIONS: List[str] = [
    'cogs.translate',
    'cogs.interactions',
    'cogs.afk',
    'cogs.embed',
    'cogs.role',
    'cogs.welcomer',
    'cogs.news',
    'cogs.misc',
    'cogs.quiz',
    'cogs.fun',
    'cogs.anime',
    'cogs.help',
    'cogs.auto',
    'cogs.user',
    'cogs.snipe',
    'cogs.mod'
]

# Setup logging using discord's prebuilt logging
discord.utils.setup_logging()

class Bot(commands.AutoShardedBot):
    def __init__(self) -> None:
        allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
        intents: discord.Intents = discord.Intents.all()
        super().__init__(
            description='Just a Bot',
            command_prefix=['?'],
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.command_stats: Counter[str] = Counter()
        self.socket_stats: Counter[str] = Counter()
        self.command_types_used: Counter[discord.ChannelType] = Counter()
        self.logger: logging.Logger = logging.getLogger('bot')
        self.logger.info("Bot instance initialized successfully")

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        self.logger.info("aiohttp ClientSession created")
        
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                self.logger.info(f"Successfully loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f'Failed to load extension {extension}: {e}')
                traceback.print_exc()
        
        group_commands: List[commands.Group] = [
            BotGroup(name="bot", description="bot commands"),
            HolyGroup(name="holy", description="holy commands")
        ]

        for group in group_commands:
            try:
                self.tree.add_command(group)
                self.logger.info(f"Successfully added slash group: {group.name}")
            except Exception as e:
                self.logger.error(f'Failed to add slash group {group.name}: {e}')
        
        try:
            self.tree.context_menu(name='Translate')(translate_ctx_menu)
            self.logger.info("Successfully added Translate context menu")
        except Exception as e:
            self.logger.error(f'Failed to add context_menu: {e}')
        
        try:
            self.tree.command(name="interactions", description="interact with a discord user through GIFs")(interactioncmd)
            self.logger.info("Successfully added interactions and help slash commands")
        except Exception as e:
            self.logger.error(f'Failed to add slash command: {e}')
        
        await self.change_presence(status=discord.Status.dnd)
        self.logger.info("Bot presence changed to DND")
                

        
        self.logger.info("Finished the setup_hook function")

    async def on_ready(self) -> None:
        try:
            # only syncs in test guild for faster sync
            # will remove later when it's production ready
            guild: Optional[discord.Guild] = self.get_guild(1292422671480651856)
            if guild:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self.logger.info("Successfully synced commands to test guild")
        except Exception as e:
            self.logger.error(f'Failed to sync: {e}')
        self.logger.info(f'Bot ready: {self.user} (ID: {self.user.id})')

    async def on_command_completion(
        self, 
        context: commands.Context
    ) -> None:
        full_command_name: str = context.command.qualified_name
        split: List[str] = full_command_name.split(" ")
        executed_command: str = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )
    async def on_command_error(
        self, 
        context: commands.Context, 
        error: commands.CommandError
    ) -> None:

        if isinstance(error, commands.CommandNotFound):
            self.logger.warning(f"CommandNotFound error: {error}")
            return

        if isinstance(error, commands.MissingPermissions):
            embed: discord.Embed = discord.Embed(
                title="Missing Permissions",
                description=f"You are missing the permission(s) `{', '.join(error.missing_permissions)}` to execute this command!",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.BotMissingPermissions):
            embed: discord.Embed = discord.Embed(
                title="Bot Missing Permissions",
                description=f"I am missing the permission(s) `{', '.join(error.missing_permissions)}` to fully perform this command!",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)
       
        elif isinstance(error, commands.MissingRequiredArgument):
            command_name = context.command.qualified_name
            params = [f"<{param}>" for param in context.command.clean_params]
            usage = f"{self.command_prefix[0]}{command_name} {' '.join(params)}"
            
            missing_param = str(error.param)
            description = f"```\n{usage}\n```"
            
            embed: discord.Embed = discord.Embed(
                title="Missing Required Argument(s)",
                description=description,
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.BadArgument):
            embed: discord.Embed = discord.Embed(
                title="Invalid Argument",
                description=f"{str(error)}",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.MissingRole):
            embed: discord.Embed = discord.Embed(
                title="Missing Role",
                description=f"You are missing the required role to use this command.",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.MissingAnyRole):
            embed: discord.Embed = discord.Embed(
                title="Missing Any Role",
                description=f"You are missing one of the required roles to use this command.",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.NSFWChannelRequired):
            embed: discord.Embed = discord.Embed(
                title="NSFW Channel Required",
                description=f"This command can only be used in NSFW channels.",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)
        
        elif isinstance(error, commands.BadUnionArgument):
            embed: discord.Embed = discord.Embed(
                title="Invalid Argument",
                description=f"Could not parse argument: {str(error)}",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        elif isinstance(error, commands.BadLiteralArgument):
            embed: discord.Embed = discord.Embed(
                title="Invalid Option",
                description=f"Invalid option. Allowed values are: {', '.join(map(str, error.literals))}",
                color=discord.Color.dark_grey()
            )
            await context.reply(embed=embed)

        else:
            try:
                owner = await self.fetch_user(876869802948452372)
                
                embed = discord.Embed(
                    title="Bot Error",
                    description=f"An error occurred in the bot{'.' if not context else f': {context.command.brief}'}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.add_field(name="Error Type", value=type(error).__name__, inline=False)
                embed.add_field(name="Error Message", value=str(error), inline=False)
                
                if context.command:
                    embed.add_field(name="Command", value=context.command.name, inline=False)
                
                if context:
                    embed.add_field(name="User", value=f"{context.author.mention}", inline=True)
                    embed.add_field(name="Channel", value=f"{context.channel.mention}", inline=False)
                    embed.add_field(name="Guild", value=f"{context.guild.name}\n{context.guild.id}" if context.guild else "DM", inline=False)
        
                await owner.send(embed=embed)
            except Exception as e:
                print(f"Failed to send error message to owner: {e}")
        self.logger.warning(f"Command error handled: {type(error).__name__}")

    async def on_message(
        self, 
        message: discord.Message
    ) -> None:

        if message.author.bot:
            return
        
        ctx: commands.Context = await self.get_context(message)
        await self.invoke(ctx)

    async def process_commands(
        self, 
        message: discord.Message
    ) -> None:

        ctx: commands.Context = await self.get_context(message)
        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def on_command(
        self, 
        ctx: commands.Context
    ) -> None:

        self.command_stats[ctx.command.qualified_name] += 1
        message: discord.Message = ctx.message
        if isinstance(message.channel, discord.TextChannel):
            self.command_types_used[message.channel.type] += 1
        self.logger.info(f"Command '{ctx.command.qualified_name}' invoked")

    async def close(
        self
    ) -> None:
        await super().close()
        if self.session:
            await self.session.close()
        self.logger.info("Bot closed successfully")

    async def start(
        self
    ) -> None:
        load_dotenv()
        await super().start(os.getenv('TOKEN'))
        self.logger.info("Bot started successfully")
