import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import utils
from bot import Morgana

class Alias(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot

    @commands.hybrid_group(name="alias", description="Manage command aliases")
    async def alias(self, ctx: commands.Context) -> None:
        """
        Manage server-specific command aliases and shortcuts

        This command group allows server administrators to create custom shortcuts
        for frequently used commands. Aliases can simplify complex commands and
        make them easier to remember and use.
        """
        
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a correct subcommand.\n> Avaliable subcommands: `add`, `remove`, `reset`, `list`")

    @alias.command(name="add", description="Add a new alias for a command")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        alias="The shortcut name for your command (must be one word)",
        command="The full command that will be executed"
    )
    async def add_alias(self, ctx: commands.Context, alias: str, *, command: str) -> None:
        """Create a new command alias for the server. You can create an alias of a subcommand too."""
        
        if " " in alias:
            return await ctx.reply("Aliases must be a single word!")

        if self.bot.get_command(alias):
            return await ctx.reply(f"Cannot create alias `{alias}` as it's an existing command name.")

        if self.bot.db.get_alias(ctx.guild.id, alias):
            return await ctx.reply(f"The alias `{alias}` already exists.")

        cmd_name = command.split()[0]
        if not self.bot.get_command(cmd_name):
            return await ctx.reply(f"The command `{cmd_name}` doesn't exist.")

        self.bot.db.add_alias(ctx.guild.id, alias, command, ctx.author.id)
        await ctx.reply(f"Successfully created alias `{alias}` for command `{command}`")

    @alias.command(name="remove", description="Remove an existing alias")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(alias="The alias name to remove")
    async def remove_alias(self, ctx: commands.Context, alias: str) -> None:
        """Remove an existing command alias from the server."""
        
        if self.bot.db.remove_alias(ctx.guild.id, alias):
            await ctx.reply(f"Successfully removed the alias `{alias}`")
        else:
            await ctx.reply(f"No alias found with the name `{alias}`")

    @alias.command(name="reset", description="Remove all aliases from the server")
    @commands.has_permissions(administrator=True)
    async def reset_aliases(self, ctx: commands.Context) -> None:
        """Remove all command aliases from the server."""
        
        self.bot.db.reset_aliases(ctx.guild.id)
        await ctx.reply("Successfully reset all aliases for this server.")
        
        
    @alias.command(name="list", description="List all aliases in the server")
    async def list_aliases(self, ctx: commands.Context) -> None:
        """List all command aliases in the server."""
        
        aliases = self.bot.db.get_all_aliases(ctx.guild.id)
        
        if not aliases:
            return await ctx.reply("No aliases have been created yet!")
        
        embeds = []
        aliases_per_page = 10
        
        for i in range(0, len(aliases), aliases_per_page):
            page_aliases = aliases[i:i + aliases_per_page]
            
            embed = discord.Embed(
                title="Server Aliases",
                color=discord.Color.dark_grey(),
                timestamp=discord.utils.utcnow()
            )
            
            description = "\n".join(f"`{alias}` → `{command}`" for alias, command in page_aliases)
            embed.description = description
            
            embed.set_footer(text=f"Page {i//aliases_per_page + 1}/{(len(aliases)-1)//aliases_per_page + 1}")
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.reply(embed=embeds[0])
        else:
            pagination_view = utils.PaginationView(embeds=embeds, author=ctx.author)
            pagination_view.message = await ctx.reply(embed=embeds[0], view=pagination_view)

    async def process_alias(self, message: discord.Message) -> Optional[str]:
        if not message.guild:
            return None
            
        prefixes = await self.bot.get_prefix(message)
        if not any(message.content.startswith(prefix) for prefix in prefixes):
            return None

        used_prefix = next(prefix for prefix in prefixes if message.content.startswith(prefix))
        content = message.content[len(used_prefix):].strip()
        
        if not content:
            return None
            
        potential_alias = content.split()[0]
        alias_data = self.bot.db.get_alias(message.guild.id, potential_alias)
        
        if alias_data:
            command = alias_data[0]
            return used_prefix + command + " " + " ".join(content.split()[1:])
        
        return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        new_content = await self.process_alias(message)
        if new_content:
            ctx = await self.bot.get_context(message)
            original_content = message.content
            message.content = new_content
            await self.bot.process_commands(message)
            message.content = original_content

async def setup(bot: Morgana):
    await bot.add_cog(Alias(bot))
