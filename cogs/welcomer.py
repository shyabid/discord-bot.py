from discord.ext import commands
import discord
from db import db
import os
import re
from typing import (
    Dict,
    List,
    Optional,
    Any
)
from urllib.parse import urlparse

def parse_welcomer_content(
    content: str, 
    member: discord.Member
) -> str:
    placeholders: Dict[str, str] = {
        '{user.mention}': member.mention,
        '{user.name}': member.name,
        '{user.display_name}': member.display_name,
        '{user.id}': str(member.id),
        '{user.avatar}': str(member.avatar.url if member.avatar else ''),
        '{guild.name}': member.guild.name,
        '{guild.id}': str(member.guild.id),
        '{guild.member_count}': str(member.guild.member_count),
        '{guild.owner}': str(member.guild.owner),
        '{guild.owner.name}': member.guild.owner.name,
        '{guild.owner.mention}': (member.guild.owner.mention),
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
        '{guild.roles}': ', '.join([role.name for role in member.guild.roles]),
        '{user.top_role}': member.top_role.name,
        '{user.roles}': ', '.join([role.name for role in member.roles]),
    }

    def replace_placeholder(
        match: re.Match[str]
    ) -> str:
        placeholder: str = match.group(0)
        return placeholders.get(placeholder, placeholder)

    pattern: str = '|'.join(
        re.escape(key) for key in placeholders.keys()
    )
    return re.sub(pattern, replace_placeholder, content)

