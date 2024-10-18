import discord
from typing import Optional
from discord import app_commands
import utils
import typing
import time
from utils import create_autocomplete_from_list as autocomplete
from discord.ext import commands
from utils import parse_time_string as strtoint
import datetime

class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.hybrid_group(name="moderation", description="Moderation commands")
    async def moderation(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply("Please specify a moderation command.")

    @moderation.command(name="setlog", description="Set the moderation log channel")
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        config_collection = self.bot.db[guild_id]["config"]
        config_collection.update_one({}, {"$set": {"modlog": channel.id}}, upsert=True)
        await ctx.reply(f"Moderation log channel set to {channel.mention}")

    async def get_log_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        config = self.bot.db[str(guild_id)]["config"].find_one({})
        if config and "modlog" in config:
            return self.bot.get_channel(config["modlog"])
        return None

    @commands.command(
        name="setlog",
        description="Set the moderation log channel",
        aliases=["setmodlog"]
    )    
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx: commands.Context, channel: discord.TextChannel):
        await self.setlog(ctx, channel)
    

    @moderation.command(name="ban", description="Ban a member")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, reason: str = "No reason provided", deletemsg: Optional[int] = None):

        conditions = {
            deletemsg is not None and (deletemsg < 1 or deletemsg > 14): "Invalid deletemsg value. It must be between 1 and 14.",
            member == ctx.author: "You cannot ban yourself.",
            member == ctx.guild.owner: "You cannot ban the server owner.",
            member == self.bot.user: "I can't ban myself. Please do it manually or through other bots.",
            member.top_role >= ctx.author.top_role: "You cannot ban a member with an equal or higher role than you.",
            not ctx.guild.me.top_role > member.top_role: "I cannot ban a member with an equal or higher role than mine."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Moderation log channel is not set. Please use `/moderation setlog` first.")
            return
        
        ban_log_embed = discord.Embed(
            title="Ban Case",
            color=discord.Color.dark_grey(),
            description=f"{member.mention} has been banned by moderator {ctx.author.mention}"
        )
        ban_log_embed.set_thumbnail(url=member.avatar.url)
        
        if reason:
            ban_log_embed.add_field(
                name="Reason", value=str(reason), inline=False
            )
        
        last_messages = []
        for channel in ctx.guild.text_channels:
            async for message in channel.history(limit=1000):
                if message.author == member:
                    last_messages.append((channel, message))

        last_messages.sort(key=lambda x: x[1].created_at, reverse=True)

        last_messages = last_messages[:3]

        last_messages_text = "\n".join([f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} in {channel.name}] {message.content}" for channel, message in last_messages]) if last_messages else "No recent messages found."
        
        ban_log_embed.add_field(
            name="User's Last Messages",
            value=last_messages_text[:1024], 
            inline=False
        )
        ban_log_embed.add_field(
            name="Banned Member Info",
            value=(
                f"Joined Server: {discord.utils.format_dt(member.joined_at, 'R')}\n"
                f"Account Created: {discord.utils.format_dt(member.created_at, 'R')}\n"
                f"Top Roles: {', '.join([role.mention for role in sorted(member.roles[1:], key=lambda r: r.position, reverse=True)[:5]])}\n"
                f"ID: {member.id}"
            ),
            inline=False
        )
        
        await log_channel.send(embed=ban_log_embed)
        await ctx.reply(f"{member} has been banned.")

        # if deletemsg:
        #     await ctx.guild.ban(member, reason=reason, delete_message_days=deletemsg)
        # else:
        #     await ctx.guild.ban(member, reason=reason)


    @commands.command(
        name="ban",
        description="Ban a member",
        aliases=["banmember"]
    )
    @commands.has_permissions(ban_members=True)
    async def ban_commands_command(self, ctx: commands.Context, args):
        args = args.split(" ")
        member = args[0]
        reason = " ".join(args[1:])
        member: discord.Member = await utils.find_member(ctx.guild, member)
        await self.ban(ctx, member, reason, 1)

    @moderation.command(name="kick", description="Kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):

        conditions = {
            member == ctx.author: "You cannot kick yourself.",
            member == ctx.guild.owner: "You cannot kick the server owner.",
            member == self.bot.user: "I can't kick myself. Please do it manually or through other bots.",
            member.top_role >= ctx.author.top_role: "You cannot kick a member with an equal or higher role than you.",
            not ctx.guild.me.top_role > member.top_role: "I cannot kick a member with an equal or higher role than mine."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Moderation log channel is not set. Please use `moderation setlog` first.")
            return

        kick_log_embed = discord.Embed(
            title="Kick Case",
            color=discord.Color.orange(),
            description=f"{member.mention} has been kicked by moderator {ctx.author.mention}"
        )
        kick_log_embed.set_thumbnail(url=member.avatar.url)

        if reason:
            kick_log_embed.add_field(
                name="Reason", value=str(reason), inline=False
            )

        last_messages = []
        for channel in ctx.guild.text_channels:
            async for message in channel.history(limit=1000):
                if message.author == member:
                    last_messages.append((channel, message))

        last_messages.sort(key=lambda x: x[1].created_at, reverse=True)

        last_messages = last_messages[:3]

        last_messages_text = "\n".join([f"[{discord.utils.format_dt(message.created_at, '')}: in {channel.name}] {message.content}" for channel, message in last_messages]) if last_messages else "No recent messages found."

        kick_log_embed.add_field(
            name="User's Last Messages",
            value=last_messages_text[:1024], 
            inline=False
        )
        kick_log_embed.add_field(
            name="Kicked Member Info",
            value=(
                f"Joined Server: {discord.utils.format_dt(member.joined_at, 'R')}\n"
                f"Account Created: {discord.utils.format_dt(member.created_at, 'R')}\n"
                f"Top Roles: {', '.join([role.mention for role in sorted(member.roles[1:], key=lambda r: r.position, reverse=True)[:5]])}\n"
                f"ID: {member.id}"
            ),
            inline=False
        )

        await log_channel.send(embed=kick_log_embed)
        await ctx.guild.kick(member, reason=reason)
        await ctx.reply(f"{member} has been kicked.")


    @moderation.command(name="timeout", description="Timeout a member")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str = "10min", *, reason: str = "No reason provided"):
        conditions = {
            member == ctx.author: "You cannot timeout yourself.",
            member == ctx.guild.owner: "You cannot timeout the server owner.",
            member == self.bot.user: "I can't timeout myself. Please do it manually or through other bots.",
            member.top_role >= ctx.author.top_role: "You cannot timeout a member with an equal or higher role than you.",
            not ctx.guild.me.top_role > member.top_role: "I cannot timeout a member with an equal or higher role than mine.",
            member.guild_permissions.administrator: "You cannot timeout an administrator."
        }

        for condition, message in conditions.items():
            if condition:
                raise commands.BadArgument(message)

        log_channel = await self.get_log_channel(ctx.guild.id)
        if not log_channel:
            await ctx.reply("Moderation log channel is not set. Please use `moderation setlog` first.")
            return

        duration_seconds = utils.parse_time_string(duration)
        if duration_seconds == 0:
            raise commands.BadArgument("Invalid duration format. Please use a valid time string (e.g., '1h 30m', '2d 4h', '90s').")

        timeout_log_embed = discord.Embed(
            title="Timeout Case",
            color=discord.Color.red(),
            description=f"{member.mention} has been timed out by moderator {ctx.author.mention}"
        )
        timeout_log_embed.set_thumbnail(url=member.avatar.url)

        if reason:
            timeout_log_embed.add_field(
                name="Reason", value=str(reason), inline=False
            )

        timeout_log_embed.add_field(
            name="Timeout Duration",
            value=utils.format_seconds(duration_seconds),
            inline=False
        )

        await log_channel.send(embed=timeout_log_embed)
        await member.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds), reason=reason)
        await ctx.reply(f"{member} has been timed out for {utils.format_seconds(duration_seconds)}.")


async def setup(bot):
    await bot.add_cog(Mod(bot))
