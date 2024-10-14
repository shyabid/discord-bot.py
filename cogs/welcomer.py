from discord.ext import commands
import discord
from db import db
import os
import re
from urllib.parse import urlparse

def parse_welcomer_content(content: str, member: discord.Member) -> str:
    placeholders = {
        '{user.mention}': member.mention,
        '{user.name}': member.name,
        '{user.display_name}': member.display_name,
        '{user.id}': str(member.id),
        '{guild.name}': member.guild.name,
        '{guild.id}': str(member.guild.id),
        '{guild.member_count}': str(member.guild.member_count),
        '{guild.owner}': str(member.guild.owner),
        '{guild.owner.name}': member.guild.owner.name,
        '{guild.owner.mention}': member.guild.owner.mention,
        '{guild.created_at}': str(member.guild.created_at),
        '{user.created_at}': str(member.created_at),
        '{user.joined_at}': str(member.joined_at),
        '{user.avatar_url}': str(member.avatar.url) if member.avatar else '',
        '{guild.icon}': str(member.guild.icon.url) if member.guild.icon else '',
        '{guild.banner}': str(member.guild.banner.url) if member.guild.banner else '',
        '{guild.description}': member.guild.description or '',
        '{guild.features}': ', '.join(member.guild.features),
        '{guild.premium_tier}': str(member.guild.premium_tier),
        '{guild.premium_subscribers}': str(len(member.guild.premium_subscribers)),
        '{guild.roles}': ', '.join([role.name for role in member.guild.roles]),
        '{user.top_role}': member.top_role.name,
        '{user.roles}': ', '.join([role.name for role in member.roles]),
    }

    def replace_placeholder(match):
        placeholder = match.group(0)
        return placeholders.get(placeholder, placeholder)

    pattern = '|'.join(re.escape(key) for key in placeholders.keys())
    return re.sub(pattern, replace_placeholder, content)

class WelcomerSetupButton(discord.ui.Button):
    def __init__(self, bot, user_id, original_message):
        super().__init__(label="Set up Welcome Message", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.user_id = user_id
        self.original_message = original_message

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        modal = WelcomerModal(self.bot, interaction.guild.id, self.original_message)
        await interaction.response.send_modal(modal)

class WelcomerEditButton(discord.ui.Button):
    def __init__(self, bot, user_id, original_message, welcomer_data):
        super().__init__(label="Edit Welcome Message", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.user_id = user_id
        self.original_message = original_message
        self.welcomer_data = welcomer_data

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        modal = WelcomerModal(self.bot, interaction.guild.id, self.original_message, self.welcomer_data)
        await interaction.response.send_modal(modal)

class WelcomerModal(discord.ui.Modal, title="Create/Update Welcome Message"):
    titletxt = discord.ui.TextInput(label="Title", placeholder="Enter the title for your embed", required=True, max_length=256)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, required=False, max_length=4000)
    color = discord.ui.TextInput(label="Color (hex code)", required=False, max_length=7)
    image_url = discord.ui.TextInput(label="Image URL", required=False)
    thumbnail_url = discord.ui.TextInput(label="Thumbnail URL", required=False)

    def __init__(self, bot, guild_id, original_message, welcomer_data=None):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.original_message = original_message
        if welcomer_data:
            self.titletxt.default = welcomer_data.get('title', '')
            self.description.default = welcomer_data.get('description', '')
            self.color.default = welcomer_data.get('color', '')
            self.image_url.default = welcomer_data.get('image_url', '')
            self.thumbnail_url.default = welcomer_data.get('thumbnail_url', '')

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed()

        if self.titletxt.value:
            embed.title = self.titletxt.value
        if self.description.value:
            embed.description = self.description.value
        if self.color.value:
            try:
                embed.color = discord.Color.from_str(self.color.value)
            except ValueError:
                pass
        if self.image_url.value:
            embed.set_image(url=self.image_url.value)
        if self.thumbnail_url.value:
            embed.set_thumbnail(url=self.thumbnail_url.value)

        welcomer_data = {
            'title': self.titletxt.value,
            'description': self.description.value,
            'color': self.color.value or '#000000',
            'image_url': self.image_url.value,
            'thumbnail_url': self.thumbnail_url.value,
            'enabled': True
        }

        view = discord.ui.View()
        view.add_item(WelcomerChannelSelect(self.bot, self.guild_id, interaction.user.id, welcomer_data, self.original_message))
        
        embed = discord.Embed(description="Select a channel to send the welcome message:", color=discord.Color.dark_gray())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class WelcomerChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot, guild_id, user_id, welcomer_data, original_message):
        super().__init__(placeholder="Select a channel", channel_types=[discord.ChannelType.text])
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.welcomer_data = welcomer_data
        self.original_message = original_message

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this select menu.", ephemeral=True)
            return

        channel = self.values[0]
        self.welcomer_data['channel_id'] = channel.id

        # Update the welcomer data instead of inserting a new document
        db[str(self.guild_id)]["welcomer"].update_one({}, {"$set": self.welcomer_data}, upsert=True)

        await interaction.response.send_message(f"Welcome message set up successfully in {channel.mention}!", ephemeral=True)
        if self.original_message:
            await self.original_message.delete()

