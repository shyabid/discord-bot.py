from discord.ext import commands
import discord
from discord import app_commands
from typing import Optional, Dict, List
import utils

class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="alias", description="Manage command aliases")
    async def alias(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `?help alias` for more information.")

    @alias.command(name="add", description="Add a new alias for a command")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        alias="The shortcut name for your command (must be one word)",
        command="The full command that will be executed"
    )
    async def add_alias(self, ctx: commands.Context, alias: str, *, command: str) -> None:
        aliases_collection = self.bot.db[str(ctx.guild.id)]["aliases"]
        
        if aliases_collection.find_one({"_id": alias}):
            await ctx.reply(f"The alias `{alias}` already exists!")
            return

        if " " in alias:
            await ctx.reply("Aliases must be a single word!")
            return

        aliases_collection.insert_one({
            "_id": alias,
            "command": command,
            "created_by": ctx.author.id
        })

        await ctx.reply(f"Successfully created alias `{alias}` for command `{command}`")

    @alias.command(name="remove", description="Remove an existing alias")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(alias="The alias name to remove")
    async def remove_alias(self, ctx: commands.Context, alias: str) -> None:
        aliases_collection = self.bot.db[str(ctx.guild.id)]["aliases"]
        result = aliases_collection.delete_one({"_id": alias})
        
        if result.deleted_count > 0:
            await ctx.reply(f"Successfully removed the alias `{alias}`")
        else:
            await ctx.reply(f"No alias found with the name `{alias}`")

    @alias.command(name="reset", description="Remove all aliases from the server")
    @commands.has_permissions(manage_guild=True)
    async def reset_aliases(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("You need administrator permissions to reset all aliases!")
            return

        aliases_collection = self.bot.db[str(ctx.guild.id)]["aliases"]
        aliases_collection.delete_many({})
        await ctx.reply("Successfully reset all aliases for this server!")

    @alias.command(name="list", description="List all aliases in the server")
    async def list_aliases(self, ctx: commands.Context) -> None:

        aliases_collection = self.bot.db[str(ctx.guild.id)]["aliases"]
        aliases = list(aliases_collection.find())

        if not aliases:
            await ctx.reply("No aliases have been created yet!")
            return
        
        embeds = []
        aliases_per_page = 10
        
        for i in range(0, len(aliases), aliases_per_page):
            page_aliases = aliases[i:i + aliases_per_page]
            
            embed = discord.Embed(
                title="Server Aliases",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            for alias_data in page_aliases:
                embed.add_field(
                    name=f"?{alias_data['_id']}", 
                    value=f"→ ?{alias_data['command']}", 
                    inline=False
                )
            
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
        
        aliases_collection = self.bot.db[str(message.guild.id)]["aliases"]
        alias_data = aliases_collection.find_one({"_id": potential_alias})
        
        if alias_data:
            return used_prefix + alias_data["command"] + " " + " ".join(content.split()[1:])
        
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

async def setup(bot):
    await bot.add_cog(Alias(bot))
