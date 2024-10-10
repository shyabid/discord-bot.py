from discord.ext import commands
import discord
from PIL import Image
import io
import aiohttp
import asyncio

class Eventpfp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="frame_pfp",
        description="Frame your avatar",
    )
    async def frame_pfp(self, ctx):
        await ctx.defer()  # Defer the response to avoid timeout
        print(f"Starting frame_pfp command for user {ctx.author}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(ctx.author.avatar.url)) as resp:
                    if resp.status != 200:
                        print(f"Failed to download avatar for user {ctx.author}. Status: {resp.status}")
                        return await ctx.send('Failed to download avatar.')
                    avatar_data = await resp.read()
                    print(f"Successfully downloaded avatar for user {ctx.author}")

            print("Opening and converting avatar image")
            avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
            print("Opening and converting frame image")
            frame = Image.open("template.png").convert("RGBA")

            print("Resizing avatar to template size")
            avatar = avatar.resize(frame.size)
            
            print("Compositing frame onto resized avatar")
            result = Image.alpha_composite(avatar, frame)

            print("Saving result image")
            result_image = io.BytesIO()
            result.save(result_image, format='PNG')
            result_image.seek(0)

            print("Sending framed avatar to user")
            await ctx.send(file=discord.File(fp=result_image, filename='framed_avatar.png'))
            print(f"Completed frame_pfp command for user {ctx.author}")
        except Exception as e:
            print(f"Error in frame_pfp command: {e}")
            await ctx.send("An error occurred while processing your request.")

async def setup(bot):
    await bot.add_cog(Eventpfp(bot))
