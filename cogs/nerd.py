from discord.ext import commands
import discord
import aiohttp
from discord import app_commands
from typing import Optional
class Nerd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="nerd")
    async def nerd(self, ctx: commands.Context):
        """Nerd commands group"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `?help nerd` to see available nerd commands.")

    @nerd.command(name="periodic-table", description="Get information about an element from the periodic table")
    @app_commands.describe(query="Element name, atomic number, or symbol (optional)")
    async def periodic_table(self, ctx: commands.Context, query: Optional[str] = None):
        """
        Get information about an element from the periodic table.

        **Usage:**
        ?nerd periodic-table [query]
        /nerd periodic-table [query]

        **Parameters:**
        query (str, optional): Element name, atomic number, or symbol. If not provided, a random element will be selected.

        **Example:**
        ?nerd periodic-table Carbon
        ?nerd periodic-table 6
        ?nerd periodic-table C
        /nerd periodic-table Oxygen
        /nerd periodic-table
        """
        async with aiohttp.ClientSession() as session:
            if query:
                url = f"https://api.popcat.xyz/periodic-table?element={query}"
            else:
                url = "https://api.popcat.xyz/periodic-table/random"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                                        
                    embed = discord.Embed(
                        title=f"{data['name']}", 
                        description=(
                            f"- **Symbol**: {data['symbol']}\n" +
                            f"- **Atomic Number**: {data['atomic_number']}\n" +
                            f"- **Atomic Mass**: {data['atomic_mass']}\n" +
                            f"- **Period**: {data['period']}\n" +
                            f"- **Phase**: {data['phase']}\n" +
                            f"- **Discovered By**: {data['discovered_by']}\n" +
                            f"- **Element Summary:**\n  - {data['summary']}"
                        ),
                        color=discord.Color.dark_grey()
                    )
                    embed.set_thumbnail(url=data['image'])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Failed to fetch element data. Please try again.")

async def setup(bot):
    await bot.add_cog(Nerd(bot))