class WelcomerSetupSelect(discord.ui.Select):
    def __init__(
        self, 
        bot: commands.Bot,
        user_id: int,
        original_message: discord.Message,
        welcomer_data: Optional[Dict[str, Any]] = None
    ) -> None:
        options: List[discord.SelectOption] = [
            discord.SelectOption(
                label="Message",
                description="Set the normal text message"
            ),
            discord.SelectOption(
                label="Embed Title",
                description="Set the title of the embed"
            ),
            discord.SelectOption(
                label="Embed Description",
                description="Set the description of the embed"
            ),
            discord.SelectOption(
                label="Embed Footer",
                description="Set the footer of the embed"
            ),
            discord.SelectOption(
                label="Embed Author",
                description="Set the author of the embed"
            ),
            discord.SelectOption(
                label="Embed Thumbnail",
                description="Set the thumbnail of the embed"
            ),
            discord.SelectOption(
                label="Embed Image",
                description="Set the image of the embed"
            ),
            discord.SelectOption(
                label="Embed Color",
                description="Set the color of the embed"
            ),
            discord.SelectOption(
                label="Add Button",
                description="Add a button to the message"
            ),
            discord.SelectOption(
                label="Remove Button",
                description="Remove a button from the message"
            ),
            discord.SelectOption(
                label="Finish",
                description="Finish setting up the welcomer"
            ),
        ]
        super().__init__(
            placeholder="Choose a field to edit",
            options=options
        )
        self.bot: commands.Bot = bot
        self.user_id: int = user_id
        self.original_message: discord.Message = (
            original_message
        )
        self.welcomer_data: Dict[str, Any] = (
            welcomer_data or {}
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You are not authorized to use this menu.",
                ephemeral=True
            )
            return

        selected_option: str = self.values[0]
        if selected_option == "Finish":
            await self.finish_setup(interaction)
        elif selected_option == "Remove Button":
            modal = RemoveButtonModal(self.bot, interaction.guild.id, self.welcomer_data)
            await interaction.response.send_modal(modal)
            await modal.wait()
        else:
            modal_class = {
                "Embed Title": TitleModal,
                "Embed Description": DescriptionModal,
                "Embed Footer": FooterModal,
                "Embed Author": AuthorModal,
                "Embed Thumbnail": ThumbnailModal,
                "Embed Image": ImageModal,
                "Embed Color": ColorModal,
                "Message": MessageModal,
                "Add Button": ButtonModal,
                "Remove Button": RemoveButtonModal,
            }[selected_option]
            
            modal: BaseModal = modal_class(
                self.bot,
                interaction.guild.id,
                self.welcomer_data
            )
            await interaction.response.send_modal(modal)
            await modal.wait()
        
        await self.update_preview_message(interaction)
        self.disabled = False
        
        combined_view = discord.ui.View()
        if 'buttons' in self.welcomer_data:
            for button in self.welcomer_data['buttons']:
                combined_view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))
        combined_view.add_item(self)
        
        await interaction.message.edit(view=combined_view)


    async def update_preview_message(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed()
        message_content = parse_welcomer_content(
            self.welcomer_data.get('message', ''),
            interaction.user
        )
        combined_view = discord.ui.View()
        if 'buttons' in self.welcomer_data:
            for button in self.welcomer_data['buttons']:
                combined_view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))
        combined_view.add_item(self)
        
        if self.welcomer_data.get('title'):
            embed.title = parse_welcomer_content(
                self.welcomer_data['title'],
                interaction.user
            )
        
        if self.welcomer_data.get('description'):
            embed.description = parse_welcomer_content(
                self.welcomer_data['description'],
                interaction.user
            )
        
        if self.welcomer_data.get('color'):
            embed.color = discord.Color.from_str(
                self.welcomer_data['color']
            )
        
        if self.welcomer_data.get('footer'):
            embed.set_footer(
                text=parse_welcomer_content(
                    self.welcomer_data['footer'].get('text', ''),
                    interaction.user
                ),
                icon_url=self.welcomer_data['footer'].get('icon_url')
            )
        
        if self.welcomer_data.get('author'):
            author_name = parse_welcomer_content(
                self.welcomer_data['author'].get('name', ''),
                interaction.user
            )
            author_url = self.welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(
                self.welcomer_data['author'].get('icon_url', ''),
                interaction.user
            )
            
            if author_icon_url and self.is_valid_url(author_icon_url):
                embed.set_author(
                    name=author_name,
                    url=author_url,
                    icon_url=author_icon_url
                )
            else:
                embed.set_author(
                    name=author_name,
                    url=author_url
                )
        
        if self.welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(
                self.welcomer_data['thumbnail_url'],
                interaction.user
            )
            if thumbnail_url and self.is_valid_url(thumbnail_url):
                embed.set_thumbnail(url=thumbnail_url)
        
        if self.welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(
                self.welcomer_data['image_url'],
                interaction.user
            )
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        await self.original_message.edit(
            content="Current welcome message preview:" + ("\n" + message_content if message_content else ""),
            embed=embed,
            view=combined_view
        )

    async def finish_setup(
        self, 
        interaction: discord.Interaction
    ) -> None:
        self.welcomer_data['enabled'] = True
        db[str(interaction.guild.id)]["welcomer"].update_one(
            {}, 
            {"$set": self.welcomer_data}, 
            upsert=True
        )
        
        channel_select: WelcomerChannelSelect = (
            WelcomerChannelSelect(
                self.bot,
                self.user_id,
                self.welcomer_data,
                interaction.guild
            )
        )
        view: discord.ui.View = discord.ui.View()
        view.add_item(channel_select)
        
        embed: discord.Embed = discord.Embed(
            title="Select Welcomer Channel",
            description=(
                "Please select the channel for welcome messages."
            ),
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(
            embed=embed, 
            view=view, 
            ephemeral=True
        )
        if self.original_message:
            await self.original_message.delete()

    async def update_preview_embed(
        self, 
        interaction: discord.Interaction
    ) -> None:
        embed: discord.Embed = discord.Embed()
        message_content = parse_welcomer_content(
            self.welcomer_data.get('message', ''),
            interaction.user
        )
        view = discord.ui.View()
        if 'buttons' in self.welcomer_data:
            for button in self.welcomer_data['buttons']:
                view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))

        if self.welcomer_data.get('title'):
            embed.title = parse_welcomer_content(
                self.welcomer_data['title'],
                interaction.user
            )
        
        if self.welcomer_data.get('description'):
            embed.description = parse_welcomer_content(
                self.welcomer_data['description'],
                interaction.user
            )
        else:
            embed.description = "\u200b"  # Add an empty character if no description
        
        if self.welcomer_data.get('color'):
            embed.color = discord.Color.from_str(
                self.welcomer_data['color']
            )
        
        if self.welcomer_data.get('footer'):
            embed.set_footer(
                text=self.welcomer_data['footer'].get('text'),
                icon_url=self.welcomer_data['footer'].get(
                    'icon_url'
                )
            )
        
        if self.welcomer_data.get('author'):
            author_name: str = parse_welcomer_content(
                self.welcomer_data['author'].get('name', ''),
                interaction.user
            )
            author_url: Optional[str] = (
                self.welcomer_data['author'].get('url')
            )
            author_icon_url: str = parse_welcomer_content(
                self.welcomer_data['author'].get(
                    'icon_url', ''
                ),
                interaction.user
            )
            
            if (
                author_icon_url and 
                not self.is_valid_url(author_icon_url)
            ):
                author_icon_url = None
            
            embed.set_author(
                name=author_name,
                url=author_url,
                icon_url=author_icon_url
            )
        
        if self.welcomer_data.get('thumbnail_url'):
            thumbnail_url: str = parse_welcomer_content(
                self.welcomer_data['thumbnail_url'],
                interaction.user
            )
            if (
                thumbnail_url and 
                self.is_valid_url(thumbnail_url)
            ):
                embed.set_thumbnail(url=thumbnail_url)
        
        if self.welcomer_data.get('image_url'):
            image_url: str = parse_welcomer_content(
                self.welcomer_data['image_url'],
                interaction.user
            )
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        await self.original_message.edit(
            content="Current welcome message preview:" + ("\n" + message_content if message_content else ""),
            embed=embed,
            view=view
        )


    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

