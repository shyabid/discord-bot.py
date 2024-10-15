from discord.ext import commands
import discord
import aiohttp
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
            url: str = "https://api.popcat.xyz/fact"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data: Dict[str, Any] = await response.json()
                        embed: discord.Embed = discord.Embed(
                            description=data["fact"],
                            color=discord.Color.dark_grey()
                        )
                        embed.set_author(name="Fun Fact")
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

async def setup(
        bot: commands.Bot
) -> None:
    await bot.add_cog(Fun(bot))
