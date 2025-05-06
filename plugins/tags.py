import discord
from discord.ext import commands
from discord import app_commands
from typing import Union, Optional, List, Dict, Any
from datetime import datetime
from bot import Morgana

class Tags(commands.Cog):
    def __init__(self, bot: Morgana):
        self.bot: Morgana = bot

    @commands.hybrid_group(name="tag", invoke_without_command=True, description="Retrieve or manage tags", aliases=["tags", "tg"])
    @app_commands.describe(name="The name of the tag to retrieve")
    async def tag(self, ctx, *, name: str = None):
        """
        Allows you to tag text for later retrieval.
        
        If a subcommand is not called, then this will search the tag database
        for the tag requested.
        """
        if name is None:
            return await ctx.reply("You need to specify a tag name or subcommand. Available subcommands:\n> `create`, `edit`, `remove`, `info`, `list`, `random`, `all`, `alias`, `search`, `stats`.")

        tag_data = self.bot.db.get_tag(ctx.guild.id, name)
        if not tag_data:
            return await ctx.reply(f"Tag `{name}` not found.")
        
        await ctx.send(tag_data["content"])

    @tag.command(name="create", description="Create a new tag")
    @app_commands.describe(
        name="The name of the tag to create",
        content="The content of the tag"
    )
    async def tag_create(self, ctx, name: str, *, content: str):
        """Creates a new tag owned by you."""
        if len(name) > 100:
            return await ctx.reply("Tag name is too long (maximum 100 characters)")
        
        if len(content) > 2000:
            return await ctx.reply("Tag content is too long (maximum 2000 characters)")
            
        success = self.bot.db.create_tag(ctx.guild.id, name, content, ctx.author.id)
        
        if success:
            await ctx.reply(f"Tag `{name}` created successfully.")
        else:
            await ctx.reply(f"A tag with the name `{name}` already exists.")

    @tag.command(name="alias", description="Create an alias for an existing tag")
    @app_commands.describe(
        new_name="The name of the alias to create",
        old_name="The name of the existing tag"
    )
    async def tag_alias(self, ctx, new_name: str, *, old_name: str):
        """Creates an alias for a pre-existing tag."""
        if len(new_name) > 100:
            return await ctx.reply("Tag alias name is too long (maximum 100 characters)")
        
        # Check if original tag exists
        original_tag = self.bot.db.get_tag(ctx.guild.id, old_name)
        if not original_tag:
            return await ctx.reply(f"Tag `{old_name}` not found.")
        
        # Create the alias
        success = self.bot.db.create_tag_alias(ctx.guild.id, new_name, old_name)
        if success:
            await ctx.reply(f"Created alias `{new_name}` pointing to `{old_name}`.")
        else:
            await ctx.reply(f"An alias or tag with the name `{new_name}` already exists.")

    @tag.command(name="all", description="List all tags in the server")
    @app_commands.describe(text="Whether to show tag names (yes) or just count (no)")
    async def tag_all(self, ctx, text: str = "yes"):
        """Lists all server-specific tags for this server."""
        show_text = text.lower() not in ("no", "false", "0")
        
        tags = self.bot.db.get_all_guild_tags(ctx.guild.id)
        if not tags:
            return await ctx.reply("This server has no tags.")
        
        tag_names = [tag["name"] for tag in tags]
        
        formatted_tags = ", ".join(tag_names) if show_text else f"{len(tags)} tags"
        
        embed = discord.Embed(
            title=f"Tags in {ctx.guild.name}",
            description=formatted_tags if show_text else None,
            color=discord.Colour.dark_grey()
        )
        
        if not show_text:
            embed.description = f"This server has {len(tags)} tags. Use `{ctx.prefix}tag all yes` to view them all."
        
        await ctx.reply(embed=embed)

    @tag.command(name="edit", description="Edit a tag you own")
    @app_commands.describe(
        name="The name of the tag to edit",
        content="The new content for the tag"
    )
    async def tag_edit(self, ctx, name: str, *, content: str = None):
        """Modifies an existing tag that you own."""
        if content is None:
            return await ctx.reply("You need to specify new content for the tag.")
            
        if len(content) > 2000:
            return await ctx.reply("Tag content is too long (maximum 2000 characters)")
        
        success = self.bot.db.edit_tag(ctx.guild.id, name, content, ctx.author.id)
        
        if success:
            await ctx.reply(f"Tag `{name}` edited successfully.")
        else:
            tag = self.bot.db.get_tag(ctx.guild.id, name)
            if not tag:
                await ctx.reply(f"Tag `{name}` does not exist.")
            else:
                await ctx.reply(f"You don't own the tag `{name}`.")

    @tag.command(name="remove", description="Remove a tag you own")
    @app_commands.describe(name="The name of the tag to remove")
    async def tag_remove(self, ctx, *, name: str):
        """Removes a tag that you own."""
        success = self.bot.db.delete_tag(ctx.guild.id, name, ctx.author.id)
        
        if success:
            await ctx.reply(f"Tag `{name}` deleted successfully.")
        else:
            tag = self.bot.db.get_tag(ctx.guild.id, name)
            if not tag:
                await ctx.reply(f"Tag `{name}` does not exist.")
            else:
                await ctx.reply(f"You don't own the tag `{name}`.")

    @tag.command(name="remove_id", description="Remove a tag by ID (Moderator only)")
    @app_commands.describe(tag_id="The ID of the tag to remove")
    @commands.has_permissions(manage_messages=True)
    async def tag_remove_id(self, ctx, tag_id: int):
        """Removes a tag by ID. Requires manage_messages permission."""
        tag = self.bot.db.get_tag_by_id(tag_id)
        
        if not tag or tag["guild_id"] != ctx.guild.id:
            return await ctx.reply(f"No tag with ID `{tag_id}` found in this server.")
        
        success = self.bot.db.delete_tag_by_id(tag_id)
        
        if success:
            await ctx.reply(f"Tag `{tag['name']}` (ID: {tag_id}) deleted successfully.")
        else:
            await ctx.reply(f"Failed to delete tag with ID `{tag_id}`.")

    @tag.command(name="info", description="Get information about a tag")
    @app_commands.describe(name="The name of the tag")
    async def tag_info(self, ctx, *, name: str):
        """Retrieves info about a tag."""
        tag = self.bot.db.get_tag_info(ctx.guild.id, name)
        
        if not tag:
            return await ctx.reply(f"Tag `{name}` not found.")
        
        created_at = datetime.strptime(tag["created_at"], "%Y-%m-%d %H:%M:%S")
        owner = ctx.guild.get_member(tag["owner_id"])
        owner_name = owner.name if owner else f"Unknown User ({tag['owner_id']})"
        
        embed = discord.Embed(
            title=f"Tag: {tag['name']}",
            color=discord.Colour.dark_grey()
        )
        
        embed.set_author(name=owner_name, icon_url=owner.avatar.url if owner and owner.avatar else None)
        embed.add_field(name="Owner", value=f"<@{tag['owner_id']}>", inline=True)
        embed.add_field(name="Uses", value=str(tag["use_count"]), inline=True)
        embed.add_field(name="ID", value=str(tag["tag_id"]), inline=True)
        embed.add_field(name="Created", value=f"<t:{int(created_at.timestamp())}:R>", inline=True)
        
        if tag["aliases"] and len(tag["aliases"]) > 0:
            embed.add_field(name="Aliases", value=", ".join(tag["aliases"]), inline=False)
        
        await ctx.reply(embed=embed)

    @tag.command(name="raw", description="Get the raw content of a tag")
    @app_commands.describe(name="The name of the tag")
    async def tag_raw(self, ctx, *, name: str):
        """Gets the raw content of the tag."""
        tag = self.bot.db.get_tag(ctx.guild.id, name)
        
        if not tag:
            return await ctx.reply(f"Tag `{name}` not found.")
        
        escaped_content = discord.utils.escape_markdown(tag["content"])
        await ctx.reply(escaped_content)

    @tag.command(name="search", description="Search for tags")
    @app_commands.describe(query="The search query (min 3 characters)")
    async def tag_search(self, ctx, *, query: str):
        """Searches for a tag."""
        if len(query) < 3:
            return await ctx.reply("Search query must be at least 3 characters long.")
            
        tags = self.bot.db.search_tags(ctx.guild.id, query)
        
        if not tags:
            return await ctx.reply(f"No tags found matching query: `{query}`")
        
        tag_list = "\n".join(f"`{tag['name']}`" for tag in tags[:15])
        
        embed = discord.Embed(
            title=f"Tag Search: {query}",
            description=tag_list,
            color=discord.Colour.dark_grey()
        )
        
        if len(tags) > 15:
            embed.set_footer(text=f"Showing 15/{len(tags)} results")
        
        await ctx.reply(embed=embed)

    @tag.command(name="list", description="List tags owned by a user")
    @app_commands.describe(member="The member whose tags to list (defaults to you)")
    async def tag_list(self, ctx, member: discord.Member = None):
        """Lists all the tags that belong to you or someone else."""
        target = member or ctx.author
        
        tags = self.bot.db.get_user_tags(ctx.guild.id, target.id)
        
        if not tags:
            return await ctx.reply(f"{target.name} has no tags.")
        
        tag_list = ", ".join(f"`{tag['name']}`" for tag in tags[:20])
        
        embed = discord.Embed(
            title=f"{target.name}'s Tags",
            description=tag_list,
            color=discord.Colour.dark_grey()
        )
        
        if len(tags) > 20:
            embed.set_footer(text=f"Showing 20/{len(tags)} tags")
        
        await ctx.reply(embed=embed)

    @tag.command(name="random", description="Display a random tag")
    async def tag_random(self, ctx):
        """Displays a random tag."""
        tag = self.bot.db.get_random_tag(ctx.guild.id)
        
        if not tag:
            return await ctx.reply("This server has no tags.")
        
        embed = discord.Embed(
            title=f"Random Tag: {tag['name']}",
            description=tag["content"],
            color=discord.Colour.dark_grey()
        )
        
        await ctx.reply(embed=embed)

    @tag.command(name="stats", description="Show tag statistics")
    @app_commands.describe(member="The member to get stats for (defaults to server stats)")
    async def tag_stats(self, ctx, member: discord.Member = None):
        """Gives tag statistics for a member or the server."""
        if member:
            # User stats
            stats = self.bot.db.get_user_tag_stats(ctx.guild.id, member.id)
            
            embed = discord.Embed(
                title=f"Tag Stats: {member.name}",
                color=discord.Colour.dark_grey()
            )
            
            embed.add_field(name="Total Tags", value=str(stats["total_tags"]), inline=True)
            embed.add_field(name="Total Uses", value=str(stats["total_uses"]), inline=True)
            
            if stats["top_tags"]:
                top_tags_text = "\n".join(f"`{tag['name']}`: {tag['use_count']} uses" for tag in stats["top_tags"])
                embed.add_field(name="Top Tags", value=top_tags_text, inline=False)
        else:
            # Server stats
            stats = self.bot.db.get_guild_tag_stats(ctx.guild.id)
            
            embed = discord.Embed(
                title=f"Tag Stats: {ctx.guild.name}",
                color=discord.Colour.dark_grey()
            )
            
            embed.add_field(name="Total Tags", value=str(stats["total_tags"]), inline=True)
            embed.add_field(name="Total Aliases", value=str(stats["total_aliases"]), inline=True)
            
            if stats["top_tags"]:
                top_tags_text = "\n".join(
                    f"`{tag['name']}`: {tag['use_count']} uses (by <@{tag['owner_id']}>)" 
                    for tag in stats["top_tags"]
                )
                embed.add_field(name="Top Tags", value=top_tags_text, inline=False)
            
            if stats["top_creators"]:
                top_creators_text = "\n".join(
                    f"<@{creator['owner_id']}>: {creator['tag_count']} tags" 
                    for creator in stats["top_creators"]
                )
                embed.add_field(name="Top Creators", value=top_creators_text, inline=False)
        
        await ctx.reply(embed=embed)

    @tag.command(name="transfer", description="Transfer ownership of a tag")
    @app_commands.describe(
        member="The member to transfer the tag to",
        name="The name of the tag to transfer"
    )
    async def tag_transfer(self, ctx, member: discord.Member, *, name: str):
        """Transfers a tag to another member."""
        if member.id == ctx.author.id:
            return await ctx.reply("You already own this tag.")
            
        if member.bot:
            return await ctx.reply("You cannot transfer tags to bots.")
        
        success = self.bot.db.transfer_tag(ctx.guild.id, name, ctx.author.id, member.id)
        
        if success:
            await ctx.reply(f"Tag `{name}` transferred to {member.mention}.")
        else:
            tag = self.bot.db.get_tag(ctx.guild.id, name)
            if not tag:
                await ctx.reply(f"Tag `{name}` does not exist.")
            else:
                await ctx.reply(f"You don't own the tag `{name}`.")

    @tag.command(name="claim", description="Claim a tag whose owner left the server")
    @app_commands.describe(name="The name of the tag to claim")
    async def tag_claim(self, ctx, *, name: str):
        """Claims an unclaimed tag."""
        tag = self.bot.db.get_tag(ctx.guild.id, name)
        
        if not tag:
            return await ctx.reply(f"Tag `{name}` not found.")
            
        owner = ctx.guild.get_member(tag["owner_id"])
        
        if owner:
            return await ctx.reply(f"Tag `{name}` is owned by {owner.mention} who is still in the server.")
        
        success = self.bot.db.claim_tag(ctx.guild.id, name, ctx.author.id, tag["owner_id"])
        
        if success:
            await ctx.reply(f"You are now the owner of the tag `{name}`.")
        else:
            await ctx.reply(f"Failed to claim tag `{name}`.")

async def setup(bot):
    await bot.add_cog(Tags(bot))