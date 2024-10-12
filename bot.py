from __future__ import annotations

import os
import sys
import asyncio
import discord
import traceback
from discord.ext import commands
from typing import Optional
from collections import Counter
import datetime
import logging
import aiohttp
import asyncpg

from db import db
from slash_groups.testing import TestingGroup
from slash_groups.bot_group import BotGroup
from slash_groups.mod_group import ModGroup
from slash_groups.user_group import UserGroup
from slash_groups.holy_group import HolyGroup
from slash_groups.anime_group import AnimeGroup

from dotenv import load_dotenv

from cogs.translate import translate_ctx_menu
from slash_commands.help import helpcmd
from slash_commands.interactions import interactioncmd

# Setup logging using discord's prebuilt logging
discord.utils.setup_logging()

class Bot(commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
        intents = discord.Intents(
            guilds=True,
            members=True,
            messages=True,
            message_content=True,
        )
        super().__init__(
            command_prefix=["?"],
            description='Just a Bot',
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.command_stats = Counter()
        self.socket_stats = Counter()
        self.command_types_used = Counter()
        self.logger = logging.getLogger('bot')

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        
        try:
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            print('Connected to the database')
        except Exception as e:
            print(f'Could not connect to database: {e}')
            traceback.print_exc()

    async def on_ready(self):
        self.remove_command('help')
        print(f'Bot ready: {self.user} (ID: {self.user.id})')
        
        for extension in [
            'cogs.translate',
            'cogs.interactions',
            'cogs.afk',
            'cogs.ban',
            'cogs.embed',
            'cogs.role'
        ]:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}: {e}')
                traceback.print_exc()
        
        # yes i like adding group commands manually... maybe i am psychopath
        group_commands = [
            BotGroup(name="bot", description="bot commands"),
            UserGroup(name="user", description="user commands"),
            TestingGroup(name="test", description="test commands"),
            ModGroup(name="moderation", description="moderation commands"),
            HolyGroup(name="holy", description="holy commands"),
            AnimeGroup(name="anime", description="anime commands")
        ]

        for group in group_commands:
            try:
                self.tree.add_command(group)
            except Exception as e:
                print(f'Failed to add slash group {group.name}: {e}')
        
        try:
            self.tree.context_menu(name='Translate')(translate_ctx_menu)
        except Exception as e:
            print(f'Failed to add context_menu: {e}')
        
        try:
            self.tree.command(name="interactions", description="interact with a discord user through GIFs")(interactioncmd)
            self.tree.command(name="help", description="Check the bot's latency")(helpcmd)
        except Exception as e:
            print(f'Failed to add slash command: {e}')
        
        await self.change_presence(status=discord.Status.dnd)
                
        try:
            # only syncs in test guild for faster sync
            # will remove later when it's production ready
            guild = self.get_guild(1292422671480651856)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("synced commands")

        except Exception as e:
            print(f'Failed to sync: {e}')
        print("Finished the on_ready function")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.reply('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}', file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.reply(str(error))
        
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        ctx = await self.get_context(message)
        await self.invoke(ctx)

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message)

        if ctx.command is None:
            return

        await self.invoke(ctx)

    async def on_command(self, ctx: commands.Context):
        self.command_stats[ctx.command.qualified_name] += 1
        message = ctx.message
        if isinstance(message.channel, discord.TextChannel):
            self.command_types_used[message.channel.type] += 1

    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()

    async def start(self):
        load_dotenv()
        await super().start(os.getenv('TOKEN'))
