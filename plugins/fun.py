from discord.ext import commands
import discord
# from Quote2Image import Convert, GenerateColors, ImgObject
import io
from bot import Morgana
import aiohttp
from discord import app_commands
from typing import Optional, Dict, Any

class Fun(commands.Cog):

    def __init__(
            self,
            bot: Morgana
        ) -> None:
        self.bot: Morgana = bot

    @commands.hybrid_group(
        name="fun",
        description="Fun-related commands"
    )
    async def fun(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Contains commands you can play with. You can either use slash command or normal prefix command. Mostly API calls.
        """
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a correct subcommand.\n> Available subcommands: `fact`, `joke`, `pickupline`, `8ball`, `roast`, `biden`, `oogway`, `pikachu`, `reverse`, `lulify`, `kanye`, `meme`")

    @fun.command(
        name="fact",
        description="Get a random fact"
    )
    async def fact(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random fact from the internet.
        """
        url: str = "https://uselessfacts.jsph.pl/api/v2/facts/random"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    
                    await ctx.reply(data["text"])
                else:
                    await ctx.reply("The Fact API is unavailable at the moment")

    @commands.command(
        name="fact",
        description="Get a random fact"
    )
    async def fact_command(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random fact from the internet.
        """
        await self.fact(ctx)

    @fun.command(
        name="joke",
        description="Get a random joke"
    )
    async def joke(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random joke from the internet.
        """
        url: str = "https://api.popcat.xyz/joke"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    await ctx.reply(data["joke"])
                else:
                    await ctx.reply("The joke API is unavailable at the moment")

    @commands.command(
        name="joke",
        description="Get a random joke"
    )
    async def joke_command(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random joke from the internet.
        """
        await self.joke(ctx)

    @fun.command(
        name="pickupline",
        description="Get a random pickup line"
    )
    async def pickupline(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random pickup line from the internet.
        """
        url: str = "https://api.popcat.xyz/pickuplines"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    await ctx.reply(data["pickupline"])
                else:
                    await ctx.reply("The pickup line API is unavailable at the moment")

    @commands.command(
        name="pickupline",
        description="Get a random pickup line"
    )
    async def pickupline_command(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random pickup line from the internet.
        """
        await self.pickupline(ctx)

    @fun.command(
        name="8ball",
        description="Ask the magic 8-ball a question"
    )
    async def eightball(
        self,
        ctx: commands.Context,
        *,
        question: str = None
    ) -> None:
        """
        Ask the magic 8-ball a question and get an answer.
        """
        url: str = "https://api.popcat.xyz/8ball"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    await ctx.reply(data["answer"])
                else:
                    await ctx.reply("The 8-ball API is unavailable at the moment")

    @commands.command(
        name="8ball",
        description="Ask the magic 8-ball a question"
    )
    async def eightball_command(
        self,
        ctx: commands.Context,
        *,
        question: str = None
    ) -> None:
        """
        Ask the magic 8-ball a question and get an answer.
        """
        await self.eightball(ctx, question=question)

    @fun.command(
        name="roast",
        description="Get a random roast"
    )
    async def roast(
        self,
        ctx: commands.Context,
        target: Optional[discord.Member] = None
    ) -> None:
        """
        Get a random roast from the internet. Optionally mention a user to roast.
        """
        url: str = "https://evilinsult.com/generate_insult.php?lang=en&type=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data: Dict[str, Any] = await response.json()
                    roast_text = data["insult"]
                    if target:
                        roast_text = f"{target.mention}, {roast_text}"
                    
                    await ctx.reply(roast_text)
                else:
                    await ctx.reply("Failed to fetch a roast. Please try again.")

    @commands.command(
        name="roast",
        description="Get a random roast"
    )
    async def roast_command(
        self,
        ctx: commands.Context,
        target: Optional[discord.Member] = None
    ) -> None:
        """
        Get a random roast from the internet. Optionally mention a user to roast.
        """
        await self.roast(ctx, target=target)
    @fun.command(
        name="biden",
        description="Generate a Biden meme image"
    )
    @app_commands.describe(text="The text to display on the Biden meme image")
    async def biden(self, ctx: commands.Context, *, text: str):
        """
        Generate a Biden meme image with custom text.
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/biden?text={formatted_text}"

        embed = discord.Embed(
            color=discord.Color.dark_grey()
        )
        embed.set_image(url=url)

        await ctx.reply(embed=embed)

    @commands.command(
        name="biden",
        description="Generate a Biden meme image"
    )
    async def biden_command(self, ctx: commands.Context, *, text: str):
        """
        Generate a Biden meme image with custom text.
        """
        await self.biden(ctx, text=text)

    @fun.command(
        name="oogway",
        description="Generate an Oogway meme image"
    )
    @app_commands.describe(text="The text to display on the Oogway meme image")
    async def oogway(self, ctx: commands.Context, *, text: str):
        """
        Generate an Oogway meme image with custom text.
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/oogway?text={formatted_text}"

        embed = discord.Embed(
            color=discord.Color.dark_grey()
        )
        embed.set_image(url=url)

        await ctx.reply(embed=embed)

    @commands.command(
        name="oogway",
        description="Generate an Oogway meme image"
    )
    async def oogway_command(self, ctx: commands.Context, *, text: str):
        """
        Generate an Oogway meme image with custom text.
        """
        await self.oogway(ctx, text=text)

    @fun.command(
        name="pikachu",
        description="Generate a Pikachu meme image"
    )
    @app_commands.describe(text="The text to display on the Pikachu meme image")
    async def pikachu(self, ctx: commands.Context, *, text: str):
        """
        Generate a Pikachu meme image with custom text.
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/pikachu?text={formatted_text}"

        embed = discord.Embed(
            color=discord.Color.dark_grey()
        )
        embed.set_image(url=url)

        await ctx.reply(embed=embed)

    @commands.command(
        name="pikachu",
        description="Generate a Pikachu meme image"
    )
    async def pikachu_command(self, ctx: commands.Context, *, text: str):
        """
        Generate a Pikachu meme image with custom text.
        """
        await self.pikachu(ctx, text=text)

    @fun.command(
        name="reverse",
        description="Reverse the given text"
    )
    @app_commands.describe(text="The text to reverse")
    async def reverse_slash(self, ctx: commands.Context, *, text: str):
        """
        Reverse the given text.
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/reverse?text={formatted_text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    reversed_text = data.get("text", "Error: No reversed text returned")
                    
                    
                    await ctx.reply(reversed_text)
                else:   
                    error_message = "The roast API is unavailable at the moment"
                    await ctx.reply(error_message)

    @commands.command(name="reverse", description="Reverse the given text")
    async def reverse_command(self, ctx: commands.Context, *, text: str):
        """
        Reverse the given text.
        """
        await self.reverse_slash(ctx, text=text)

    @fun.command(
        name="lulify",
        description="Convert text to lulcat speak"
    )
    @app_commands.describe(text="The text to convert to lulcat speak")
    async def lulify(self, ctx: commands.Context, *, text: str):
        """
        Translate your text into funny Lul Cat Language! 
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/lulcat?text={formatted_text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    lulcat_text = data.get("text", "Error: No lulified text returned")
                    
                    
                    ctx.reply(lulcat_text)
                else:   
                    error_message = "The lulify API is unavailable at the moment"
                    await ctx.reply(error_message)
                    
    @commands.command(name="lulify", description="Translate your text into funny Lul Cat Language! ")
    async def lulify_command(self, ctx: commands.Context, *, text: str):
        """
        Translate your text into funny Lul Cat Language! 
        """
        await self.lulify(ctx, text=text)
    # @fun.command(name="kanye", description="Get a random Kanye West quote")
    # async def kanye(self, ctx: commands.Context):
    #     """
    #     Get a random Kanye West quote as an image.

    #     **Usage:**
    #     ?kanye
    #     /kanye

    #     **Example:**
    #     ?kanye
    #     /kanye
    #     """
    #     url = "https://api.kanye.rest/"

    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as response:
    #             if response.status == 200:
    #                 data = await response.json()
    #                 quote = data.get("quote", "Error: No quote returned")
                    
    #                 bg = ImgObject(image="assets/kanye.png", brightness=40, blur=0)

    #                 img = Convert(
    #                     quote=quote,
    #                     author="Kanye West",
    #                     fg="#ffffff",
    #                     bg=bg,
    #                     font_size=25,
    #                     font_type="assets/arial.ttf",
    #                     width=600,
    #                     height=450,
    #                     watermark_text=" "
    #                 )

    #                 img_byte_arr = io.BytesIO()
    #                 img.save(img_byte_arr, format='PNG')
    #                 img_byte_arr.seek(0)

    #                 embed = discord.Embed(color=discord.Color.dark_grey())
    #                 embed.set_image(url="attachment://kanye_quote.png")
                    
    #                 if isinstance(ctx, discord.Interaction):
    #                     await ctx.response.send_message(embed=embed, file=discord.File(img_byte_arr, filename="kanye_quote.png"))
    #                 else:
    #                     await ctx.reply(embed=embed, file=discord.File(img_byte_arr, filename="kanye_quote.png"))
    #             else:   
    #                 error_message = "Failed to fetch a Kanye West quote. Please try again."
    #                 if isinstance(ctx, discord.Interaction):
    #                     await ctx.response.send_message(error_message, ephemeral=True)
    #                 else:
    #                     await ctx.reply(error_message)

    # @commands.command(name="kanye", description="Get a random Kanye West quote")
    # async def kanye_command(self, ctx: commands.Context):
    #     """
    #     Get a random Kanye West quote as an image.

    #     **Usage:**
    #     ?kanye

    #     **Example:**
    #     ?kanye
    #     """
    #     await self.kanye(ctx)


    @fun.command(
        name="meme",
        description="Get a random meme"
    )
    async def meme(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random meme from the internet.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://meme-api.com/gimme') as response:
                    if response.status == 200:
                        meme_data = await response.json()
                        meme_title = meme_data['title']
                        meme_url = meme_data['url']
                        embed = discord.Embed(description=meme_title, color=discord.Color.from_rgb(195, 238, 250))
                        embed.set_image(url=meme_url)
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to fetch a meme. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @commands.command(
        name="meme",
        description="Get a random meme"
    )
    async def meme_command(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Get a random meme from the internet.
        """
        await self.meme(ctx)


    
        
async def setup(
        bot: commands.Bot
) -> None:
    await bot.add_cog(Fun(bot))
