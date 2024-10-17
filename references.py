import discord 
from discord.ext import commands
import datetime
import asyncio


bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


# CONVERTERS
class DurationConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> datetime.timedelta:
        multipliers = {
            's': 1,  # seconds
            'm': 60,  # minutes
            'h': 3600,  # hours
            'd': 86400,  # days
            'w': 604800  # weeks
        }

        try:
            amount = int(argument[:-1])
            unit = argument[-1]
            seconds = amount * multipliers[unit]
            delta = datetime.timedelta(seconds=seconds)
            return delta
        except (ValueError, KeyError):
            raise commands.BadArgument("Invalid duration provided.")
        
# PARAMETER METADATA
@bot.command()
async def timeout(ctx: commands.Context, member: discord.Member, duration: datetime.timedelta = commands.parameter(converter=DurationConverter)):
    await member.timeout(duration)
    await ctx.send(f"Timed out {member.mention} for {duration}")



# GLOBAL CHECKS 
@bot.check
def check(ctx: commands.Context):
    ...

# When an error inside check happens, the error is propagated to the error handlers.
# If you don't raise an exception but return false-like value, then it will get wrapped up into a CheckFailure exception.
class CustomException(commands.CommandError): ...

async def check(ctx: commands.Context):
    if "1" in ctx.message.content:
        raise CustomException()
    if "2" in ctx.message.content:
        return False
    return True

@commands.check(check)
@bot.command()
async def foo(ctx: commands.Context):
    await ctx.send("Success!")

@foo.error
async def handler(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, CustomException):
        await ctx.send("CustomException was raised inside check!")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("Check has failed!")
    else:
        await ctx.send(f"Got unexpected error: {error}")


"""
ALL THE PERMISSIONS 

add_reactions, administrator, attach_files, ban_members, change_nickname, 
connect, create_instant_invite, create_private_threads, create_public_threads, 
deafen_members, embed_links, external_emojis, external_stickers, kick_members, 
manage_channels, manage_emojis, manage_emojis_and_stickers, manage_events, 
manage_guild, manage_messages, manage_nicknames, manage_permissions, manage_roles,
manage_threads, manage_webhooks, mention_everyone, moderate_members, move_members,
mute_members, priority_speaker, read_message_history, read_messages, request_to_speak,
send_messages, send_messages_in_threads, send_tts_messages, speak, stream, 
use_application_commands, use_embedded_activities, use_external_emojis, 
use_external_stickers, use_voice_activation, view_audit_log, view_channel,
view_guild_insights
"""

# HANDLED BY DISCORD 
@bot.tree.command()
@discord.app_commands.guild_only()
async def foo(interaction: discord.Interaction):
    await interaction.response.send_message(f"Success!")


# BEFORE INVOKE HOOK
async def func(ctx: commands.Context):
    await ctx.send("hook")


@bot.hybrid_command()
@commands.before_invoke(func)
async def foo(ctx: commands.Context):
    await ctx.send("command")
    
    
# AFTER INVOKE HOOK
async def func(ctx: commands.Context):
    await ctx.send("hook")


@bot.hybrid_command()
@commands.after_invoke(func)
async def foo(ctx: commands.Context):
    await ctx.send("command")


#COOLDOWN (throws CommandOnCooldown Exception)
@bot.hybrid_command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def foo(ctx: commands.Context):
    await ctx.send("Success!")
    
#-      -     -       -       -       -        -       -       -       -      -

def cooldown(ctx: commands.Context):
    """A cooldown for 10 seconds for everyone except listed users"""
    if ctx.author.id in (656919778572632094, 703327554936766554):
        return
    return commands.Cooldown(1, 10)


@bot.hybrid_command()
@commands.dynamic_cooldown(cooldown, commands.BucketType.user)
async def foo(ctx: commands.Context):
    await ctx.send("Success!")
    

# MaxConcurrency 
@bot.hybrid_command()
@commands.max_concurrency(1, commands.BucketType.member, wait=False)
async def foo(ctx: commands.Context):
    await asyncio.sleep(1)
    await ctx.send("Success!")
    
    
# A CUSTOM CHECK
banwords = {"rabbit", "horse"}


async def safe_content(ctx):
    return not (set(ctx.message.content.lower().split()) & banwords)


@bot.command()
@commands.check(safe_content)
async def check_content(ctx):
    await ctx.send("Content is clean!")



#### ANSIIIIIIIIIIIIIIIIIIIIIIII

import enum

class Style(enum.IntEnum):
    def __str__(self) -> str:
        return f"{self.value}"


class Colors(Style):
    GRAY = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37


class BackgroundColors(Style):
    FIREFLY_DARK_BLUE = 40
    ORANGE = 41
    MARBLE_BLUE = 42
    GREYISH_TURQUOISE = 43
    GRAY = 44
    INDIGO = 45
    LIGHT_GRAY = 46
    WHITE = 47


class Styles(Style):
    NORMAL = 0
    BOLD = 1
    UNDERLINE = 4


class AnsiBuilder:
    def __init__(self, text: str = "", *styles: Style) -> None:
        self.styles = styles
        self.cursor = len(text)
        self.text = f"\033[{';'.join(map(str, styles))}m{text}\033[0m" if styles and text else text

    def __add__(self, other: str) -> "AnsiBuilder":
        self.text += other
        self.cursor += len(other)
        return self

    def write(self, cursor: int, text: str) -> "AnsiBuilder":
        if cursor > self.cursor or cursor > len(self.text):
            raise ValueError("Cursor cannot be greater than the length of the text")
        if cursor < 0:
            raise ValueError("Cursor cannot be less than 0")
        self.text = self.text[:cursor] + text + self.text[cursor:]
        self.cursor += len(text)
        return self

    def __str__(self) -> str:
        return self.text

    @classmethod
    def to_ansi(cls, text: str, *styles: Style) -> str:
        return str(cls(text, *styles))

    @property
    def block(self) -> str:
        return f"```ansi\n{self.text}```"

        
        