class Welcomer(commands.Cog):
    def __init__(
        self, 
        bot: commands.Bot
    ) -> None:
        self.bot = bot
 
    @commands.hybrid_group(
        name="welcomer",
        description="Manage the welcome message for new members.",
        invoke_without_command=True
    )
    async def welcomer_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_embed = discord.Embed(
                title="Welcomer Commands",
                description="""
- `?welcomer setup`
  - Set up the welcome message
- `?welcomer edit`
  - Edit the existing welcome message
- `?welcomer toggle`
  - Turn the welcomer on or off
- `?welcomer test`
  - Test the welcome message
                """,
                color=discord.Color.blue()
            )
            await ctx.reply(embed=help_embed)

    @welcomer_group.command(
        name="setup",
        description="Set up the welcome message."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_setup(self, ctx: commands.Context):
        view = discord.ui.View()
        message = await ctx.reply("Click the button below to set up your welcome message.", view=view)
        view.add_item(WelcomerSetupButton(self.bot, ctx.author.id, message))
        await message.edit(view=view)

    @welcomer_group.command(
        name="edit",
        description="Edit the existing welcome message."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_edit(self, ctx: commands.Context):
        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            await ctx.reply("No welcome message has been set up yet. Use `?welcomer setup` first.")
            return

        view = discord.ui.View()
        message = await ctx.reply("Click the button below to edit your welcome message.", view=view)
        view.add_item(WelcomerEditButton(self.bot, ctx.author.id, message, welcomer_data))
        await message.edit(view=view)

    @welcomer_group.command(
        name="toggle",
        description="Turn the welcomer on or off."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_toggle(self, ctx: commands.Context, state: str):
        if state.lower() not in ['on', 'off']:
            await ctx.reply("Please specify either 'on' or 'off'.")
            return

        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            await ctx.reply("No welcome message has been set up yet. Use `?welcomer setup` first.")
            return

        welcomer_data['enabled'] = (state.lower() == 'on')
        db[str(ctx.guild.id)]["welcomer"].update_one({}, {"$set": welcomer_data}, upsert=False)
        await ctx.reply(f"Welcomer has been turned {state.lower()}.")

    @welcomer_group.command(
        name="test",
        description="Test the welcome message."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_test(self, ctx: commands.Context):
        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            await ctx.reply("No welcome message has been set up yet. Use `?welcomer setup` first.")
            return

        embed = discord.Embed(
            title=parse_welcomer_content(welcomer_data.get('title', 'Welcome!'), ctx.author),
            description=parse_welcomer_content(welcomer_data.get('description', ''), ctx.author),
            color=discord.Color.from_str(welcomer_data.get('color', '#000000'))
        )
        if welcomer_data.get('image_url'):
            embed.set_image(url=welcomer_data['image_url'])
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(welcomer_data['thumbnail_url'], ctx.author)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        welcomer_data = db[str(member.guild.id)]["welcomer"].find_one()
        if not welcomer_data or not welcomer_data.get('enabled', False):
            return

        channel_id = welcomer_data.get('channel_id')
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=parse_welcomer_content(welcomer_data.get('title', 'Welcome!'), member),
            description=parse_welcomer_content(welcomer_data.get('description', ''), member),
            color=discord.Color.from_str(welcomer_data.get('color', '#000000'))
        )
        if welcomer_data.get('image_url'):
            embed.set_image(url=welcomer_data['image_url'])
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(welcomer_data['thumbnail_url'], member)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)

        await channel.send(embed=embed)

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

async def setup(bot):
    try:
        await bot.add_cog(Welcomer(bot))
    except Exception as e:
        bot.logger.error(f'Failed to add welcomer cog: {e}')
