from discord import app_commands
from discord.ext import commands
from bot import Morgana
from typing import Union
import discord
import random
from gender_guesser.detector import Detector
from utils import find_member
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

    @commands.cooldown(1, 5)
    @commands.hybrid_command(name="avatar", aliases=['av', 'pfp'], description="Get the avatar of a user")
    @app_commands.describe(user="The user to get the avatar of")
    async def avatar(
        self, 
        ctx: commands.Context,
        *, 
        user: str = None
    ):
        await ctx.defer()
        
        if user == "random":
            user = [random.choice(ctx.guild.members)]
            
        if user == "random girl":
            d = Detector()
            
            possible_girls = []
            for member in ctx.guild.members:
                name_gender = d.get_gender(member.display_name.split()[0])
                if name_gender in ['female', 'mostly_female']:
                    possible_girls.append(member)
            user = [random.choice(possible_girls)] if possible_girls else [random.choice(ctx.guild.members)]
        
        if user == "random boy":
            d = Detector()
            
            possible_dudes = []
            for member in ctx.guild.members:
                name_gender = d.get_gender(member.display_name.split()[0])
                if name_gender in ['male', 'mostly_male']:
                    possible_dudes.append(member)
            user = [random.choice(possible_dudes)] if possible_dudes else [random.choice(ctx.guild.members)]
        
        elif not user: 
            user = [ctx.author]
        
        else:
            user = user.replace(',', ' ').split()
            mem_list = []
            print(user)
            
            for _ in user:
                mem = await find_member(ctx.guild, _)
                if mem:
                    mem_list.append(mem)
                    print(mem)
            user = mem_list
            
        view = discord.ui.LayoutView()
        container = discord.ui.Container(id=1)
        
        avatar_files = []
        gallery_items = []
        
        for _ in user:
            av_file = await _.display_avatar.to_file()
            avatar_files.append(av_file)
            
            gallery_items.append(
                discord.MediaGalleryItem(
                    media=f"attachment://{av_file.filename}",
                    description=f"{_.name}'s avatar"
                )
            )
        
        gallery = discord.ui.MediaGallery(*gallery_items)
        names = "Showing avatar(s) for: " + ", ".join(f"``{_.name}``" for _ in user)
        
        container.add_item(
            discord.ui.TextDisplay(
                content=names,
            )
        )
        container.add_item(gallery)
        
        view.add_item(container)
        await ctx.reply(view=view, files=avatar_files)

           
async def setup(bot: Morgana):
    await bot.add_cog(UngrpdCmds(bot))