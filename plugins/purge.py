from discord.ext import commands
import discord
from bot import Morgana
from discord import app_commands
from typing import List, Optional, Callable, Union

class Purge(commands.Cog):
    """Message cleanup and moderation tools"""

    def __init__(self, bot: Morgana) -> None:
        self.bot: Morgana = bot
        self.limit_err: str = "Cannot check more than 1000 messages at once."

    @commands.hybrid_group(
        name="purge",
        description="Delete messages in bulk with various filters",
        aliases=["clear", "clean"]
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, limit=100) -> None:
        """Bulk message deletion system with filtering capabilities"""
        await self.purge_all(ctx, limit)

    @purge.command(name="all", description="Delete a specified number of messages")
    @app_commands.describe(limit="Number of messages to delete (max 1000)")
    @commands.has_permissions(manage_messages=True)
    async def purge_all(
        self, 
        ctx: commands.Context, 
        limit: int = 100
    ) -> None:
        """Remove messages without any filtering criteria"""
        if limit > 1000:
            return await ctx.reply(self.limit_err)
        
        deleted: List[discord.Message] = await ctx.channel.purge(limit=limit+1)
        await ctx.send(f"Purged {len(deleted) - 1} messages.", delete_after=5)

    @purge.command(name="user", description="Delete messages from a specific user")
    @app_commands.describe(
        user="The user whose messages to delete",
        limit="Number of messages to delete from this user"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_user(
        self, 
        ctx: commands.Context, 
        user: discord.Member, 
        limit: int = 100
    ) -> None:
        """Remove messages from a single user account"""
        check: Callable[[discord.Message], bool] = (
            lambda msg: msg.author == user
        )
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages from {user.mention}.",
            delete_after=5
        )

    @purge.command(name="links", description="Delete messages containing links")
    @app_commands.describe(limit="Number of messages containing links to delete")
    @commands.has_permissions(manage_messages=True)
    async def purge_links(
        self, 
        ctx: commands.Context, 
        limit: int = 100
    ) -> None:
        """Remove messages containing URLs"""
        check: Callable[[discord.Message], bool] = (
            lambda msg: "http://" in msg.content 
            or "https://" in msg.content
        )
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages containing links.",
            delete_after=5
        )

    @purge.command(
        name="mentions", 
        description="Delete messages containing mentions"
    )
    @app_commands.describe(
        limit="Number of messages containing mentions to delete"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_mentions(
        self, 
        ctx: commands.Context, 
        limit: int = 100
    ) -> None:
        """Remove messages that ping users or roles"""
        def check(msg: discord.Message) -> bool:
            return (len(msg.mentions) > 0 
                   or len(msg.role_mentions) > 0 
                   or msg.mention_everyone)

        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages containing mentions.",
            delete_after=5
        )

    @purge.command(name="embeds", description="Delete messages containing embeds")
    @app_commands.describe(limit="Number of messages containing embeds to delete")
    @commands.has_permissions(manage_messages=True)
    async def purge_embeds(
        self, 
        ctx: commands.Context, 
        limit: int = 100
    ) -> None:
        """Remove messages with rich embeds"""
        check: Callable[[discord.Message], bool] = (
            lambda msg: len(msg.embeds) > 0
        )
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages containing embeds.",
            delete_after=5
        )

    @purge.command(
        name="contains",
        description="Delete messages containing specific text"
    )
    @app_commands.describe(
        text="The text to search for in messages",
        limit="Number of messages containing the text to delete"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_contains(
        self, 
        ctx: commands.Context, 
        text: str, 
        limit: int = 100
    ) -> None:
        """Remove messages containing specific text patterns"""
        check: Callable[[discord.Message], bool] = (
            lambda msg: text.lower() in msg.content.lower()
        )
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages containing '{text}'.",
            delete_after=5
        )

    @purge.command(
        name="after",
        description="Delete messages after a specific message"
    )
    @app_commands.describe(
        message_id="The message ID to start deleting after",
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_after(
        self, 
        ctx: commands.Context, 
        message_id: int
    ) -> None:
        """Remove messages after a specific message"""

        message = await ctx.channel.fetch_message(message_id)
        if not message:
            return await ctx.send("Message not found.")
        
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=None,
            after=message.created_at, 
            oldest_first=False
        )
        await ctx.send(
            f"Purged {len(deleted) - 1} messages after {message.jump_url}.",
            delete_after=5
        )
        
    
    @purge.command(
        name="attachments",
        description="Delete messages containing attachments"
    )
    @app_commands.describe(
        limit="Number of messages containing attachments to delete"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_attachments(
        self, 
        ctx: commands.Context, 
        limit: int = 100
    ) -> None:
        """Remove messages with file attachments"""
        check: Callable[[discord.Message], bool] = (
            lambda msg: len(msg.attachments) > 0
        )
        deleted: List[discord.Message] = await ctx.channel.purge(
            limit=limit+1, 
            check=check, 
            after=None, 
            oldest_first=False
        )
        deleted = deleted[:limit]
        await ctx.send(
            f"Purged {len(deleted) - 1} messages containing attachments.",
            delete_after=5
        )

async def setup(bot: Morgana) -> None:
    await bot.add_cog(Purge(bot))
