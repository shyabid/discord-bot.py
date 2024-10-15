from discord.ext import commands
import discord
from discord import app_commands
from utils import find_member, find_role
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Tuple,
    Union
)
class Role(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.hybrid_group(
        name="role",
        invoke_without_command=True,
        description="Manage roles for members"
    )
    @commands.has_permissions(manage_roles=True)
    async def role(
        self, 
        ctx: commands.Context, 
        user: str, 
        role_name: str
    ) -> None:
        """Toggle a role for a user."""
        member: Optional[discord.Member] = await find_member(ctx.guild, user)
        if not member:
            await ctx.send("Couldn't find that user.")
            return

        role: Optional[discord.Role] = await find_role(ctx.guild, role_name)
        if not role:
            await ctx.send("Couldn't find that role.")
            return

        if role in member.roles:
            await member.remove_roles(role)
            action: str = "Removed"
        else:
            await member.add_roles(role)
            action: str = "Added"

        await ctx.send(f"{action} `{role.name}` {'from' if action == 'Removed' else 'to'} {member.mention}.")

    @role.command(
        name="add",
        description="Add a role to a member"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(user="The user to add the role to", role="The role to add")
    async def role_add(
        self, 
        ctx: commands.Context, 
        user: discord.Member, 
        role: discord.Role
    ) -> None:
        if role in user.roles:
            await ctx.send(f"{user.mention} already has the role {role.name}.")
            return
        await user.add_roles(role)
        await ctx.send(f"Added {role.name} to {user.mention}.")

    @role.command(
        name="remove",
        description="Remove a role from a member"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(user="The user to remove the role from", role="The role to remove")
    async def role_remove(
        self, 
        ctx: commands.Context, 
        user: discord.Member, 
        role: discord.Role
    ) -> None:
        if role not in user.roles:
            await ctx.send(f"{user.mention} doesn't have the role {role.name}.")
            return
        await user.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {user.mention}.")

    @role.command(
        name="create",
        description="Create a new role"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(name="The name of the new role", color="The color of the new role (optional)")
    async def role_create(
        self, 
        ctx: commands.Context, 
        name: str, 
        color = discord.Color.default()
    ) -> None:
        new_role: discord.Role = await ctx.guild.create_role(name=name, color=color)
        await ctx.send(f"Created new role: {new_role.name}")

    @role.command(
        name="info",
        description="Get information about a role"
    )
    @app_commands.describe(role="The role to get information about")
    async def role_info(
        self, 
        ctx: commands.Context, 
        *, 
        role: str
    ) -> None:
        role_obj: Optional[discord.Role] = await find_role(ctx.guild, role)
        if not role_obj:
            await ctx.send("Couldn't find that role.")
            return

        embed: discord.Embed = discord.Embed(title=f"Role Info: {role_obj.name}", color=role_obj.color)
        embed_fields: List[Tuple[str, Union[int, str, bool]]] = [
            ("ID", role_obj.id),
            ("Color", str(role_obj.color)),
            ("Position", role_obj.position),
            ("Mentionable", role_obj.mentionable),
            ("Hoisted", role_obj.hoist),
            ("Created At", role_obj.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        ]

        for name, value in embed_fields:
            embed.add_field(name=name, value=value)

        await ctx.send(embed=embed)

    @role.command(
        name="edit",
        description="Edit a role's name or color"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to edit", name="The new name for the role (optional)", color="The new color for the role (optional)")
    async def role_edit(
        self, 
        ctx: commands.Context, 
        role: str, 
        name: Optional[str] = None, 
        color: Optional[str] = None
    ) -> None:
        role_obj: Optional[discord.Role] = await find_role(ctx.guild, role)
        if not role_obj:
            await ctx.send("Couldn't find that role.")
            return

        update_params: dict = {}
        if name:
            update_params['name'] = name
        if color:
            update_params['color'] = color

        if update_params:
            await role_obj.edit(**update_params)
            await ctx.send(f"Role `{role_obj.name}` has been updated.")
        else:
            await ctx.send("No changes were specified for the role.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Role(bot))
