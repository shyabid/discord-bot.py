from discord.ext import commands
import discord
from Quote2Image import Convert, GenerateColors, ImgObject
import io
import aiohttp
from discord import app_commands
from typing import Optional, Dict, Any

class Fun(commands.Cog):

    def __init__(
            self,
            bot: commands.Bot
        ) -> None:
        self.bot: commands.Bot = bot

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

        **Usage:**
        ?fun
        /fun

        **Parameters:**
        None

        **Example:**
        ?fun
        /fun
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

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

        **Usage:**
        ?fun fact
        /fun fact

        **Parameters:**
        None

        **Example:**
        ?fun fact
        /fun fact
        """
        try:
            url: str = "https://uselessfacts.jsph.pl/api/v2/facts/random"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        embed: discord.Embed = discord.Embed(
                            description=data["text"],
                            color=discord.Color.dark_grey()
                        )
                        embed.title = "Fun Fact"
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to fetch a fact. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

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

        **Usage:**
        ?fact

        **Parameters:**
        None

        **Example:**
        ?fact
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

        **Usage:**
        ?fun joke
        /fun joke

        **Parameters:**
        None

        **Example:**
        ?fun joke
        /fun joke
        """
        try:
            url: str = "https://api.popcat.xyz/joke"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        embed: discord.Embed = discord.Embed(
                            description=data["joke"],
                            color=discord.Color.dark_grey()
                        )
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to fetch a joke. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

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

        **Usage:**
        ?joke

        **Parameters:**
        None

        **Example:**
        ?joke
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

        **Usage:**
        ?fun pickupline
        /fun pickupline

        **Parameters:**
        None

        **Example:**
        ?fun pickupline
        /fun pickupline
        """
        try:
            url: str = "https://api.popcat.xyz/pickuplines"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        embed: discord.Embed = discord.Embed(
                            description=data["pickupline"],
                            color=discord.Color.dark_grey()
                        )
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to fetch a pickup line. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

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

        **Usage:**
        ?pickupline

        **Parameters:**
        None

        **Example:**
        ?pickupline
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
        question: str
    ) -> None:
        """
        Ask the magic 8-ball a question and get an answer.

        **Usage:**
        ?fun 8ball <question>
        /fun 8ball <question>

        **Parameters:**
        question (str): The question you want to ask the magic 8-ball

        **Example:**
        ?fun 8ball Will I win the lottery?
        /fun 8ball Will I win the lottery?
        """
        try:
            url: str = "https://api.popcat.xyz/8ball"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        embed: discord.Embed = discord.Embed(
                            title="Magic 8-Ball",
                            description=f"Question: {question}\nAnswer: {data['answer']}",
                            color=discord.Color.dark_grey()
                        )
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to consult the magic 8-ball. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

    @commands.command(
        name="8ball",
        description="Ask the magic 8-ball a question"
    )
    async def eightball_command(
        self,
        ctx: commands.Context,
        *,
        question: str
    ) -> None:
        """
        Ask the magic 8-ball a question and get an answer.

        **Usage:**
        ?8ball <question>

        **Parameters:**
        question (str): The question you want to ask the magic 8-ball

        **Example:**
        ?8ball Will I win the lottery?
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

        **Usage:**
        ?fun roast [target]
        /fun roast [target]

        **Parameters:**
        target (discord.Member, optional): The user to roast. If not provided, the roast will be general.

        **Example:**
        ?fun roast @username
        ?fun roast
        /fun roast @username
        /fun roast
        """
        try:
            url: str = "https://evilinsult.com/generate_insult.php?lang=en&type=json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        roast_text = data["insult"]
                        if target:
                            roast_text = f"{target.mention}, {roast_text}"
                        embed: discord.Embed = discord.Embed(
                            description=roast_text,
                            color=discord.Color.dark_grey()
                        )
                        await ctx.reply(embed=embed)
                    else:
                        await ctx.reply("Failed to fetch a roast. Please try again.")
        except Exception as e:
            await ctx.reply(f"An error occurred: {e}")

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

        **Usage:**
        ?roast [target]

        **Parameters:**
        target (discord.Member, optional): The user to roast. If not provided, the roast will be general.

        **Example:**
        ?roast @username
        ?roast
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

        **Usage:**
        /fun biden <text>

        **Parameters:**
        text (str): The text to display on the Biden meme image.

        **Example:**
        /fun biden Hello world!
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

        **Usage:**
        ?fun biden <text>

        **Parameters:**
        text (str): The text to display on the Biden meme image.

        **Example:**
        ?fun biden Hello world!
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

        **Usage:**
        /fun oogway <text>

        **Parameters:**
        text (str): The text to display on the Oogway meme image.

        **Example:**
        /fun oogway There are no accidents
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

        **Usage:**
        ?fun oogway <text>

        **Parameters:**
        text (str): The text to display on the Oogway meme image.

        **Example:**
        ?fun oogway There are no accidents
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

        **Usage:**
        /fun pikachu <text>

        **Parameters:**
        text (str): The text to display on the Pikachu meme image.

        **Example:**
        /fun pikachu Pika pika!
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

        **Usage:**
        ?fun pikachu <text>

        **Parameters:**
        text (str): The text to display on the Pikachu meme image.

        **Example:**
        ?fun pikachu Pika pika!
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

        **Usage:**
        /fun reverse <text>

        **Parameters:**
        text (str): The text to reverse.

        **Example:**
        /fun reverse Hello World
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/reverse?text={formatted_text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    reversed_text = data.get("text", "Error: No reversed text returned")
                    
                    embed = discord.Embed(
                        description=reversed_text,
                        color=discord.Color.dark_grey()
                    )
                    
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                else:   
                    error_message = "Failed to reverse the text. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(error_message, ephemeral=True)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="reverse", description="Reverse the given text")
    async def reverse_command(self, ctx: commands.Context, *, text: str):
        """
        Reverse the given text.

        **Usage:**
        ?reverse <text>

        **Parameters:**
        text (str): The text to reverse.

        **Example:**
        ?reverse Hello World
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

        **Usage:**
        /fun lulify <text>

        **Parameters:**
        text (str): The text to convert to luliflied speak.

        **Example:**
        /fun lulify Hello World
        """
        formatted_text = text.replace(" ", "+")
        url = f"https://api.popcat.xyz/lulcat?text={formatted_text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    lulcat_text = data.get("text", "Error: No lulified text returned")
                    
                    embed = discord.Embed(
                        description=lulcat_text,
                        color=discord.Color.dark_grey()
                    )
                    
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(embed=embed)
                    else:
                        await ctx.reply(embed=embed)
                else:   
                    error_message = "Failed to convert text to lulified text. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(error_message, ephemeral=True)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="lulify", description="Translate your text into funny Lul Cat Language! ")
    async def lulify_command(self, ctx: commands.Context, *, text: str):
        """
        Translate your text into funny Lul Cat Language! 

        **Usage:**
        ?lulify <text>

        **Parameters:**
        text (str): The text to convert to lulified speak.

        **Example:**
        ?lulify Hello World
        """
        await self.lulify(ctx, text=text)
    @fun.command(name="kanye", description="Get a random Kanye West quote")
    async def kanye(self, ctx: commands.Context):
        """
        Get a random Kanye West quote as an image.

        **Usage:**
        ?kanye
        /kanye

        **Example:**
        ?kanye
        /kanye
        """
        url = "https://api.kanye.rest/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    quote = data.get("quote", "Error: No quote returned")
                    
                    bg = ImgObject(image="assets/kanye.png", brightness=40, blur=0)

                    img = Convert(
                        quote=quote,
                        author="Kanye West",
                        fg="#ffffff",
                        bg=bg,
                        font_size=25,
                        font_type="assets/arial.ttf",
                        width=600,
                        height=450,
                        watermark_text=" "
                    )

                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)

                    embed = discord.Embed(color=discord.Color.dark_grey())
                    embed.set_image(url="attachment://kanye_quote.png")
                    
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(embed=embed, file=discord.File(img_byte_arr, filename="kanye_quote.png"))
                    else:
                        await ctx.reply(embed=embed, file=discord.File(img_byte_arr, filename="kanye_quote.png"))
                else:   
                    error_message = "Failed to fetch a Kanye West quote. Please try again."
                    if isinstance(ctx, discord.Interaction):
                        await ctx.response.send_message(error_message, ephemeral=True)
                    else:
                        await ctx.reply(error_message)

    @commands.command(name="kanye", description="Get a random Kanye West quote")
    async def kanye_command(self, ctx: commands.Context):
        """
        Get a random Kanye West quote as an image.

        **Usage:**
        ?kanye

        **Example:**
        ?kanye
        """
        await self.kanye(ctx)


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

        **Usage:**
        ?fun meme
        /fun meme

        **Parameters:**
        None

        **Example:**
        ?fun meme
        /fun meme
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

        **Usage:**
        ?meme

        **Parameters:**
        None

        **Example:**
        ?meme
        """
        await self.meme(ctx)


    
        
async def setup(
        bot: commands.Bot
) -> None:
    await bot.add_cog(Fun(bot))
