import discord
from discord.ext import commands
from bot import Morgana

class Bookmark(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "🔖":
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        except (discord.Forbidden, discord.HTTPException):
            return

        embed = self._create_bookmark_embed(message)
        user = self.bot.get_user(payload.user_id)
        if not user:
            return

        await self._send_bookmark(user, message, embed)

    def _create_bookmark_embed(self, message: discord.Message) -> discord.Embed:
        embed = discord.Embed(
            title="Message Bookmarked",
            description=f"> {message.content[:1021]}..." if len(message.content) > 1024 else f"> {message.content}",
            color=discord.Color(0x99b3ff),  # Hex color code #99b3ff
            timestamp=message.created_at
        )

        # Fetch bot's ping and profile picture (avatar)
        bot_ping = round(self.bot.latency * 1000)  # Convert from seconds to milliseconds
        bot_avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url

        embed.set_footer(
            text=f"Morgana $ {bot_ping}ms",
            icon_url=bot_avatar_url
        )

        embed.set_author(
            name="Info",
            icon_url="https://i.imgur.com/8GRtR2G.png"
        )

        embed.add_field(name="Author", value=message.author.mention, inline=False)
        embed.add_field(name="Jump to Message", value=f"[Click Here]({message.jump_url})", inline=False)

        if message.attachments:
            attachments_info = "\n".join([attachment.url for attachment in message.attachments])
            embed.add_field(name="Attachments", value=attachments_info, inline=False)

        return embed

    async def _send_bookmark(self, user: discord.User, message: discord.Message, embed: discord.Embed):
        try:
            await user.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            notify_message = await message.channel.send(
                f"{user.mention}, I couldn't send you a DM. Please enable DMs to receive bookmarks."
            )
            await notify_message.delete(delay=30)

async def setup(bot: Morgana):
    await bot.add_cog(Bookmark(bot))
