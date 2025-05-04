from discord.ext import commands
import discord
import os
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

def parse_welcomer_content(content: str, member: discord.Member) -> str:
    if content is None:
        return ''
    
    placeholders = {'{user.mention}': member.mention, '{user.name}': member.name, 
                   '{user.display_name}': member.display_name, '{user.id}': str(member.id),
                   '{user.avatar}': str(member.avatar.url if member.avatar else ''),
                   '{guild.name}': member.guild.name, '{guild.id}': str(member.guild.id),
                   '{guild.member_count}': str(member.guild.member_count),
                   '{guild.owner}': str(member.guild.owner),
                   '{guild.owner.name}': member.guild.owner.name,
                   '{guild.owner.mention}': member.guild.owner.mention,
                   '{guild.created_at}': str(member.guild.created_at),
                   '{user.created_at}': str(member.created_at),
                   '{user.joined_at}': str(member.joined_at),
                   '{user.avatar_url}': str(member.avatar.url if member.avatar else ''),
                   '{guild.icon}': str(member.guild.icon.url if member.guild.icon else ''),
                   '{guild.banner}': str(member.guild.banner.url if member.guild.banner else ''),
                   '{guild.description}': (member.guild.description or ''),
                   '{guild.features}': ', '.join(member.guild.features),
                   '{guild.premium_tier}': str(member.guild.premium_tier),
                   '{guild.premium_subscribers}': str(len(member.guild.premium_subscribers)),
                   '{guild.roles}': ', '.join([r.name for r in member.guild.roles]),
                   '{user.top_role}': member.top_role.name,
                   '{user.roles}': ', '.join([r.name for r in member.roles])}
    return re.sub('|'.join(re.escape(k) for k in placeholders), 
                 lambda m: placeholders.get(m.group(0), m.group(0)), content)

class WelcomerSetupSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, user_id: int, original_message: discord.Message, welcomer_data: Optional[Dict[str, Any]] = None) -> None:
        options = [discord.SelectOption(label="Message", description="Set the normal text message"),
                   discord.SelectOption(label="Embed Title", description="Set the title of the embed"),
                   discord.SelectOption(label="Embed Description", description="Set the description of the embed"),
                   discord.SelectOption(label="Embed Footer", description="Set the footer of the embed"),
                   discord.SelectOption(label="Embed Author", description="Set the author of the embed"),
                   discord.SelectOption(label="Embed Thumbnail", description="Set the thumbnail of the embed"),
                   discord.SelectOption(label="Embed Image", description="Set the image of the embed"),
                   discord.SelectOption(label="Embed Color", description="Set the color of the embed"),
                   discord.SelectOption(label="Add Button", description="Add a button to the message"),
                   discord.SelectOption(label="Remove Button", description="Remove a button from the message"),
                   discord.SelectOption(label="Finish", description="Finish setting up the welcomer")]
        super().__init__(placeholder="Choose a field to edit", options=options)
        self.bot = bot
        self.user_id = user_id
        self.original_message = original_message
        self.welcomer_data = welcomer_data or {}

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not authorized", ephemeral=True)
        selected_option = self.values[0]
        if selected_option == "Finish":
            self.welcomer_data['enabled'] = True
            self.bot.db.update_welcomer_settings(interaction.guild.id, self.welcomer_data)
            view = discord.ui.View().add_item(WelcomerChannelSelect(self.bot, self.user_id, 
                                            self.welcomer_data, interaction.guild))
            await interaction.response.send_message(embed=discord.Embed(
                title="Select Welcomer Channel",
                description="Please select the channel for welcome messages.",
                color=discord.Color.dark_grey()), view=view, ephemeral=True)
            if self.original_message: await self.original_message.delete()
        else:
            modal = {
                "Embed Title": TitleModal, "Embed Description": DescriptionModal,
                "Embed Footer": FooterModal, "Embed Author": AuthorModal,
                "Embed Thumbnail": ThumbnailModal, "Embed Image": ImageModal,
                "Embed Color": ColorModal, "Message": MessageModal,
                "Add Button": ButtonModal, "Remove Button": RemoveButtonModal,
            }[selected_option](self.bot, interaction.guild.id, self.welcomer_data)
            await interaction.response.send_modal(modal)
            await modal.wait()
            await self.update_preview_message(interaction)

    async def update_preview_message(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed()
        message_content = parse_welcomer_content(self.welcomer_data.get('message', ''), interaction.user)
        combined_view = discord.ui.View()
        
        # Initialize with default empty string if value is None
        if 'buttons' in self.welcomer_data:
            for button in self.welcomer_data['buttons']:
                combined_view.add_item(discord.ui.Button(label=button['label'], url=button['url'], style=discord.ButtonStyle.grey))
        combined_view.add_item(self)
        
        if self.welcomer_data.get('title'):
            embed.title = parse_welcomer_content(self.welcomer_data['title'], interaction.user)
        
        if self.welcomer_data.get('description'):
            embed.description = parse_welcomer_content(self.welcomer_data['description'], interaction.user)
        
        if self.welcomer_data.get('color'):
            embed.color = discord.Color.from_str(self.welcomer_data['color'])
        
        if self.welcomer_data.get('footer', {}):
            footer_text = self.welcomer_data['footer'].get('text', '')
            footer_icon = self.welcomer_data['footer'].get('icon_url', '')
            embed.set_footer(text=parse_welcomer_content(footer_text, interaction.user),
                           icon_url=footer_icon)
        
        if self.welcomer_data.get('author', {}):
            author_name = parse_welcomer_content(self.welcomer_data['author'].get('name', ''), interaction.user)
            author_url = self.welcomer_data['author'].get('url', '')
            author_icon_url = parse_welcomer_content(self.welcomer_data['author'].get('icon_url', ''), interaction.user)
            
            if author_icon_url and self.is_valid_url(author_icon_url):
                embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
            else:
                embed.set_author(name=author_name, url=author_url)
        
        thumbnail_url = parse_welcomer_content(self.welcomer_data.get('thumbnail_url', ''), interaction.user)
        if thumbnail_url and self.is_valid_url(thumbnail_url):
            embed.set_thumbnail(url=thumbnail_url)
        
        image_url = parse_welcomer_content(self.welcomer_data.get('image_url', ''), interaction.user)
        if image_url and self.is_valid_url(image_url):
            embed.set_image(url=image_url)

        await self.original_message.edit(
            content="Current welcome message preview:" + ("\n" + message_content if message_content else ""),
            embed=embed,
            view=combined_view
        )

    async def finish_setup(self, interaction: discord.Interaction) -> None:
        self.welcomer_data['enabled'] = True
        self.bot.db.update_welcomer_settings(interaction.guild.id, self.welcomer_data)
        
        channel_select = WelcomerChannelSelect(self.bot, self.user_id, self.welcomer_data, interaction.guild)
        view = discord.ui.View().add_item(channel_select)
        
        embed = discord.Embed(title="Select Welcomer Channel", description="Please select the channel for welcome messages.",
                              color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        if self.original_message:
            await self.original_message.delete()

    async def update_preview_embed(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed()
        message_content = parse_welcomer_content(self.welcomer_data.get('message', ''), interaction.user)
        view = discord.ui.View()
        if 'buttons' in self.welcomer_data:
            for button in self.welcomer_data['buttons']:
                view.add_item(discord.ui.Button(label=button['label'], url=button['url'], style=discord.ButtonStyle.grey))

        if self.welcomer_data.get('title'):
            embed.title = parse_welcomer_content(self.welcomer_data['title'], interaction.user)
        
        if self.welcomer_data.get('description'):
            embed.description = parse_welcomer_content(self.welcomer_data['description'], interaction.user)
        else:
            embed.description = "\u200b"
        
        if self.welcomer_data.get('color'):
            embed.color = discord.Color.from_str(self.welcomer_data['color'])
        
        if self.welcomer_data.get('footer'):
            embed.set_footer(text=self.welcomer_data['footer'].get('text'), icon_url=self.welcomer_data['footer'].get('icon_url'))
        
        if self.welcomer_data.get('author'):
            author_name = parse_welcomer_content(self.welcomer_data['author'].get('name', ''), interaction.user)
            author_url = self.welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(self.welcomer_data['author'].get('icon_url', ''), interaction.user)
            
            if author_icon_url and not self.is_valid_url(author_icon_url):
                author_icon_url = None
            
            embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
        
        if self.welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(self.welcomer_data['thumbnail_url'], interaction.user)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)
        
        if self.welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(self.welcomer_data['image_url'], interaction.user)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        await self.original_message.edit(content="Current welcome message preview:" + ("\n" + message_content if message_content else ""),
                                         embed=embed, view=view)

    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

class WelcomerChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot: commands.Bot, user_id: int, welcomer_data: Dict[str, Any], guild: discord.Guild):
        self.bot = bot
        self.user_id = user_id
        self.welcomer_data = welcomer_data
        super().__init__(
            placeholder="Select a channel",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return

        selected_channel = self.values[0]
        self.welcomer_data['channel_id'] = selected_channel.id
        self.bot.db.update_welcomer_settings(interaction.guild.id, self.welcomer_data)

        embed = discord.Embed(
            title="Welcomer Setup Complete", 
            description=f"Your welcome message has been set up successfully! Welcome messages will be sent to {selected_channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BaseModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(title="Edit Welcomer")
        self.bot = bot
        self.guild_id = guild_id
        self.welcomer_data = welcomer_data

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.update_welcomer_data()
        self.bot.db.update_welcomer_settings(self.guild_id, self.welcomer_data)
        await interaction.response.send_message("Field updated successfully!", ephemeral=True)

    def update_welcomer_data(self) -> None:
        pass

class TitleModal(BaseModal):
    embed_title = discord.ui.TextInput(label="Embed Title", style=discord.TextStyle.short, required=False, max_length=4000)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.embed_title.default = welcomer_data.get('title', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['title'] = self.embed_title.value

class DescriptionModal(BaseModal):
    description = discord.ui.TextInput(label="Embed Description", style=discord.TextStyle.paragraph, required=False, max_length=4000)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.description.default = welcomer_data.get('description', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['description'] = self.description.value

class FooterModal(BaseModal):
    footer_text = discord.ui.TextInput(label="Footer Text", style=discord.TextStyle.short, required=False)
    footer_icon_url = discord.ui.TextInput(label="Footer Icon URL", style=discord.TextStyle.short, required=False)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.footer_text.default = welcomer_data.get('footer', {}).get('text', '')
        self.footer_icon_url.default = welcomer_data.get('footer', {}).get('icon_url', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['footer'] = {'text': self.footer_text.value, 'icon_url': self.footer_icon_url.value}

class AuthorModal(BaseModal):
    author_name = discord.ui.TextInput(label="Author Name", style=discord.TextStyle.short, required=False)
    author_url = discord.ui.TextInput(label="Author URL", style=discord.TextStyle.short, required=False)
    author_icon_url = discord.ui.TextInput(label="Author Icon URL", style=discord.TextStyle.short, required=False)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.author_name.default = welcomer_data.get('author', {}).get('name', '')
        self.author_url.default = welcomer_data.get('author', {}).get('url', '')
        self.author_icon_url.default = welcomer_data.get('author', {}).get('icon_url', '')

    def update_welcomer_data(self):
        self.welcomer_data['author'] = {'name': self.author_name.value, 'url': self.author_url.value, 'icon_url': self.author_icon_url.value}

class ThumbnailModal(BaseModal):
    thumbnail_url = discord.ui.TextInput(label="Thumbnail URL", style=discord.TextStyle.short, required=False)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.thumbnail_url.default = welcomer_data.get('thumbnail_url', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['thumbnail_url'] = self.thumbnail_url.value

class MessageModal(BaseModal):
    message_content = discord.ui.TextInput(label="Message Content", style=discord.TextStyle.paragraph, required=False, max_length=2000)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.message_content.default = welcomer_data.get('message', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['message'] = self.message_content.value

class ButtonModal(BaseModal):
    button_label = discord.ui.TextInput(label="Button Label", style=discord.TextStyle.short, required=True)
    button_url = discord.ui.TextInput(label="Button URL", style=discord.TextStyle.short, required=True)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.button_label.default = ''
        self.button_url.default = ''

    def update_welcomer_data(self) -> None:
        if 'buttons' not in self.welcomer_data:
            self.welcomer_data['buttons'] = []
        self.welcomer_data['buttons'].append({'label': self.button_label.value, 'url': self.button_url.value})

class RemoveButtonModal(BaseModal):
    button_label = discord.ui.TextInput(label="Button Label to Remove", style=discord.TextStyle.short, required=True)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.button_label.default = ''

    def update_welcomer_data(self) -> None:
        if 'buttons' in self.welcomer_data:
            self.welcomer_data['buttons'] = [button for button in self.welcomer_data['buttons'] if button['label'] != self.button_label.value]

class ImageModal(BaseModal):
    image_url = discord.ui.TextInput(label="Image URL", style=discord.TextStyle.short, required=False)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.image_url.default = welcomer_data.get('image_url', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['image_url'] = self.image_url.value

class ColorModal(BaseModal):
    color = discord.ui.TextInput(label="Color (hex code)", style=discord.TextStyle.short, required=False, max_length=7)

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.color.default = welcomer_data.get('color', '#000000')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['color'] = self.color.value

class Welcomer(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
 
    @commands.hybrid_group(name="welcomer", description="Manage welcome messages", invoke_without_command=True)
    async def welcomer_group(self, ctx: commands.Context) -> None:
        """
        You can manage the welcome message settings using this command.
        Use the subcommands to edit the message, toggle it on/off, or test it.
        
        Placeholders: 
        `{user.mention}`, `{user.name}`, `{user.display_name}`, `{user.id}`,
        `{user.avatar}`, `{guild.name}`, `{guild.id}`, `{guild.member_count}`,
        `{guild.owner}`, `{guild.owner.name}`, `{guild.owner.mention}`,
        `{guild.created_at}`, `{user.created_at}`, `{user.joined_at}`,
        `{user.avatar_url}`, `{guild.icon}`, `{guild.banner}`,
        `{guild.description}`, `{guild.features}`, `{guild.premium_tier}`,
        `{guild.premium_subscribers}`, `{guild.roles}`, `{user.top_role}`,
        `{user.roles}`
        """
        if ctx.invoked_subcommand is None:
            await ctx.reply(embed=discord.Embed(title="Welcomer Commands",
                description="- `?welcomer edit`\n- `?welcomer toggle`\n- `?welcomer test`",
                color=discord.Color.dark_grey()))

    @welcomer_group.command(name="edit", description="Edit the welcome message")
    @commands.has_permissions(manage_guild=True)
    async def welcomer_edit(self, ctx: commands.Context) -> None:
        """Pretty self guiding command, try it out. You wont need any help."""

        welcomer_data = self.bot.db.get_welcomer_settings(ctx.guild.id)
        if not welcomer_data:
            welcomer_data = {'enabled': False, 'channel_id': None, 'title': 'Welcome!',
                           'description': 'Welcome to the server!', 'color': '#000000',
                           'footer': {'text': '', 'icon_url': ''}, 
                           'author': {'name': '', 'url': '', 'icon_url': ''},
                           'thumbnail_url': '', 'image_url': ''}
            self.bot.db.update_welcomer_settings(ctx.guild.id, welcomer_data)
        
        view = discord.ui.View()
        select = WelcomerSetupSelect(self.bot, ctx.author.id, ctx.message, welcomer_data)
        view.add_item(select)
        if 'buttons' in welcomer_data:
            for btn in welcomer_data['buttons']:
                view.add_item(discord.ui.Button(label=btn['label'], url=btn['url'], style=discord.ButtonStyle.grey))
        
        embed = discord.Embed()
        if welcomer_data.get('title'): 
            embed.title = parse_welcomer_content(welcomer_data['title'], ctx.author)
        if welcomer_data.get('description'): 
            embed.description = parse_welcomer_content(welcomer_data['description'], ctx.author)
        if welcomer_data.get('color'): 
            embed.color = discord.Color.from_str(welcomer_data['color'])
        
        if welcomer_data.get('footer'):
            embed.set_footer(text=welcomer_data['footer'].get('text'), icon_url=welcomer_data['footer'].get('icon_url'))
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(welcomer_data['author'].get('name', ''), ctx.author)
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(welcomer_data['author'].get('icon_url', ''), ctx.author)
            
            if author_icon_url and self.is_valid_url(author_icon_url):
                embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
            else:
                embed.set_author(name=author_name, url=author_url)
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(welcomer_data['thumbnail_url'], ctx.author)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(welcomer_data['image_url'], ctx.author)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)
        
        message_content = parse_welcomer_content(welcomer_data.get('message', ''), ctx.author)
        
        try:
            msg = await ctx.reply(content="Select fields to edit:" + 
                      (message_content if message_content else ""),
                      view=view, embed=embed)
            select.original_message = msg
        except discord.HTTPException as e:
            await ctx.reply(f"Error creating preview: {e}")

    @welcomer_group.command(name="toggle", description="Enable or disable the welcomer")
    @commands.has_permissions(manage_guild=True)
    async def welcomer_toggle(self, ctx: commands.Context, state: str) -> None:
        """Toggle the state of the welcomer on or off."""
        if state.lower() not in ['on', 'off']:
            return await ctx.reply("Please specify 'on' or 'off'.")
        welcomer_data = self.bot.db.get_welcomer_settings(ctx.guild.id) or {}
        welcomer_data['enabled'] = (state.lower() == 'on')
        self.bot.db.update_welcomer_settings(ctx.guild.id, welcomer_data)
        await ctx.reply(f"Welcomer turned {state.lower()}")

    @welcomer_group.command(name="test", description="Send a test welcome message")
    @commands.has_permissions(manage_guild=True)
    async def welcomer_test(self, ctx: commands.Context) -> None:
        """Send a test welcome message to the channel."""
        welcomer_data = self.bot.db.get_welcomer_settings(ctx.guild.id)
        if not welcomer_data:
            welcomer_data = {'enabled': False, 'channel_id': None, 'title': 'Welcome!',
                           'description': 'Welcome to the server!', 'color': '#000000',
                           'footer': {'text': '', 'icon_url': ''}, 
                           'author': {'name': '', 'url': '', 'icon_url': ''},
                           'thumbnail_url': '', 'image_url': ''}
            self.bot.db.update_welcomer_settings(ctx.guild.id, welcomer_data)
        
        embed = discord.Embed()
        
        if welcomer_data.get('title'):
            embed.title = parse_welcomer_content(welcomer_data['title'], ctx.author)
        
        if welcomer_data.get('description'):
            embed.description = parse_welcomer_content(welcomer_data['description'], ctx.author)
        else:
            embed.description = "\u200b"  # Add an empty character if no description
        
        if welcomer_data.get('color'):
            embed.color = discord.Color.from_str(welcomer_data['color'])
        
        if welcomer_data.get('footer'):
            embed.set_footer(text=parse_welcomer_content(welcomer_data['footer'].get('text', ''), ctx.author),
                             icon_url=welcomer_data['footer'].get('icon_url'))
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(welcomer_data['author'].get('name', ''), ctx.author)
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(welcomer_data['author'].get('icon_url', ''), ctx.author)
            
            if author_icon_url and self.is_valid_url(author_icon_url):
                embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
            else:
                embed.set_author(name=author_name, url=author_url)
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(welcomer_data['thumbnail_url'], ctx.author)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(welcomer_data['image_url'], ctx.author)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        message_content = parse_welcomer_content(welcomer_data.get('message', ''), ctx.author)
        view = discord.ui.View()
        if 'buttons' in welcomer_data:
            for button in welcomer_data['buttons']:
                view.add_item(discord.ui.Button(label=button['label'], url=button['url'], style=discord.ButtonStyle.grey))

        try:
            await ctx.reply(content=message_content, embed=embed, view=view)
        except discord.errors.HTTPException as e:
            await ctx.reply(f"An error occurred while sending the test message: {str(e)}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        welcomer_data = self.bot.db.get_welcomer_settings(member.guild.id)
        if not welcomer_data or not welcomer_data.get('enabled') or not welcomer_data.get('channel_id'):
            return
        
        channel = member.guild.get_channel(welcomer_data['channel_id'])
        if not channel: return

        embed = discord.Embed()
        
        if welcomer_data.get('title'):
            embed.title = parse_welcomer_content(welcomer_data['title'], member)
        
        if welcomer_data.get('description'):
            embed.description = parse_welcomer_content(welcomer_data['description'], member)
        
        if welcomer_data.get('color'):
            embed.color = discord.Color.from_str(welcomer_data['color'])
        
        if welcomer_data.get('footer'):
            embed.set_footer(text=parse_welcomer_content(welcomer_data['footer'].get('text', ''), member),
                             icon_url=welcomer_data['footer'].get('icon_url'))
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(welcomer_data['author'].get('name', ''), member)
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(welcomer_data['author'].get('icon_url', ''), member)
            
            if author_icon_url and self.is_valid_url(author_icon_url):
                embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
            else:
                embed.set_author(name=author_name, url=author_url)
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(welcomer_data['image_url'], member)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(welcomer_data['thumbnail_url'], member)
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)

        message_content = parse_welcomer_content(welcomer_data.get('message', ''), member)
        view = discord.ui.View()
        if 'buttons' in welcomer_data:
            for button in welcomer_data['buttons']:
                view.add_item(discord.ui.Button(label=button['label'], url=button['url'], style=discord.ButtonStyle.grey))

        try:
            await channel.send(content=message_content, embed=embed, view=view)
        except discord.errors.HTTPException as e:
            print(f"An error occurred while sending the welcome message: {str(e)}")

    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    async def select_welcomer_channel(self, ctx: commands.Context) -> None:
        class ChannelSelect(discord.ui.Select):
            def __init__(self, channels):
                options = [discord.SelectOption(label=channel.name, value=str(channel.id)) for channel in channels]
                super().__init__(placeholder="Select a channel for welcome messages", options=options)
            async def callback(self, interaction: discord.Interaction):
                channel_id = int(self.values[0])
                welcomer_data = self.bot.db.get_welcomer_settings(ctx.guild.id) or {}
                welcomer_data['channel_id'] = channel_id
                self.bot.db.update_welcomer_settings(ctx.guild.id, welcomer_data)
                await interaction.response.send_message(f"Welcome messages will now be sent to <#{channel_id}>.")

        text_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel)]
        view = discord.ui.View().add_item(ChannelSelect(text_channels))
        await ctx.reply("Please select a channel for welcome messages:", view=view)

async def setup(bot):
    try:
        await bot.add_cog(Welcomer(bot))
    except Exception as e:
        bot.logger.error(f'Failed to add welcomer cog: {e}')
