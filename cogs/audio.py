from discord.ext import commands
from discord import app_commands
import discord
import yt_dlp
import asyncio
from collections import deque
from typing import Optional, Dict, Any, List
import time
import os
import tempfile

class AudioControlView(discord.ui.View):
    def __init__(self, cog: 'Audio'):
        super().__init__(timeout=None)
        self.cog: 'Audio' = cog

    @discord.ui.button(
        label="🔁", 
        style=discord.ButtonStyle.secondary
    )
    async def loop(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ) -> None:
        self.cog.loop = not self.cog.loop
        await interaction.response.send_message(
            f"Loop {'enabled' if self.cog.loop else 'disabled'}.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔉", 
        style=discord.ButtonStyle.secondary
    )
    async def volume_down(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ) -> None:
        if self.cog.volume > 0:
            self.cog.volume = max(0, self.cog.volume - 0.1)
            if (self.cog.vc_client and 
                self.cog.vc_client.source):
                self.cog.vc_client.source.volume = self.cog.volume
            await interaction.response.send_message(
                f"Volume decreased to {int(self.cog.volume * 100)}%",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Volume is already at minimum.",
                ephemeral=True
            )

    @discord.ui.button(
        label="⏸️", 
        style=discord.ButtonStyle.secondary
    )
    async def play_pause(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ) -> None:
        if self.cog.vc_client.is_paused():
            self.cog.vc_client.resume()
            await interaction.response.send_message(
                "Resumed the song.",
                ephemeral=True
            )
        elif self.cog.vc_client.is_playing():
            self.cog.vc_client.pause()
            await interaction.response.send_message(
                "Paused the song.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No song is currently playing.",
                ephemeral=True
            )

    @discord.ui.button(
        label="🔊", 
        style=discord.ButtonStyle.secondary
    )
    async def volume_up(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ) -> None:
        if self.cog.volume < 2.0:
            self.cog.volume = min(2.0, self.cog.volume + 0.1)
            if (self.cog.vc_client and 
                self.cog.vc_client.source):
                self.cog.vc_client.source.volume = self.cog.volume
            await interaction.response.send_message(
                f"Volume increased to {int(self.cog.volume * 100)}%",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Volume is already at maximum.",
                ephemeral=True
            )

    @discord.ui.button(
        label="⏭️", 
        style=discord.ButtonStyle.secondary
    )
    async def skip(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ) -> None:
        if (self.cog.vc_client and 
            (self.cog.vc_client.is_playing() or 
             self.cog.vc_client.is_paused())):
            self.cog.vc_client.stop()
            await interaction.response.send_message(
                "Skipped the current song.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No song is currently playing.",
                ephemeral=True
            )