class WelcomerChannelSelect(discord.ui.Select):
    def __init__(
        self, 
        bot: commands.Bot,
        user_id: int,
        welcomer_data: Dict[str, Any],
        guild: discord.Guild
    ):
        self.bot: commands.Bot = bot
        self.user_id: int = user_id
        self.welcomer_data: Dict[str, Any] = welcomer_data
        options: List[discord.SelectOption] = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id)
            ) 
            for channel in guild.text_channels
        ]
        super().__init__(
            placeholder="Select a channel",
            options=options
        )

    async def callback(
        self, 
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You are not authorized to use this menu.",
                ephemeral=True
            )
            return

        selected_channel_id: int = int(self.values[0])
        self.welcomer_data['channel_id'] = selected_channel_id
        db[str(interaction.guild.id)]["welcomer"].update_one(
            {}, 
            {"$set": self.welcomer_data}, 
            upsert=True
        )

        channel: discord.TextChannel = (
            interaction.guild.get_channel(selected_channel_id)
        )
        embed: discord.Embed = discord.Embed(
            title="Welcomer Setup Complete", 
            description=(
                f"Your welcome message has been set up "
                f"successfully! Welcome messages will be "
                f"sent to {channel.mention}."
            ), 
            color=discord.Color.green()
        )
        await interaction.response.send_message(
            embed=embed, 
            ephemeral=True
        )

