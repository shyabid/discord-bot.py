from discord.ext import commands
import discord
from bot import Morgana
from discord import app_commands
import json

class Prefix(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot
    
    
    def validate_prefix(self, prefix: str) -> bool:
        conditions = {
            prefix == "": "Prefix cannot be empty.",
            len(prefix) > 5: "Prefix cannot be longer than 5 characters.",
            not prefix.isascii(): "Prefix cannot contain non-ASCII characters."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)
        return True


    @commands.hybrid_group(
        name="prefix",
        description="Change the prefix for the bot."
    )
    async def prefix(self, ctx: commands.Context):
        """Command prefix management system"""
        if ctx.invoked_subcommand is None:
            await self.prefix_list(ctx)
    
    @prefix.command(
        name="set",
        description="Set a single prefix for the bot, replacing existing prefixes."
    )
    @app_commands.describe(prefix="The prefix to set.")
    @commands.has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: commands.Context, prefix: str):
        """Replace all existing prefixes with a single new one"""
        if not self.validate_prefix(prefix):
            return

        self.bot.db.set_guild_prefixes(str(ctx.guild.id), [prefix])
        await ctx.reply(f"Prefix changed to {prefix}")

    @prefix.command(
        name="reset",
        description="Reset the prefix for the bot."
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: commands.Context):
        """Restore the default command prefix"""
        self.bot.db.set_guild_prefixes(str(ctx.guild.id), ["?"])
        await ctx.reply("Prefix reset to default.")

    @prefix.command(
        name="list",
        description="List all prefixes for the bot."
    )
    async def prefix_list(self, ctx: commands.Context):
        """Show all active command prefixes"""
        prefixes = self.bot.db.get_guild_prefixes(str(ctx.guild.id))
        if len(prefixes) == 1:
            message = f"My prefix for the server is `{prefixes[0]}`"
        else:
            prefixes_formatted = [f"`{prefix}`" for prefix in prefixes]
            last_prefix = prefixes_formatted.pop()
            message = f"My prefixes for the server are {', '.join(prefixes_formatted)}, and {last_prefix}"
        await ctx.reply(message)

    @prefix.command(
        name="remove",
        description="Remove a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to remove.")
    async def prefix_remove(self, ctx: commands.Context, prefix: str):
        """Delete a specific command prefix"""
        if not self.validate_prefix(prefix):
            return

        prefixes = self.bot.db.get_guild_prefixes(str(ctx.guild.id))
        if prefix not in prefixes:
            await ctx.reply(f"Prefix '{prefix}' was not found in the list.")
            return
            
        prefixes.remove(prefix)
        self.bot.db.set_guild_prefixes(str(ctx.guild.id), prefixes)
        await ctx.reply(f"Prefix '{prefix}' has been removed.")
    
    @prefix.command(
        name="add",
        description="Add a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to add.")
    async def prefix_add(self, ctx: commands.Context, prefix: str):
        """Add a new command prefix"""
        if not self.validate_prefix(prefix):
            return

        prefixes = self.bot.db.get_guild_prefixes(str(ctx.guild.id))
        if prefix in prefixes:
            await ctx.reply(f"Prefix '{prefix}' already exists.")
            return
            
        prefixes.append(prefix)
        self.bot.db.set_guild_prefixes(str(ctx.guild.id), prefixes)
        await ctx.reply(f"Prefix '{prefix}' has been added.")
    

async def setup(bot: Morgana):
    await bot.add_cog(Prefix(bot))
