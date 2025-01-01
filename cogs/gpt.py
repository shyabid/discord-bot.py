from discord.ext import commands
import discord
from openai import OpenAI

class Gpt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = OpenAI(api_key=self.bot.openai_key)
        
    @commands.hybrid_command(
        name="gpt",
        aliases=["ai", "ask"],
        description="Generate text using GPT-4o-mini",
    )
    async def gpt(
        self, 
        ctx, 
        *, 
        prompt: str
    ) -> None:
        with ctx.typing():
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=[
                    {"role": "system", "content": "You are an AI assistant named Morgana. A discord bot."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1000
            )
            await ctx.replt(completion.choices[0].message.content)
        
async def setup(bot):
    await bot.add_cog(Gpt(bot))
