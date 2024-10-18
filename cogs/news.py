import discord
import aiohttp
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Any, Optional
from utils import PaginationView
from urllib.parse import urlparse

class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.api_url: str = "https://bbc-api.vercel.app/news?lang=english"
        self._news_categories: List[str] = []

    async def fetch_news_data(self) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

    async def create_news_embeds(self, news_data: Dict[str, Any], category: str) -> List[discord.Embed]:
        embeds: List[discord.Embed] = []
        for index, article in enumerate(news_data.get(category, []), start=1):
            embed = discord.Embed(
                title=article['title'],
                description=article['summary'],
                color=discord.Color.dark_grey()
            )
            if article['news_link'] and self.is_valid_url(article['news_link']):
                embed.url = article['news_link']
            if article['image_link'] and self.is_valid_url(article['image_link']):
                embed.set_thumbnail(url=article['image_link'])
            embed.set_footer(text=f"Page {index}/{len(news_data.get(category, []))}")
            embeds.append(embed)
        return embeds

    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:  
            return False

    async def category_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not self._news_categories:
            news_data = await self.fetch_news_data()
            self._news_categories = list(news_data.keys())
        
        return [
            app_commands.Choice(name=cat, value=cat)
            for cat in self._news_categories
            if current.lower() in cat.lower()
        ][:25]  # Discord limits choices to 25

    @commands.hybrid_command(name="news", description="Get the latest news")
    @app_commands.autocomplete(category=category_autocomplete)
    async def news_hybrid(self, ctx: commands.Context, category: str = "Latest"):
        """
        Get the latest news from a specific category.

        **Usage:**
        ?news [category]
        /news [category]

        **Parameters:**
        category (optional): The news category to fetch. If not provided, 'Latest' will be used.

        **Example:**
        ?news Technology
        ?news
        /news Sports
        /news
        """
        await ctx.defer()
        news_data = await self.fetch_news_data()
        
        if not news_data:
            await ctx.reply("Failed to fetch news data.")
            return

        self._news_categories = list(news_data.keys())
        
        if category not in news_data:
            category = "Latest"

        embeds = await self.create_news_embeds(news_data, category)
        
        if not embeds:
            await ctx.reply(f"No news found for category: {category}")
            return

        view = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=view)
        view.message = await ctx.interaction.original_response()

    @commands.Cog.listener()
    async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        error = args[0] if args else None
        if isinstance(error, discord.errors.HTTPException) and error.code == 50035:
            self.bot.logger.error(f"HTTPException in {event}: {error}")
            # You might want to send a message to a log channel or the user here
        else:
            self.bot.logger.error(f"Error in {event}: {error}")

async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
