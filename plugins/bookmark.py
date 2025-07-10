import io
import discord
from discord.ext import commands
import aiohttp

ADD_BOOKMARK_EMOJI = "🔖"
REMOVE_BOOKMARK_EMOJI = "❌"

class Bookmark(commands.Cog):
    """Message bookmark system for personal reference"""
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not self.bot.user or payload.user_id == self.bot.user.id or not payload.emoji.name:
            return
        if payload.emoji.name not in (ADD_BOOKMARK_EMOJI, REMOVE_BOOKMARK_EMOJI):
            return
        try:
            user = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)
            channel = self.bot.get_channel(payload.channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(payload.channel_id)
            if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
                return
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return
        if payload.emoji.name == ADD_BOOKMARK_EMOJI:
            await self.add_bookmark(user, message)
        elif payload.emoji.name == REMOVE_BOOKMARK_EMOJI:
            await self.remove_bookmark(message)

    async def add_bookmark(self, user: discord.User, message: discord.Message):
        embed = self._create_bookmark_embed(message)
        files = await self._get_files_from_message(message)
        try:
            dm_message = await user.send(embed=embed, files=files)
            await dm_message.add_reaction(REMOVE_BOOKMARK_EMOJI)
        except (discord.Forbidden, discord.HTTPException):
            try:
                notify_message = await message.channel.send(
                    f"{user.mention}, I couldn't send you a DM. Please enable DMs to receive bookmarks.",
                    delete_after=30
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def remove_bookmark(self, message: discord.Message):
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _get_files_from_attachments(self, message, files):
        for attachment in message.attachments:
            if len(files) >= 10:
                break
            if attachment.content_type and "image" in attachment.content_type:
                try:
                    files.append(await attachment.to_file())
                except (discord.HTTPException, discord.NotFound):
                    pass

    async def _get_files_from_stickers(self, message, files):
        if len(files) >= 10:
            return
        for sticker in message.stickers:
            if len(files) >= 10:
                break
            if sticker.format in {discord.StickerFormatType.png, discord.StickerFormatType.apng}:
                try:
                    sticker_bytes = await sticker.read()
                    files.append(discord.File(io.BytesIO(sticker_bytes), filename=f"{sticker.name}.png"))
                except (discord.HTTPException, discord.NotFound):
                    pass

    async def _get_files_from_embeds(self, message, files):
        if len(files) >= 10:
            return
        for embed in message.embeds:
            if len(files) >= 10:
                break
            if embed.image and embed.image.url:
                try:
                    async with self.session.get(embed.image.url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            filename = embed.image.url.split("/")[-1].split("?")[0]
                            files.append(discord.File(io.BytesIO(data), filename=filename))
                except aiohttp.ClientError:
                    pass

    async def _get_files_from_message(self, message):
        files = []
        await self._get_files_from_attachments(message, files)
        await self._get_files_from_stickers(message, files)
        await self._get_files_from_embeds(message, files)
        return files

    def _create_bookmark_embed(self, message: discord.Message) -> discord.Embed:
        content = message.content or ""
        if len(content) > 1020:
            content = f"> {content[:1017]}..."
        else:
            content = f"> {content}" if content else "> No content available to display"
        embed = discord.Embed(
            title="Message Bookmarked",
            description=content,
            color=discord.Color(0x99b3ff),
            timestamp=message.created_at
        )
        embed.set_author(
            name="Info",
            icon_url="https://i.imgur.com/8GRtR2G.png"
        )
        embed.add_field(
            name="Author",
            value=message.author.display_name,
            inline=False
        )
        if message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
            ref_msg = message.reference.resolved
            embed.add_field(
                name="Replying to",
                value=f"[Click Here]({ref_msg.jump_url})",
            )
        embed.add_field(
            name="Jump to Message",
            value=f"[Click Here]({message.jump_url})",
        )
        if message.attachments:
            attachments = "\n".join(f"[{a.filename}]({a.url})" for a in message.attachments)
            embed.add_field(name="Attachments", value=attachments, inline=False)
        if message.stickers:
            stickers = "\n".join(f"{s.name}" for s in message.stickers)
            embed.add_field(name="Stickers", value=stickers, inline=False)
        if message.embeds:
            embed.add_field(
                name="Contains Embeds",
                value="Original message contains embeds which are not shown here.",
                inline=False,
            )
        if message.guild and isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            embed.set_footer(text=f"In #{message.channel.name} on {message.guild.name}")
        return embed

async def setup(bot):
    await bot.add_cog(Bookmark(bot))