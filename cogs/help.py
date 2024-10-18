from discord.ext import commands
import discord
from discord import app_commands
from typing import List, Optional

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
                embed = discord.Embed(title="Bot Help", description=self.bot.description or "No description available.", color=discord.Color.dark_grey())
                
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
                    embed.clear_fields()
                    if selected_option == "Ungrouped":
                        embed.title = "Ungrouped Commands"
                        for cmd in ungrouped_commands:
                            if isinstance(cmd, discord.app_commands.ContextMenu):
                                signature = f"{cmd.name} (Context Menu)"
                            else:
                                signature = f"/{cmd.name} {' '.join([f'<{param.name}>' if param.required else f'[{param.name}]' for param in cmd.parameters])}"
                            embed.add_field(name=signature, value=f"╰- {cmd.description or 'No description available.'}", inline=False)
                    else:
                        group = discord.utils.get(self.bot.tree.get_commands(), name=selected_option)
                        if group:
                            embed.title = f"{selected_option.capitalize()} Commands"
                            for cmd in group.commands:
                                if isinstance(cmd, discord.app_commands.ContextMenu):
                                    signature = f"{group.name} {cmd.name} (Context Menu)"
                                else:
                                    signature = f"/{group.name} {cmd.name} {' '.join([f'<{param.name}>' if param.required else f'[{param.name}]' for param in cmd.parameters])}"
                                embed.add_field(
                                    name=signature,
                                    value=f"- {cmd.description or 'No description available.'}",
                                    inline=False
                                )
                    
                    await interaction.response.edit_message(embed=embed)

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
