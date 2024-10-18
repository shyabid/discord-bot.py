from discord.ext import commands
import discord
from discord import app_commands
from urllib.parse import urlparse
import typing
from cogs.welcomer import parse_welcomer_content, WelcomerSetupSelect, BaseModal


class TitleModal(BaseModal):
    title = discord.ui.TextInput(
        label="Embed Title",
        style=discord.TextStyle.short,
        required=False
    )

    def __init__(self, bot: commands.Bot, guild_id: int, embed_data: dict):
        super().__init__(bot, guild_id, embed_data)
        self.title.default = embed_data.get('title', '')

    def update_embed_data(self):
        self.embed_data['title'] = self.title.value

class DescriptionModal(BaseModal):
    description = discord.ui.TextInput(
        label="Embed Description",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, bot: commands.Bot, guild_id: int, embed_data: dict):
        super().__init__(bot, guild_id, embed_data)
        self.description.default = embed_data.get('description', '')

    def update_embed_data(self):
        self.embed_data['description'] = self.description.value

class ColorModal(BaseModal):
    color = discord.ui.TextInput(
        label="Embed Color (hex code)",
        style=discord.TextStyle.short,
        required=False
    )

    def __init__(self, bot: commands.Bot, guild_id: int, embed_data: dict):
        super().__init__(bot, guild_id, embed_data)
        self.color.default = embed_data.get('color', '')

    def update_embed_data(self):
        self.embed_data['color'] = self.color.value

class ImageModal(BaseModal):
    image_url = discord.ui.TextInput(
        label="Image URL",
        style=discord.TextStyle.short,
        required=False
    )

    def __init__(self, bot: commands.Bot, guild_id: int, embed_data: dict):
        super().__init__(bot, guild_id, embed_data)
        self.image_url.default = embed_data.get('image_url', '')

    def update_embed_data(self):
        self.embed_data['image_url'] = self.image_url.value

class EmbedSetupSelect(WelcomerSetupSelect):
    def __init__(self, bot: commands.Bot, user_id: int, original_message: discord.Message, embed_data: dict):
        super().__init__(bot, user_id, original_message, embed_data)
        self.embed_data = embed_data
        self.options = [
            discord.SelectOption(label="Embed Title", description="Set the title of the embed"),
            discord.SelectOption(label="Embed Description", description="Set the description of the embed"),
            discord.SelectOption(label="Embed Color", description="Set the color of the embed"),
            discord.SelectOption(label="Embed Image", description="Set the image of the embed"),
            discord.SelectOption(label="Finish", description="Finish setting up the embed")
        ]

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return

        selected_option = self.values[0]
        if selected_option == "Finish":
            await self.finish_setup(interaction)
        else:
            modal_class = {
                "Embed Title": TitleModal,
                "Embed Description": DescriptionModal,
                "Embed Color": ColorModal,
                "Embed Image": ImageModal
            }[selected_option]
            
            modal = modal_class(self.bot, interaction.guild.id, self.embed_data)
            await interaction.response.send_modal(modal)
            await modal.wait()
            
            await self.update_preview_embed(interaction)

    async def finish_setup(self, interaction: discord.Interaction):
        self.bot.db[str(interaction.guild.id)]["embeds"].update_one(
            {"name": self.embed_data['name']}, 
            {"$set": self.embed_data}, 
            upsert=True
        )
        
        await interaction.response.send_message(f"Embed '{self.embed_data['name']}' has been created/updated successfully.", ephemeral=True)
        await self.original_message.delete()

    async def update_preview_embed(self, interaction: discord.Interaction):
        embed = discord.Embed()
        
        if self.embed_data.get('title'):
            embed.title = parse_welcomer_content(self.embed_data['title'], interaction.user)
        
        if self.embed_data.get('description'):
            embed.description = parse_welcomer_content(self.embed_data['description'], interaction.user)
        
        if self.embed_data.get('color'):
            embed.color = discord.Color.from_str(self.embed_data['color'])
        
        if self.embed_data.get('image_url'):
            image_url = parse_welcomer_content(self.embed_data['image_url'], interaction.user)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        await self.original_message.edit(content="Current embed preview:", embed=embed)

