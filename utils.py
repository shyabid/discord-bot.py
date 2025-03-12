import discord 
import typing 
from discord import app_commands
import re
from difflib import SequenceMatcher

def format_seconds(
    total_seconds: int
) -> str:
    if total_seconds < 60: return f"{total_seconds}s"
    minutes = total_seconds // 60
    if minutes < 60: return f"{minutes}m"
    hours = minutes // 60
    if hours < 24: return f"{hours}h {minutes % 60}m" if minutes % 60 else f"{hours}h"
    days = hours // 24
    return f"{days}d {hours % 24}h" if hours % 24 else f"{days}d"

class PaginationView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], author: discord.Member, timeout: int = 300) -> None:
        super().__init__(timeout=timeout)
        self.embeds: list[discord.Embed] = embeds
        self.index: int = 0
        self.message: typing.Optional[discord.Message] = None
        self.author: discord.Member = author

        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Viewing page {i+1}/{len(embeds)}")

        # Disable buttons if only one page
        if len(embeds) == 1:
            self.prev_button.disabled = True
            self.goto_button.disabled = True
            self.next_button.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You cannot control this pagination!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    class PageSelectModal(discord.ui.Modal, title="Go to Page"):
        page = discord.ui.TextInput(label="Page Number", placeholder="Enter page number...")

        def __init__(self, max_pages: int):
            super().__init__()
            self.max_pages = max_pages

    @discord.ui.button(label="Go to", style=discord.ButtonStyle.gray)
    async def goto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = self.PageSelectModal(len(self.embeds))

        async def modal_callback(interaction: discord.Interaction):
            try:
                page = int(modal.page.value)
                if 1 <= page <= len(self.embeds):
                    self.index = page - 1
                    await interaction.response.edit_message(embed=self.embeds[self.index], view=self)
                else:
                    await interaction.response.send_message(
                        f"Please enter a number between 1 and {len(self.embeds)}",
                        ephemeral=True
                    )
            except ValueError:
                await interaction.response.send_message("Please enter a valid number", ephemeral=True)

        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    async def on_timeout(self) -> None:
        for child in self.children: child.disabled = True
        if self.message: await self.message.edit(view=self)


class WaifuImagePagination(discord.ui.View):
    def __init__(self, waifu_card_data: list, author: discord.Member) -> None:
        super().__init__(timeout=300)
        self.cards = waifu_card_data
        self.index = 0
        self.author = author
        self.message = None
        self.update_buttons()

    def update_buttons(self) -> None:
        self.previous_button.disabled = (self.index == 0)
        self.next_button.disabled = (self.index == len(self.cards) - 1)
        self.page_indicator.label = f"{self.index + 1}/{len(self.cards)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This button is not for you", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="<", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index -= 1
        self.update_buttons()
        card_data = self.cards[self.index]
            
        # Update message with new image
        file = discord.File(fp=card_data["image"], filename="card.png")
        await interaction.response.edit_message(attachments=[file], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label=">", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index += 1
        self.update_buttons()
        card_data = self.cards[self.index]
            
        # Update message with new image
        file = discord.File(fp=card_data["image"], filename="card.png")
        await interaction.response.edit_message(attachments=[file], view=self)


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

async def find_member(
    guild: discord.Guild,
    query: str
) -> typing.Optional[discord.Member]:

    best_match: typing.Optional[discord.Member] = None
    best_score: float = 0
    count: int = 0

    for member in guild.members:
        if query.isdigit() and str(member.id).startswith(query):
            return member

        username_score = SequenceMatcher(None, query.lower(), member.name.lower()).ratio()
        if username_score > best_score:
            best_match = member
            best_score = username_score

        if member.display_name != member.name:
            display_name_score = SequenceMatcher(None, query.lower(), member.display_name.lower()).ratio()
            if display_name_score > best_score:
                best_match = member
                best_score = display_name_score
        count += 1
        print(f"{count} {best_score} {best_match.name}")
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