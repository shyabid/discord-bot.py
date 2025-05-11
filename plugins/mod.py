import discord
from typing import Optional
from discord import app_commands
import utils
import typing
from utils import PaginationView
import time
from discord.ext import commands
import datetime
from typing import Dict, Union, List, Any, cast
import shlex
import argparse
from typing import Type, TypeVar


T = TypeVar('T', bound='RoleOrChannel')

class RoleOrChannel:
    def __init__(self, roles: list[discord.Role], channels: list[discord.TextChannel]) -> None:
        self.roles = roles
        self.channels = channels

    @classmethod
    async def from_string(cls: Type[T], guild: discord.Guild, content: str) -> T:
        roles: list[discord.Role] = []
        channels: list[discord.TextChannel] = []
        
        words = content.split()
        
        for word in words:
            if word.startswith('<@&') and word.endswith('>'):
                role_id = int(word[3:-1])
                if role := guild.get_role(role_id):
                    roles.append(role)
                    
            elif word.startswith('<#') and word.endswith('>'):
                channel_id = int(word[2:-1])
                if channel := guild.get_channel(channel_id):
                    if isinstance(channel, discord.TextChannel):
                        channels.append(channel)

        return cls(roles=roles, channels=channels)


class RoleOrChannelConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
            return RoleOrChannel(roles=[role], channels=[])
        except commands.RoleNotFound:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, argument)
                return RoleOrChannel(roles=[], channels=[channel])
            except commands.ChannelNotFound:
                return await RoleOrChannel.from_string(ctx.guild, argument)
    