class BaseModal(discord.ui.Modal):
    def __init__(
        self, 
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(title="Edit Welcomer")
        self.bot: commands.Bot = bot
        self.guild_id: int = guild_id
        self.welcomer_data: Dict[str, Any] = welcomer_data

    async def on_submit(
        self, 
        interaction: discord.Interaction
    ) -> None:
        self.update_welcomer_data()
        db[str(self.guild_id)]["welcomer"].update_one(
            {}, 
            {"$set": self.welcomer_data}, 
            upsert=True
        )
        await interaction.response.send_message(
            "Field updated successfully!",
            ephemeral=True
        )

    def update_welcomer_data(self) -> None:
        pass

class TitleModal(BaseModal):
    embed_title: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Embed Title",
            style=discord.TextStyle.short,
            required=False,
            max_length=4000
        )
    )

    def __init__(
        self, 
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.embed_title.default = welcomer_data.get('title', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['title'] = self.embed_title.value

class DescriptionModal(BaseModal):
    description: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Embed Description",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=4000
        )
    )

    def __init__(
        self, 
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.description.default = welcomer_data.get(
            'description', ''
        )

    def update_welcomer_data(self) -> None:
        self.welcomer_data['description'] = self.description.value

class FooterModal(BaseModal):
    footer_text: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Footer Text",
            style=discord.TextStyle.short,
            required=False
        )
    )
    footer_icon_url: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Footer Icon URL",
            style=discord.TextStyle.short,
            required=False
        )
    )

    def __init__(
        self, 
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.footer_text.default = welcomer_data.get(
            'footer', {}
        ).get('text', '')
        self.footer_icon_url.default = welcomer_data.get(
            'footer', {}
        ).get('icon_url', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['footer'] = {
            'text': self.footer_text.value,
            'icon_url': self.footer_icon_url.value
        }

class AuthorModal(BaseModal):
    author_name: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Author Name",
            style=discord.TextStyle.short,
            required=False
        )
    )
    author_url: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Author URL",
            style=discord.TextStyle.short,
            required=False
        )
    )
    author_icon_url: discord.ui.TextInput = (
        discord.ui.TextInput(
            label="Author Icon URL",
            style=discord.TextStyle.short,
            required=False
        )
    )

    def __init__(
        self, 
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.author_name.default = welcomer_data.get('author', {}).get('name', '')
        self.author_url.default = welcomer_data.get('author', {}).get('url', '')
        self.author_icon_url.default = welcomer_data.get('author', {}).get('icon_url', '')

    def update_welcomer_data(self):
        self.welcomer_data['author'] = {
            'name': self.author_name.value,
            'url': self.author_url.value,
            'icon_url': self.author_icon_url.value
        }

class ThumbnailModal(BaseModal):
    thumbnail_url = discord.ui.TextInput(
        label="Thumbnail URL",
        style=discord.TextStyle.short,
        required=False
    )

    def __init__(
        self,
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.thumbnail_url.default = welcomer_data.get(
            'thumbnail_url', ''
        )

    def update_welcomer_data(self) -> None:
        self.welcomer_data['thumbnail_url'] = (
            self.thumbnail_url.value
        )

class MessageModal(BaseModal):
    message_content: discord.ui.TextInput = discord.ui.TextInput(
        label="Message Content",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=2000
    )

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.message_content.default = welcomer_data.get('message', '')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['message'] = self.message_content.value


class ButtonModal(BaseModal):
    button_label: discord.ui.TextInput = discord.ui.TextInput(
        label="Button Label",
        style=discord.TextStyle.short,
        required=True
    )
    button_url: discord.ui.TextInput = discord.ui.TextInput(
        label="Button URL",
        style=discord.TextStyle.short,
        required=True
    )

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.button_label.default = ''
        self.button_url.default = ''

    def update_welcomer_data(self) -> None:
        if 'buttons' not in self.welcomer_data:
            self.welcomer_data['buttons'] = []
        self.welcomer_data['buttons'].append({
            'label': self.button_label.value,
            'url': self.button_url.value
        })


class RemoveButtonModal(BaseModal):
    button_label: discord.ui.TextInput = discord.ui.TextInput(
        label="Button Label to Remove",
        style=discord.TextStyle.short,
        required=True
    )

    def __init__(self, bot: commands.Bot, guild_id: int, welcomer_data: Dict[str, Any]):
        super().__init__(bot, guild_id, welcomer_data)
        self.button_label.default = ''

    def update_welcomer_data(self) -> None:
        if 'buttons' in self.welcomer_data:
            self.welcomer_data['buttons'] = [
                button for button in self.welcomer_data['buttons']
                if button['label'] != self.button_label.value
            ]
        

class ImageModal(BaseModal):
    image_url = discord.ui.TextInput(
        label="Image URL",
        style=discord.TextStyle.short,
        required=False
    )

    def __init__(
        self,
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.image_url.default = welcomer_data.get(
            'image_url', ''
        )

    def update_welcomer_data(self) -> None:
        self.welcomer_data['image_url'] = self.image_url.value

class ColorModal(BaseModal):
    color = discord.ui.TextInput(
        label="Color (hex code)",
        style=discord.TextStyle.short,
        required=False,
        max_length=7
    )

    def __init__(
        self,
        bot: commands.Bot,
        guild_id: int,
        welcomer_data: Dict[str, Any]
    ):
        super().__init__(bot, guild_id, welcomer_data)
        self.color.default = welcomer_data.get('color', '#000000')

    def update_welcomer_data(self) -> None:
        self.welcomer_data['color'] = self.color.value

class Welcomer(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
 
    @commands.hybrid_group(
        name="welcomer",
        description="Manage the welcome message for new members.",
        invoke_without_command=True
    )
    async def welcomer_group(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Manage the welcome message for new members.
        - test: Test the welcome message

        If no subcommand is provided, this command will display help information.
        """
        if ctx.invoked_subcommand is None:
            help_embed = discord.Embed(
                title="Welcomer Commands",
                description="""
- `?welcomer edit`
  - Edit the welcome message
- `?welcomer toggle`
  - Turn the welcomer on or off
- `?welcomer test`
  - Test the welcome message
                """,
                color=discord.Color.dark_grey()
            )
            await ctx.reply(embed=help_embed)

    @welcomer_group.command(
        name="edit",
        description="Edit the welcome message."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_edit(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Edit the welcome message.

        **Usage:**
        ?welcomer edit
        /welcomer edit

        This command allows you to customize various aspects of the welcome message,
        including the title, description, color, footer, author, thumbnail, and image.

        **Note:** You must have the 'Manage Server' permission to use this command.
        """
        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            welcomer_data = {
                'enabled': False,
                'channel_id': None,
                'title': 'Welcome to the server!',
                'description': 'We hope you enjoy your stay.',
                'color': '#000000',
                'footer': {
                    'text': 'Thanks for joining!',
                    'icon_url': ''
                },
                'author': {
                    'name': '',
                    'url': '',
                    'icon_url': ''
                },
                'thumbnail_url': '',
                'image_url': ''
            }
            db[str(ctx.guild.id)]["welcomer"].insert_one(
                welcomer_data
            )
        
        combined_view = discord.ui.View()
        select = WelcomerSetupSelect(
            self.bot,
            ctx.author.id,
            ctx.message,
            welcomer_data
        )
        combined_view.add_item(select)
        
        if 'buttons' in welcomer_data:
            for button in welcomer_data['buttons']:
                combined_view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))
        
        # Create initial preview embed
        embed = discord.Embed()
        
        if welcomer_data.get('title'):
            embed.title = parse_welcomer_content(
                welcomer_data['title'],
                ctx.author
            )
        
        if welcomer_data.get('description'):
            embed.description = parse_welcomer_content(
                welcomer_data['description'],
                ctx.author
            )
        
        if welcomer_data.get('color'):
            embed.color = discord.Color.from_str(
                welcomer_data['color']
            )
        
        if welcomer_data.get('footer'):
            embed.set_footer(
                text=welcomer_data['footer'].get('text'),
                icon_url=welcomer_data['footer'].get('icon_url')
            )
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(
                welcomer_data['author'].get('name', ''),
                ctx.author
            )
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(
                welcomer_data['author'].get('icon_url', ''),
                ctx.author
            )
            
            if author_icon_url and self.is_valid_url(
                author_icon_url
            ):
                embed.set_author(
                    name=author_name,
                    url=author_url,
                    icon_url=author_icon_url
                )
            else:
                embed.set_author(
                    name=author_name,
                    url=author_url
                )
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(
                welcomer_data['thumbnail_url'],
                ctx.author
            )
            if thumbnail_url and self.is_valid_url(
                thumbnail_url
            ):
                embed.set_thumbnail(url=thumbnail_url)
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(
                welcomer_data['image_url'],
                ctx.author
            )
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)
        
        message_content = parse_welcomer_content(welcomer_data.get('message', ''), ctx.author)
        
        try:
            message = await ctx.reply(
                content="Please select the fields you want to edit for your welcome message:\n" + 
                        (message_content if message_content else ""),
                view=combined_view,
                embed=embed
            )
            select.original_message = message
        except discord.errors.HTTPException as e:
            error_message = f"An error occurred while creating the preview: {str(e)}"
            await ctx.reply(error_message)

    @welcomer_group.command(
        name="toggle",
        description="Turn the welcomer on or off."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_toggle(
        self,
        ctx: commands.Context,
        state: str
    ) -> None:
        """
        Turn the welcomer on or off.

        **Usage:**
        ?welcomer toggle <state>
        /welcomer toggle <state>

        **Parameters:**
        state: Either 'on' or 'off' to enable or disable the welcomer.

        **Example:**
        ?welcomer toggle on
        /welcomer toggle off

        **Note:** You must have the 'Manage Server' permission to use this command.
        """
        if state.lower() not in ['on', 'off']:
            await ctx.reply(
                "Please specify either 'on' or 'off'."
            )
            return

        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one() or {}
        welcomer_data['enabled'] = (state.lower() == 'on')
        db[str(ctx.guild.id)]["welcomer"].update_one(
            {},
            {"$set": welcomer_data},
            upsert=True
        )
        await ctx.reply(f"Welcomer has been turned {state.lower()}.")

    @welcomer_group.command(
        name="test",
        description="Test the welcome message."
    )
    @commands.has_permissions(manage_guild=True)
    async def welcomer_test(
        self,
        ctx: commands.Context
    ) -> None:
        """
        Test the welcome message.

        **Usage:**
        ?welcomer test
        /welcomer test

        This command will display a preview of the current welcome message,
        allowing you to see how it will appear for new members.

        **Note:** You must have the 'Manage Server' permission to use this command.
        """
        welcomer_data = db[str(ctx.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            welcomer_data = {
                'enabled': False,
                'channel_id': None,
                'title': 'Welcome to the server!',
                'description': 'We hope you enjoy your stay.',
                'color': '#000000',
                'footer': {
                    'text': 'Thanks for joining!',
                    'icon_url': ''
                },
                'author': {
                    'name': '',
                    'url': '',
                    'icon_url': ''
                },
                'thumbnail_url': '',
                'image_url': ''
            }
            db[str(ctx.guild.id)]["welcomer"].insert_one(
                welcomer_data
            )
        
        embed = discord.Embed()
        
        if welcomer_data.get('title'):
            embed.title = parse_welcomer_content(
                welcomer_data['title'],
                ctx.author
            )
        
        if welcomer_data.get('description'):
            embed.description = parse_welcomer_content(
                welcomer_data['description'],
                ctx.author
            )
        else:
            embed.description = "\u200b"  # Add an empty character if no description
        
        if welcomer_data.get('color'):
            embed.color = discord.Color.from_str(
                welcomer_data['color']
            )
        
        if welcomer_data.get('footer'):
            embed.set_footer(
                text=parse_welcomer_content(
                    welcomer_data['footer'].get('text', ''),
                    ctx.author
                ),
                icon_url=welcomer_data['footer'].get('icon_url')
            )
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(
                welcomer_data['author'].get('name', ''),
                ctx.author
            )
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(
                welcomer_data['author'].get('icon_url', ''),
                ctx.author
            )
            
            if author_icon_url and self.is_valid_url(
                author_icon_url
            ):
                embed.set_author(
                    name=author_name,
                    url=author_url,
                    icon_url=author_icon_url
                )
            else:
                embed.set_author(
                    name=author_name,
                    url=author_url
                )
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(
                welcomer_data['thumbnail_url'],
                ctx.author
            )
            if thumbnail_url and self.is_valid_url(
                thumbnail_url
            ):
                embed.set_thumbnail(url=thumbnail_url)
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(
                welcomer_data['image_url'],
                ctx.author
            )
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        message_content = parse_welcomer_content(welcomer_data.get('message', ''), ctx.author)
        view = discord.ui.View()
        if 'buttons' in welcomer_data:
            for button in welcomer_data['buttons']:
                view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))

        try:
            await ctx.send(content=message_content, embed=embed, view=view)
        except discord.errors.HTTPException as e:
            error_message = (
                f"An error occurred while sending "
                f"the test message: {str(e)}"
            )
            await ctx.reply(error_message)

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ) -> None:
        welcomer_data = db[str(member.guild.id)]["welcomer"].find_one()
        if not welcomer_data:
            welcomer_data = {
                'enabled': False,
                'channel_id': None,
                'title': 'Welcome to the server!',
                'description': 'We hope you enjoy your stay.',
                'color': '#000000',
                'footer': {
                    'text': 'Thanks for joining!',
                    'icon_url': ''
                },
                'author': {
                    'name': '',
                    'url': '',
                    'icon_url': ''
                },
                'thumbnail_url': '',
                'image_url': ''
            }
            db[str(member.guild.id)]["welcomer"].insert_one(
                welcomer_data
            )

        if not welcomer_data.get('enabled', False):
            return

        channel_id = welcomer_data.get('channel_id')
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed()
        
        if welcomer_data.get('title'):
            embed.title = parse_welcomer_content(
                welcomer_data['title'],
                member
            )
        
        if welcomer_data.get('description'):
            embed.description = parse_welcomer_content(
                welcomer_data['description'],
                member
            )
        
        if welcomer_data.get('color'):
            embed.color = discord.Color.from_str(
                welcomer_data['color']
            )
        
        if welcomer_data.get('footer'):
            embed.set_footer(
                text=parse_welcomer_content(
                    welcomer_data['footer'].get('text', ''),
                    member
                ),
                icon_url=welcomer_data['footer'].get('icon_url')
            )
        
        if welcomer_data.get('author'):
            author_name = parse_welcomer_content(
                welcomer_data['author'].get('name', ''),
                member
            )
            author_url = welcomer_data['author'].get('url')
            author_icon_url = parse_welcomer_content(
                welcomer_data['author'].get('icon_url', ''),
                member
            )
            
            if author_icon_url and self.is_valid_url(
                author_icon_url
            ):
                embed.set_author(
                    name=author_name,
                    url=author_url,
                    icon_url=author_icon_url
                )
            else:
                embed.set_author(
                    name=author_name,
                    url=author_url
                )
        
        if welcomer_data.get('image_url'):
            image_url = parse_welcomer_content(
                welcomer_data['image_url'],
                member
            )
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)
        
        if welcomer_data.get('thumbnail_url'):
            thumbnail_url = parse_welcomer_content(
                welcomer_data['thumbnail_url'],
                member
            )
            if thumbnail_url and self.is_valid_url(
                thumbnail_url
            ):
                embed.set_thumbnail(url=thumbnail_url)

        message_content = parse_welcomer_content(welcomer_data.get('message', ''), member)
        view = discord.ui.View()
        if 'buttons' in welcomer_data:
            for button in welcomer_data['buttons']:
                view.add_item(discord.ui.Button(
                    label=button['label'], 
                    url=button['url'],
                    style=discord.ButtonStyle.grey
                ))

        try:
            await channel.send(content=message_content, embed=embed, view=view)
        except discord.errors.HTTPException as e:
            print(
                f"An error occurred while sending "
                f"the welcome message: {str(e)}"
            )

    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    async def select_welcomer_channel(
        self,
        ctx: commands.Context
    ) -> None:
        class ChannelSelect(discord.ui.Select):
            def __init__(self, channels):
                options = [
                    discord.SelectOption(
                        label=channel.name,
                        value=str(channel.id)
                    ) for channel in channels
                ]
                super().__init__(
                    placeholder="Select a channel for welcome messages",
                    options=options
                )
            async def callback(
                self,
                interaction: discord.Interaction
            ):
                channel_id = int(self.values[0])
                welcomer_data = (
                    db[str(ctx.guild.id)]
                    ["welcomer"]
                    .find_one() or {}
                )
                welcomer_data['channel_id'] = channel_id
                db[str(ctx.guild.id)]["welcomer"].update_one(
                    {},
                    {"$set": welcomer_data},
                    upsert=True
                )
                await interaction.response.send_message(
                    f"Welcome messages will now be sent to <#{channel_id}>."
                )

        text_channels = [
            channel for channel in ctx.guild.channels
            if isinstance(channel, discord.TextChannel)
        ]
        view = discord.ui.View()
        view.add_item(ChannelSelect(text_channels))
        await ctx.send(
            "Please select a channel for welcome messages:",
            view=view
        )

async def setup(bot):
    try:
        await bot.add_cog(Welcomer(bot))
    except Exception as e:
        bot.logger.error(
            f'Failed to add welcomer cog: {e}'
        )
