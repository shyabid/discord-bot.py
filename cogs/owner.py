from discord.ext import commands
import discord
from utils import PaginationView


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 1076064221210628118
        
        
        
    @commands.command(name="servers", description="List all servers the bot is in")
    async def servers(self, ctx):
        """Lists all servers the bot is in (Owner only)"""
        if ctx.author.id != self.owner_id:
            await ctx.author.send("This command is only available to the bot owner.")
            return

        try:
            embeds = []
            servers_per_page = 10
            guild_list = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)

            for i in range(0, len(guild_list), servers_per_page):
                embed = discord.Embed(
                    title=f"Server List ({len(guild_list)} total)", 
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"Page {i//servers_per_page + 1}/{-(-len(guild_list)//servers_per_page)}")
                
                for guild in guild_list[i:i + servers_per_page]:
                    invite = "No invite found"
                    try:
                        # Only get invites if bot has permission
                        if guild.me.guild_permissions.manage_guild:
                            invites = await guild.invites()
                            if invites:
                                invite = invites[0].url
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                        
                    value = (
                        f"Members: {guild.member_count:,}\n"
                        f"Owner: {guild.owner} ({guild.owner_id})\n"
                        f"Created: {discord.utils.format_dt(guild.created_at, 'R')}\n"
                        f"Invite: {invite}"
                    )
                    
                    embed.add_field(
                        name=f"{guild.name} (ID: {guild.id})",
                        value=value,
                        inline=False
                    )
                
                embeds.append(embed)
            
            if not embeds:
                await ctx.author.send("No servers found.")
                return
                
            view = PaginationView(embeds, ctx.author)
            view.message = await ctx.author.send(embed=embeds[0], view=view)
            
        except Exception as e:
            await ctx.author.send(f"An error occurred: {str(e)}")

    
    @commands.command(hidden=True)
    async def global_sync(self, ctx):
        if ctx.author.id != self.owner_id:
            return
            
        await self.bot.tree.sync()
        await ctx.author.send("Successfully synced commands globally!")

    
    @commands.command(hidden=True)
    async def changepfp(self, ctx, url: str):
        if ctx.author.id != self.owner_id:
            return
            
        try:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.author.send('Failed to download the image.')
                avatar_bytes = await resp.read()
                
            await self.bot.user.edit(avatar=avatar_bytes)
            await ctx.author.send('Successfully changed the bot\'s profile picture!')
        except Exception as e:
            await ctx.author.send(f'An error occurred: {e}')

async def setup(bot):
    await bot.add_cog(Owner(bot))