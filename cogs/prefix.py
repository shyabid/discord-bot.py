from discord.ext import commands
import discord
from discord import app_commands
import json

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

        cursor = self.bot.prefix_db.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO guild_prefixes (guild_id, prefixes) VALUES (?, ?)",
            (str(ctx.guild.id), json.dumps([prefix]))
        )
        self.bot.prefix_db.commit()
        await ctx.reply(f"Prefix changed to {prefix}")

    @prefix.command(
        name="reset",
        description="Reset the prefix for the bot."
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: commands.Context):
        cursor = self.bot.prefix_db.cursor()
        cursor.execute("DELETE FROM guild_prefixes WHERE guild_id = ?", (str(ctx.guild.id),))
        self.bot.prefix_db.commit()
        await ctx.reply("Prefix reset to default.")

    @prefix.command(
        name="list",
        description="List all prefixes for the bot."
    )
    async def prefix_list(self, ctx: commands.Context):
        cursor = self.bot.prefix_db.cursor()
        cursor.execute("SELECT prefixes FROM guild_prefixes WHERE guild_id = ?", (str(ctx.guild.id),))
        result = cursor.fetchone()
        
        prefixes = json.loads(result[0]) if result else ["?"]
        embed = discord.Embed(title="Bot Prefixes", color=discord.Color.dark_grey())
        embed.description = "\n".join([f"{i+1}. {prefix}" for i, prefix in enumerate(prefixes)])
        await ctx.reply(embed=embed)

    @prefix.command(
        name="remove",
        description="Remove a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to remove.")
    async def prefix_remove(self, ctx: commands.Context, prefix: str):
        if not self.validate_prefix(prefix):
            return

        cursor = self.bot.prefix_db.cursor()
        cursor.execute("SELECT prefixes FROM guild_prefixes WHERE guild_id = ?", (str(ctx.guild.id),))
        result = cursor.fetchone()
        
        if not result:
            await ctx.reply(f"Prefix '{prefix}' was not found in the list.")
            return
            
        prefixes = json.loads(result[0])
        if prefix not in prefixes:
            await ctx.reply(f"Prefix '{prefix}' was not found in the list.")
            return
            
        prefixes.remove(prefix)
        cursor.execute(
            "UPDATE guild_prefixes SET prefixes = ? WHERE guild_id = ?",
            (json.dumps(prefixes), str(ctx.guild.id))
        )
        self.bot.prefix_db.commit()
        await ctx.reply(f"Prefix '{prefix}' has been removed.")
    
    @prefix.command(
        name="add",
        description="Add a prefix for the bot."
    )
    @app_commands.describe(prefix="The prefix to add.")
    async def prefix_add(self, ctx: commands.Context, prefix: str):
        if not self.validate_prefix(prefix):
            return

        cursor = self.bot.prefix_db.cursor()
        cursor.execute("SELECT prefixes FROM guild_prefixes WHERE guild_id = ?", (str(ctx.guild.id),))
        result = cursor.fetchone()
        
        prefixes = json.loads(result[0]) if result else []
        if prefix in prefixes:
            await ctx.reply(f"Prefix '{prefix}' already exists.")
            return
            
        prefixes.append(prefix)
        cursor.execute(
            "INSERT OR REPLACE INTO guild_prefixes (guild_id, prefixes) VALUES (?, ?)",
            (str(ctx.guild.id), json.dumps(prefixes))
        )
        self.bot.prefix_db.commit()
        await ctx.reply(f"Prefix '{prefix}' has been added.")
    

async def setup(bot):
    await bot.add_cog(Prefix(bot))
