import discord
from discord.ext import commands
from discord import app_commands
from utils.slash_tools import find_usr, find_role
import typing


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(
        name="role", 
        invoke_without_command=True
    )
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, user: str, role_name: str):
        member = await find_usr(ctx.guild, user)
        if not member:
            return await ctx.send("Couldn't find that user.")

        role = await find_role(ctx.guild, role_name)
        if not role:
            return await ctx.send("Couldn't find that role.")

        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"Removed `{role.name}` from {member.mention}.")
        else:
            await member.add_roles(role)
            await ctx.send(f"Added `{role.name}` to {member.mention}.")

    @role.command(
        name="add",
        description="Add a role to a member"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(user="The user to add the role to", role="The role to add")
    async def role_add(self, ctx, user: discord.Member, role: discord.Role):
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
    async def role_remove(self, ctx, user: discord.Member, role: discord.Role):
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
    async def role_create(self, ctx, name: str, color: discord.Color = discord.Color.default()):
        
        new_role = await ctx.guild.create_role(name=name, color=color)
        await ctx.send(f"Created new role: {new_role.name}")

    @role.command(
        name="info",
        description="Get information about a role"
    )
    @app_commands.describe(role="The role to get information about")
    async def role_info(self, ctx, *, role: str):
        role_obj = await find_role(ctx.guild, role)
        if not role_obj:
            return await ctx.send("Couldn't find that role.")

        embed = discord.Embed(title=f"Role Info: {role_obj.name}", color=role_obj.color)
        embed.add_field(name="ID", value=role_obj.id)
        embed.add_field(name="Color", value=str(role_obj.color))
        embed.add_field(name="Position", value=role_obj.position)
        embed.add_field(name="Mentionable", value=role_obj.mentionable)
        embed.add_field(name="Hoisted", value=role_obj.hoist)
        embed.add_field(name="Created At", value=role_obj.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        await ctx.send(embed=embed)

    @role.command(
        name="edit",
        description="Edit a role's name or color"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to edit", name="The new name for the role (optional)", color="The new color for the role (optional)")
    async def role_edit(self, ctx, role: str, name: str = None, color: discord.Color = None):
        role_obj = await find_role(ctx.guild, role)
        if not role_obj:
            return await ctx.send("Couldn't find that role.")

        if name:
            await role_obj.edit(name=name)
        if color:
            await role_obj.edit(color=color)
        await ctx.send(f"Role `{role_obj.name}` has been updated.")

async def setup(bot):
    await bot.add_cog(Role(bot))
