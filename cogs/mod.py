import discord
from typing import Optional
from discord import app_commands
import utils
import typing
import time
from discord.ext import commands
import datetime
from typing import Dict, Union, List, Any, cast

class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        
    @commands.hybrid_group(
        name="moderation", 
        description="Moderation commands"
    )
    async def moderation(
        self, 
        ctx: commands.Context
    ) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                "Please specify a moderation command."
            )

    @moderation.command(
        name="setlog",
        description="Set the moderation log channel"
    )
    @commands.has_permissions(administrator=True)
    async def setlog(
        self, 
        ctx: commands.Context, 
        channel: discord.TextChannel
    ) -> None:
        guild_id: str = str(ctx.guild.id)
        config_collection = self.bot.db[guild_id]["config"]
        config_collection.update_one(
            {}, 
            {"$set": {"modlog": channel.id}}, 
            upsert=True
        )
        await ctx.reply(
            f"Moderation log channel set to {channel.mention}"
        )

    async def get_log_channel(
        self, 
        guild_id: int
    ) -> Optional[discord.TextChannel]:
        config: Optional[Dict[str, Any]] = (
            self.bot.db[str(guild_id)]["config"].find_one({})
        )
        if config and "modlog" in config:
            return self.bot.get_channel(config["modlog"])
        return None

    @commands.command(
        name="setlog",
        description="Set the moderation log channel",
        aliases=["setmodlog"]
    )    
    @commands.has_permissions(administrator=True)
    async def setlog_command(
        self, 
        ctx: commands.Context, 
        channel: discord.TextChannel
    ) -> None:
        await self.setlog(ctx, channel)

    async def _notify_user(
        self,
        user: discord.Member,
        action: str,
        reason: str,
        guild: discord.Guild,
        **kwargs
    ) -> None:
        try:
            embed = discord.Embed(
                title=f"You've been {action}",
                color=discord.Color.red(),
                description=f"**Server:** {guild.name}"
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if "duration" in kwargs:
                embed.add_field(name="Duration", value=kwargs["duration"], inline=False)
                
            await user.send(embed=embed)
        except discord.Forbidden:
            # If we can't DM the user, we'll just continue with the action
            pass

    async def _do_ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str,
        deletemsg: Optional[int] = None
    ) -> None:
        conditions: Dict[bool, str] = {
            bool(deletemsg is not None and 
                (deletemsg < 1 or deletemsg > 14)): 
                "Invalid deletemsg value. Must be 1-14.",
            member == ctx.author: 
                "You cannot ban yourself.",
            member == ctx.guild.owner: 
                "Cannot ban server owner.",
            member == self.bot.user: 
                "I can't ban myself.",
            member.top_role >= ctx.author.top_role: 
                "Cannot ban member with higher role.",
            not ctx.guild.me.top_role > member.top_role: 
                "Cannot ban member with higher role than me."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel: Optional[discord.TextChannel] = (
            await self.get_log_channel(ctx.guild.id)
        )
        if not log_channel:
            await ctx.reply(
                "Modlog not set. Use `/moderation setlog`."
            )
            return

        ban_log_embed: discord.Embed = discord.Embed(
            title="Ban Case",
            color=discord.Color.dark_grey(),
            description=(
                f"{member.mention} banned by "
                f"{ctx.author.mention}"
            )
        )
        ban_log_embed.set_thumbnail(url=member.avatar.url)
        
        if reason:
            ban_log_embed.add_field(
                name="Reason", 
                value=str(reason), 
                inline=False
            )

        roles: List[discord.Role] = sorted(
            member.roles[1:],
            key=lambda r: r.position,
            reverse=True
        )[:5]
        
        role_mentions: str = ", ".join(
            [role.mention for role in roles]
        )

        ban_log_embed.add_field(
            name="Banned Member Info",
            value=(
                f"Joined: {discord.utils.format_dt(member.joined_at, 'R')}\n"
                f"Created: {discord.utils.format_dt(member.created_at, 'R')}\n"
                f"Top Roles: {role_mentions}\n"
                f"ID: {member.id}"
            ),
            inline=False
        )
        
        await self._notify_user(member, "banned", reason, ctx.guild)
        if deletemsg:
            await ctx.guild.ban(
                member, 
                reason=reason,
                delete_message_days=deletemsg
            )
        else:
            await ctx.guild.ban(member, reason=reason)
            
        await log_channel.send(embed=ban_log_embed)
        await ctx.reply(f"{member} has been banned.")

    @moderation.command(
        name="ban", 
        description="Ban a member"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context, 
        member: discord.Member,
        reason: str = "No reason provided",
        deletemsg: Optional[int] = None
    ) -> None:
        """
        Ban a member from the server.

        **Usage:**
        ?moderation ban <member> [reason] [delete_days]
        /moderation ban <member> [reason] [delete_days]

        **Parameters:**
        member (discord.Member): The member to ban
        reason (str, optional): The reason for the ban. Defaults to "No reason provided"
        deletemsg (int, optional): Number of days of messages to delete (1-14)

        **Example:**
        ?moderation ban @user Spamming 7
        /moderation ban @user Breaking rules
        """
        await self._do_ban(ctx, member, reason, deletemsg)

    @commands.command(
        name="ban",
        description="Ban a member",
        aliases=["banmember"]
    )
    @commands.has_permissions(ban_members=True)
    async def ban_command(
        self, 
        ctx: commands.Context, 
        member: str, 
        *, 
        reason: Optional[str] = None
    ) -> None:
        """
        Ban a member from the server.

        **Usage:**
        ?ban <member> [reason]

        **Parameters:**
        member (str): The member's name, nickname, or ID
        reason (str, optional): The reason for the ban

        **Example:**
        ?ban username Breaking rules
        ?banmember userID Spamming
        """
        found_member: Optional[discord.Member] = (
            await utils.find_member(ctx.guild, member)
        )
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self._do_ban(ctx, found_member, reason if reason else "No reason provided", 1)

    async def _do_kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str
    ) -> None:
        conditions: Dict[bool, str] = {
            member == ctx.author: "You cannot kick yourself.",
            member == ctx.guild.owner: "Cannot kick server owner.", 
            member == self.bot.user: "I can't kick myself.",
            member.top_role >= ctx.author.top_role: "Cannot kick member with higher role.",
            not ctx.guild.me.top_role > member.top_role: "Cannot kick member with higher role than me."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel: Optional[discord.TextChannel] = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Modlog not set. Use `/moderation setlog`.")
            return

        kick_log_embed = discord.Embed(
            title="Kick Case",
            color=discord.Color.orange(),
            description=f"{member.mention} kicked by {ctx.author.mention}"
        )
        kick_log_embed.set_thumbnail(url=member.avatar.url)
        kick_log_embed.add_field(name="Reason", value=reason, inline=False)

        roles = sorted(
            member.roles[1:],
            key=lambda r: r.position,
            reverse=True
        )[:5]
        
        role_mentions = ", ".join([role.mention for role in roles])
        kick_log_embed.add_field(
            name="Kicked Member Info",
            value=(
                f"Joined: {discord.utils.format_dt(member.joined_at, 'R')}\n"
                f"Created: {discord.utils.format_dt(member.created_at, 'R')}\n"
                f"Top Roles: {role_mentions}\n"
                f"ID: {member.id}"
            ),
            inline=False
        )

        await self._notify_user(member, "kicked", reason, ctx.guild)
        await ctx.guild.kick(member, reason=reason)
        await log_channel.send(embed=kick_log_embed)
        await ctx.reply(f"{member} has been kicked.")

    @moderation.command(name="kick", description="Kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ) -> None:
        """
        Kick a member from the server.

        **Usage:**
        ?moderation kick <member> [reason]
        /moderation kick <member> [reason]

        **Parameters:**
        member (discord.Member): The member to kick
        reason (str, optional): The reason for the kick. Defaults to "No reason provided"

        **Example:**
        ?moderation kick @user Spamming
        /moderation kick @user Breaking rules
        """
        await self._do_kick(ctx, member, reason)

    @commands.command(name="kick", description="Kick a member", aliases=["kickmember"])
    @commands.has_permissions(kick_members=True)
    async def kick_command(
        self,
        ctx: commands.Context,
        member: str,
        *,
        reason: str = "No reason provided"
    ) -> None:
        """
        Kick a member from the server.

        **Usage:**
        ?kick <member> [reason]

        **Parameters:**
        member (str): The member's name, nickname, or ID
        reason (str, optional): The reason for the kick

        **Example:**
        ?kick username Breaking rules
        ?kickmember userID Spamming
        """
        found_member = await utils.find_member(ctx.guild, member)
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self._do_kick(ctx, found_member, reason)

    async def _do_timeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        reason: str
    ) -> None:
        duration_seconds = utils.parse_time_string(duration)
        if duration_seconds == 0:
            raise commands.BadArgument("Invalid duration format")

        conditions: Dict[bool, str] = {
            member == ctx.author: "You cannot timeout yourself.",
            member == ctx.guild.owner: "Cannot timeout server owner.",
            member == self.bot.user: "I can't timeout myself.",
            member.top_role >= ctx.author.top_role: "Cannot timeout member with higher role.",
            not ctx.guild.me.top_role > member.top_role: "Cannot timeout member with higher role than me.",
            duration_seconds < 60: "Duration must be at least 1 minute."
        }

        log_channel: Optional[discord.TextChannel] = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Modlog not set. Use `/moderation setlog`.")
            return

        timeout_duration = datetime.timedelta(seconds=duration_seconds)
        formatted_duration = utils.format_seconds(duration_seconds)
        
        await self._notify_user(
            member, 
            "timed out", 
            reason, 
            ctx.guild, 
            duration=formatted_duration
        )
        
        await member.timeout(timeout_duration, reason=reason)

        timeout_log_embed = discord.Embed(
            title="Timeout Case",
            color=discord.Color.yellow(),
            description=f"{member.mention} timed out by {ctx.author.mention}"
        )
        timeout_log_embed.set_thumbnail(url=member.avatar.url)
        timeout_log_embed.add_field(name="Duration", value=formatted_duration, inline=False)
        timeout_log_embed.add_field(name="Reason", value=reason, inline=False)

        await log_channel.send(embed=timeout_log_embed)
        await ctx.reply(f"{member} has been timed out for {formatted_duration}.")

    @moderation.command(
        name="timeout",
        description="Timeout a member"
    )
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        *,
        reason: str = "No reason provided"
    ) -> None:
        """
        Timeout (mute) a member for a specified duration.

        **Usage:**
        ?moderation timeout <member> <duration> [reason]
        /moderation timeout <member> <duration> [reason]

        **Parameters:**
        member (discord.Member): The member to timeout
        duration (str): Duration of timeout (e.g., "1h", "30m", "2h30m")
        reason (str, optional): The reason for the timeout

        **Example:**
        ?moderation timeout @user 2h Spamming
        /moderation timeout @user 30m Breaking rules
        """
        await self._do_timeout(ctx, member, duration, reason)

    @commands.command(
        name="timeout",
        description="Timeout a member",
        aliases=["mute", "stfu"]
    )
    @commands.has_permissions(moderate_members=True)
    async def timeout_command(
        self,
        ctx: commands.Context,
        member: str,
        duration: str,
        *,
        reason: Optional[str] = None
    ) -> None:
        """
        Timeout (mute) a member for a specified duration.

        **Usage:**
        ?timeout <member> <duration> [reason]

        **Parameters:**
        member (str): The member's name, nickname, or ID
        duration (str): Duration of timeout (e.g., "1h", "30m", "2h30m")
        reason (str, optional): The reason for the timeout

        **Example:**
        ?timeout username 2h Spamming
        ?mute userID 30m Breaking rules
        """
        found_member: Optional[discord.Member] = await utils.find_member(ctx.guild, member)
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self._do_timeout(ctx, found_member, duration, reason if reason else "No reason provided")
    
    @moderation.command(
        name="removetimeout",
        description="Remove timeout from a member"
    )
    @commands.has_permissions(moderate_members=True)
    async def removetimeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ) -> None:
        conditions: Dict[bool, str] = {
            member == ctx.author: "You cannot remove timeout from yourself.",
            member == self.bot.user: "I can't remove timeout from myself.",
            member.top_role >= ctx.author.top_role: "Cannot remove timeout from member with higher role.",
            not ctx.guild.me.top_role > member.top_role: "Cannot remove timeout from member with higher role than me.",
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel: Optional[discord.TextChannel] = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Modlog not set. Use `/moderation setlog`.")
            return

        await member.timeout(None, reason=reason)

        timeout_log_embed = discord.Embed(
            title="Timeout Removed",
            color=discord.Color.green(),
            description=f"{member.mention}'s timeout removed by {ctx.author.mention}"
        )
        timeout_log_embed.set_thumbnail(url=member.avatar.url)
        timeout_log_embed.add_field(name="Reason", value=reason, inline=False)

        await log_channel.send(embed=timeout_log_embed)
        await ctx.reply(f"Timeout removed from {member}.")

    @commands.command(
        name="removetimeout",
        description="Remove timeout from a member",
        aliases=["unmute"]
    )
    @commands.has_permissions(moderate_members=True)
    async def removetimeout_commands_command(
        self,
        ctx: commands.Context,
        member: str,
        *,
        reason: Optional[str] = None
    ) -> None:
        found_member: Optional[discord.Member] = await utils.find_member(ctx.guild, member)
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self.removetimeout(ctx, found_member, reason=reason)

    async def _do_unban(
        self,
        ctx: commands.Context,
        user_id: str,
        reason: Optional[str] = None
    ) -> None:
        try:
            user_id = int(user_id)
            banned_users = [entry.user async for entry in ctx.guild.bans()]
            user = discord.utils.get(banned_users, id=user_id)
            
            if not user:
                raise commands.BadArgument("User not found in ban list.")
                
            await ctx.guild.unban(user, reason=reason or "No reason provided")
            
            log_channel = await self.get_log_channel(ctx.guild.id)
            if not log_channel:
                await ctx.reply("Modlog not set. Use `/moderation setlog`.")
                return

            unban_log_embed = discord.Embed(
                title="Unban Case",
                color=discord.Color.green(),
                description=f"{user.mention} unbanned by {ctx.author.mention}"
            )
            unban_log_embed.set_thumbnail(url=user.display_avatar.url)
            unban_log_embed.add_field(name="User ID", value=str(user.id), inline=False)
            unban_log_embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)

            await log_channel.send(embed=unban_log_embed)
            await ctx.reply(f"{user} has been unbanned.")
            
        except ValueError:
            raise commands.BadArgument("Please provide a valid user ID.")

    @moderation.command(name="unban", description="Unban a user")
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        reason: Optional[str] = None
    ) -> None:
        """
        Unban a user from the server.

        **Usage:**
        ?moderation unban <user_id> [reason]
        /moderation unban <user_id> [reason]

        **Parameters:**
        user_id (str): The ID of the user to unban
        reason (str, optional): The reason for the unban

        **Example:**
        ?moderation unban 123456789 Appeal accepted
        /moderation unban 123456789 Reformed
        """
        await self._do_unban(ctx, user_id, reason)

    @commands.command(
        name="unban",
        description="Unban a user",
        aliases=["unbanuser"]
    )
    @commands.has_permissions(ban_members=True)
    async def unban_command(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        reason: Optional[str] = None
    ) -> None:
        """
        Unban a user from the server.

        **Usage:**
        ?unban <user_id> [reason]

        **Parameters:**
        user_id (str): The ID of the user to unban
        reason (str, optional): The reason for the unban

        **Example:**
        ?unban 123456789 Appeal accepted
        ?unbanuser 123456789 Reformed
        """
        await self._do_unban(ctx, user_id, reason)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mod(bot))