class Audio(commands.Cog):
    """Advanced VC stuff"""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.queue: deque = deque()
        self.current_song: Optional[Dict[str, Any]] = None
        self.vc_client: Optional[discord.VoiceClient] = None
        self.volume: float = 1.0
        self.loop: bool = False
        self.start_time: float = 0
        self.is_playing: bool = False
        self.temp_dir: str = tempfile.mkdtemp()

    async def update_progress_bar(
        self, 
        ctx: commands.Context, 
        message: discord.Message
    ) -> None:
        while self.vc_client and self.is_playing:
            if self.vc_client.is_paused():
                await asyncio.sleep(1)
                continue
            current_time: int = int(time.time() - self.start_time)
            total_time: int = self.current_song['duration']
            progress: int = int(20 * current_time / total_time)
            progress_bar: str = f"[{'=' * progress}{' ' * (20 - progress)}]"
            current_time_str: str = f"{current_time // 60:02d}:{current_time % 60:02d}"
            total_time_str: str = f"{total_time // 60:02d}:{total_time % 60:02d}"
            embed: discord.Embed = message.embeds[0]
            embed.set_field_at(
                0, 
                name="Progress", 
                value=f"`{progress_bar} [{current_time_str}/{total_time_str}]`"
            )
            await message.edit(embed=embed)
            await asyncio.sleep(5)  # Update more frequently

    async def play_next(self, ctx: commands.Context) -> None:
        if self.vc_client and self.vc_client.is_playing():
            return

        if self.loop and self.current_song:
            self.queue.appendleft(self.current_song)
        if self.queue:
            self.current_song = self.queue.popleft()
            temp_file: str = os.path.join(
                self.temp_dir, 
                f"{self.current_song['title']}.mp3"
            )
            source: discord.PCMVolumeTransformer = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(temp_file)
            )
            source.volume = self.volume
            self.vc_client.play(
                source, 
                after=lambda e: self.bot.loop.create_task(
                    self.on_song_complete(ctx)
                )
            )
            self.start_time = time.time()
            self.is_playing = True
            
            embed: discord.Embed = discord.Embed(
                title=f"{self.current_song['title']}", 
                color=discord.Color.dark_grey()
            )
            embed.set_thumbnail(url=self.current_song['thumbnail'])
            total_time: int = self.current_song['duration']
            total_time_str: str = f"{total_time // 60:02d}:{total_time % 60:02d}"
            embed.add_field(
                name="Progress", 
                value=f"`[                    ] [00:00/{total_time_str}]`", 
                inline=False
            )
            embed.add_field(name="Duration", value=total_time_str)
            message: discord.Message = await ctx.send(
                embed=embed, 
                view=AudioControlView(self)
            )
            
            self.bot.loop.create_task(
                self.update_progress_bar(ctx, message)
            )
        else:
            self.current_song = None
            self.is_playing = False

    async def on_song_complete(self, ctx: commands.Context) -> None:
        self.is_playing = False
        await self.play_next(ctx)

    @commands.command(
        name="play", 
        aliases=["p"], 
        description="Play a song or add it to the queue"
    )
    async def music_play(
        self, 
        ctx: commands.Context, 
        *, 
        query: str
    ) -> None:
        """Play a song or add it to the queue"""
        await self.play(ctx, query=query)

    @commands.command(
        name="pause", 
        description="Pause the current song"
    )
    async def music_pause(self, ctx: commands.Context) -> None:
        """Pause the current song"""
        if self.vc_client and self.vc_client.is_playing():
            self.vc_client.pause()
            await ctx.reply("Paused the song.")
        else:
            await ctx.reply("No song is currently playing.")

    @commands.command(
        name="resume", 
        description="Resume the paused song"
    )
    async def music_resume(self, ctx: commands.Context) -> None:
        """Resume the paused song"""
        if self.vc_client and self.vc_client.is_paused():
            self.vc_client.resume()
            await ctx.reply("Resumed the song.")
        else:
            await ctx.reply("No song is paused.")

    @commands.command(
        name="stop", 
        description="Stop playing and clear the queue"
    )
    async def music_stop(self, ctx: commands.Context) -> None:
        """Stop playing and clear the queue"""
        await self.stop(ctx)

    @commands.hybrid_group(
        name="music",
        invoke_without_command=True,
        description="Music commands group"
    )
    async def music(self, ctx: commands.Context) -> None:
        """Music commands group"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @music.command(
        name="play",
        description="Play a song or add it to the queue"
    )
    @app_commands.describe(query="The song to play")    
    async def play(
        self, 
        ctx: commands.Context, 
        *, 
        query: str
    ) -> None:
        """Play a song or add it to the queue"""
        await ctx.defer()
        if not ctx.author.voice:
            await ctx.reply(
                "You need to be in a voice channel to use this command."
            )
            return
        
        ytdlp_opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'noplaylist': 'True',
            'default_search': 'auto',
            'quiet': True,
            'outtmpl': os.path.join(
                self.temp_dir, 
                '%(title)s.%(ext)s'
            ),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ytdlp_opts) as ytdlp:
                info: Dict[str, Any] = ytdlp.extract_info(
                    f"ytsearch:{query}", 
                    download=True
                )['entries'][0]
                song: Dict[str, Any] = {
                    'url': info['url'],
                    'title': info['title'],
                    'duration': info['duration'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            await ctx.reply(f"An error occurred: {str(e)}")
            return

        if not self.vc_client:
            self.vc_client = await ctx.author.voice.channel.connect()

        if not self.is_playing:
            self.current_song = song
            temp_file: str = os.path.join(
                self.temp_dir, 
                f"{song['title']}.mp3"
            )
            source: discord.PCMVolumeTransformer = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(temp_file)
            )
            source.volume = self.volume
            self.vc_client.play(
                source, 
                after=lambda e: self.bot.loop.create_task(
                    self.on_song_complete(ctx)
                )
            )
            self.start_time = time.time()
            self.is_playing = True
            
            embed: discord.Embed = discord.Embed(
                title=f"{song['title']}", 
                color=discord.Color.dark_grey()
            )
            embed.set_thumbnail(url=song['thumbnail'])
            total_time: int = song['duration']
            total_time_str: str = f"{total_time // 60:02d}:{total_time % 60:02d}"
            embed.add_field(
                name="Progress", 
                value=f"`[                    ] [00:00/{total_time_str}]`", 
                inline=False
            )

            message: discord.Message = await ctx.reply(
                embed=embed, 
                view=AudioControlView(self)
            )
            
            self.bot.loop.create_task(
                self.update_progress_bar(ctx, message)
            )
        else:
            self.queue.append(song)
            await ctx.reply(f"Added to queue: {song['title']}")

    @music.command(
        name="queue",
        description="Show the current queue"
    )
    async def queue(self, ctx: commands.Context) -> None:
        if not self.current_song and not self.queue:
            await ctx.reply("The queue is empty.")
            return

        embed: discord.Embed = discord.Embed(
            title="Music Queue", 
            color=discord.Color.dark_grey()
        )
        if self.current_song:
            duration: int = self.current_song['duration']
            duration_str: str = f"{duration // 60:02d}:{duration % 60:02d}"
            embed.add_field(
                name="Now Playing...", 
                value=f"{self.current_song['title']} ({duration_str})", 
                inline=False
            )

        queue_list: str = "\n".join([
            f"{i+1}. {song['title']} ({song['duration'] // 60:02d}:{song['duration'] % 60:02d})" 
            for i, song in enumerate(self.queue)
        ])
        if queue_list:
            embed.add_field(
                name="Up Next", 
                value=queue_list, 
                inline=False
            )
        else:
            embed.add_field(
                name="Up Next", 
                value="No songs in queue", 
                inline=False
            )

        await ctx.reply(embed=embed, view=AudioControlView(self))

    @music.command(
        name="loop",
        description="Toggle loop mode"
    )
    async def loop_command(self, ctx: commands.Context) -> None:
        self.loop = not self.loop
        await ctx.reply(
            f"Loop mode {'enabled' if self.loop else 'disabled'}."
        )

    @music.command(
        name="stop",
        description="Stop playing and clear the queue"
    )
    async def stop(self, ctx: commands.Context) -> None:
        if self.vc_client and self.vc_client.is_connected():
            self.vc_client.stop()
            await self.vc_client.disconnect()
            self.vc_client = None
        self.queue.clear()
        self.current_song = None
        self.is_playing = False
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        await ctx.reply("Stopped playing and cleared the queue.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Audio(bot))
