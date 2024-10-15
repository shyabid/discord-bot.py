from discord.ext import commands
import discord 
import html
import asyncio
import datetime
import time
import aiohttp
import re
import urllib
from discord import app_commands
from typing import Optional
from utils import PaginationView
import random
import requests
import json
from typing import Literal, Union
import os
from db import db


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_group(name="misc")
    async def misc(self, ctx: commands.Context):
        """Misc commands group"""
        if ctx.invoked_subcommand is None:
            await ctx.reply("Use `?help misc` to see available misc commands.")

    @misc.command(name="periodic-table", description="Get information about an element from the periodic table")
    @app_commands.describe(query="Element name, atomic number, or symbol (optional)")
    async def periodic_table(self, ctx: commands.Context, query: Optional[str] = None):
        """
        Get information about an element from the periodic table.

        **Usage:**
        ?misc periodic-table [query]
        /misc periodic-table [query]

        **Parameters:**
        query (str, optional): Element name, atomic number, or symbol. If not provided, a random element will be selected.

        **Example:**
        ?misc periodic-table Carbon
        ?misc periodic-table 6
        ?misc periodic-table C
        /misc periodic-table Oxygen
        /misc periodic-table
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
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply("Failed to fetch element data. Please try again.")

    @commands.command(name="periodic-table", aliases=["pt", "element"], description="Get information about an element from the periodic table")
    async def periodic_table_command(self, ctx: commands.Context, *, query: Optional[str] = None):
        """
        Get information about an element from the periodic table.

        Usage:
        ?periodic-table [query]
        ?pt [query]
        ?element [query]

        Parameters:
        query (str, optional): Element name, atomic number, or symbol. If not provided, a random element will be selected.

        Example:
        ?periodic-table Carbon
        ?pt 6
        ?element C
        """
        await self.periodic_table(ctx, query)
    
    @misc.command(name="urbandictionary", description="Get definitions from Urban Dictionary")
    @app_commands.describe(word="Word to look up (required)")
    async def urban_dictionary(self, ctx: commands.Context, word: str):
        """
        Get definitions from Urban Dictionary.

        **Usage:**
        ?misc ud <word>
        /misc ud <word>

        **Parameters:**
        word (str, required): The word to look up in Urban Dictionary.

        **Example:**
        ?misc ud hello
        /misc ud programming
        """
        async with aiohttp.ClientSession() as session:
            url = f"https://api.urbandictionary.com/v0/define?term={word}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    definitions = data.get('list', [])
                    
                    if not definitions:
                        await ctx.reply(f"No definitions found for '{word}'.")
                        return
                    embeds = []
                    for index, entry in enumerate(definitions, start=1):
                        definition = entry['definition'][:2048]
                        example = entry['example'][:1024]
                        
                        
                        def process_text(text):
                            return re.sub(r'\[([^\]]+)\]', lambda m: f"[{m.group(1)}](https://www.urbandictionary.com/define.php?term={m.group(1).replace(' ', '%20')})", text)
                        
                        definition = process_text(definition)
                        example = process_text(example)
                        
                        embed = discord.Embed(
                            title=f"{word.capitalize()} {index}/{len(definitions)}",
                            description=definition,
                            color=discord.Color.dark_grey()
                        )
                        embed.url = entry['permalink']
                        embed.add_field(name="Example", value=example or "N/A", inline=False)
                        embed.add_field(name="Author", value=entry['author'], inline=True)
                        embed.add_field(name="Likes", value=entry['thumbs_up'], inline=True)
                        embed.add_field(name="Dislikes", value=entry['thumbs_down'], inline=True)
                        embed.set_footer(text=f"Definition ID: {entry['defid']}")
                        embeds.append(embed)

                    paginator = PaginationView(embeds)
                    await ctx.reply(embed=embeds[0], view=paginator)
                else:
                    await ctx.reply("Failed to fetch data from Urban Dictionary. Please try again.")

    @commands.command(name="urbandictionary", aliases=["urban", "ud", "urbandict"], description="Get definitions from Urban Dictionary")
    async def ud_command(self, ctx: commands.Context, *, word: str):
        """
        Get definitions from Urban Dictionary.

        Usage:
        ?ud <word>

        Parameters:
        word (str, required): The word to look up in Urban Dictionary.

        Example:
        ?ud hello
        """
        await self.urban_dictionary(ctx, word)


    @misc.command(name="imdb", description="Get information about a movie or TV show from IMDb")
    @app_commands.describe(title="Title of the movie or TV show to look up (required)")
    async def imdb_command(self, ctx: commands.Context, *, title: str):
        """
        Get information about a movie or TV show from IMDb.

        Usage:
        ?imdb <title>

        Parameters:
        title (str, required): The title of the movie or TV show to look up.

        Example:
        ?imdb Iron Man
        """
        await self.imdb(ctx, title)

    async def imdb(self, ctx: Union[commands.Context, discord.Interaction], title: str):
        url = f"https://api.popcat.xyz/imdb?q={urllib.parse.quote(title)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title=f"{data['title']} ({data['year']})",
                        description=data['plot'],
                        color=discord.Color.gold(),
                        url=data['imdburl']
                    )
                    
                    embed.set_thumbnail(url=data['poster'])
                    
                    embed.add_field(name="Rating", value=f"{data['rating']}/10", inline=True)
                    embed.add_field(name="Runtime", value=data['runtime'], inline=True)
                    embed.add_field(name="Genres", value=data['genres'], inline=True)
                    
                    embed.add_field(name="Director", value=data['director'], inline=True)
                    embed.add_field(name="Actors", value=data['actors'], inline=True)
                    
                    ratings = "\n".join([f"{rating['source']}: {rating['value']}" for rating in data['ratings']])
                    embed.add_field(name="Ratings", value=ratings, inline=False)
                    
                    embed.add_field(name="Awards", value=data['awards'], inline=False)
                    
                    embed.set_footer(text=f"IMDb ID: {data['imdbid']} | Type: {data['type'].capitalize()}")
                    
                    if isinstance(ctx, discord.Interaction):
                        await ctx.followup.send(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                else:
                    error_message = "Failed to fetch data from IMDb. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.followup.send(error_message)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="imdb", description="Get information about a movie or TV show from IMDb")
    async def imdb_slash(self, ctx:commands.Context, title: str):
        """
        Get information about a movie or TV show from IMDb.

        Parameters:
        title (str): The title of the movie or TV show to look up.
        """
        await self.imdb(ctx, title)

    @misc.command(
        name="ttm",
        description="Convert text to Morse code"
    )
    @app_commands.describe(text="The text to convert to Morse code")
    async def ttm(self, ctx: commands.Context, *, text: str):
        """
        Convert text to Morse code using the PopCat API.

        **Usage:**
        /misc ttm <text>

        **Parameters:**
        text (str): The text to convert to Morse code.

        **Example:**
        /misc ttm Hello World
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/texttomorse?text={formatted_text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    morse_text = data.get("morse", "Error: No Morse code returned")
                    
                    embed = discord.Embed(
                        description=f"**Morse Code**\n{morse_text}",
                        color=discord.Color.dark_grey()
                    )
                    
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                else:   
                    error_message = "Failed to convert text to Morse code. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(error_message, ephemeral=True)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="ttm", description="Convert text to Morse code")
    async def ttm_command(self, ctx: commands.Context, *, text: str):
        """
        Convert text to Morse code using the PopCat API.

        **Usage:**
        ?ttm <text>

        **Parameters:**
        text (str): The text to convert to Morse code.

        **Example:**
        ?ttm Hello World
        """
        await self.ttm(ctx, text=text)



async def setup(bot):
    await bot.add_cog(Misc(bot))
