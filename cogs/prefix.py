from discord.ext import commands
import discord
from discord import app_commands

class Prefix(commands.Cog):
    def __init__(self, bot):
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
        if ctx.invoked_subcommand is None:
            await self.prefix_list(ctx)
    
    @prefix.command(
        name="set",
        description="Set a single prefix for the bot, replacing existing prefixes."
    )
    @app_commands.describe(prefix="The prefix to set.")
    @commands.has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: commands.Context, prefix: str):
        if not self.validate_prefix(prefix):
            return

        loop = self.bot.loop
        await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].update_one(
                {"_id": "prefix"},
                {"$set": {"prefix": [prefix]}},
                upsert=True
            )
        )

        await ctx.send(f"Prefix changed to {prefix}")

    @prefix.command(
        name="reset",
        description="Reset the prefix for the bot."
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: commands.Context):
        loop = self.bot.loop
        await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].delete_one({"_id": "prefix"})
        )
        await ctx.send("Prefix reset to default.")

    @prefix.command(
        name="list",
        description="List all prefixes for the bot."
    )
    async def prefix_list(self, ctx: commands.Context):
        loop = self.bot.loop
        prefixes = await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].find_one({"_id": "prefix"})
        )
        embed = discord.Embed(title="Bot Prefixes", color=discord.Color.blue())
        prefix_list = "\n".join([f"{i+1}. {prefix}" for i, prefix in enumerate(prefixes.get('prefix', []))]) if prefixes else "No custom prefixes set."
        embed.description = prefix_list if prefix_list else "No custom prefixes set."
        await ctx.send(embed=embed)

    @prefix.command(
        name="remove",
        description="Remove a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to remove.")
    async def prefix_remove(self, ctx: commands.Context, prefix: str):
        if not self.validate_prefix(prefix):
            return 

        loop = self.bot.loop
        result = await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].update_one(
                {"_id": "prefix"},
                {"$pull": {"prefix": prefix}}
            )
        )
        
        if result.modified_count == 0:
            await ctx.send(f"Prefix '{prefix}' was not found in the list.")
        else:
            await ctx.send(f"Prefix '{prefix}' has been removed.")
    
    @prefix.command(
        name="add",
        description="Add a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to add.")
    async def prefix_add(self, ctx: commands.Context, prefix: str):
        if not self.validate_prefix(prefix):
            return 

        loop = self.bot.loop
        existing_prefixes = await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].find_one({"_id": "prefix"})
        )
        if existing_prefixes and prefix in existing_prefixes.get("prefix", []):
            await ctx.send(f"Prefix '{prefix}' already exists.")
            return

        await loop.run_in_executor(
            None, 
            lambda: self.bot.db[str(ctx.guild.id)]["config"].update_one(
                {"_id": "prefix"},
                {"$push": {"prefix": prefix}},
                upsert=True
            )
        )

        await ctx.send(f"Prefix '{prefix}' has been added.")
    

async def setup(bot):
    await bot.add_cog(Prefix(bot))
