from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
import math
from bot import Morgana

class PaginatedHelpView(discord.ui.View):
    def __init__(self, embeds: List[discord.Embed]):
        super().__init__(timeout=180.0)
        self.embeds = embeds
        self.current_page = 0
        
        # Update button states
        self.update_buttons()
        
    def update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.last_page.disabled = self.current_page == len(self.embeds) - 1
        
    @discord.ui.button(label="<<", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        
    @discord.ui.button(label="<", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        
    @discord.ui.button(label=">", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        
    @discord.ui.button(label=">>", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.embeds) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class Help(commands.Cog):
    """Custom help command for the bot."""

    def __init__(self, bot: Morgana):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = None

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    async def command_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = []
        for command in self.bot.walk_commands():
            if current.lower() in command.qualified_name.lower():
                choices.append(app_commands.Choice(name=command.qualified_name, value=command.qualified_name))
        return choices[:25]
    
    def create_command_pages(self, ctx, commands_list, title, items_per_page=10):
        filtered_commands = [cmd for cmd in commands_list if not isinstance(cmd, app_commands.ContextMenu)]
        
        pages = []
        total_pages = math.ceil(len(filtered_commands) / items_per_page)
        
        if not filtered_commands:
            embed = discord.Embed(
                title=title,
                description="No commands available.",
                color=discord.Color.dark_grey()
            )
            return [embed]
        
        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            current_commands = filtered_commands[start_idx:end_idx]
            
            embed = discord.Embed(
                title=f"{title} (Page {page + 1}/{total_pages})", 
                color=discord.Color.dark_grey()
            )
            
            prefix = self.bot.get_prefix(ctx.message)
            if isinstance(prefix, list):
                prefix = prefix[0]
            
            if prefix is None:
                prefix = "?"
                
            # Group regular commands together
            regular_commands = [cmd for cmd in current_commands if not isinstance(cmd, commands.Group)]
            if regular_commands:
                value = ""
                for cmd in regular_commands:
                    prefix = "?" if isinstance(cmd, commands.Command) else "/"
                    signature = f"{cmd.signature}".strip() if hasattr(cmd, 'signature') and cmd.signature else ""
                    value += f"**{prefix}{cmd.name}** {signature}\n{cmd.description or 'No description available.'}\n\n"
                embed.add_field(name="Commands", value=value, inline=False)
            
            # Handle command groups separately
            for cmd in current_commands:
                if isinstance(cmd, commands.Group):
                    value = f"{cmd.description or 'No description'}\n"
                    for subcmd in cmd.commands:
                        prefix = "?" if isinstance(subcmd, commands.Command) else "/"
                        value += f"• `{prefix}{cmd.name} {subcmd.name}` - {subcmd.description or 'No description'}\n"
                    embed.add_field(name=f"/{cmd.name}", value=value, inline=False)
            
            pages.append(embed)
        return pages

    def get_command_help(self, command) -> discord.Embed:
        embed = discord.Embed(
            title=f"Command Help: {command.qualified_name}",
            color=discord.Color.dark_grey()
        )
        
        # Command description
        embed.description = command.help or command.description or "No description available."
        
        # Command syntax
        prefix = "?" if isinstance(command, commands.Command) else "/"
        if command.signature:
            usage = f"{prefix}{command.qualified_name} {command.signature}"
        else:
            usage = f"{prefix}{command.qualified_name}"
        embed.add_field(name="Usage", value=f"```\n{usage}\n```", inline=False)
        
        # Parameters detail
        if hasattr(command, 'clean_params') and command.clean_params:
            params_text = ""
            for name, param in command.clean_params.items():
                param_type = param.annotation.__name__ if param.annotation != param.empty else "Any"
                required = "Required" if param.default == param.empty else "Optional"
                default = f" (Default: {param.default})" if param.default != param.empty else ""
                params_text += f"• **{name}** ({param_type}) - {required}{default}\n"
            if params_text:
                embed.add_field(name="Parameters", value=params_text, inline=False)
        
        # Examples
        if command.help:
            example_section = False
            examples = []
            for line in command.help.split('\n'):
                if line.strip().startswith('Examples:'):
                    example_section = True
                    continue
                if example_section and line.strip():
                    examples.append(line.strip())
            if examples:
                embed.add_field(name="Examples", value="\n".join(examples), inline=False)
        
        # Aliases
        if hasattr(command, 'aliases') and command.aliases:
            aliases = [f"?{alias}" for alias in command.aliases]
            embed.add_field(name="Aliases", value=", ".join(aliases), inline=False)
        
        return embed

    @commands.hybrid_command(
        name="help",
        description="Get help on commands or list all plugins",
    )
    async def help_command(self, ctx: commands.Context, *, command: Optional[str] = None) -> None:
        try:
            if command:
                if ' ' in command:
                    group_name, cmd_name = command.split(' ', 1)
                    group = self.bot.get_command(group_name)
                    if group and isinstance(group, commands.Group):
                        cmd = group.get_command(cmd_name)
                        if cmd:
                            embed = self.get_command_help(cmd)
                            await ctx.reply(embed=embed)
                            return
                else:
                    cmd = self.bot.get_command(command)
                    if cmd:
                        if isinstance(cmd, commands.Group):
                            embed = discord.Embed(
                                title=f"Command Group: {cmd.qualified_name}",
                                description=cmd.help or cmd.description or "No description available.",
                                color=discord.Color.dark_grey()
                            )
                            
                            prefix = "?" if isinstance(cmd, commands.Command) else "/"
                            usage = f"{prefix}{cmd.qualified_name} <subcommand>"
                            embed.add_field(name="Usage", value=f"```\n{usage}\n```", inline=False)
                            
                            subcommands = ""
                            for subcmd in cmd.commands:
                                subcommands += f"• **{subcmd.name}** - {subcmd.description or 'No description'}\n"
                            
                            if subcommands:
                                embed.add_field(name="Subcommands", value=subcommands, inline=False)
                                embed.add_field(
                                    name="Detailed Help",
                                    value=f"Use `?help {cmd.qualified_name} <subcommand>` for more details on a subcommand.",
                                    inline=False
                                )
                            
                            await ctx.reply(embed=embed)
                            return
                        else:
                            embed = self.get_command_help(cmd)
                            await ctx.reply(embed=embed)
                            return
                
                await ctx.reply(f"No command called '{command}' found.")
                return

            # If no command specified, show the plugin selection menu
            embed = discord.Embed(
                title="Bot Help",
                description=self.bot.description or "Select a plugin from the dropdown menu below.",
                color=discord.Color.dark_grey()
            )
            
            # Get all cogs and create select options
            options = []
            for cog_name, cog in sorted(self.bot.cogs.items()):  # Sort cogs alphabetically
                if hasattr(cog, 'qualified_name') and not cog_name.startswith('_'):  # Skip system cogs
                    description = cog.__doc__ or f"Commands in {cog_name}"
                    options.append(discord.SelectOption(
                        label=cog_name,
                        description=description[:100]  # Discord limit
                    ))
            
            if not options:
                await ctx.reply("No plugins available.")
                return

            # Limit to 25 options
            options = options[:25]

            select_menu = discord.ui.Select(
                placeholder="Choose a plugin",
                options=options
            )

            async def select_callback(interaction: discord.Interaction):
                selected_cog = self.bot.get_cog(select_menu.values[0])
                if selected_cog:
                    commands_list = selected_cog.get_commands()
                    pages = self.create_command_pages(
                        ctx,
                        commands_list,
                        f"{selected_cog.qualified_name} Plugin"
                    )
                    paginated_view = PaginatedHelpView(pages)
                    paginated_view.add_item(select_menu)
                    await interaction.response.edit_message(embed=pages[0], view=paginated_view)

            select_menu.callback = select_callback
            view = discord.ui.View()
            view.add_item(select_menu)
            
            await ctx.reply(embed=embed, view=view)

        except Exception as e:
            await ctx.reply(f"An error occurred: {str(e)}")
            self.bot.logger.error(f"Error in help command: {e}", exc_info=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
