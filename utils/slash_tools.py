from discord import app_commands
import discord 
import typing
from difflib import SequenceMatcher

def autocomplete(options: list):
    async def autocompletion(
        interaction: discord.Interaction,
        current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=option, value=option)
            for option in options
            if current.lower() in option.lower()
        ]
    return autocompletion

def autocomplete_DICT(options: dict):
    async def autocompletion(
        interaction: discord.Interaction,
        current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=key, value=value)
            for key, value in options.items()
            if current.lower() in key.lower()
        ]
    return autocompletion

def autocomplete_DICT2(options: dict):
    async def autocompletion(
        interaction: discord.Interaction,
        current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=key, value=key)
            for key, value in options.items()
            if current.lower() in key.lower()
        ]
    return autocompletion


async def find_str(interaction: discord.Interaction, q: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    def similarity(a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    best_match = None
    best_score = 0

    for member in guild.members:
        if q in str(member.id):
            best_match = member
            break

        username_score = similarity(q, member.name)
        if username_score > best_score:
            best_match = member
            best_score = username_score

        if member.display_name != member.name:
            display_name_score = similarity(q, member.display_name)
            if display_name_score > best_score:
                best_match = member
                best_score = display_name_score

    if best_match:
        return best_match
    else:
        return None
    
def has_higher_role(user: discord.Member, target: discord.Member):
    if user.top_role > target.top_role:
        return True
    else:
        return False

