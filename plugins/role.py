from discord.ext import commands
import discord
from discord import app_commands
from utils import parse_time_string, find_role, find_member
from bot import Morgana
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Tuple,
    Union
)
import asyncio

class Role(commands.Cog):
    def __init__(self, bot: Morgana) -> None:
        self.bot: Morgana = bot

    @commands.hybrid_group(
        name="role",
        invoke_without_command=True,
        description="Manage roles for members"
    )
    @commands.has_permissions(manage_roles=True)
    async def role(
        self, 
        ctx: commands.Context
    ) -> None:
        if not ctx.invoked_subcommand:
            if len(ctx.message.content.split()) > 2:
                member_name = ctx.message.content.split()[1].lower()
                role_name = ctx.message.content.split()[2].lower()

                member = await self.bot.find_member(ctx.guild, member_name)
                if not member:
                    raise commands.UserNotFound("Couldn't find that user.")

                role: Optional[discord.Role] = await self.bot.find_role(ctx.guild, role_name)
                if not role:
                    raise commands.RoleNotFound("Couldn't find that role.")

                if role in member.roles:
                    await member.remove_roles(role)
                    action: str = "Removed"
                else:
                    await member.add_roles(role)
                    action: str = "Added"

                await ctx.reply(f"{action} `{role.name}` {'from' if action == 'Removed' else 'to'} {member.mention}.")
            else:
                raise commands.CommandNotFound("No subcommand specified. Use `?help role` for more information.")
                

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
            await ctx.reply(f"{user.mention} already has the role {role.name}.")
            return
        await user.add_roles(role)
        await ctx.reply(f"Added {role.name} to {user.mention}.")

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
            await ctx.reply(f"{user.mention} doesn't have the role {role.name}.")
            return
        await user.remove_roles(role)
        await ctx.reply(f"Removed {role.name} from {user.mention}.")

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
        await ctx.reply(f"Created new role: {new_role.name}")

    @role.command(
        name="info",
        description="Get information about a role"
    )
    @app_commands.describe(role="Name of the role to get information about")
    async def role_info(
        self, 
        ctx: commands.Context, 
        role: str
    ) -> None:
        role_obj: Optional[discord.Role] = await self.bot.find_role(ctx.guild, role)
        if not role_obj:
            await ctx.reply("Couldn't find that role.")
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

        await ctx.reply(embed=embed)

    @role.command(
        name="edit",
        description="Edit a role's name or color"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to edit", name="The new name for the role (optional)", color="The new color for the role (optional)")
    async def role_edit(
        self, 
        ctx: commands.Context, 
        role: discord.Role, 
        name: Optional[str] = None, 
        color: Optional[str] = None
    ) -> None:

        update_params: dict = {}
        if name:
            update_params['name'] = name
        if color:
            update_params['color'] = color

        if update_params:
            await role.edit(**update_params)
            await ctx.reply(f"Role `{role.name}` has been updated.")
        else:
            await ctx.reply("No changes were specified for the role.")

    @role.command(
        name="temporary",
        description="Give a role to a member temporarily"
    )
    @commands.has_permissions(manage_roles=True)
    @app_commands.describe(
        user="The user to give the temporary role to",
        role="The role to give temporarily",
        duration="Duration"
    )
    async def role_temporary(
        self,
        ctx: commands.Context,
        user: discord.Member,
        role: discord.Role,
        duration: str
    ) -> None:
        
        duration = parse_time_string(duration)
        
        if role in user.roles:
            await ctx.reply(f"{user.mention} already has the role {role.name}.")
            return

        await user.add_roles(role)
        
        # Store the task
        if user.id not in self.temp_role_tasks:
            self.temp_role_tasks[user.id] = {}
            
        # Cancel existing task if there is one
        if role.id in self.temp_role_tasks[user.id]:
            self.temp_role_tasks[user.id][role.id].cancel()
            
        # Create new task
        task = asyncio.create_task(self.remove_temporary_role(user, role, duration))
        self.temp_role_tasks[user.id][role.id] = task
        
        await ctx.reply(f"Added {role.name} to {user.mention} for {duration} minutes.")

    @commands.command(
        name="temprole",
        description="Give a role to a member temporarily (alias for /role temporary)"
    )
    @commands.has_permissions(manage_roles=True)
    async def temprole(
        self,
        ctx: commands.Context,
        user: str,
        role: str,
        duration: str
    ) -> None:
        
        user: discord.Member = await find_member(guild=ctx.guild, query=user)
        role: discord.Role = await find_role(guild=ctx.guild, query=role)
        duration: int = parse_time_string(duration)
        
        await self.role_temporary(ctx, user, role, duration)

async def setup(bot: Morgana) -> None:
    await bot.add_cog(Role(bot))
