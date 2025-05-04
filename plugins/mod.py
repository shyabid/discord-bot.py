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
        """Server administration and moderation command suite
        
        This command group provides comprehensive tools for server administrators
        and moderators to manage users effectively. Includes capabilities for 
        timeout management, banning, kicking, and moderation logs to maintain
        a well-organized and safe server environment.
        """
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
        """Configure a dedicated channel for moderation action logs
        
        This command designates a specific text channel to receive automatic
        notifications about all moderation actions performed in the server.
        Useful for maintaining transparency and accountability among staff members.
        Only server administrators can configure this setting.
        """
        # Replace MongoDB with SQLite
        await ctx.defer()
        self.bot.db.set_modlog(ctx.guild.id, channel.id)
        await ctx.reply(
            f"Moderation log channel set to {channel.mention}"
        )

    async def get_log_channel(
        self, 
        guild_id: int
    ) -> Optional[discord.TextChannel]:
        # Replace MongoDB with SQLite
        channel_id = self.bot.db.get_modlog(guild_id)
        if channel_id:
            return self.bot.get_channel(channel_id)
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
        if deletemsg is not None and (deletemsg < 1 or deletemsg > 14):
            raise commands.BadArgument("Invalid deletemsg value. Must be 1-14.")
        elif member == ctx.author:
            raise commands.BadArgument("You cannot ban yourself.")   
        elif member == ctx.guild.owner:
            raise commands.BadArgument("I cannot ban the server owner.")    
        elif member == self.bot.user:
            raise commands.BadArgument("I can't ban myself.")
        elif member.top_role >= ctx.author.top_role and member != ctx.guild.owner:
            raise commands.BadArgument("You cannot ban member with higher or same highest role as you.")   
        elif not ctx.guild.me.top_role > member.top_role:
            raise commands.BadArgument("Cannot ban member with same or higher role than me.")

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
        
        if not member.bot:
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

        # Add case to database
        self.bot.db.add_mod_case(
            guild_id=ctx.guild.id,
            moderator_id=ctx.author.id,
            target_id=member.id,
            action="ban",
            reason=reason
        )

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
        """Permanently remove a member from the server
        
        This command bans a member from the server, preventing them from rejoining
        unless unbanned. Includes options to delete their recent message history
        and automatically notifies the user about their ban when possible.
        All ban actions are recorded in the moderation log.
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
        user: Union[discord.Member, str, int],
        *, 
        reason: Optional[str] = None
    ) -> None:
        """
        Ban a member from the server.
        """

        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except discord.NotFound:
                raise commands.BadArgument("User with that ID not found.")

        if isinstance(user, str):
            user = await utils.find_member(ctx.guild, user)
            if not user:
                raise commands.BadArgument("User not found")
      
        await self._do_ban(ctx, user, reason if reason else "No reason provided")



    async def _do_kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str
    ) -> None:
        if member == ctx.author:
            raise commands.BadArgument("You cannot kick yourself.")
        elif member == ctx.guild.owner:
            raise commands.BadArgument("Cannot kick server owner.")
        elif member == self.bot.user:
            raise commands.BadArgument("I can't kick myself.")
        elif member.top_role >= ctx.author.top_role and member != ctx.guild.owner:
            raise commands.BadArgument("Cannot kick member with higher role.")
        elif not ctx.guild.me.top_role > member.top_role:
            raise commands.BadArgument("Cannot kick member with higher role than me.")

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

        if not member.bot:
            await self._notify_user(member, "kicked", reason, ctx.guild)
        await ctx.guild.kick(member, reason=reason)
        await log_channel.send(embed=kick_log_embed)
        await ctx.reply(f"{member} has been kicked.")

        # Add case to database
        self.bot.db.add_mod_case(
            guild_id=ctx.guild.id,
            moderator_id=ctx.author.id,
            target_id=member.id,
            action="kick",
            reason=reason
        )

    @moderation.command(name="kick", description="Kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ) -> None:
        """Remove a member from the server temporarily
        
        This command kicks a member from the server, forcing them to leave
        but allowing them to rejoin with a new invite. The member will be
        notified about the kick reason when possible. All kick actions
        are recorded in the moderation log for accountability.
        """
        await self._do_kick(ctx, member, reason)

    @commands.command(name="kick", description="Kick a member", aliases=["kickmember"])
    @commands.has_permissions(kick_members=True)
    async def kick_command(
        self,
        ctx: commands.Context,
        member: Union[discord.Member, str, int],
        *,
        reason: str = "No reason provided"
    ) -> None:
        """
        Kick a member from the server.

        """

        if not isinstance(member, discord.Member):
            if isinstance(member, int):
                try:
                    member = await self.bot.fetch_user(member)
                except discord.NotFound:
                    raise commands.BadArgument("User with that ID not found.")
            else: 
                member: Optional[discord.Member] = await utils.find_member(ctx.guild, member)
                if not member:
                    raise commands.BadArgument("Member not found")
            

        await self._do_kick(ctx, member, reason)

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
        elif member == ctx.author:
            raise commands.BadArgument("You cannot timeout yourself.")
        elif member == ctx.guild.owner:
            raise commands.BadArgument("Cannot timeout server owner.")  
        elif member == self.bot.user:
            raise commands.BadArgument("I can't timeout myself.")
        elif member.bot and member != self.bot.user:
            raise commands.BadArgument("I cannot timeout other bots.")
        elif member.top_role >= ctx.author.top_role:
            raise commands.BadArgument("Cannot timeout member with higher role.")
        elif not ctx.guild.me.top_role > member.top_role and member != ctx.guild.owner:
            raise commands.BadArgument("Cannot timeout member with higher role than me.")
        elif duration_seconds < 60:
            raise commands.BadArgument("Duration must be at least 1 minute.")

        log_channel: Optional[discord.TextChannel] = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Modlog not set. Use `/moderation setlog`.")
            return

        timeout_duration = datetime.timedelta(seconds=duration_seconds)
        formatted_duration = utils.format_seconds(duration_seconds)
        
        if not member.bot:
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


        # Add case to database with duration
        self.bot.db.add_mod_case(
            guild_id=ctx.guild.id,
            moderator_id=ctx.author.id,
            target_id=member.id,
            action="timeout",
            reason=reason,
            duration=duration_seconds
        )

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
        """Temporarily restrict a member's ability to interact
        
        This command applies a timeout to a member, preventing them from sending
        messages, adding reactions, joining voice channels, or using slash commands
        for the specified duration. The member will be notified about the timeout
        when possible, and the action will be logged in the moderation channel.
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
        member: Union[discord.Member, str, int],
        duration: str,
        *,
        reason: Optional[str] = None
    ) -> None:
        """
        Timeout (mute) a member for a specified duration.
        """
        
        if not isinstance(member, discord.Member):
            if isinstance(member, int):
                try:
                    member = await self.bot.fetch_user(member)
                except discord.NotFound:
                    raise commands.BadArgument("User with that ID not found.")
                
            member: Optional[discord.Member] = await utils.find_member(ctx.guild, member)
            if not member:
                raise commands.BadArgument("Member not found")
        await self._do_timeout(ctx, member, duration, reason if reason else "No reason provided")

    
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
        """Lift an active timeout restriction from a member
        
        This command removes an active timeout from a member, immediately restoring
        their ability to send messages, add reactions, join voice channels, and use
        slash commands. The action will be recorded in the moderation log and can
        only be performed by moderators with appropriate permissions.
        """
        
        if member == ctx.author:
            raise commands.BadArgument("You cannot remove timeout from yourself.")
        elif member == self.bot.user:
            raise commands.BadArgument("I can't remove timeout from myself.")
        elif member.top_role >= ctx.author.top_role:
            raise commands.BadArgument("Cannot remove timeout from member with higher role.")
        elif not ctx.guild.me.top_role > member.top_role:
            raise commands.BadArgument("Cannot remove timeout from member with higher role than me.")

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

        # Add case to database
        self.bot.db.add_mod_case(
            guild_id=ctx.guild.id,
            moderator_id=ctx.author.id,
            target_id=member.id,
            action="untimeout",
            reason=reason
        )

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
            
            # Add case to database
            self.bot.db.add_mod_case(
                guild_id=ctx.guild.id,
                moderator_id=ctx.author.id,
                target_id=int(user_id),
                action="unban",
                reason=reason
            )
            
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
        """Remove a ban, allowing a user to rejoin the server
        
        This command removes an active ban from a user, allowing them to rejoin
        the server if they have an invite. Requires the exact user ID of the banned
        user. The unban action will be recorded in the moderation logs and can only
        be performed by members with the ban permission.
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
        """
        await self._do_unban(ctx, user_id, reason)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mod(bot))
