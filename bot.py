import os
import discord 
from logger import log
from dotenv import load_dotenv
from discord.ext import commands 

from slash_groups.testing import TestingGroup
from slash_groups.bot_group import BotGroup
from slash_groups.mod_group import ModGroup
from slash_groups.user_group import UserGroup
from slash_groups.holy_group import HolyGroup
from slash_groups.anime_group import AnimeGroup


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
            command_prefix='!',
            description='A simplified version of RoboDanny bot.',
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
        )
    
    async def on_ready(self):
        log.info(f'Bot ready: {self.user} (ID: {self.user.id})')
        try: 
            
            # yes i like addibgn group commands manually... maybe i am psychopath
            self.tree.add_command(BotGroup(name="bot", description="bot commands"))
            self.tree.add_command(UserGroup(name="user", description="user commands"))
            self.tree.add_command(TestingGroup(name="test", description="test commands"))
            self.tree.add_command(ModGroup(name="moderation", description="moderation commands"))
            self.tree.add_command(HolyGroup(name="holy", description="holy commands"))
            self.tree.add_command(AnimeGroup(name="anime", description="anime commands"))
        
        except Exception as e:
            log.error(f'Failed to add command group: {e}')
        
        await self.change_presence(
            status=discord.Status.dnd
        )
        
        try:
            # only syncs in test guild for faster sync
            # will remove lator when its production ready
            guild = discord.Object(id=1281246026459644027)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("synced commands")
            
        except Exception as e:
            log.error(f'Failed to sync: {e}')
        log.info("Finished the on_ready function")


    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        
        # could make a better version for this... maybe an error handling class?
        
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.reply('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.reply(f'Error in command {ctx.command}: {error}')
        elif isinstance(error, commands.MissingPermissions):
            await ctx.author.send('Sorry, you do not have the required permissions to use this command.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply('This command requires a missing argument.')
        elif isinstance(error, commands.TooManyArguments):
            await ctx.reply('This command accepts too many arguments.')
        elif isinstance(error, commands.BadArgument):
            await ctx.reply('This command received an invalid argument.')
        
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self):
        await super().close()

    async def start(self):
        load_dotenv()
        await super().start(
            os.getenv('TOKEN')
        )
        


