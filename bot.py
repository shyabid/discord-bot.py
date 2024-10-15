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
    'cogs.snipe'
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

    async def setup_hook(
        self
    ) -> None:

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
            ModGroup(name="moderation", description="moderation commands"),
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
                description=f"You are missing the permission(s) `{', '.join(error.missing_permissions)}` to execute this command!",
                color=discord.Color.dark_grey()
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed: discord.Embed = discord.Embed(
                description=f"I am missing the permission(s) `{', '.join(error.missing_permissions)}` to fully perform this command!",
                color=discord.Color.dark_grey()
            )
            await context.send(embed=embed)

        elif isinstance(error, commands.MissingRequiredArgument):
            embed: discord.Embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=discord.Color.dark_grey()
            )
            await context.send(embed=embed)

        else:
            raise error

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
