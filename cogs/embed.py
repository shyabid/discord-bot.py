from discord.ext import commands
import discord
from discord import app_commands
from db import db
import typing

def get_embed_names(guild_id: str):
    embeds = db[guild_id]['embeds'].find({}, {"name": 1, "_id": 0})
    return [embed['name'] for embed in embeds]

def autocomplete():
    async def autocompletion(
        interaction: discord.Interaction,
        current: str
    ) -> typing.List[app_commands.Choice[str]]:
        embed_names = get_embed_names(str(interaction.guild.id))
        return [
            app_commands.Choice(name=name, value=name)
            for name in embed_names
        ]
    return autocompletion

class EmbedMakerModal(discord.ui.Modal, title="Create/Update Reaction Role Embed"):
    titletxt = discord.ui.TextInput(label="Title", placeholder="Enter the title for your embed", required=True, max_length=4000)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, required=False, max_length=4000)
    color = discord.ui.TextInput(label="Color (hex code)", required=False, max_length=7)
    image_url = discord.ui.TextInput(label="Image URL", required=False)
    
    def __init__(self, bot, embed_name, embed_data=None, original_message=None):
        super().__init__()
        self.bot = bot
        self.embed_name = embed_name
        self.embed_data = embed_data
        self.original_message = original_message
        
        if self.embed_data:
            self.titletxt.default = self.embed_data.get('title', '')
            self.description.default = self.embed_data.get('description', '')
            self.color.default = self.embed_data.get('color', '')
            self.image_url.default = self.embed_data.get('image_url', '')

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

        if self.embed_data:  # If editing an embed
            channel = await interaction.guild.fetch_channel(self.embed_data['channel_id'])
            message = await channel.fetch_message(self.embed_data['msg_id'])
            await message.edit(embed=embed)

            db[str(interaction.guild.id)]['embeds'].update_one(
                {"name": self.embed_name},
                {"$set": {
                    "title": self.titletxt.value,
                    "description": self.description.value,
                    "color": self.color.value,
                    "image_url": self.image_url.value
                }}
            )
            await interaction.response.send_message(f"Embed '{self.embed_name}' updated successfully.", ephemeral=True)
            if self.original_message:
                await self.original_message.delete()
        else:
            interaction.client.reaction_role_embed = embed
            interaction.client.reaction_role_embed_name = self.embed_name
            
            view = discord.ui.View()
            view.add_item(ChannelSelect(interaction.client, interaction.guild.id, interaction.user.id, self.original_message))
            
            embed = discord.Embed(description="Select a channel to send the embed:", color=discord.Color.dark_gray())
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot, guild_id, user_id, original_message):
        super().__init__(placeholder="Select a channel", channel_types=[discord.ChannelType.text])
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.original_message = original_message

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return

        channel = self.values[0].id
        channel = await interaction.client.fetch_channel(channel)

        msg: discord.Message = await channel.send(embed=self.bot.reaction_role_embed)

        db[str(self.guild_id)]['embeds'].insert_one({
            "name": self.bot.reaction_role_embed_name,
            "msg_id": msg.id,
            "channel_id": msg.channel.id,
            "user": self.user_id,
            "title": self.bot.reaction_role_embed.title,
            "description": self.bot.reaction_role_embed.description,
            "color": str(self.bot.reaction_role_embed.color),
            "image_url": self.bot.reaction_role_embed.image.url if self.bot.reaction_role_embed.image else ""
        })

        await interaction.response.send_message(content=f"Done! Embed '{self.bot.reaction_role_embed_name}' sent to the selected channel and stored in the database.", ephemeral=True)
        
        # Delete the original message containing the button
        if self.original_message:
            await self.original_message.delete()

class EmbedCreateButton(discord.ui.Button):
    def __init__(self, bot, name: str, user_id: int, original_message):
        super().__init__(label="Click to create embed", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.name = name
        self.user_id = user_id
        self.original_message = original_message

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
            return
        modal = EmbedMakerModal(self.bot, self.name, original_message=self.original_message)
        await interaction.response.send_modal(modal)

class Embed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
  - Creates an embed the unique name
- `?embed list`
  - Lists all the embeds in this guild
- `?embed delete <name>`
  - Deletes an embed by name
- `?embed edit <name>`
  - Edits an existing embed
                """,
                color=discord.Color.blue()
            )
            await ctx.reply(embed=help_embed)
    @embedgroup.command(
        name="create",
        description="Create a new embed."
    )
    @app_commands.describe(name="Give a name for your embed. It should be unique and one worded.")
    async def embed_create(self, ctx: commands.Context, name: str):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True, delete_after=5)
            return

        if ' ' in name:
            await ctx.reply("Embed name cannot contain spaces. Please use a single word or connect words with underscores.", ephemeral=True)
            return
        
        view = discord.ui.View()
        message = await ctx.reply("Click the button below to start creating your embed.", view=view)
        view.add_item(EmbedCreateButton(self.bot, name, ctx.author.id, message))
        await message.edit(view=view)

    @embedgroup.command(
        name="list",
        description="List all the embeds in this guild."
    )
    async def embed_list(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True, delete_after=5)
            return


        embeds = db[str(ctx.guild.id)]['embeds'].find() 
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
            await ctx.reply("You do not have permission to use this command.", ephemeral=True, delete_after=5)
            return

        embed_data = db[str(ctx.guild.id)]['embeds'].find_one({"name": name})
        
        if not embed_data:
            await ctx.reply(f"No embed found with name `{name}`.")
            return
    
        channel = await ctx.guild.fetch_channel(embed_data["channel_id"])
        message = await channel.fetch_message(embed_data["msg_id"])
        await message.delete()

        db[str(ctx.guild.id)]['embeds'].delete_one({"name": name})

        await ctx.reply(f"Embed `{name}` deleted successfully.")
    
    @embedgroup.command(
        name="edit",
        description="Edit an existing embed."
    )
    @app_commands.autocomplete(name=autocomplete())
    @app_commands.describe(name="Name of the embed that you want to edit")
    async def embed_edit(self, ctx: commands.Context, name: str):
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("You do not have permission to use this command.", ephemeral=True, delete_after=5)
            return

        embed_data = db[str(ctx.guild.id)]['embeds'].find_one({"name": name})

        if not embed_data:
            await ctx.reply(f"No embed found with name `{name}`.")
            return

        class EditEmbedButton(discord.ui.Button):
            def __init__(self, bot, embed_data, name, user_id, original_message):
                super().__init__(label="Edit Embed", style=discord.ButtonStyle.primary)
                self.bot = bot
                self.embed_data = embed_data
                self.name = name
                self.user_id = user_id
                self.original_message = original_message
                
            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("You are not authorized to use this button.", ephemeral=True)
                    return
                modal = EmbedMakerModal(self.bot, self.name, embed_data=self.embed_data, original_message=self.original_message)
                await interaction.response.send_modal(modal)

        view = discord.ui.View()
        message = await ctx.reply(f"Click the button to edit the embed '{name}':")
        view.add_item(EditEmbedButton(self.bot, embed_data, name, ctx.author.id, message))
        await message.edit(view=view)

async def setup(bot):
    await bot.add_cog(Embed(bot))
    