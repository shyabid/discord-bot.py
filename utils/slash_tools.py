from discord import app_commands
import discord 
import typing

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