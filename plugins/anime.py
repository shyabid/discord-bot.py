from discord.ext import commands
from discord import app_commands
import discord
import requests
from utils import PaginationView
from typing import List, Dict, Any, Optional

class Anime(commands.Cog):
    def __init__(
            self, 
            bot: commands.Bot
        ) -> None:
        self.bot: commands.Bot = bot    
        

    @commands.hybrid_group(
        name="anime",
        description="Anime-related commands"
    )
    async def anime(
        self,
        ctx: commands.Context
    ) -> None:
        """Access comprehensive anime content and information features through this command group. 
        Includes functionality for image retrieval and series searching through the Kitsu API. 
        Use a subcommand to access specific features."""
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a corret subcommand.\n> Avaliable subcommands: `waifu`, `neko`, `hubby`, `search`")

    @anime.command(
        name="waifu",
        description="Get a random waifu image"
    )
    async def waifu(
        self,
        ctx: commands.Context
    ) -> None:
        """Retrieves a curated high-quality anime waifu image from nekos.best API, 
        complete with artist attribution and profile links."""
        try:
            url: str = "https://nekos.best/api/v2/waifu"
            response: requests.Response = requests.get(url)
            data: Dict[str, Any] = response.json()
            
            if response.status_code == 200:
                embed: discord.Embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=ctx.author.avatar.url, text=f"Command ran by {ctx.author.display_name}")
                await ctx.reply(embed=embed)
        
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @anime.command(
        name="neko",
        description="Get a random neko image"
    )
    async def neko(
        self,
        ctx: commands.Context
    ) -> None:
        """Retrieves a curated high-quality anime neko character image from nekos.best API, 
        complete with artist attribution and profile links."""
        try:
            url: str = "https://nekos.best/api/v2/neko"
            response: requests.Response = requests.get(url)
            data: Dict[str, Any] = response.json()
            
            if response.status_code == 200:
                embed: discord.Embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=ctx.author.avatar.url, text=f"Command ran by {ctx.author.display_name}")
                await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @commands.command(
        name="neko",
        description="Get a random neko image",
        aliases=["ne", "nya"]
    )
    async def neko_command(
        self,
        ctx: commands.Context
    ) -> None:
        """Retrieves a curated high-quality anime neko character image from nekos.best API, 
        complete with artist attribution and profile links."""
        await self.neko(ctx)

    @anime.command(
        name="hubby",
        description="Get a random husbando image"
    )
    async def husbando(
        self,
        ctx: commands.Context
    ) -> None:
        """Retrieves a curated high-quality anime male character image from nekos.best API, 
        complete with artist attribution and profile links."""
        try:
            url: str = "https://nekos.best/api/v2/husbando"
            response: requests.Response = requests.get(url)
            data: Dict[str, Any] = response.json()
            
            if response.status_code == 200:
                embed: discord.Embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=ctx.author.avatar.url, text=f"Command ran by {ctx.author.display_name}")
                await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @commands.command(
        name="hubby",
        description="Get a random husbando image",
        aliases=["husbando", "huby", "husband", "h"]
    )
    async def husbando_command(
        self,
        ctx: commands.Context
    ) -> None:
        """Retrieves a curated high-quality anime male character image from nekos.best API, 
        complete with artist attribution and profile links."""
        await self.husbando(ctx)

    @anime.command(
        name="search",
        description="Search for an anime"
    )
    @app_commands.describe(name="The name of the anime to search for")
    async def search(
        self,
        ctx: commands.Context,
        name: str
    ) -> None:
        """Performs a comprehensive search for anime series using the Kitsu API. 
        Displays detailed information including titles, synopsis, ratings, episode details, 
        and media content in a paginated format. Supports partial or complete title search queries."""
        try:
            url: str = f"https://kitsu.io/api/edge/anime?filter[text]={name}"
            response: requests.Response = requests.get(url)
            data: Dict[str, Any] = response.json()
            
            if response.status_code == 200 and data['data']:
                embeds: List[discord.Embed] = []
                for anime in data['data']:
                    attr: Dict[str, Any] = anime['attributes']
                    embed: discord.Embed = discord.Embed(
                        title=attr['canonicalTitle'],
                        url=f"https://kitsu.io/anime/{anime['id']}",
                        description=attr['synopsis'],
                        color=discord.Color.dark_grey()
                    )
                    embed.add_field(name="Type", value=attr['subtype'], inline=True)
                    embed.add_field(name="Status", value=attr['status'], inline=True)
                    embed.add_field(name="Age Rating", value=f"{attr['ageRating']} - {attr['ageRatingGuide']}", inline=True)
                    embed.add_field(name="Episodes", value=attr['episodeCount'], inline=True)
                    embed.add_field(name="Episode Length", value=f"{attr['episodeLength']} min", inline=True)
                    embed.add_field(name="Total Length", value=f"{attr['totalLength']} min", inline=True)
                    embed.add_field(name="Start Date", value=attr['startDate'], inline=True)
                    embed.add_field(name="End Date", value=attr['endDate'] or "Ongoing", inline=True)
                    embed.add_field(name="Average Rating", value=f"{attr['averageRating']}/100", inline=True)
                    embed.add_field(name="Popularity Rank", value=attr['popularityRank'], inline=True)
                    embed.add_field(name="Rating Rank", value=attr['ratingRank'], inline=True)
                    embed.add_field(name="User Count", value=attr['userCount'], inline=True)
                    if attr['posterImage']:
                        embed.set_thumbnail(url=attr['posterImage']['original'])
                    if attr['coverImage']:
                        embed.set_image(url=attr['coverImage']['original'])
                    embed.set_footer(text=f"Page {len(embeds)+1}/{len(data['data'])}")
                    embeds.append(embed)

                if embeds:
                    view: PaginationView = PaginationView(embeds, ctx.author)
                    message: discord.Message = await ctx.reply(embed=embeds[0], view=view)
                    view.message = message
                else:
                    await ctx.reply("No results found.")
            else:
                await ctx.reply("No results found or an error occurred.")

        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @commands.command(
        name="search",
        description="Search for an anime"
    )
    async def search_command(
        self,
        ctx: commands.Context,
        name: str
    ) -> None:
        """Performs a comprehensive search for anime series using the Kitsu API. 
        Displays detailed information including titles, synopsis, ratings, episode details, 
        and media content in a paginated format. Supports partial or complete title search queries."""
        await self.search(ctx, name)




async def setup(
    bot: commands.Bot
) -> None:
    await bot.add_cog(Anime(bot))
