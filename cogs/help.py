from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional
import math

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

    def __init__(self, bot: commands.Bot):
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
    def create_command_pages(self, commands_list, title, items_per_page=10):
        # Filter out context menu commands
        filtered_commands = [cmd for cmd in commands_list if not isinstance(cmd, discord.app_commands.ContextMenu)]
        
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
            
            for cmd in current_commands:
                # Ensure proper signature formatting for different command types
                if hasattr(cmd, 'signature'):
                    signature = f"/{cmd.name} {cmd.signature}".strip()
                else:
                    signature = f"/{cmd.name}"
                
                embed.add_field(
                    name=signature,
                    value=cmd.description or "No description available.", 
                    inline=False
                )
            
            pages.append(embed)
        
        return pages


    @commands.hybrid_command(
        name="help",
        description="Get help on a command or list all commands",
    )
    @app_commands.describe(command="The command to get help for")
    @app_commands.autocomplete(command=command_autocomplete)
    async def help_command(self, ctx: commands.Context, *, command: Optional[str] = None) -> None:
        """
        Get detailed help on a specific command or list all available commands.

        Usage:
        /help [command]
        ?help [command]

        Parameters:
        command (str, optional): The name of the command to get help for.

        Examples:
        /help
        /help fun
        ?help
        ?help role create
        """
        try:
            if command is None:
                embed = discord.Embed(
                    title="Bot Help", 
                    description=self.bot.description or "No description available.", 
                    color=discord.Color.dark_grey()
                )
                
                options = []
                for group in self.bot.tree.get_commands():
                    if isinstance(group, app_commands.Group):
                        options.append(discord.SelectOption(label=group.name, description=f"Commands in {group.name}"))
                
                ungrouped_commands = [cmd for cmd in self.bot.tree.get_commands() if not isinstance(cmd, app_commands.Group)]
                if ungrouped_commands:
                    options.append(discord.SelectOption(label="Ungrouped", description="Commands without a group"))

                select_menu = discord.ui.Select(placeholder="Choose a command group", options=options)

                async def select_callback(interaction: discord.Interaction):
                    selected_option = select_menu.values[0]
                    if selected_option == "Ungrouped":
                        pages = self.create_command_pages(ungrouped_commands, "Ungrouped Commands")
                        paginated_view = PaginatedHelpView(pages)
                        # Add the select menu to the paginated view
                        paginated_view.add_item(select_menu)
                        await interaction.response.edit_message(embed=pages[0], view=paginated_view)
                    else:
                        group = discord.utils.get(self.bot.tree.get_commands(), name=selected_option)
                        if group:
                            pages = self.create_command_pages(group.commands, f"{selected_option.capitalize()} Commands")
                            paginated_view = PaginatedHelpView(pages)
                            # Add the select menu to the paginated view
                            paginated_view.add_item(select_menu)
                            await interaction.response.edit_message(embed=pages[0], view=paginated_view)

                select_menu.callback = select_callback
                view = discord.ui.View()
                view.add_item(select_menu)
                
                await ctx.reply(embed=embed, view=view)
            else:
                cmd = self.bot.get_command(command)
                if cmd is None:
                    await ctx.reply(f"No command called '{command}' found.")
                    return

                embed = discord.Embed(
                    title=f"Help: {cmd.qualified_name}", 
                    description=cmd.help or "No description available.",    
                    color=discord.Color.dark_grey()
                )
                if isinstance(cmd, commands.Group):
                    for subcmd in cmd.commands:
                        if isinstance(subcmd, commands.Command):
                            signature = f"/{cmd.name} {subcmd.name} {subcmd.signature}"
                        else:
                            signature = f"/{cmd.name} {subcmd.name}"
                        embed.add_field(
                            name=signature,
                            value=f"- {subcmd.short_doc or 'No description available.'}",
                            inline=False
                        )

                if cmd.aliases:
                    embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=False)

                await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"An error occurred: {str(e)}")
            self.bot.logger.error(f"Error in help command: {e}", exc_info=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
