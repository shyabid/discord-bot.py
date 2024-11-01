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

    @commands.command(
        name="ban",
        description="Ban a member",
        aliases=["banmember"]
    )
    @commands.has_permissions(ban_members=True)
    async def ban_commands_command(
        self, 
        ctx: commands.Context, 
        member: str, 
        *, 
        reason: Optional[str] = None
    ) -> None:
        found_member: Optional[discord.Member] = (
            await utils.find_member(ctx.guild, member)
        )
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self.ban(ctx, found_member, reason, 1)

    @moderation.command(
        name="kick", 
        description="Kick a member"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ) -> None:
        conditions: Dict[bool, str] = {
            member == ctx.author: 
                "You cannot kick yourself.",
            member == ctx.guild.owner: 
                "Cannot kick server owner.", 
            member == self.bot.user: 
                "I can't kick myself.",
            member.top_role >= ctx.author.top_role:
                "Cannot kick member with higher role.",
            not ctx.guild.me.top_role > member.top_role:
                "Cannot kick member with higher role than me."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel: Optional[discord.TextChannel] = (
            await self.get_log_channel(ctx.guild.id)
        )
        if not log_channel:
            await ctx.reply(
                "Modlog not set. Use `?setlog #channel`."
            )
            return

        kick_log_embed: discord.Embed = discord.Embed(
            title="Kick Case",
            color=discord.Color.orange(),
            description=(
                f"{member.mention} kicked by "
                f"{ctx.author.mention}"
            )
        )
        kick_log_embed.set_thumbnail(url=member.avatar.url)

        if reason:
            kick_log_embed.add_field(
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

        await ctx.guild.kick(member, reason=reason)
        await log_channel.send(embed=kick_log_embed)
        await ctx.reply(f"{member} has been kicked.")

    @commands.command(
        name="kick",
        description="Kick a member",
        aliases=["kickmember"]
    )
    @commands.has_permissions(kick_members=True)
    async def kick_commands_command(
        self, 
        ctx: commands.Context, 
        member: str, 
        *, reason: Optional[str] = None
    ) -> None:
        found_member: Optional[discord.Member] = (
            await utils.find_member(ctx.guild, member)
        )
        if not found_member:
            raise commands.BadArgument("Member not found")
        await self.kick(ctx, found_member, reason)

    # @moderation.command(
    #     name="timeout",
    #     description="Timeout a member"
    # )
    # @commands.has_permissions(moderate_members=True)
    # async def timeout(
    #     self,
    #     ctx: commands.Context,
    #     member: discord.Member,
    #     duration: str = "10min",
    #     *,
    #     reason: str = "No reason provided"
    # ) -> None:
    #     conditions: Dict[bool, str] = {
    #         member == ctx.author:
    #             "You cannot timeout yourself.",
    #         member == ctx.guild.owner:
    #             "Cannot timeout server owner.", 
    #         member == self.bot.user:
    #             "I can't timeout myself.",
    #         member.top_role >= ctx.author.top_role:
    #             "Cannot timeout member with higher role.",
    #         not ctx.guild.me.top_role > member.top_role:
    #             "Cannot timeout member with higher role than me.",
    #         member.guild_permissions.administrator:
    #             "Cannot timeout an administrator."
    #     }

    #     for condition, message in conditions.items():
    #         if condition:
    #             raise commands.BadArgument(message)

    #     log_channel: Optional[discord.TextChannel] = (
    #         await self.get_log_channel(ctx.guild.id)
    #     )
    #     if not log_channel:
    #         await ctx.reply(
    #             "Modlog not set. Use `moderation setlog`."
    #         )
    #         return

    #     duration_seconds: int = utils.parse_time_string(duration)
    #     if duration_seconds == 0:
    #         raise commands.BadArgument(
    #             "Invalid duration. Use format: '1h 30m', '2d', '90s'"
    #         )

    #     timeout_log_embed: discord.Embed = discord.Embed(
    #         title="Timeout Case",
    #         color=discord.Color.red(),
    #         description=(
    #             f"{member.mention} timed out by "
    #             f"{ctx.author.mention}"
    #         )
    #     )
    #     timeout_log_embed.set_thumbnail(url=member.avatar.url)

    #     if reason:
    #         timeout_log_embed.add_field(
    #             name="Reason",
    #             value=str(reason),
    #             inline=False
    #         )

    #     timeout_log_embed.add_field(
    #         name="Timeout Duration",
    #         value=utils.format_seconds(duration_seconds),
    #         inline=False
    #     )

    #     await member.timeout(
    #         discord.utils.utcnow() + 
    #         datetime.timedelta(seconds=duration_seconds),
    #         reason=reason
    #     )
    #     await ctx.reply(
    #         f"{member} timed out for "
    #         f"{utils.format_seconds(duration_seconds)}."
    #     )
    #     await log_channel.send(embed=timeout_log_embed)

    # @commands.command(
    #     name="timeout",
    #     description="Timeout a member",
    #     aliases=["timeoutmember"]
    # )
    # @commands.has_permissions(moderate_members=True)
    # async def timeout_commands_command(
    #     self, 
    #     ctx: commands.Context, 
    #     member: str, 
    #     duration: str = "10min",
    #     *, reason: Optional[str] = None
    # ) -> None: 
    #     found_member: Optional[discord.Member] = (
    #         await utils.find_member(ctx.guild, member)
    #     )
    #     if not found_member:
    #         raise commands.BadArgument("Member not found")
        
    #     await self.timeout(
    #         ctx,
    #         member=found_member,
    #         duration=duration,
    #         reason=reason if reason else "No reason provided"
    #     )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mod(bot))
