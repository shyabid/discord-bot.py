import discord
from typing import Optional
from discord import app_commands
import typing
from utils import create_autocomplete_from_list as autocomplete


class UserGroup(app_commands.Group):
    @app_commands.command(
        name='info',
        description="Get information about the user"
    )
    async def info(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        embed = discord.Embed(
            title=f"Information for {user.display_name}",
            description=f"""
- Username: **{user.name}**
- Display Name: **{user.display_name}**
- User ID: **{user.id}**
- Member Since: **{discord.utils.format_dt(user.created_at, style='F')}**
- Avatar: [View]({user.avatar.url})
            """
        )

        if isinstance(user, discord.Member):
            embed.add_field(
                name="Joined Server",
                value=discord.utils.format_dt(user.joined_at, style='F')
            )
            top_roles = [role.name for role in user.roles if role.name != "@everyone"][:3]
            embed.add_field(
                name="Roles",
                value=', '.join(top_roles) if top_roles else 'No roles',
                inline=False
            )
        else:
            embed.add_field(
                name="Server Info",
                value="This user is not a member of the server."
            )
        embed.set_author(name=user.display_name, icon_url=user.avatar.url)
        embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed)
