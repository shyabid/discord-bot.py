from __future__ import annotations
from collections import Counter
import discord
from discord.ext import commands
import datetime
from typing import Optional
import data

class Meta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emoji = data.emoji

    @commands.hybrid_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(embed=discord.Embed(description=f"Pong! Latency: {latency}ms", color=discord.Color.dark_grey()))

    @commands.hybrid_command(
        name="serverinfo", 
        aliases=['guildinfo'], 
        description="Shows info about the current server or a specified server"
    )
    @commands.guild_only()
    async def serverinfo(
        self, 
        ctx: commands.Context
    ) -> None:
        
        guild = ctx.guild
        roles = [role.name.replace('@', '@\u200b') for role in guild.roles if not role.is_bot_managed()]

        if not guild.chunked:
            async with ctx.typing():
                await guild.chunk(cache=True)

        everyone = guild.default_role
        everyone_perms = everyone.permissions.value

        secret = Counter()
        totals = Counter()

        for channel in guild.channels:
            allow, deny = channel.overwrites_for(everyone).pair()
            perms = discord.Permissions((everyone_perms & ~deny.value) | allow.value)
            channel_type = type(channel)
            totals[channel_type] += 1
            if not perms.read_messages:
                secret[channel_type] += 1
            elif isinstance(channel, discord.VoiceChannel) and (not perms.connect or not perms.speak):
                secret[channel_type] += 1

        e = discord.Embed(color=discord.Color.dark_grey())
        e.title = guild.name
        e.description = f'**ID**: {guild.id}\n**Owner**: {guild.owner.mention if guild.owner else "Unknown"}'
        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        channel_info = []
        key_to_emoji = {
            discord.TextChannel: self.emoji['text_channel'],
            discord.VoiceChannel: self.emoji['voice_channel'],
        }
        for key, total in totals.items():
            secrets = secret[key]
            try:
                emoji_icon = key_to_emoji[key]
            except KeyError:
                continue

            if secrets:
                channel_info.append(f'{emoji_icon} {total} ({secrets} locked)')
            else:
                channel_info.append(f'{emoji_icon} {total}')

        info = []
        features = set(guild.features)
        all_features = {
            'PARTNERED': 'Partnered',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Server Discovery',
            'COMMUNITY': 'Community Server',
            'FEATURABLE': 'Featured',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'INVITE_SPLASH': 'Invite Splash',
            'VIP_REGIONS': 'VIP Voice Servers',
            'VANITY_URL': 'Vanity Invite',
            'COMMERCE': 'Commerce',
            'LURKABLE': 'Lurkable',
            'NEWS': 'News Channels',
            'ANIMATED_ICON': 'Animated Icon',
            'BANNER': 'Banner',
        }

        for feature, label in all_features.items():
            if feature in features:
                info.append(f'{self.emoji["green_tick"]} {label}')

        if info:
            e.add_field(name='Features', value='\n'.join(info))

        e.add_field(name='Channels', value='\n'.join(channel_info))

        if guild.premium_tier != 0:
            boosts = f'{self.emoji["booster"]} Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts'
            last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
            if last_boost.premium_since is not None:
                boosts = f'{boosts}\nLast Boost: {last_boost.mention} ({discord.utils.format_dt(last_boost.premium_since, style="R")})'
            e.add_field(name='Boosts', value=boosts, inline=False)

        bots = sum(m.bot for m in guild.members)
        fmt = f'Total: {guild.member_count} ({bots} {"bot" if bots == 1 else "bots"})'

        e.add_field(name='Members', value=fmt, inline=False)
        
        top_roles = sorted([role for role in guild.roles if not role.is_bot_managed()], key=lambda r: r.position, reverse=True)[:15]
        e.add_field(name='Top Roles', value=', '.join(role.mention for role in top_roles) if top_roles else 'No roles', inline=False)
        e.add_field(name='Total Roles', value=f'{len(roles)} roles')

        emoji_stats = Counter()
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_stats['animated'] += 1
                emoji_stats['animated_disabled'] += not emoji.available
            else:
                emoji_stats['regular'] += 1
                emoji_stats['disabled'] += not emoji.available

        fmt = (
            f'Regular: {emoji_stats["regular"]}/{guild.emoji_limit}\n'
            f'Animated: {emoji_stats["animated"]}/{guild.emoji_limit}\n'
        )
        if emoji_stats['disabled'] or emoji_stats['animated_disabled']:
            fmt = f'{fmt}Disabled: {emoji_stats["disabled"]} regular, {emoji_stats["animated_disabled"]} animated\n'

        fmt = f'{fmt}Total Emoji: {len(guild.emojis)}/{guild.emoji_limit*2}'
        e.add_field(name='Emoji', value=fmt, inline=False)
        e.set_footer(text='Created').timestamp = guild.created_at
        await ctx.send(embed=e)



async def setup(bot):
    await bot.add_cog(Meta(bot))
