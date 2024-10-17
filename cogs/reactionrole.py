from discord.ext import commands
import discord
from discord import app_commands

class Reactionrole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_group(
        name="reactionrole",
        description="Manage reaction roles for embeds.",
        invoke_without_command=True
    )
    async def reactionrole(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_embed = discord.Embed(
                title="Reaction Role Commands",
                description="""
- `?reactionrole add <embedName> <emoji> <role_name>`
  - Adds a reaction role to the specified embed
- `?reactionrole remove <embedName> <emoji> <role_name>`
  - Removes a reaction role from the specified embed
- `?reactionrole type <embedName> <option>`
  - Sets the type of reaction role (unique or multiple)
                """,
                color=discord.Color.blue()
            )
            await ctx.reply(embed=help_embed)

    @reactionrole.command(
        name="add",
        description="Add a reaction role to an embed."
    )
    @app_commands.describe(
        embed_name="Name of the embed to add the reaction role to",
        emoji="Emoji to use for the reaction role",
        role_name="Name, mention, or ID of the role"
    )
    async def add_reaction_role(self, ctx: commands.Context, embed_name: str, emoji: str, role_name: str):
        embed_data = self.bot.db[str(ctx.guild.id)]['embeds'].find_one({"name": embed_name})
        if not embed_data:
            await ctx.reply(f"No embed found with name `{embed_name}`.")
            return

        role = await self.get_role(ctx, role_name)
        if not role:
            await ctx.reply(f"Could not find a role matching `{role_name}`.")
            return

        channel = self.bot.get_channel(embed_data['channel_id'])
        message = await channel.fetch_message(embed_data['msg_id'])

        try:
            await message.add_reaction(emoji)
        except discord.errors.HTTPException:
            await ctx.reply(f"Invalid emoji: `{emoji}`")
            return

        reaction_role_data = {
            "emoji": emoji,
            "role_id": role.id
        }

        self.bot.db[str(ctx.guild.id)]["reactionrole"].update_one(
            {"embed_name": embed_name},
            {"$push": {"roles": reaction_role_data}},
            upsert=True
        )

        await ctx.reply(f"Reaction role added: {emoji} for role {role.name} on embed '{embed_name}'")

    @reactionrole.command(
        name="remove",
        description="Remove a reaction role from an embed."
    )
    @app_commands.describe(
        embed_name="Name of the embed to remove the reaction role from",
        emoji="Emoji of the reaction role to remove",
        role_name="Name, mention, or ID of the role to remove"
    )
    async def remove_reaction_role(self, ctx: commands.Context, embed_name: str, emoji: str, role_name: str):
        embed_data = self.bot.db[str(ctx.guild.id)]['embeds'].find_one({"name": embed_name})
        if not embed_data:
            await ctx.reply(f"No embed found with name `{embed_name}`.")
            return

        role = await self.get_role(ctx, role_name)
        if not role:
            await ctx.reply(f"Could not find a role matching `{role_name}`.")
            return

        result = self.bot.db[str(ctx.guild.id)]["reactionrole"].update_one(
            {"embed_name": embed_name},
            {"$pull": {"roles": {"emoji": emoji, "role_id": role.id}}}
        )

        if result.modified_count > 0:
            channel = self.bot.get_channel(embed_data['channel_id'])
            message = await channel.fetch_message(embed_data['msg_id'])
            await message.clear_reaction(emoji)
            await ctx.reply(f"Reaction role removed: {emoji} for role {role.name} from embed '{embed_name}'")
        else:
            await ctx.reply(f"No matching reaction role found for emoji {emoji} and role {role.name} on embed '{embed_name}'")

    @reactionrole.command(
        name="type",
        description="Set the type of reaction role for an embed."
    )
    @app_commands.describe(
        embed_name="Name of the embed to set the reaction role type for",
        option="Type of reaction role (unique or multiple)"
    )
    @app_commands.choices(option=[
        app_commands.Choice(name="Unique", value="unique"),
        app_commands.Choice(name="Multiple", value="multiple")
    ])
    async def set_reaction_role_type(self, ctx: commands.Context, embed_name: str, option: str):
        embed_data = self.bot.db[str(ctx.guild.id)]['embeds'].find_one({"name": embed_name})
        if not embed_data:
            await ctx.reply(f"No embed found with name `{embed_name}`.")
            return

        self.bot.db[str(ctx.guild.id)]["reactionrole"].update_one(
            {"embed_name": embed_name},
            {"$set": {"type": option}},
            upsert=True
        )

        await ctx.reply(f"Reaction role type for embed '{embed_name}' set to: {option}")

    async def get_role(self, ctx: commands.Context, role_name: str):
        role = None
        try:
            role = await commands.RoleConverter().convert(ctx, role_name)
        except commands.RoleNotFound:
            roles = [r for r in ctx.guild.roles if role_name.lower() in r.name.lower()]
            if roles:
                role = min(roles, key=lambda r: len(r.name))
        return role

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        reaction_role_data = self.bot.db[guild_id]["reactionrole"].find_one({"embed_name": {"$exists": True}})

        if not reaction_role_data:
            return

        for role_data in reaction_role_data.get("roles", []):
            if str(payload.emoji) == role_data["emoji"] and payload.message_id == self.bot.db[guild_id]['embeds'].find_one({"name": reaction_role_data["embed_name"]})["msg_id"]:
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(role_data["role_id"])
                member = guild.get_member(payload.user_id)

                if role and member:
                    if reaction_role_data.get("type") == "unique":
                        for r in member.roles:
                            if r.id in [rd["role_id"] for rd in reaction_role_data["roles"] if rd != role_data]:
                                await member.remove_roles(r)
                    await member.add_roles(role)
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        reaction_role_data = self.bot.db[guild_id]["reactionrole"].find_one({"embed_name": {"$exists": True}})

        if not reaction_role_data:
            return

        for role_data in reaction_role_data.get("roles", []):
            if str(payload.emoji) == role_data["emoji"] and payload.message_id == self.bot.db[guild_id]['embeds'].find_one({"name": reaction_role_data["embed_name"]})["msg_id"]:
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(role_data["role_id"])
                member = guild.get_member(payload.user_id)

                if role and member:
                    await member.remove_roles(role)
                break
    
        
async def setup(bot):
    await bot.add_cog(Reactionrole(bot))
