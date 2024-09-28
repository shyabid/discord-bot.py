
import discord
from typing import Optional
from discord import app_commands
import typing
import time
from utils.slash_tools import autocomplete
from discord.ext import commands
from utils.timeparsetool import strtoint
from db import db
from datetime import datetime

class ModGroup(app_commands.Group):
    
    @app_commands.command(
        name="ban",
        description="Bans a user from the server."
    )
    @app_commands.describe(
        member="Mention or paste the ID of the user you want to ban",
        reason="The reason for the ban",
        deletemsg="Number of days to delete the message history of the banned user"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = None,
        deletemsg: app_commands.Range[int, None, 14] = None
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
            return
        if member.id == interaction.guild.owner.id:
            await interaction.response.send_message("You cannot ban the server owner.", ephemeral=True)
            return
        
        if member.id == interaction.client.user.id:
            await interaction.response.send_message("If you want to ban me, kindly use another bot higher than myself or ban manually.", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You cannot ban a user with the same or higher role.", ephemeral=True)
            return

        try:
            
            await member.send(f"You have been banned from {interaction.guild.name}.\n**Reason:** `{reason}`")
            await member.ban(reason=reason, delete_message_days=deletemsg)

            ban_collection = self.db[str(interaction.guild.id)]['bans']
            ban_data = {
                'action_type': 'ban',
                'user_id': member.id,
                'moderator_id': interaction.user.id,
                'reason': reason,
                'timestamp': time.time(),
                'delete_message_days': deletemsg
            }

            result = await ban_collection.insert_one(ban_data)
            action_id = str(result.inserted_id)

            confirmation_embed = discord.Embed(
                description=f"{member.mention} has been banned. Reason: \n`{reason}`"
            )
            confirmation_embed.set_footer(text=f"actionId: {action_id}")

            await interaction.response.send_message(embed=confirmation_embed)

        except commands.BotMissingPermissions:
            await interaction.response.send_message("The bot does not have the necessary permissions.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred while banning the user: {str(e)}", ephemeral=True)


    @app_commands.command(
        name="kick",
        description="Kicks a user from the server."
    )
    @app_commands.describe(
        member="Mention or paste the ID of the user you want to kick",
        reason="The reason for the kick"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = None
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
            return
        if member.id == interaction.guild.owner.id:
            await interaction.response.send_message("You cannot kick the server owner.", ephemeral=True)
            return
        
        if member.id == interaction.client.user.id:
            await interaction.response.send_message("If you want to kick me, kindly use another bot higher than myself or kick manually.", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You cannot kick a user with the same or higher role.", ephemeral=True)
            return

        try:
            
            await member.send(f"You have been kicked from {interaction.guild.name}.\nReason:+**{reason}**")
            await member.kick(reason=reason)

            kick_collection = self.db[str(interaction.guild.id)]['kicks']
            kick_data = {
                'action_type': 'kick',
                'user_id': member.id,
                'moderator_id': interaction.user.id,
                'reason': reason,
                'timestamp': time.time()
            }

            result = await kick_collection.insert_one(kick_data)
            action_id = str(result.inserted_id)

            confirmation_embed = discord.Embed(
                description=f"{member.mention} has been kicked. Reason: \n`{reason}`"
            )
            confirmation_embed.set_footer(text=f"actionId: {action_id}")

            await interaction.response.send_message(embed=confirmation_embed)

        except commands.BotMissingPermissions:
            await interaction.response.send_message("The bot does not have the necessary permissions.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred while kicking the user: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="unban",
        description="Unbans a user from the server."
    )
    @app_commands.describe(
        user="Mention or paste the ID of the user you want to unban"
    )
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        if user.id == interaction.client.user.id:
            await interaction.response.send_message("I cannot unban myself.", ephemeral=True)
            return
        
        try:
            await interaction.guild.unban(user)
            
            unban_collection = self.db[str(interaction.guild.id)]['unbans']
            unban_data = {
                'action_type': 'unban',
                'user_id': user.id,
                'moderator_id': interaction.user.id,
                'timestamp': time.time()
            }

            result = await unban_collection.insert_one(unban_data)
            action_id = str(result.inserted_id)

            await interaction.response.send_message(f"User {user.mention} has been unbanned. Action ID: {action_id}")

        except discord.Forbidden:
            await interaction.response.send_message("I don't have the necessary permissions to unban this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error occurred while unbanning user: {str(e)}", ephemeral=True)

    @app_commands.command(
        name='timeout',
        description='Timeouts a user for a specified period of time.'
    )
    @app_commands.describe(
        member="Select a member to timeout",
        duration="Set the timeout duration in any format",
        reason="Provide a reason for the timeout"
    )
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "No reason provided"
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("You cannot timeout yourself.", ephemeral=True)
            return

        if member.id == interaction.guild.owner.id:
            await interaction.response.send_message("You cannot timeout the server owner.", ephemeral=True)
            return

        if member.id == interaction.client.user.id:
            await interaction.response.send_message("You cannot timeout the bot itself.", ephemeral=True)
            return
        
        if member.guild_permissions.administrator:
            await interaction.response.send_message("You cannot timeout a user with administrator permissions.", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You cannot timeout a user with the same or higher role.", ephemeral=True)
            return

        try:
            timeout_duration = strtoint(duration)
            if timeout_duration <= 0:
                await interaction.response.send_message("Please provide a valid timeout duration.", ephemeral=True)
                return
        except Exception as e:
            await interaction.response.send_message(f"Error parsing duration: {str(e)}", ephemeral=True)
            return

        try:
            await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=timeout_duration), reason=reason)

            timeout_collection = self.db[str(interaction.guild.id)]['timeouts']
            timeout_data = {
                'action_type': 'timeout',
                'user_id': member.id,
                'moderator_id': interaction.user.id,
                'duration': timeout_duration,
                'reason': reason,
                'timestamp': time.time()
            }

            result = await timeout_collection.insert_one(timeout_data)
            action_id = str(result.inserted_id)

            await interaction.response.send_message(f"User {member.mention} has been timed out for {timeout_duration} seconds. Action ID: {action_id}")

        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to timeout this member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to timeout the user: {str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)


    @app_commands.command(
        name="warn",
        description="Warns a user for a specified reason."
    )
    @app_commands.describe(
        member="Select a member to warn",
        reason="Provide a reason for the warning"
    )
    @commands.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("You cannot warn yourself.", ephemeral=True)
            return
        
        if member.id == interaction.guild.owner.id:
            await interaction.response.send_message("You cannot warn the server owner.", ephemeral=True)
            return
        
        if member.id == interaction.client.user.id:
            await interaction.response.send_message("You cannot warn the bot itself.", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You cannot kick a user with the same or higher role.", ephemeral=True)
            return
        
        