class Embed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_embed_names(self, guild_id: str):
        embeds = self.bot.db[guild_id]['embeds'].find({}, {"name": 1, "_id": 0})
        return [embed['name'] for embed in embeds]

    
    @commands.hybrid_group(
        name="embed",
        description="Edit and create embeds.",
        invoke_without_command=True
    )
    async def embedgroup(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            help_embed = discord.Embed(
                title="Embed Commands",
                description="""
- `?embed create <name>`
  - Creates an embed with the unique name
- `?embed list`
  - Lists all the embeds in this guild
- `?embed delete <name>`
  - Deletes an embed by name
- `?embed edit <name>`
  - Edits an existing embed
- `?embed send <name> <channel>`
  - Sends an embed to a specified channel
                """,
                color=discord.Color.dark_grey()
            )
            await ctx.reply(embed=help_embed)

    @embedgroup.command(
        name="create",
        description="Create a new embed."
    )
    @app_commands.describe(name="Give a name for your embed. It should be unique and one worded.")
    async def embed_create(self, ctx: commands.Context, name: str):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True)
            return

        if ' ' in name:
            await ctx.reply("Embed name cannot contain spaces. Please use a single word or connect words with underscores.", ephemeral=True)
            return
        
        embed_data = {"name": name}
        view = discord.ui.View()
        select = EmbedSetupSelect(self.bot, ctx.author.id, None, embed_data)
        view.add_item(select)
        
        message = await ctx.reply("Please select the fields you want to edit for your embed:", view=view)
        select.original_message = message

    @embedgroup.command(
        name="list",
        description="List all the embeds in this guild."
    )
    async def embed_list(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True)
            return

        embeds = self.bot.db[str(ctx.guild.id)]['embeds'].find() 
        embed_list = [f"`{embed['name']}`" for embed in embeds]

        if not embed_list:
            await ctx.reply("No embeds found.")
        else:
            embed = discord.Embed(
                title="Embeds List",
                description=", ".join(embed_list),
                color=discord.Color.green()
            )
            await ctx.reply(embed=embed)
    
    @embedgroup.command(
        name="delete",
        description="Delete an embed by name."
    )
    @app_commands.describe(name="Name of the embed that you want to delete")
    async def embed_delete(self, ctx: commands.Context, name: str):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True)
            return

        result = self.bot.db[str(ctx.guild.id)]['embeds'].delete_one({"name": name})

        if result.deleted_count > 0:
            await ctx.reply(f"Embed `{name}` deleted successfully from the database.")
        else:
            await ctx.reply(f"No embed found with name `{name}`.")
    
    @embedgroup.command(
        name="edit",
        description="Edit an existing embed."
    )
    # @app_commands.autocomplete(name=autocomplete())
    @app_commands.describe(name="Name of the embed that you want to edit")
    async def embed_edit(self, ctx: commands.Context, name: str):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True)
            return

        embed_data = self.bot.db[str(ctx.guild.id)]['embeds'].find_one({"name": name})

        if not embed_data:
            await ctx.reply(f"No embed found with name `{name}`.")
            return

        view = discord.ui.View()
        select = EmbedSetupSelect(self.bot, ctx.author.id, None, embed_data)
        view.add_item(select)
        
        message = await ctx.reply(f"Please select the fields you want to edit for the embed '{name}':", view=view)
        select.original_message = message

    @embedgroup.command(
        name="send",
        description="Send an embed to a specified channel."
    )
    # @app_commands.autocomplete(name=autocomplete())
    @app_commands.describe(
        name="Name of the embed that you want to send",
        channel="The channel where you want to send the embed"
    )
    async def embed_send(self, ctx: commands.Context, name: str, channel: discord.TextChannel):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True)
            return

        embed_data = self.bot.db[str(ctx.guild.id)]['embeds'].find_one({"name": name})

        if not embed_data:
            await ctx.reply(f"No embed found with name `{name}`.")
            return

        embed = discord.Embed()
        
        if embed_data.get('title'):
            embed.title = parse_welcomer_content(embed_data['title'], ctx.author)
        
        if embed_data.get('description'):
            embed.description = parse_welcomer_content(embed_data['description'], ctx.author)
        
        if embed_data.get('color'):
            embed.color = discord.Color.from_str(embed_data['color'])
        
        if embed_data.get('image_url'):
            image_url = parse_welcomer_content(embed_data['image_url'], ctx.author)
            if image_url and self.is_valid_url(image_url):
                embed.set_image(url=image_url)

        try:
            await channel.send(embed=embed)
            await ctx.reply(f"Embed '{name}' sent successfully to {channel.mention}.")
        except discord.errors.Forbidden:
            await ctx.reply(f"I don't have permission to send messages in {channel.mention}.")
        except Exception as e:
            await ctx.reply(f"An error occurred while sending the embed: {str(e)}")

    def is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

async def setup(bot):
    await bot.add_cog(Embed(bot))