from discord.ext import commands
import discord
from discord import app_commands
import random
import os
import time
from typing import Optional, Dict, List
import math

def calculate_xp_for_level(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100

def calculate_level_from_xp(xp: int) -> int:
    level = 0
    while xp >= calculate_xp_for_level(level):
        xp -= calculate_xp_for_level(level)
        level += 1
    return level

def create_progress_bar(current: int, maximum: int, size: int = 10) -> str:
    """Create an ASCII progress bar."""
    filled = int((current / maximum) * size)
    return f"[{'█' * filled}{'░' * (size - filled)}]"

class ranking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldown: Dict[int, Dict[int, float]] = {}  
        self.default_card_settings = {
            "bg_color": "36393f", 
            "text_color": "ffffff",
            "xp_color": "5865f2",
            "circle_avatar": True
        }
        self.level_up_channels = {}
        self.load_level_channels()

    def load_level_channels(self):
        for guild in self.bot.guilds:
            channel_id = self.bot.db.get_levelup_channel(guild.id)
            if channel_id:
                self.level_up_channels[guild.id] = channel_id

    def get_user_data(self, guild_id: int, user_id: int) -> dict:
        xp, level, last_xp = self.bot.db.get_user_level_data(guild_id, user_id)
        return {
            "user_id": user_id,
            "xp": xp,
            "level": level,
            "last_xp": last_xp
        }

    async def update_user_data(self, guild_id: int, user_id: int, xp: int) -> tuple[int, int, bool]:
        data = self.get_user_data(guild_id, user_id)
        old_level = data["level"]
        total_xp = data["xp"] + xp
        new_level = calculate_level_from_xp(total_xp)
        self.bot.db.update_user_level(guild_id, user_id, total_xp, new_level)
        return old_level, new_level, new_level > old_level

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (message.author.bot or not message.guild or 
            isinstance(message.channel, discord.DMChannel)):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        
        if guild_id not in self.xp_cooldown:
            self.xp_cooldown[guild_id] = {}
            
        if user_id in self.xp_cooldown[guild_id]:
            if time.time() - self.xp_cooldown[guild_id][user_id] < 15:
                return

        xp_gained = random.randint(15, 25)
        old_level, new_level, leveled_up = await self.update_user_data(guild_id, user_id, xp_gained)
        
        if leveled_up:
            level_up_channel = None
            if guild_id in self.level_up_channels:
                level_up_channel = message.guild.get_channel(self.level_up_channels[guild_id])

                await level_up_channel.send(
                    f"Congratulations {message.author.mention}! You've reached level {new_level}!"
                )
            reward_role_id = self.bot.db.get_level_reward(message.guild.id, new_level)
            if reward_role_id:
                reward_role = message.guild.get_role(reward_role_id)
                if reward_role:
                    try:
                        await message.author.add_roles(reward_role)
                        await message.author.send(f"You've earned the {reward_role.mention} role! for reaching level {new_level} in {message.guild.name}")
                    except discord.HTTPException:
                        pass
            
        self.xp_cooldown[guild_id][user_id] = time.time()

    def get_user_badges(self, user: discord.Member) -> List[str]:
        badges = []
        if user.public_flags.hypesquad_bravery:
            badges.append("bravery")
        if user.public_flags.hypesquad_brilliance:
            badges.append("brilliance")
        if user.public_flags.hypesquad_balance:
            badges.append("balance")
        if user.public_flags.early_supporter:
            badges.append("early")
        if user.premium_since:
            badges.append("boost")
        if user.public_flags.verified_bot_developer:
            badges.append("developer")
        if user.public_flags.staff:
            badges.append("staff")
        return badges

    @commands.hybrid_command(
        name="rank",
        aliases=["level"],
        description="View your own or another user's level and XP progress"
    )
    @app_commands.describe(user="The user to check rank for (optional)")
    async def rank(self, ctx: commands.Context, user: Optional[discord.Member] = None) -> None:
        await ctx.defer()
        user: discord.Member = user or ctx.author
        
        data = self.get_user_data(ctx.guild.id, user.id)
        level = data["level"]
        total_xp = data["xp"]
        
        current_level_xp = total_xp - sum(calculate_xp_for_level(i) for i in range(level))
        next_level_xp = calculate_xp_for_level(level)
        
        rank = self.bot.db.get_user_rank(ctx.author.id, ctx.guild.id)

        progress = create_progress_bar(current_level_xp, next_level_xp, 15)
        percentage = (current_level_xp / next_level_xp) * 100

        def format_xp(xp: int) -> str:
            return f"{xp/1000:.1f}K" if xp >= 1000 else str(xp)

        embed = discord.Embed(
            color=user.top_role.color,
            description=f"**{user.display_name}**\nRank **#{rank}** | `{format_xp(total_xp)} XP` total"
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        def format_xp(xp: int) -> str:
            return f"{xp/1000:.1f}K" if xp >= 1000 else str(xp)

        current_formatted = format_xp(current_level_xp)
        next_formatted = format_xp(next_level_xp)

        embed.add_field(
            name=f"Level {str(level)}",
            value=f"{progress} {current_formatted}/{next_formatted} XP",
            inline=False
        )

        await ctx.reply(embed=embed)

    @commands.hybrid_group(
        name="ranking",
        description="Manage server ranking system settings and rewards"
    )
    async def ranking(self, ctx: commands.Context) -> None:
        """
        Manage the server's ranking system settings and rewards.
        Use subcommands to configure various aspects of the ranking system.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @ranking.command(
        name="leaderboard",
        description="View the server's top ranked members"
    )
    async def leaderboard(self, ctx: commands.Context) -> None:
        """
        Display the server's ranking leaderboard showing top members.

        **Usage:**
        ?ranking leaderboard
        /ranking leaderboard

        **Example:**
        ?ranking leaderboard
        """
        leaderboard_data = self.bot.db.get_guild_leaderboard(ctx.guild.id)
        
        embed = discord.Embed(
            title="Rank Leaderboard",
            color=discord.Color.dark_gray()
        )

        description = []
        for i, (user_id, xp, level) in enumerate(leaderboard_data, 1):
            user = ctx.guild.get_member(user_id)
            if user:
                description.append(
                    f"#{i} {user.mention} Level {level} `{xp:,} XP`"
                )

        if description:
            embed.description = "\n".join(description)
        else:
            embed.description = "No data available yet!"
        
        await ctx.reply(embed=embed)

    @ranking.command(
        name="reset",
        description="Reset a user's level and XP progress"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(user="The user whose progress to reset")
    async def reset(self, ctx: commands.Context, user: discord.Member) -> None:
        """
        Reset a user's level and XP back to zero.

        **Usage:**
        ?ranking reset <user>
        /ranking reset <user>

        **Parameters:**
        user: The user whose progress to reset

        **Example:**
        ?ranking reset @username
        """
        self.bot.db.reset_user_level(ctx.guild.id, user.id)
        await ctx.reply(f"Reset {user.mention}'s level and XP.")

    @ranking.command(
        name="setlevel",
        description="Set a user's level to a specific value"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        user="The user to set level for",
        level="The level to set (0 or higher)"
    )
    async def setlevel(self, ctx: commands.Context, user: discord.Member, level: int) -> None:
        """
        Set a user's level to a specific value.

        **Usage:**
        ?ranking setlevel <user> <level>
        /ranking setlevel <user> <level>

        **Parameters:**
        user: The user whose level to set
        level: The new level value (must be 0 or higher)

        **Example:**
        ?ranking setlevel @username 5
        """
        if level < 0:
            await ctx.reply("Level cannot be negative!")
            return

        total_xp = sum(calculate_xp_for_level(i) for i in range(level))
        current_xp = self.get_user_data(ctx.guild.id, user.id)["xp"]
        await self.update_user_data(ctx.guild.id, user.id, total_xp - current_xp)
        await ctx.reply(f"Set {user.mention}'s level to {level}!")

    @ranking.command(
        name="setxp",
        description="Set a user's XP to a specific amount"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        user="The user to set XP for",
        xp="The amount of XP to set (0 or higher)"
    )
    async def setxp(self, ctx: commands.Context, user: discord.Member, xp: int) -> None:
        """
        Set a user's XP to a specific amount.

        **Usage:**
        ?ranking setxp <user> <xp>
        /ranking setxp <user> <xp>

        **Parameters:**
        user: The user whose XP to set
        xp: The new XP amount (must be 0 or higher)

        **Example:**
        ?ranking setxp @username 1000
        """
        if xp < 0:
            await ctx.reply("XP cannot be negative!")
            return

        current_xp = self.get_user_data(ctx.guild.id, user.id)["xp"]
        await self.update_user_data(ctx.guild.id, user.id, xp - current_xp)
        await ctx.reply(f"Set {user.mention}'s XP to {xp}!")

    @ranking.command(
        name="setreward",
        description="Set or remove a role reward for reaching a specific level"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        level="The level at which to award the role",
        role="The role to give as reward (leave empty to remove reward)"
    )
    async def setreward(self, ctx: commands.Context, level: int, role: Optional[discord.Role] = None) -> None:
        """
        Set or remove a role reward for reaching a specific level.

        **Usage:**
        ?ranking setreward <level> [role]
        /ranking setreward <level> [role]

        **Parameters:**
        level: The level at which to award the role
        role (optional): The role to give as reward. Remove reward if not specified.

        **Example:**
        ?ranking setreward 10 @Pro
        /ranking setreward 5 @Veteran
        """
        if level < 0:
            await ctx.reply("Level cannot be negative!")
            return

        self.bot.db.set_level_reward(ctx.guild.id, level, role.id if role else None)
        if role:
            await ctx.reply(f"Set {role.mention} as the reward for level {level}!")
        else:
            await ctx.reply(f"Removed the reward for level {level}!")

    @ranking.command(
        name="rewards",
        description="Display all configured level-based role rewards"
    )
    async def rewards(self, ctx: commands.Context) -> None:
        """
        Display all configured level-based role rewards.

        **Usage:**
        ?ranking rewards
        /ranking rewards

        **Example:**
        ?ranking rewards
        """
        rewards = self.bot.db.get_level_rewards(ctx.guild.id)
        
        if not rewards:
            await ctx.reply("No level rewards have been set up yet!")
            return

        embed = discord.Embed(
            title="Level Rewards",
            color=discord.Color.dark_grey(),
            description="Here are all the role rewards you can earn by ranking up!"
        )

        total_members = len(ctx.guild.members)
        leaderboard = self.bot.db.get_guild_leaderboard(ctx.guild.id)
        users_with_levels = len(leaderboard)
        highest_level = leaderboard[0][2] if leaderboard else 0  # level is third in tuple

        embed.add_field(
            name="Statistics",
            value=f"Total Members: {total_members}\n"
                  f"Active Members: {users_with_levels}\n"
                  f"Highest Level: {highest_level}",
            inline=False
        )

        for level, role_id in rewards:
            role = ctx.guild.get_role(role_id)
            if role:
                members_with_role = len([m for m in ctx.guild.members if role in m.roles])
                embed.add_field(
                    name=f"Level {level}",
                    value=f"Role: {role.mention}\nMembers with role: {members_with_role}",
                    inline=True
                )

        await ctx.reply(embed=embed)

    @ranking.command(
        name="setchannel",
        description="Set the channel for level up announcements"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="The channel for level up messages (leave empty to reset)"
    )
    async def setchannel(
        self, 
        ctx: commands.Context, 
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        """
        Set the channel where level up messages will be sent.

        **Usage:**
        ?ranking setchannel [channel]
        /ranking setchannel [channel]

        **Parameters:**
        channel (optional): The channel for level up messages. Leave empty to reset to default behavior.

        **Examples:**
        ?ranking setchannel #level-ups
        ?ranking setchannel
        """
        self.bot.db.set_levelup_channel(ctx.guild.id, channel.id if channel else None)
        
        if channel:
            # Update cache
            self.level_up_channels[ctx.guild.id] = channel.id
            await ctx.reply(f"Level up messages will now be sent to {channel.mention}!")
        else:
            # Remove from cache
            self.level_up_channels.pop(ctx.guild.id, None)
            await ctx.reply("Level up messages is now disabled.")

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard_ctx(self, ctx): await self.leaderboard(ctx)
    
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ranking(bot))
