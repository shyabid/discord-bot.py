from discord import app_commands
from discord.ext import commands
from bot import Morgana
from typing import Union
import discord
import time

class UngrpdCmds(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot

    @app_commands.checks.cooldown(1, 10)
    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        start_time = time.time()
        pong = await ctx.reply(content="Pinging...")
        end_time = time.time()
        
        await pong.edit(content=f"Pong! Latency: {round((end_time - start_time) * 1000 + self.bot.latency)}ms")
    
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message="The message to echo", channel="The channel to send the message in")
    @app_commands.command(name="echo", description="Echo a message")
    async def echo(self, interaction, message: str, channel: Union[discord.TextChannel, discord.VoiceChannel] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not channel: channel = interaction.channel
        
        async with channel.typing():
            await channel.send(message)
        
        await interaction.followup.send(content="Message sent in " + channel.mention, ephemeral=True)
    
    
async def setup(bot: Morgana):
    await bot.add_cog(UngrpdCmds(bot))