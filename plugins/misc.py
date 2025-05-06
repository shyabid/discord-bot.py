from discord.ext import commands
import discord 
import html
import asyncio
import datetime
import time
import io
import aiohttp
import re
import urllib
from discord import app_commands
from typing import Optional, List, Literal, Union, Dict, Any
from utils import PaginationView
import random
import requests
import json
import unicodedata
import os
from libgen_api_enhanced import LibgenSearch
import functools
from concurrent.futures import ThreadPoolExecutor


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._executor = ThreadPoolExecutor(max_workers=2)

    @commands.hybrid_group(name="misc")
    async def misc(self, ctx: commands.Context):
        """Collection of various utility and information commands
        
        This command group provides access to a diverse set of informational tools
        and utilities that don't fit into other specific categories. Includes
        reference resources like Urban Dictionary, IMDb, the periodic table,
        dictionary definitions, and song lyrics finder, all accessible through
        an intuitive subcommand interface.
        """
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Available subcommands: `urban-dictionary`, `imdb`, `periodic-table`, `define`, `lyrics`")

    @misc.command(name="periodic-table", description="Get information about an element from the periodic table")
    @app_commands.describe(query="Element name, atomic number, or symbol (optional)")
    async def periodic_table(self, ctx: commands.Context, query: Optional[str] = None):
        """Access comprehensive chemical element information
        
        This command provides detailed data about elements from the periodic table,
        including physical properties, atomic characteristics, historical discovery
        information, and a brief scientific summary. When used without specifying
        an element, it returns information about a randomly selected element for
        educational exploration.
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
        """Access comprehensive chemical element information
        
        This command provides detailed data about elements from the periodic table,
        including physical properties, atomic characteristics, historical discovery
        information, and a brief scientific summary. When used without specifying
        an element, it returns information about a randomly selected element for
        educational exploration.
        """
        await self.periodic_table(ctx, query)
    
    @misc.command(name="urbandictionary", description="Get definitions from Urban Dictionary")
    @app_commands.describe(word="Word to look up (required)")
    async def urban_dictionary(self, ctx: commands.Context, word: str):
        """Search for slang and colloquial term definitions
        
        This command queries Urban Dictionary to find user-submitted definitions
        for slang terms, internet memes, and other informal language. Results include
        the definition, usage examples, and community ratings. The interactive display
        allows browsing through multiple definition entries when available.
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

                    paginator = PaginationView(embeds, ctx.author)
                    await ctx.reply(embed=embeds[0], view=paginator)
                else:
                    await ctx.reply("Failed to fetch data from Urban Dictionary. Please try again.")

    @commands.command(name="urbandictionary", aliases=["urban", "ud", "urbandict"], description="Get definitions from Urban Dictionary")
    async def ud_command(self, ctx: commands.Context, *, word: str):
        """Search for slang and colloquial term definitions
        
        This command queries Urban Dictionary to find user-submitted definitions
        for slang terms, internet memes, and other informal language. Results include
        the definition, usage examples, and community ratings. The interactive display
        allows browsing through multiple definition entries when available.
        """
        await self.urban_dictionary(ctx, word)


    @misc.command(name="imdb", description="Get information about a movie or TV show from IMDb")
    @app_commands.describe(title="Title of the movie or TV show to look up (required)")
    async def imdb_command(self, ctx: commands.Context, *, title: str):
        """Retrieve detailed film and television show information
        
        This command searches the Internet Movie Database (IMDb) for comprehensive
        details about movies, TV shows, and other video media. Results include
        production information, cast details, ratings from various sources,
        plot summaries, and other relevant metadata for the requested title.
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
        """
        await self.imdb(ctx, title)
        
        
    @misc.command(name="define", description="Get the definition of a word")
    @app_commands.describe(word="The word to define")
    async def define(self, ctx: commands.Context, word: str):
        """Look up formal dictionary definitions for words
        
        This command retrieves official definitions from a dictionary API,
        providing proper meanings, phonetic pronunciations, parts of speech,
        and usage examples when available. Useful for language learning,
        writing assistance, and resolving vocabulary questions with
        authoritative references.
        """
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        word_data = data[0]
                        embed = discord.Embed(title=f"Definition of '{word_data['word']}'", color=discord.Color.dark_grey())
                        
                        if 'phonetic' in word_data:
                            embed.add_field(name="Phonetic", value=word_data['phonetic'], inline=False)
                        
                        for meaning in word_data.get('meanings', []):
                            part_of_speech = meaning.get('partOfSpeech', 'Unknown')
                            definitions = meaning.get('definitions', [])
                            if definitions:
                                definition_text = definitions[0].get('definition', 'No definition available')
                                example = definitions[0].get('example', '')
                                field_value = f"{definition_text}\n\n*Example:* {example}" if example else definition_text
                                embed.add_field(name=part_of_speech.capitalize(), value=field_value, inline=False)
                        
                        if isinstance(ctx, discord.Interaction):
                            await ctx.response.send_message(embed=embed)
                        else:
                            await ctx.reply(embed=embed)
                    else:
                        error_message = f"No definition found for '{word}'."
                        if isinstance(ctx, discord.Interaction):
                            await ctx.response.send_message(error_message, ephemeral=True)
                        else:
                            await ctx.reply(error_message)
                else:
                    error_message = f"Failed to fetch definition for '{word}'. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(error_message, ephemeral=True)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="define", description="Get the definition of a word")
    async def define_command(self, ctx: commands.Context, word: str):
        """Look up formal dictionary definitions for words
        
        This command retrieves official definitions from a dictionary API,
        providing proper meanings, phonetic pronunciations, parts of speech,
        and usage examples when available. Useful for language learning,
        writing assistance, and resolving vocabulary questions with
        authoritative references.
        """
        await self.define(ctx, word=word)
    
    
    @misc.command(name="lyrics", description="Get lyrics for a song")
    async def lyrics(self, ctx: commands.Context, *, query: str):
        """Find and display lyrics for music tracks
        
        This command searches for and displays the full lyrics for a specified
        song. Results include the complete song text along with artist information
        and album artwork when available. For longer lyrics, the output may be
        truncated to comply with Discord's message length limitations.
        """
        formatted_query = query.replace(" ", "+")
        api_url = f"https://api.popcat.xyz/lyrics?song={formatted_query}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                    else:
                        await ctx.reply(f"Error fetching lyrics. Status code: {response.status}")
                        return
        except Exception as e:
            await ctx.reply(f"An error occurred: {str(e)}")
            return

        try:
            title = data.get("title", "Unknown Title")
            artist = data.get("artist", "Unknown Artist")
            lyrics = f"`Artist - {artist}` \n\n" + data.get("lyrics", "Lyrics not available")
            image = data.get("image")

            if not lyrics:
                await ctx.reply(f"No lyrics found for '{query}'")
                return

            embed = discord.Embed(
                title=f"{title}",
                description=lyrics[:2048],
                color=discord.Color.dark_grey()
            )
            
            
            if image:
                embed.set_image(url=image)

            if len(lyrics) > 2048:
                embed.set_footer(text="Lyrics were truncated due to length.")

            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(embed=embed)
            else:
                await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(f"An error occurred while processing the lyrics: {str(e)}")

    @commands.command(name="lyrics", description="Get lyrics for a song")
    async def lyrics_command(self, ctx: commands.Context, *, query: str):
        """Find and display lyrics for music tracks
        
        This command searches for and displays the full lyrics for a specified
        song. Results include the complete song text along with artist information
        and album artwork when available. For longer lyrics, the output may be
        truncated to comply with Discord's message length limitations.
        """
        await self.lyrics(ctx, query=query)

    @commands.hybrid_group(name="book", description="Search and download books from Library Genesis")
    async def book(self, ctx: commands.Context):
        """Advanced book search and download system
        
        This command provides a comprehensive interface to search for books,
        research papers, and other publications across the Library Genesis
        database. It offers multiple search methods, advanced filtering options,
        and direct download links when available.
        """
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Available subcommands: `search`, `author`, `advanced`")
    
    @book.command(name="search", description="Search for books by title")
    @app_commands.describe(
        query="Title of the book to search for (minimum 3 characters)",
        extension="Filter by file extension (pdf, epub, mobi, etc)",
        language="Filter by language",
        year="Filter by publication year"
    )
    async def book_search(
        self, 
        ctx: commands.Context, 
        query: str,
        extension: Optional[str] = None,
        language: Optional[str] = None,
        year: Optional[str] = None
    ):
        """Search for books by title with optional filters
        
        This command performs a comprehensive search across Library Genesis
        for books matching the provided title. Results can be further refined
        using optional filters for file format, language, and publication year.
        For each match, detailed information and download links are provided.
        """
        if len(query) < 3:
            await ctx.reply("Search query must be at least 3 characters long.")
            return
            
        await ctx.defer()
        
        clean_query = query.strip('"\'')
        
        filters = {}
        if extension: filters["Extension"] = extension
        if language: filters["Language"] = language
        if year: filters["Year"] = year
            
        try:
            if filters:
                results = await self._run_in_executor(
                    self._search_books_filtered, "title", clean_query, filters
                )
            else:
                results = await self._run_in_executor(
                    self._search_books, "title", clean_query
                )
            
            # If no results found, try to find common misspellings
            if not results:
                alternative_queries = self._find_similar_titles(clean_query)
                alternative_results = []
                
                # Try up to 2 alternative spellings
                for alt_query in alternative_queries[:2]:
                    
                    alt_results = await self._run_in_executor(
                        self._search_books, "title", alt_query
                    )
                    
                    if alt_results:
                        alternative_results.append((alt_query, alt_results))
                
                if alternative_results:
                    # Use the first successful alternative
                    alt_query, results = alternative_results[0]
                    await ctx.send(f"No books found for '{clean_query}'. Showing results for '{alt_query}' instead.")
                
            await self._send_book_results(ctx, results, clean_query)
        except Exception as e:
            await ctx.reply(f"An error occurred while searching for books: {str(e)}")
    
    @book.command(name="author", description="Search for books by author name")
    @app_commands.describe(
        author="Name of the author to search for (minimum 3 characters)",
        extension="Filter by file extension (pdf, epub, mobi, etc)",
        language="Filter by language",
        year="Filter by publication year"
    )
    async def book_author(
        self, 
        ctx: commands.Context, 
        author: str,
        extension: Optional[str] = None,
        language: Optional[str] = None,
        year: Optional[str] = None
    ):
        """Search for books by a specific author with optional filters
        
        This command searches Library Genesis for all publications by a specific
        author. Results can be refined with optional filters for file type,
        language, and year of publication. Each result includes comprehensive
        metadata and download options when available.
        """
        if len(author) < 3:
            await ctx.reply("Author name must be at least 3 characters long.")
            return
            
        await ctx.defer()
        clean_author = author.strip('"\'')
        
        filters = {}
        if extension: filters["Extension"] = extension
        if language: filters["Language"] = language
        if year: filters["Year"] = year
            
        try:
            # Run the potentially slow network operation in a thread pool
            if filters:
                results = await self._run_in_executor(
                    self._search_books_filtered, "author", clean_author, filters
                )
            else:
                results = await self._run_in_executor(
                    self._search_books, "author", clean_author
                )
                
            await self._send_book_results(ctx, results, f"Author: {clean_author}")
        except Exception as e:
            await ctx.reply(f"An error occurred while searching for books: {str(e)}")
    
    @book.command(name="advanced", description="Advanced book search with multiple filters")
    @app_commands.describe(
        query="Search query (title or keywords, minimum 3 characters)",
        search_type="Type of search to perform",
        exact_match="Whether to require exact matches for filters",
        extension="Filter by file extension (pdf, epub, mobi, etc)",
        language="Filter by language",
        year="Filter by publication year",
        publisher="Filter by publisher name",
        pages="Filter by page count (e.g. '100' or '100-200')"
    )
    async def book_advanced(
        self, 
        ctx: commands.Context, 
        query: str,
        search_type: Literal["title", "author", "default"],
        exact_match: bool = True,
        extension: Optional[str] = None,
        language: Optional[str] = None,
        year: Optional[str] = None,
        publisher: Optional[str] = None,
        pages: Optional[str] = None
    ):
        """Perform an advanced multi-filter book search
        
        This command provides the most comprehensive search capabilities,
        allowing simultaneous filtering across multiple metadata fields.
        Users can specify exact or partial matching, and combine filters
        for precise results tailored to specific research or reading needs.
        """
        if len(query) < 3:
            await ctx.reply("Search query must be at least 3 characters long.")
            return
            
        await ctx.defer()
        
        clean_query = query.strip('"\'')
        
        filters = {}
        if extension: filters["Extension"] = extension
        if language: filters["Language"] = language
        if year: filters["Year"] = year
        if publisher: filters["Publisher"] = publisher
        if pages: filters["Pages"] = pages
            
        try:
            results = await self._run_in_executor(
                self._search_books_filtered, 
                search_type, 
                clean_query, 
                filters,
                exact_match
            )
                
            await self._send_book_results(ctx, results, f"Advanced search: {clean_query}")
        except Exception as e:
            await ctx.reply(f"An error occurred during advanced search: {str(e)}")
    
    @book.command(name="default", description="General search for books across all fields")
    @app_commands.describe(
        query="Search query (looks across titles, authors, etc.)",
        extension="Filter by file extension (pdf, epub, mobi, etc)",
        language="Filter by language"
    )
    async def book_default(
        self, 
        ctx: commands.Context, 
        query: str,
        extension: Optional[str] = None,
        language: Optional[str] = None
    ):
        """Perform a general search across all book metadata fields
        
        This command uses LibGen's default search which checks across multiple
        fields including title, author, ISBN, publisher and more. This provides
        the broadest possible search for finding books without needing to know
        exactly where the search term appears.
        """
        if len(query) < 3:
            await ctx.reply("Search query must be at least 3 characters long.")
            return
            
        await ctx.defer()
        
        clean_query = query.strip('"\'')
        
        filters = {}
        if extension: filters["Extension"] = extension
        if language: filters["Language"] = language
            
        if filters:
            results = await self._run_in_executor(
                self._search_books_filtered, "default", clean_query, filters
            )
        else:
            results = await self._run_in_executor(
                self._search_books, "default", clean_query
            )
            
        await self._send_book_results(ctx, results, f"General search: {clean_query}")

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in a thread pool executor"""
        return await self.bot.loop.run_in_executor(
            self._executor, 
            functools.partial(func, *args, **kwargs)
        )
    
    def _search_books(self, search_type: str, query: str) -> List[Dict[str, Any]]:
        """Search for books by title, author, or default"""
        searcher = LibgenSearch()
        try:
            if search_type == "title":
                return searcher.search_title(query)
            elif search_type == "author":
                return searcher.search_author(query)
            else: 
                return searcher.search_default(query)
        except json.JSONDecodeError as e:
            print(f"JSON decode error in _search_books: {str(e)}")
            print(f"Query was: {query}, search_type: {search_type}")
            # Return empty list on JSON error
            return []
        except Exception as e:
            print(f"Error in _search_books: {str(e)}")
            return []
    
    def _search_books_filtered(
        self, 
        search_type: str, 
        query: str, 
        filters: Dict[str, str],
        exact_match: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for books with filters by title or author"""
        searcher = LibgenSearch()
        try:
            # Make a copy of filters and replace "extension" with the parameter
            # that LibgenSearch actually accepts (likely "Extension")
            clean_filters = {}
            for key, value in filters.items():
                if key.lower() == "extension":
                    clean_filters["Extension"] = value
                else:
                    clean_filters[key] = value
            
            if search_type == "title":
                return searcher.search_title_filtered(query, clean_filters, exact_match)
            elif search_type == "author":
                return searcher.search_author_filtered(query, clean_filters, exact_match)
            else:
                # Enhanced library doesn't have filtered default search, 
                # so we'll get results and filter them manually
                results = searcher.search_default(query)
                return self._filter_results(results, clean_filters, exact_match)
        except json.JSONDecodeError as e:
            print(f"JSON decode error in _search_books_filtered: {str(e)}")
            print(f"Query was: {query}, search_type: {search_type}")
            print(f"Filters: {filters}")
            # Return empty list on JSON error
            return []
        except Exception as e:
            print(f"Error in _search_books_filtered: {str(e)}")
            return []
    
    def _filter_results(
        self, 
        results: List[Dict[str, Any]], 
        filters: Dict[str, str],
        exact_match: bool = True
    ) -> List[Dict[str, Any]]:
        """Filter results based on the provided filters"""
        filtered_results = []
        
        for result in results:
            matches_all_filters = True
            
            for filter_key, filter_value in filters.items():
                result_value = result.get(filter_key, "")
                
                if exact_match:
                    if result_value != filter_value:
                        matches_all_filters = False
                        break
                else:
                    if filter_value.lower() not in result_value.lower():
                        matches_all_filters = False
                        break
                        
            if matches_all_filters:
                filtered_results.append(result)
                
        return filtered_results
    
    def _find_similar_titles(self, query: str) -> List[str]:
        """Find similar book titles that might match a misspelled query"""
        return []
    

    async def _send_book_results(self, ctx: commands.Context, results: List[Dict[str, Any]], query_info: str):
        """Format and send book search results"""
        if not results:
            await ctx.reply(f"No books found for '{query_info}'.")
            return
            
        results = results[:25]
        embeds = []
        
        for idx, book in enumerate(results, 1):
            embed = discord.Embed(
                title=f"{book.get('Title', 'Unknown Title')}",
                description=f"**By** {book.get('Author', 'Unknown')}\n**Published by** {book.get('Publisher', 'Unknown')}",
                color=discord.Color.dark_blue()
            )
            
            cover_url = book.get('Cover')
            if cover_url: embed.set_image(url=cover_url)
            
            metadata = {
                "Year": book.get("Year", "Unknown"),
                "Language": book.get("Language", "Unknown"),
                "Pages": book.get("Pages", "Unknown"),
                "Size": book.get("Size", "Unknown"),
                "Format": book.get("Extension", "Unknown"),
                "ID": book.get("ID", "Unknown")
            }
            embed.description += f'\n\n{metadata["Year"]} | {metadata["Language"]} | {metadata["Pages"]} pages | {metadata["Size"]} | {metadata["Format"]}'
            
            download_links = ""
            
            direct_link = book.get("Direct_Download_Link")
            if direct_link:
                download_links += f"[__↓ Direct Download__]({direct_link})\n"
                        
            mirror_links = []
            for i in range(1, 6):
                mirror_key = f"Mirror_{i}"
                if mirror_key in book and book[mirror_key]:
                    mirror_links.append(f"[Mirror {i}]({book[mirror_key]})")
            
            if mirror_links:
                download_links += " | ".join(mirror_links)
            
            if download_links:
                embed.description += f"\n\n{download_links}"
            
            embed.set_footer(text=f"Result {idx}/{len(results)} for search: {query_info}")
            embeds.append(embed)
    
        paginator = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=paginator)


    @misc.command(name="charinfo", description="Get information about Unicode characters")
    @app_commands.describe(characters="Characters to get information about")
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Display detailed Unicode character information
        
        This command analyzes the provided characters and returns detailed Unicode
        information for each character including its code point, official name,
        and the Python escape sequence needed to represent it.
        """
        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            fileformat_link = f"https://www.fileformat.info/info/unicode/char/{digit}/index.htm"
            return f'[`\\U{digit:>08}`](<{fileformat_link}>) {name} {c}'

        msg = '\n'.join(map(to_string, characters))
        if msg.strip():
            await ctx.reply(msg)
        else: await ctx.reply('No characters provided.')

    @commands.command(name="charinfo", description="Get information about Unicode characters")
    async def charinfo_command(self, ctx: commands.Context, *, characters: str):
        """Display detailed Unicode character information
        
        This command analyzes the provided characters and returns detailed Unicode
        information for each character including its code point, official name,
        and the Python escape sequence needed to represent it.
        """
        await self.charinfo(ctx, characters=characters)


async def setup(bot):
    await bot.add_cog(Misc(bot))
