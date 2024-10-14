from discord import app_commands
import discord
import typing
from difflib import SequenceMatcher
import re

def create_autocomplete_from_list(
    options: list[str]
) -> typing.Callable[[discord.Interaction, str], typing.Coroutine[typing.Any, typing.Any, list[app_commands.Choice[str]]]]:

    async def autocomplete_function(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=option, value=option)
            for option in options
            if current.lower() in option.lower()
        ]
    return autocomplete_function


def create_autocomplete_from_dict(
    options: dict[str, typing.Any]
) -> typing.Callable[[discord.Interaction, str], typing.Coroutine[typing.Any, typing.Any, list[app_commands.Choice[str]]]]:

    async def autocomplete_function(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=key, value=value)
            for key, value in options.items()
            if current.lower() in key.lower()
        ]
    return autocomplete_function


def create_autocomplete_from_dict_keys(
    options: dict[str, typing.Any]
) -> typing.Callable[[discord.Interaction, str], typing.Coroutine[typing.Any, typing.Any, list[app_commands.Choice[str]]]]:

    async def autocomplete_function(
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=key, value=key)
            for key in options.keys()
            if current.lower() in key.lower()
        ]
    return autocomplete_function


async def find_member(
    guild: discord.Guild,
    query: str
) -> typing.Optional[discord.Member]:

    def calculate_similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    best_match: typing.Optional[discord.Member] = None
    best_score: float = 0

    for member in guild.members:
        if query in str(member.id):
            return member

        username_score = calculate_similarity(query, member.name)
        if username_score > best_score:
            best_match = member
            best_score = username_score

        if member.display_name != member.name:
            display_name_score = calculate_similarity(query, member.display_name)
            if display_name_score > best_score:
                best_match = member
                best_score = display_name_score

    return best_match

async def find_role(
    guild: discord.Guild, 
    query: str
) -> typing.Optional[discord.Role]:

    def calculate_similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    best_match: typing.Optional[discord.Role] = None
    best_score: float = 0

    for role in guild.roles:
        if query in str(role.id):
            return role

        role_name_score = calculate_similarity(query, role.name)
        if role_name_score > best_score:
            best_match = role
            best_score = role_name_score

    return best_match

def has_higher_role(
    user: discord.Member, 
    target: discord.Member
) -> bool:
    return user.top_role > target.top_role

def parse_time_string(
    time_str: str
) -> int:
    total_seconds = 0
    pattern = re.compile(r'(?:(\d+)\s*(hr|hrs|h|hour|hours|mins|min|m|minutes|seconds|sec|s|second|secs)?\s*)')
    matches = pattern.findall(time_str)

    for value, unit in matches:
        value = int(value)
        if unit in ['hr', 'hrs', 'h', 'hour', 'hours']:
            total_seconds += value * 3600
        elif unit in ['min', 'mins', 'm', 'minutes']:
            total_seconds += value * 60
        elif unit in ['sec', 's', 'seconds', 'secs']:
            total_seconds += value

    return total_seconds

def format_seconds(
    total_seconds: int
) -> str:
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m" if minutes % 60 else f"{hours}h"
    
    days = hours // 24
    
    return f"{days}d {hours % 24}h" if hours % 24 else f"{days}d"
