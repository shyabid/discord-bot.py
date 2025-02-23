from discord.ext import commands
import discord
from discord import app_commands
import random
import os
import time
import io
import aiohttp
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

class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldown: Dict[int, Dict[int, float]] = {}  # {guild_id: {user_id: last_xp_time}}
        self.default_card_settings = {
            "bg_color": "36393f",  # Discord dark theme color
            "text_color": "ffffff",
            "xp_color": "5865f2",
            "circle_avatar": True
        }

    def get_user_data(self, guild_id: int, user_id: int) -> dict:
        return self.bot.db[str(guild_id)]["leveling"].find_one({"user_id": user_id}) or {
            "user_id": user_id,
            "xp": 0,
            "level": 0,
            "last_xp": 0
        }

    async def update_user_data(self, guild_id: int, user_id: int, xp: int) -> tuple[int, int, bool]:
        data = self.get_user_data(guild_id, user_id)
        old_level = data["level"]
        total_xp = data["xp"] + xp
        new_level = calculate_level_from_xp(total_xp)
        
        self.bot.db[str(guild_id)]["leveling"].update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "xp": total_xp,
                "level": new_level,
                "last_xp": time.time()
            }},
            upsert=True
        )
        
        return old_level, new_level, new_level > old_level

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (message.author.bot or not message.guild or 
            isinstance(message.channel, discord.DMChannel)):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        
        # Check cooldown
        if guild_id not in self.xp_cooldown:
            self.xp_cooldown[guild_id] = {}
            
        if user_id in self.xp_cooldown[guild_id]:
            if time.time() - self.xp_cooldown[guild_id][user_id] < 15:
                return

        xp_gained = random.randint(15, 25)
        old_level, new_level, leveled_up = await self.update_user_data(guild_id, user_id, xp_gained)
        
        if leveled_up:
            await message.channel.send(
                f"🎉 Congratulations {message.author.mention}! You've reached level {new_level}!"
            )
            # Check for rewards
            reward_role = await self.get_level_reward(message.guild.id, new_level)
            if reward_role:
                try:
                    await message.author.add_roles(reward_role)
                    await message.channel.send(f"You've earned the {reward_role.mention} role!")
                except discord.HTTPException:
                    pass
            
        self.xp_cooldown[guild_id][user_id] = time.time()

    async def get_level_reward(self, guild_id: int, level: int) -> Optional[discord.Role]:
        reward_data = self.bot.db[str(guild_id)]["level_rewards"].find_one({"level": level})
        if reward_data and reward_data.get("role_id"):
            guild = self.bot.get_guild(guild_id)
            return guild.get_role(reward_data["role_id"])
        return None

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
        if user.premium_since:  # Check if user is boosting
            badges.append("boost")
        if user.public_flags.verified_bot_developer:
            badges.append("developer")
        if user.public_flags.staff:
            badges.append("staff")
        return badges

    def get_card_settings(self, guild_id: int) -> dict:
        settings = self.bot.db[str(guild_id)]["config"].find_one({"_id": "card_settings"})
        return settings or self.default_card_settings.copy()

    @commands.hybrid_command(
        name="rank",
        description="View your own or another user's level card with rank, XP, and progress"
    )
    @app_commands.describe(user="The user to check rank for (optional)")
    async def rank(self, ctx: commands.Context, user: Optional[discord.Member] = None) -> None:
        """
        Shows a user's rank card with their level, XP, and ranking information.

        **Usage:**
        ?rank [user]
        /rank [user]

        **Parameters:**
        user (optional): The user whose rank to check. Shows your own rank if not specified.

        **Example:**
        ?rank @username
        /rank @username
        """
        await ctx.defer()
        user = user or ctx.author
        
        # Get server-wide card settings
        card_settings = self.get_card_settings(ctx.guild.id)
        
        data = self.get_user_data(ctx.guild.id, user.id)
        
        # Calculate current level progress
        level = data["level"]
        total_xp = data["xp"]
        level_xp = calculate_xp_for_level(level)
        next_level_xp = calculate_xp_for_level(level + 1)
        current_level_xp = total_xp - sum(calculate_xp_for_level(i) for i in range(level))
        
        # Get user rank
        rank = 1
        all_users = self.bot.db[str(ctx.guild.id)]["leveling"].find().sort("xp", -1)
        for user_data in all_users:
            if user_data["user_id"] == user.id:
                break
            rank += 1

        # Get user badges
        badges = self.get_user_badges(user)
        badges_str = "|".join(badges) if badges else "none"

        # Generate colors based on user's top role color
        role_color = user.top_role.color
        hex_color = f"{role_color.value:0>6x}"
        
        # Calculate contrasting colors for text and XP bar
        brightness = (role_color.r * 299 + role_color.g * 587 + role_color.b * 114) / 1000
        text_color = "ffffff" if brightness < 128 else "000000"
        xp_color = hex_color  # Using role color for XP bar

        # Generate rank card URL with custom settings - fixed color replacements
        base_url = os.getenv("API_LEVELING")
        rank_card_url = (
            base_url
            .replace("DummyUser", user.display_name)
            .replace("avatar=https://avatars.githubusercontent.com/u/136696763?v=4", f"avatar={user.display_avatar.url}")
            .replace("currentXp=1500", f"currentXp={current_level_xp}")
            .replace("nextLevelXp=2000", f"nextLevelXp={level_xp}")
            .replace("previousLevelXp=1000", f"previousLevelXp=0")
            .replace("level=3", f"level={level}")
            .replace("rank=25", f"rank={rank}")
            .replace("customBg=HEX_COLOR", f"customBg={card_settings['bg_color']}")
            .replace("textShadowColor=HEX_COLOR", f"textShadowColor={card_settings['text_color']}")
            .replace("xpColor=HEX_COLOR", f"xpColor={card_settings['xp_color']}")
            .replace("circleAvatar=true", f"circleAvatar={str(card_settings['circle_avatar']).lower()}")
            .replace("badges=developer|boost|bravery", f"badges={badges_str}")
        )

        # Send the image directly without embed
        async with aiohttp.ClientSession() as session:
            async with session.get(rank_card_url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    await ctx.reply(file=discord.File(fp=io.BytesIO(image_data), filename="rank.png"))
                else:
                    await ctx.reply("Failed to generate rank card.")

    @commands.hybrid_group(
        name="leveling",
        description="Manage server leveling system settings and rewards"
    )
    async def leveling(self, ctx: commands.Context) -> None:
        """
        Manage the server's leveling system settings and rewards.
        Use subcommands to configure various aspects of the leveling system.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @leveling.command(
        name="leaderboard",
        description="View the server's top ranked members"
    )
    async def leaderboard(self, ctx: commands.Context) -> None:
        """
        Display the server's leveling leaderboard showing top members.

        **Usage:**
        ?leveling leaderboard
        /leveling leaderboard

        **Example:**
        ?leveling leaderboard
        """
        data = self.bot.db[str(ctx.guild.id)]["leveling"].find().sort("xp", -1).limit(10)
        
        embed = discord.Embed(
            title="🏆 Leaderboard",
            color=discord.Color.dark_grey()
        )
        
        for i, user_data in enumerate(data, 1):
            user = ctx.guild.get_member(user_data["user_id"])
            if user:
                embed.add_field(
                    name=f"#{i} {user.display_name}",
                    value=f"Level: {user_data['level']} | XP: {user_data['xp']}",
                    inline=False
                )
        
        await ctx.reply(embed=embed)

    @leveling.command(
        name="reset",
        description="Reset a user's level and XP progress"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(user="The user whose progress to reset")
    async def reset(self, ctx: commands.Context, user: discord.Member) -> None:
        """
        Reset a user's level and XP back to zero.

        **Usage:**
        ?leveling reset <user>
        /leveling reset <user>

        **Parameters:**
        user: The user whose progress to reset

        **Example:**
        ?leveling reset @username
        """
        self.bot.db[str(ctx.guild.id)]["leveling"].delete_one({"user_id": user.id})
        await ctx.reply(f"Reset {user.mention}'s level and XP.")

    @leveling.command(
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
        ?leveling setlevel <user> <level>
        /leveling setlevel <user> <level>

        **Parameters:**
        user: The user whose level to set
        level: The new level value (must be 0 or higher)

        **Example:**
        ?leveling setlevel @username 5
        """
        if level < 0:
            await ctx.reply("Level cannot be negative!")
            return

        total_xp = sum(calculate_xp_for_level(i) for i in range(level))
        await self.update_user_data(ctx.guild.id, user.id, total_xp - self.get_user_data(ctx.guild.id, user.id)["xp"])
        await ctx.reply(f"Set {user.mention}'s level to {level}!")

    @leveling.command(name="setxp", description="Set a user's XP to a specific amount")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        user="The user to set XP for",
        xp="The amount of XP to set (0 or higher)"
    )
    async def setxp(self, ctx: commands.Context, user: discord.Member, xp: int) -> None:
        """
        Set a user's XP to a specific amount.

        **Usage:**
        ?leveling setxp <user> <xp>
        /leveling setxp <user> <xp>

        **Parameters:**
        user: The user whose XP to set
        xp: The new XP amount (must be 0 or higher)

        **Example:**
        ?leveling setxp @username 1000
        """
        if xp < 0:
            await ctx.reply("XP cannot be negative!")
            return

        await self.update_user_data(ctx.guild.id, user.id, xp - self.get_user_data(ctx.guild.id, user.id)["xp"])
        await ctx.reply(f"Set {user.mention}'s XP to {xp}!")

    @leveling.command(
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
        ?leveling setreward <level> [role]
        /leveling setreward <level> [role]

        **Parameters:**
        level: The level at which to award the role
        role (optional): The role to give as reward. Remove reward if not specified.

        **Example:**
        ?leveling setreward 10 @Pro
        /leveling setreward 5 @Veteran
        """
        if level < 0:
            await ctx.reply("Level cannot be negative!")
            return

        if role:
            self.bot.db[str(ctx.guild.id)]["level_rewards"].update_one(
                {"level": level},
                {"$set": {"role_id": role.id}},
                upsert=True
            )
            await ctx.reply(f"Set {role.mention} as the reward for level {level}!")
        else:
            self.bot.db[str(ctx.guild.id)]["level_rewards"].delete_one({"level": level})
            await ctx.reply(f"Removed the reward for level {level}!")

    @leveling.command(name="rewards", description="Display all configured level-based role rewards")
    async def rewards(self, ctx: commands.Context) -> None:
        """
        Display all configured level-based role rewards.

        **Usage:**
        ?leveling rewards
        /leveling rewards

        **Example:**
        ?leveling rewards
        """
        rewards = list(self.bot.db[str(ctx.guild.id)]["level_rewards"].find().sort("level", 1))
        
        if not rewards:
            await ctx.reply("No level rewards have been set up yet!")
            return

        embed = discord.Embed(
            title="🎁 Level Rewards",
            color=discord.Color.dark_grey(),
            description="Here are all the role rewards you can earn by leveling up!"
        )

        total_members = len(ctx.guild.members)
        users_with_levels = self.bot.db[str(ctx.guild.id)]["leveling"].count_documents({})
        highest_level = self.bot.db[str(ctx.guild.id)]["leveling"].find_one(sort=[("level", -1)])

        embed.add_field(
            name="📊 Statistics",
            value=f"Total Members: {total_members}\n"
                  f"Active Members: {users_with_levels}\n"
                  f"Highest Level: {highest_level['level'] if highest_level else 0}",
            inline=False
        )

        for reward in rewards:
            role = ctx.guild.get_role(reward["role_id"])
            if role:
                members_with_role = len([m for m in ctx.guild.members if role in m.roles])
                embed.add_field(
                    name=f"Level {reward['level']}",
                    value=f"Role: {role.mention}\nMembers with role: {members_with_role}",
                    inline=True
                )

        await ctx.reply(embed=embed)

    @leveling.command(
        name="customize",
        description="Customize the server's rank card appearance"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        bg_color="Background color in HEX (e.g., ff0000 for red)",
        text_color="Text color in HEX (e.g., ffffff for white)",
        xp_color="XP bar color in HEX (e.g., 5865f2 for Discord blue)",
        circle_avatar="Whether to display avatar in a circle"
    )
    async def customize(
        self, 
        ctx: commands.Context, 
        bg_color: Optional[str] = None,
        text_color: Optional[str] = None,
        xp_color: Optional[str] = None,
        circle_avatar: Optional[bool] = None
    ) -> None:
        """
        Customize the appearance of the server's rank cards.

        **Usage:**
        ?leveling customize [options]
        /leveling customize [options]

        **Parameters:**
        bg_color (optional): Background color in HEX format
        text_color (optional): Text color in HEX format
        xp_color (optional): XP bar color in HEX format
        circle_avatar (optional): Whether to show avatars in circles

        **Example:**
        ?leveling customize bg_color:36393f text_color:ffffff xp_color:5865f2
        """
        """Customize server-wide rank card appearance"""
        
        # Get current settings
        current_settings = self.get_card_settings(ctx.guild.id)
        
        # Update settings
        if bg_color is not None:
            current_settings["bg_color"] = bg_color.lower().replace("#", "")
        if text_color is not None:
            current_settings["text_color"] = text_color.lower().replace("#", "")
        if xp_color is not None:
            current_settings["xp_color"] = xp_color.lower().replace("#", "")
        if circle_avatar is not None:
            current_settings["circle_avatar"] = circle_avatar

        # Save settings
        self.bot.db[str(ctx.guild.id)]["config"].update_one(
            {"_id": "card_settings"},
            {"$set": current_settings},
            upsert=True
        )

        # Show preview
        await self.rank(ctx, ctx.author)
        await ctx.reply("Server rank card customization updated! Here's a preview.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
