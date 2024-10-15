from discord.ext import commands
import discord
from discord import app_commands
from typing import Optional

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_group(
        name="user",
        description="User-related commands"
    )
    async def user(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Contains commands related to user information. You can either use slash command or normal prefix command.

        **Usage:**
        ?user
        /user

        **Parameters:**
        None

        **Example:**
        ?user
        /user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @user.command(
        name="info",
        description="Get information about a user"
    )
    async def info(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get information about a user.

        **Usage:**
        ?user info [member]
        /user info [member]

        **Parameters:**
        member (discord.Member, optional): The user to get information about. If not provided, shows information about the command user.

        **Example:**
        ?user info @username
        ?user info
        /user info @username
        /user info
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"User Info - {member}", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        await ctx.send(embed=embed)

    @commands.command(
        name="userinfo",
        description="Get information about a user"
    )
    async def info_command(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get information about a user.

        **Usage:**
        ?userinfo [member]

        **Parameters:**
        member (discord.Member, optional): The user to get information about. If not provided, shows information about the command user.

        **Example:**
        ?userinfo @username
        ?userinfo
        """
        await self.info(ctx, member=member)

    @user.command(
        name="avatar",
        description="Get the avatar of a user"
    )
    async def avatar(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the avatar of a user.

        **Usage:**
        ?user avatar [member]
        /user avatar [member]

        **Parameters:**
        member (discord.Member, optional): The user whose avatar to get. If not provided, shows the avatar of the command user.

        **Example:**
        ?user avatar @username
        ?user avatar
        /user avatar @username
        /user avatar
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"Avatar - {member}", color=discord.Color.blue())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(
        name="avatar",
        description="Get the avatar of a user"
    )
    async def avatar_command(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the avatar of a user.

        **Usage:**
        ?avatar [member]

        **Parameters:**
        member (discord.Member, optional): The user whose avatar to get. If not provided, shows the avatar of the command user.

        **Example:**
        ?avatar @username
        ?avatar
        """
        await self.avatar(ctx, member=member)

    @user.command(
        name="permissions",
        description="Get the permissions of a user"
    )
    async def permissions(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the permissions of a user.

        **Usage:**
        ?user permissions [member]
        /user permissions [member]

        **Parameters:**
        member (discord.Member, optional): The user whose permissions to get. If not provided, shows the permissions of the command user.

        **Example:**
        ?user permissions @username
        ?user permissions
        /user permissions @username
        /user permissions
        """
        member = member or ctx.author
        global_perms = member.guild_permissions
        channel_perms = ctx.channel.permissions_for(member)
        
        embed = discord.Embed(title=f"Permissions - {member}", color=discord.Color.blue())
        
        global_perm_list = []
        channel_perm_list = []
        
        for perm, value in global_perms:
            if value:
                global_perm_list.append(f"`{perm.replace('_', ' ').title()}`")
        for perm, value in channel_perms:
            if value and (not getattr(global_perms, perm, False) or perm not in dir(global_perms)):
                channel_perm_list.append(f"`{perm.replace('_', ' ').title()}`")
            elif not value and getattr(global_perms, perm, False):
                channel_perm_list.append(f"`{perm.replace('_', ' ').title()}` (Overridden)")
        
        global_permissions_str = ", ".join(global_perm_list)
        channel_permissions_str = ", ".join(channel_perm_list)
        
        embed.description = f"Global Permissions:\n{global_permissions_str}"
        if channel_permissions_str:
            embed.description += f"\n\nChannel-specific Permissions:\n{channel_permissions_str}"
        
        await ctx.send(embed=embed)

    @commands.command(
        name="permissions",
        description="Get the permissions of a user"
    )
    async def permissions_command(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the permissions of a user.

        **Usage:**
        ?permissions [member]

        **Parameters:**
        member (discord.Member, optional): The user whose permissions to get. If not provided, shows the permissions of the command user.

        **Example:**
        ?permissions @username
        ?permissions
        """
        await self.permissions(ctx, member=member)

    @user.command(
        name="banner",
        description="Get the banner of a user"
    )
    async def banner(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the banner of a user.

        **Usage:**
        ?user banner [member]
        /user banner [member]

        **Parameters:**
        member (discord.Member, optional): The user whose banner to get. If not provided, shows the banner of the command user.

        **Example:**
        ?user banner @username
        ?user banner
        /user banner @username
        /user banner
        """
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.banner:
            embed = discord.Embed(title=f"Banner - {member}", color=discord.Color.blue())
            embed.set_image(url=user.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member} doesn't have a banner.")

    @commands.command(
        name="banner",
        description="Get the banner of a user"
    )
    async def banner_command(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None
    ) -> None:
        """
        Get the banner of a user.

        **Usage:**
        ?banner [member]

        **Parameters:**
        member (discord.Member, optional): The user whose banner to get. If not provided, shows the banner of the command user.

        **Example:**
        ?banner @username
        ?banner
        """
        await self.banner(ctx, member=member)

async def setup(bot):
    await bot.add_cog(User(bot))