async def create_autocomplete_from_dict(
    interaction: discord.Interaction, 
    current: str
) -> list[app_commands.Choice[str]]:
    """Creates choices for autocompletion of rule names"""
    try:
        _ = await interaction.guild.fetch_automod_rules()
        
        rules = {}
        for r in _: 
            rules[r.name] = r.id
            
        return [
            app_commands.Choice(name=name, value=name)
            for name in rules.keys()
            if current.lower() in name.lower()
        ][:25] 
    except Exception:
        return []

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


    @commands.hybrid_group(
        name="automod",
        description="Automod commands",
        aliases=["am"]
    )
    async def automod(
        self, 
        ctx: commands.Context,
        *,
        args: str = None
    ) -> None:
        """Automod command group
        
        This command group provides tools for configuring and managing
        automatic moderation features in the server. Includes options
        for setting up filters, actions, and other automod settings.
        
        CLI-style subcommands:
        ```
          ls, list              List all automod rules
          mkrule, mkrl, create  Create a new automod rule```
        
        For creating rules (`mkrule`), the following parameters are available:
        ```
        -n, --name NAME       Rule name 
        -t, --trigger WORDS   Trigger words, comma separated 
        -b, --block           Block messages containing triggers (default: True)
        -a, --alert CHANNEL   Channel to send alerts to
        -d, --duration DUR    Timeout duration: '1 Minute', '3 Minute', '5 Minute',
                               or "Don't Timeout" (default: "Don't Timeout")
        -i, --bypass ROLES    Roles or channels that bypass the rule
        ```     
        Examples:
          !automod list
          !automod mkrule -n "No Profanity" -t "bad,words,here" -a #alerts -d "1 Minute"
          !automod create -n "No Links" -t "http,https,www" --block
        """
        if ctx.invoked_subcommand is None:
            if not args:
                await ctx.reply("Please specify a subcommand")
                return
                
            if args.startswith(("ls", "list")): 
                await self.automod_list(ctx)
                return
                
            if args.startswith(("mkrule", "mkrl", "create")):
                try:
                    parser = argparse.ArgumentParser(exit_on_error=False)
                    parser.add_argument('-n', '--name', required=True, help='Rule name')
                    parser.add_argument('-t', '--trigger', required=True, help='Trigger words (comma separated)')
                    parser.add_argument('-b', '--block', action='store_true', help='Block messages', default=True) 
                    parser.add_argument('-a', '--alert', type=str, help='Alert channel', default=None) 
                    parser.add_argument('-d', '--duration', choices=['1 Minute', '3 Minute', '5 Minute', "Don't Timeout"], 
                        default="Don't Timeout", help='Timeout duration') 
                    parser.add_argument('-i', '--bypass', type=str, help='Roles or channels to bypass', default=None)  
                    
                    args = ' '.join(args.split()[1:]) # Remove the command name
                    split_args = shlex.split(args)
                    parsed_args = parser.parse_args(split_args)
                    
                    alert_channel = None
                    if parsed_args.alert:
                        alert_channel = await commands.TextChannelConverter().convert(ctx, parsed_args.alert)
                    
                    bypass = None
                    if parsed_args.bypass:
                        bypass = await RoleOrChannel.from_string(ctx.guild, parsed_args.bypass)

                    await self.automod_rules_add(
                        ctx,
                        parsed_args.name,
                        parsed_args.trigger,
                        parsed_args.block,
                        alert_channel,
                        parsed_args.duration,
                        bypass
                    )
                except Exception as e:
                    await ctx.reply(f"Error parsing command: {str(e)}")

    @automod.error
    async def automod_err(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You don't have permission to use this command")
        elif "AUTO_MODERATION_MAX_RULES_OF_TYPE_EXCEEDED" in str(error):
            await ctx.reply("Maximum number of automod rules reached (6).")
        else:
            await ctx.reply(f"An error occurred: {str(error)}")
    
    @automod.command(name="rules", description="List all automod rules")
    @commands.has_permissions(manage_guild=True)
    async def automod_list(self, ctx: commands.Context) -> None:
        all_rules: List[discord.AutoModRule] = await ctx.guild.fetch_automod_rules()

        if not all_rules:
            await ctx.reply("No automod rules found.")
            return
        
        embeds: List[discord.Embed] = []
        for rule in all_rules:
            e = discord.Embed(
                title=rule.name,
                color=discord.Color.dark_grey()
            )
            e.description = f"Rule ID: `{rule.id}`\n"
            e.description += f"Excempt Channels: {', '.join([f'{channel.mention}' for channel in rule.exempt_channels]) if rule.exempt_channels else 'None'}\n"
            e.description += f"Excempt Roles: {', '.join([f'{role.mention}' for role in rule.exempt_roles]) if rule.exempt_roles else 'None'}\n"
            e.description += f"Actions: {', '.join([f'`{action.type}`' for action in rule.actions]) if rule.actions else 'None'}\n"
            e.description += f"Enabled: {rule.enabled}\n"
            e.description += f"Trigger(s):\n" + ', '.join([f'`{trigger}`' for trigger in rule.trigger.keyword_filter]) if hasattr(rule.trigger, 'keyword_filter') else 'No keywords'
            embeds.append(e)
            
        view = PaginationView(embeds, author=ctx.author, timeout=3600)
        await ctx.reply(embed=embeds[0], view=view,)
        
    
    @automod.command(name="delete", description="Delete an automod rule")
    @commands.has_permissions(manage_guild=True)
    async def automod_delete(
        self, 
        ctx: commands.Context, 
        rule_id: int
    ) -> None:
        """Delete an automod rule from the server
        
        This command removes an existing automatic moderation rule from the server.
        The rule will no longer be applied to messages in the server.
        """
        try:
            rule = await ctx.guild.fetch_automod_rule(rule_id)
            await rule.delete()
            await ctx.reply(f"Deleted automod rule: {rule.name}")
        except discord.NotFound:
            await ctx.reply("Automod rule not found.")
        except discord.Forbidden:
            await ctx.reply("I don't have permission to delete this automod rule.")
    
    
    @automod.command(name="create", description="Add a new automod rule")
    async def automod_rules_add(
        self, 
        ctx: commands.Context, 
        name: str,
        trigger: str,
        block_mesasges: bool = True,
        alert: discord.TextChannel = None,
        timeout: typing.Literal["1 Minute", "3 Minute", "5 Minute", "Don't Timeout"] = "Don't Timeout",
        bypass: RoleOrChannelConverter = None,
    ) -> None:
        """Add a new automod rule to the server
        
        This command creates a new automatic moderation rule with the specified
        trigger and action. The rule will be applied to all messages in the server
        and can help maintain a safe and respectful environment.
        """
        trigger_words = trigger.split(',')
        trigger_words = [word.strip() for word in trigger_words]

        actions = []
        if block_mesasges:
            actions.append(discord.AutoModRuleAction(
                type=discord.AutoModRuleActionType.block_message
            ))

        if alert:
            if isinstance(alert, discord.TextChannel):
                actions.append(discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.send_alert_message,
                    channel_id=alert.id
                ))
                print(alert.id)

        if timeout != "Don't Timeout":
            duration = {
                "1 Minute": 60,
                "3 Minute": 180, 
                "5 Minute": 300
            }[timeout]
            actions.append(discord.AutoModRuleAction(
                type=discord.AutoModRuleActionType.timeout,
                duration=datetime.timedelta(seconds=duration)
            ))
            
        rule = await ctx.guild.create_automod_rule(
            name=name,
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.keyword,
                keyword_filter=trigger_words
            ),
            actions=actions,
            enabled=True,
            exempt_roles=bypass.roles if bypass else [],
            exempt_channels=bypass.channels if bypass else [],
        )

        print(rule.id)
        await ctx.reply(f"Created automod rule: {rule.name}")
    

    @automod.command(
        name="edit",
        description="Edit an existing automod rule"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.autocomplete(rule_name=create_autocomplete_from_dict)
    async def automod_edit(
        self,
        ctx: commands.Context,
        rule_name: str
    ) -> None:
        """Edit an existing automod rule
        
        This command allows you to modify various aspects of an existing automod rule
        including triggers, actions, bypasses and other settings through an interactive
        menu interface.
        """
        # Get all automod rules and create name->id mapping
        _ = await ctx.guild.fetch_automod_rules()
        
        rules = {}
        for r in _: 
            rules[r.name] = r.id
        
        if rule_name not in rules:
            await ctx.reply("Rule not found")
            return
            
        rule = await ctx.guild.fetch_automod_rule(rules[rule_name])

        # Create edit options
        options = [
            discord.SelectOption(
                label="Rule Name",
                value="name",
                description="Change the rule name"
            ),
            discord.SelectOption(
                label="Trigger Words", 
                value="trigger",
                description="Edit trigger word list"
            ),
            discord.SelectOption(
                label="Block Messages",
                value="block",
                description="Toggle message blocking"
            ),
            discord.SelectOption(
                label="Alert Channel",
                value="alert",
                description="Change alert channel"
            ),
            discord.SelectOption(
                label="Timeout Duration",
                value="timeout",
                description="Modify timeout duration"
            ),
            discord.SelectOption(
                label="Bypass Roles/Channels",
                value="bypass",
                description="Edit bypass settings"
            )
        ]

        class EditModal(discord.ui.Modal):
            def __init__(self, field: str, current_value: str):
                super().__init__(title=f"Edit {field.title()}")
                self.field = field
                
                if field == "trigger":
                    # Large text box for trigger words
                    self.value = discord.ui.TextInput(
                        label="Trigger Words (comma separated)",
                        style=discord.TextStyle.paragraph,
                        default=current_value,
                        placeholder="word1, word2, word3",
                        required=True
                    )
                else:
                    # Regular text input for other fields
                    self.value = discord.ui.TextInput(
                        label=field.title(),
                        default=current_value,
                        required=True
                    )
                self.add_item(self.value)

        class RuleEditView(discord.ui.View):
            def __init__(self, original_rule):
                super().__init__(timeout=300)
                self.rule = original_rule
                self.message = None
                self.modified = False

                # Add alert channel select
                alert_channel = next(
                    (a.channel_id for a in self.rule.actions
                    if a.type == discord.AutoModRuleActionType.send_alert_message),
                    None
                )

                self.alert_select = discord.ui.ChannelSelect(
                    placeholder="Select alert channel",
                    channel_types=[discord.ChannelType.text],
                    default_values=[ctx.guild.get_channel(alert_channel)] if alert_channel else None,
                    min_values=0,
                    max_values=1
                )
                self.alert_select.callback = self.alert_channel_callback
                self.add_item(self.alert_select)

                # Add bypass role select
                self.role_select = discord.ui.RoleSelect(
                    placeholder="Select bypass roles", 
                    min_values=0,
                    max_values=25,
                    default_values=self.rule.exempt_roles
                )
                self.role_select.callback = self.bypass_role_callback
                self.add_item(self.role_select)

                # Add bypass channel select
                self.channel_select = discord.ui.ChannelSelect(
                    placeholder="Select bypass channels",
                    channel_types=[discord.ChannelType.text],
                    min_values=0, 
                    max_values=25,
                    default_values=self.rule.exempt_channels
                )
                self.channel_select.callback = self.bypass_channel_callback
                self.add_item(self.channel_select)

            async def update_preview(self):
                embed = discord.Embed(
                    title=self.rule.name,
                    color=discord.Color.dark_grey()
                )
                embed.description = f"Rule ID: `{self.rule.id}`\n"
                embed.description += f"Excempt Channels: {', '.join([f'{channel.mention}' for channel in self.rule.exempt_channels]) if self.rule.exempt_channels else 'None'}\n"
                embed.description += f"Excempt Roles: {', '.join([f'{role.mention}' for role in self.rule.exempt_roles]) if self.rule.exempt_roles else 'None'}\n"
                embed.description += f"Actions: {', '.join([f'`{action.type}`' for action in self.rule.actions]) if self.rule.actions else 'None'}\n"
                embed.description += f"Enabled: {self.rule.enabled}\n"
                embed.description += f"Trigger(s):\n" + ', '.join([f'`{trigger}`' for trigger in self.rule.trigger.keyword_filter]) if hasattr(self.rule.trigger, 'keyword_filter') else 'No keywords'
                
                if self.message:
                    await self.message.edit(embed=embed)

            async def save_changes(self):
                try:
                    await self.rule.edit(
                        name=self.rule.name,
                        event_type=self.rule.event_type,
                        trigger=self.rule.trigger,
                        actions=self.rule.actions,
                        enabled=self.rule.enabled,
                        exempt_roles=self.rule.exempt_roles,
                        exempt_channels=self.rule.exempt_channels
                    )
                    return True
                except Exception as e:
                    return str(e)

            async def bypass_role_callback(self, interaction: discord.Interaction):
                try:
                    await self.rule.edit(exempt_roles=self.role_select.values)
                    self.modified = True
                    await self.update_preview()
                    await interaction.response.send_message("Updated bypass roles!", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Error updating bypass roles: {str(e)}", ephemeral=True)

            async def bypass_channel_callback(self, interaction: discord.Interaction):
                try:
                    await self.rule.edit(exempt_channels=self.channel_select.values)
                    self.modified = True
                    await self.update_preview()
                    await interaction.response.send_message("Updated bypass channels!", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Error updating bypass channels: {str(e)}", ephemeral=True)

            async def alert_channel_callback(self, interaction: discord.Interaction):
                self.rule._actions = [
                    a for a in self.rule.actions 
                    if a.type != discord.AutoModRuleActionType.send_alert_message
                ]
                
                if self.alert_select.values:
                    self.rule._actions.append(discord.AutoModRuleAction(
                        type=discord.AutoModRuleActionType.send_alert_message,
                        channel_id=self.alert_select.values[0].id
                    ))
                
                await self.update_preview()
                result = await self.save_changes()
                if isinstance(result, str):
                    await interaction.response.send_message(f"Error saving changes: {result}", ephemeral=True)
                else:
                    await interaction.response.send_message("Changes saved!", ephemeral=True)

            @discord.ui.select(
                placeholder="Select what to edit",
                options=options
            )
            async def select_edit(self, interaction: discord.Interaction, select: discord.ui.Select):
                field = select.values[0]
                
                if field == "name":
                    modal = EditModal("name", self.rule.name)

                elif field == "trigger":
                    current = ", ".join(self.rule.trigger.keyword_filter)
                    modal = EditModal("trigger words", current)
                
                elif field == "block":
                    has_block = any(a.type == discord.AutoModRuleActionType.block_message for a in self.rule.actions)
                    self.rule._actions = [
                        a for a in self.rule.actions 
                        if a.type != discord.AutoModRuleActionType.block_message
                    ]
                    if not has_block:
                        self.rule._actions.append(discord.AutoModRuleAction(
                            type=discord.AutoModRuleActionType.block_message
                        ))
                    await self.update_preview()
                    result = await self.save_changes()
                    if isinstance(result, str):
                        await interaction.response.send_message(f"Error saving changes: {result}", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"Block messages: {not has_block}\nChanges saved!", ephemeral=True)
                    return

                elif field == "timeout":
                    timeout_action = next(
                        (a for a in self.rule.actions 
                         if a.type == discord.AutoModRuleActionType.timeout),
                        None
                    )
                    current = f"{timeout_action.duration.seconds if timeout_action else 0} seconds"
                    modal = EditModal("timeout duration", current)

                async def modal_callback(interaction: discord.Interaction):
                    try:
                        if field == "name":
                            self.rule._name = modal.value.value
                            
                        elif field == "trigger":
                            words = [w.strip() for w in modal.value.value.split(",")]
                            self.rule._trigger.keyword_filter = words
                            
                        elif field == "timeout":
                            seconds = int(modal.value.value.split()[0])
                            self.rule._actions = [
                                a for a in self.rule.actions 
                                if a.type != discord.AutoModRuleActionType.timeout
                            ]
                            if seconds > 0:
                                self.rule._actions.append(discord.AutoModRuleAction(
                                    type=discord.AutoModRuleActionType.timeout,
                                    duration=datetime.timedelta(seconds=seconds)
                                ))

                        await self.update_preview()
                        result = await self.save_changes()
                        if isinstance(result, str):
                            await interaction.response.send_message(f"Error saving changes: {result}", ephemeral=True)
                        else:
                            await interaction.response.send_message(f"Updated {field} successfully!\nChanges saved!", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"Error updating {field}: {str(e)}", ephemeral=True)

                modal.on_submit = modal_callback
                await interaction.response.send_modal(modal)

        # Create initial preview embed
        embed = discord.Embed(
            title=rule.name,
            color=discord.Color.dark_grey()
        )
        embed.description = f"Rule ID: `{rule.id}`\n"
        embed.description += f"Excempt Channels: {', '.join([f'{channel.mention}' for channel in rule.exempt_channels]) if rule.exempt_channels else 'None'}\n"
        embed.description += f"Excempt Roles: {', '.join([f'{role.mention}' for role in rule.exempt_roles]) if rule.exempt_roles else 'None'}\n"
        embed.description += f"Actions: {', '.join([f'`{action.type}`' for action in rule.actions]) if rule.actions else 'None'}\n"
        embed.description += f"Enabled: {rule.enabled}\n"
        embed.description += f"Trigger(s):\n" + ', '.join([f'`{trigger}`' for trigger in rule.trigger.keyword_filter]) if hasattr(rule.trigger, 'keyword_filter') else 'No keywords'

        view = RuleEditView(rule)
        view.message = await ctx.reply(
            f"Editing rule: {rule.name}\nSelect what you want to edit:",
            embed=embed,
            view=view
        )
    

    
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mod(bot))
