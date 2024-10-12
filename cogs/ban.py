import discord
from discord.ext import commands
import asyncio
from utils.slash_tools import find_usr

class UserSelectView(discord.ui.View):
    def __init__(self, bot, max_select=1):
        super().__init__()
        self.bot = bot
        self.max_select = max_select
        self.add_item(UserSelectMenu(self.bot, self.max_select))

class UserSelectMenu(discord.ui.UserSelect):
    def __init__(self, bot, max_select):
        super().__init__(placeholder="Select users to ban", min_values=1, max_values=max_select)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        selected_users = self.values
        if len(selected_users) > 10:
            await interaction.response.edit_message(content="You can select a maximum of 10 users.", view=None)
            return
        
        await interaction.response.send_modal(MassBanModal(self.bot, selected_users, interaction))

class MassBanModal(discord.ui.Modal, title="Mass Ban Users"):
    def __init__(self, bot, users, original_interaction):
        super().__init__()
        self.bot = bot
        self.users = users
        self.original_interaction = original_interaction

    reason = discord.ui.TextInput(
        label="Reason", style=discord.TextStyle.paragraph, required=True
    )

    delete_messages = discord.ui.TextInput(
        label="Delete messages (in days, 0-7)",
        style=discord.TextStyle.short,
        required=True,
        max_length=1,
        default="0",
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            delete_days = max(0, min(7, int(self.delete_messages.value)))
            banned_users = []
            failed_users = []

            # Attempt to ban each selected user
            for user in self.users:
                try:
                    await interaction.guild.ban(user, reason=self.reason.value, delete_message_days=delete_days)
                    banned_users.append(user)
                except discord.errors.Forbidden:
                    failed_users.append(user)

            result_message = ""
            if banned_users:
                user_mentions = ', '.join(user.mention for user in banned_users)
                result_message += f"Successfully banned: {user_mentions}\n"
            if failed_users:
                user_mentions = ', '.join(user.mention for user in failed_users)
                result_message += f"Failed to ban (no permission): {user_mentions}\n"

            result_message += f"Reason: {self.reason.value}"

            await self.original_interaction.edit_original_response(content=result_message, view=None)

        except ValueError:
            await self.original_interaction.edit_original_response(content="Invalid input for delete messages. Please use a number between 0 and 7.", view=None)
        except asyncio.TimeoutError:
            await self.original_interaction.edit_original_response(content="The ban operation timed out.", view=None)

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name="ban", description="Ban a user from the server")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: str = None, reason: str = "No reason provided"):
        """Ban a user from the server, with confirmation."""

        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.reply("I do not have permission to ban members in this server.")
            return
        
        if member.isdigit():
            try:
                member = await ctx.guild.fetch_member(int(member))
                if member is None:
                    await ctx.reply("No valid user found with that ID.")
                    return
            except discord.NotFound:
                await ctx.reply("No valid user found with that ID.")
                return
            
        elif member.startswith("<@") and member.endswith(">"):
            try:
                user_id = int(member[2:-1])  # Extract user ID from mention format
                member = await ctx.guild.fetch_member(user_id)
                if member is None:
                    await ctx.reply("No valid user found with that mention.")
                    return
            except discord.NotFound:
                await ctx.reply("No valid user found with that mention")
                return
            
            except ValueError:
                await ctx.reply("Invalid user mention.")
                return
        
        else:
            user = await find_usr(ctx.guild, member)
            if user is None:
                await ctx.reply("No valid users found.")
                return

        if ctx.author.top_role < member.top_role:
            await ctx.reply("You can't ban a user with a higher role than you@")
            return
                
        elif member == self.bot.user:
            await ctx.reply("I can not ban myself!")
            return
        
        if member == ctx.guild.owner:
            await ctx.reply("You cannot ban the server owner!")
            return

    
        class ConfirmBanView(discord.ui.View):
            def __init__(self, ctx, user, reason):
                super().__init__(timeout=60)
                self.ctx = ctx
                self.user = user
                self.reason = reason
                self.value = None

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user != self.ctx.author:
                    await interaction.response.send_message("You are not permitted to use this button", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()

            @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()

        view = ConfirmBanView(ctx, member, reason)
        embed = discord.Embed(
            description=f"Are you sure you want to ban {member.mention}? Reason: `{reason}`",
            color=discord.Color.dark_grey()
        )
        message = await ctx.reply(embed=embed, view=view)

        await view.wait()

        if view.value is None:
            await message.edit(content="Ban confirmation timed out.", embed=None, view=None)
        elif view.value:
            try:
                await ctx.guild.ban(member, reason=reason)
                await message.edit(content=f"Successfully banned {member.mention} for reason: `{reason}`", embed=None, view=None)
            except discord.errors.Forbidden:
                await message.edit(content=f"Failed to ban {member.mention} (bot lacks permission).", embed=None, view=None)
            except discord.errors.HTTPException as e:
                await message.edit(content=f"An error occurred while banning {member.mention}: {e}", embed=None, view=None)
        else:
            await message.edit(content="Ban cancelled.", embed=None, view=None)


    @commands.command(name="massban", description="Mass ban users from the server")
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx, *args):
        if len(args) > 0:
            users, reason = await self._parse_massban_args(ctx, args)
            if not users:
                await ctx.reply("No valid users found.")
                return

            await self._ban_users(ctx, users, reason)
        else:
            view = UserSelectView(self.bot, max_select=10)
            await ctx.reply("Please select up to 10 users to ban:", view=view)

async def setup(bot):
    await bot.add_cog(Ban(bot))
