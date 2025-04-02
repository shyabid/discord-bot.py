from discord.ext import commands
from discord import app_commands
import discord
import asyncio
from difflib import SequenceMatcher
import os 
from dotenv import load_dotenv
from db_manager import DBManager
from typing import Union, List, Optional
import traceback
import json
load_dotenv()

class Morgana(commands.AutoShardedBot):
    def __init__(self, plguins: list[commands.Cog] = None):
        super().__init__(
            command_prefix=self.get_prefix,
            description=os.getenv("description"),
            help_attrs=dict(hidden=True),
            chunk_guilds_at_startup=False,
            heartbeat_timeout=100.0,
            allowed_mentions=discord.AllowedMentions(
                roles=False, 
                everyone=False, 
                users=True
            ),
            intents=discord.Intents.all(),
            enable_debug_events=True,
            
        )
        self.db = DBManager()
        self.owner_id = 821755569248403487
        self.token = os.getenv("token")
        self.plugins = plguins
        self.status_messages = []
    
    async def get_prefix(
        self, 
        message: discord.Message
    ) -> List[str]:
        if not message.guild:
            return ["?"]
            
        return self.db.get_guild_prefixes(str(message.guild.id))
    
    async def setup_hook(self):
        for _ in self.plugins: await self.load_extension(_)
        
    async def on_ready(self):
        # for guild in self.guilds:
        #     self.tree.clear_commands(guild=guild)
        #     await self.tree.sync(guild=guild)
            
        #     self.tree.copy_global_to(guild=guild)
        await self.tree.sync()
        ...
    async def on_command_completion(
        self, 
        ctx: commands.Context
    ) -> None:
        self.db.count_up_command(ctx.command.qualified_name)
        ttl_cmd_use_cnt = self.db.get_command_usage(ctx.command.name)
    
    async def on_command_error(
        self, 
        context: commands.Context, 
        error: commands.CommandError
    ) -> None:
        if hasattr(context.command, 'on_error'): return
        if isinstance(error, commands.CommandNotFound):
            return


        elif isinstance(error, commands.CommandOnCooldown):
            await context.reply(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds")
        elif isinstance(error, commands.errors.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            await context.reply(f"You are missing `{', '.join(missing)}` permission(s) to execute this command!")
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            await context.reply(f"I am missing the permission(s) `{', '.join(missing)}` to fully perform this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await self._handle_missing_arg(context, error)
        elif isinstance(error, commands.BadArgument):
            await context.reply(f"{str(error)}")
        elif isinstance(error, commands.ArgumentParsingError):
            await context.reply(f"{error.argument if hasattr(error, 'argument') else str(error)}")
        elif isinstance(error, commands.MissingRole):
            await context.reply("You are missing the required role to use this command.")
        elif isinstance(error, commands.MissingAnyRole):
            await context.reply("You are missing one of the required roles to use this command.")
        elif isinstance(error, commands.NSFWChannelRequired):
            await context.reply("This command can only be used in NSFW channels.")
        elif isinstance(error, commands.BadUnionArgument):
            await context.reply(f"Could not parse argument '{error.param.name}'. Accepted types: {', '.join([t.__name__ for t in error.converters])}")
        elif isinstance(error, commands.BadLiteralArgument):
            await context.reply(f"Invalid option for '{error.param.name}'. Allowed values are: {', '.join(map(str, error.literals))}")
    
        
        else:
            try:
                owner = await self.fetch_user(821755569248403487)
                embed = discord.Embed(
                    title="Bot Error",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                
                embed.add_field(name="Error Details", value=str(error)[:1024], inline=False)
                
                tb_string = ''.join(traceback.format_tb(error.__traceback__))
                
                if context.command:
                    embed.add_field(name="Command", value=context.command.name, inline=True)
                
                if context:
                    embed.add_field(name="User", value=f"{context.author.mention}", inline=True)
                    embed.add_field(name="Channel", value=f"{context.channel.mention}", inline=True)
                    embed.add_field(name="Guild", value=f"{context.guild.name}\n{context.guild.id}" if context.guild else "DM", inline=True)
        
                await owner.send(embed=embed, content=f"```py\n{tb_string}\n```")
                await context.reply("An error occurred while executing the command. The developers have been notified.")
            except Exception as e: print(str(e))
            

    async def _handle_missing_arg(self, context, error):    
        command_name = context.command.qualified_name
        params = [f"`{param}`" for param in context.command.clean_params]
        prefixes = await self.get_prefix(context.message)
        usage = f"{prefixes[0]}{command_name} {' '.join(params)}"
        await context.reply(f"Missing required argument(s)\n> {usage}")
    
    async def close(
        self
    ) -> None:
        """Cleanup and close the bot."""
        await super().close()
        if hasattr(self, 'db'):
            self.db.close()

    def run(
        self
    ) -> None:
        """Start the bot."""
        super().run(os.getenv('TOKEN'))
