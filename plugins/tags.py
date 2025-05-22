import discord
from discord.ext import commands
from discord import app_commands
from typing import Union, Optional, List, Dict, Any
from datetime import datetime
from bot import Morgana
from utils import PaginationView



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

        sub_cmds = [command.name for command in self.tag.commands]
        sub_cmd_alias = [alias for command in self.tag.commands for alias in (command.aliases or [])]
        all_sub_and_alias = sub_cmds + sub_cmd_alias
    
        if name in all_sub_and_alias:
            return await ctx.reply(f"Can't create tag `{name}`, it's a subcommand of tag.")
        
        can_bypass = ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator
        
        # Updated to use the new check_automod_violation that returns [bool, message]
        violation_check = await self.check_automod_violation(ctx.guild.id, content)
        has_banned_words = violation_check[0]
        violation_message = violation_check[1]
        
        if has_banned_words and not can_bypass:
            return await ctx.reply(f"Tag creation canceled. {violation_message}")
        
        success = self.bot.db.create_tag(ctx.guild.id, name, content, ctx.author.id)
        
        
        if success:
            tag_id = self.bot.db.get_tag_info(ctx.guild.id, name)["tag_id"]
            
            if has_banned_words and can_bypass:
                await ctx.reply(f"Tag `{name}` created successfully with the ID: `{tag_id}`.\n> Note: {violation_message}")
            else:
                await ctx.reply(f"Tag `{name}` created successfully with the ID: `{tag_id}`.")
        else:
            await ctx.reply(f"A tag or tag alias with the name `{name.lower()}` already exists.")


    
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
        
        # Check if user can bypass automod
        can_bypass = ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator
        
        # Updated to use the new check_automod_violation that returns [bool, message]
        violation_check = await self.check_automod_violation(ctx.guild.id, new_name)
        has_banned_words = violation_check[0]
        violation_message = violation_check[1]
        
        if has_banned_words and not can_bypass:
            return await ctx.reply(f"Your tag alias contains content that violates this server's automod rules. Alias creation canceled. {violation_message}")
        
        # Create the alias
        success = self.bot.db.create_tag_alias(ctx.guild.id, new_name, old_name)
        if success:
            if has_banned_words and can_bypass:
                await ctx.reply(f"Created alias `{new_name}` pointing to `{old_name}`, but be aware it contains content that would normally trigger automod filters. {violation_message}")
            else:
                await ctx.reply(f"Created alias `{new_name}` pointing to `{old_name}`.")
        else:
            await ctx.reply(f"An alias or tag with the name `{new_name}` already exists.")

    # Add a helper method to check for automod violations
    async def check_automod_violation(self, guild_id, content):
        """
        Checks if the content would violate the server's automod rules.
        
        Returns True if violations are found, False otherwise.
        """
        guild = self.bot.get_guild(guild_id)
        
        try:
            rules: list[discord.AutoModRule] = await guild.fetch_automod_rules()
            
            found_words = []
            for rule in rules:
                if hasattr(rule.trigger, 'keyword_filter'):
                    censored: List[str] = rule.trigger.keyword_filter
                    for word in censored:
                        if word.lower() in content.lower():
                            found_words.append(word)
            
            if found_words:
                censored_display = []
                for word in found_words[:3]:
                    if len(word) <= 2:
                        masked = word
                    else:
                        masked = f"{word[0]}{'*' * (len(word)-2)}{word[-1]}"
                    censored_display.append(masked)
                
                if len(found_words) > 3:
                    censored_display.append("etc...")
                
                return [True, f"Your content has {len(found_words)} censored words, like {', '.join(censored_display)}"]
            
            return [False, ""]
        except Exception as e:
            # Log the error but allow the tag to be created
            print(f"Error in automod check: {e}")
            return [False, ""]

    @tag.command(name="all", description="List all tags in the server")
    @app_commands.describe(page="The page number to view")
    async def tag_all(self, ctx, page: int = 1):
        """Lists all server-specific tags for this server."""
        if page < 1:
            return await ctx.reply("Page number must be positive.")

        tags = self.bot.db.get_all_guild_tags(ctx.guild.id)
        stats = self.bot.db.get_guild_tag_stats(ctx.guild.id)
        
        if not tags and page == 1:
            return await ctx.reply("This server has no tags.")
        elif not tags:
            return await ctx.reply("No tags found on this page.")

        embeds = []
        for i in range(0, len(tags), 20):
            embed = discord.Embed(
                description="\n".join(f'[{tag["tag_id"]}] `{tag["name"]}`' for tag in tags[i:i+20])
            )
            embeds.append(embed)
            
        view = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=view)
        
        
    @tag.command(name="leaderboard", aliases=["lb", "top"], description="Show the tag leaderboard")
    async def tag_leaderboard(self, ctx):
        """Shows the tag leaderboard for the server."""
        stats = self.bot.db.get_guild_tag_stats(ctx.guild.id)
        
        if not stats["top_tags"]:
            return await ctx.reply("No tags have been used in this server.")
        
        embed = discord.Embed(
            title="Tags Leaderboard",
            color=discord.Colour.dark_grey()
        )
        
        leaderboard_text = "\n".join(
            f"""{i}. `{tag['name']}`: {tag['use_count']} uses (by {f"<@{tag['owner_id']}>" if tag['owner_id'] is not None else 'an unknown user'})""" 
            for i, tag in enumerate(stats["top_tags"], 1)
        )
        
        embed.description = leaderboard_text
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

    @tag.command(name="remove", aliases=["delete"], description="Remove a tag you own")
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
        
        embed.description = "**Owner:** " + (f"<@{tag['owner_id']}>" if owner else f"Left the server (tag claimable)") + "\n"
        embed.description +="**Total Usage:** " + str(tag["use_count"]) + "\n"
        embed.description +="**Created At:** " + f"<t:{int(created_at.timestamp())}:R>" + "\n"
        embed.description +="**Tag ID:** " + str(tag["tag_id"]) + "\n"
        
        if tag["aliases"] and len(tag["aliases"]) > 0:
            embed.description += "\n**Aliases:** " + ", ".join(f"`{alias}`" for alias in tag["aliases"])
        
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
        
        tags = ", ".join(f"`{tag['name']}`" for tag in tags)
        embed = discord.Embed(
            description=tags,
            color=discord.Colour.dark_grey()
        )
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
