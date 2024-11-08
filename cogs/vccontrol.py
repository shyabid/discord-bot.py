from discord.ext import commands
import discord
from discord import app_commands
from typing import (
    Optional, 
    Dict, 
    Any, 
    Union,
    List,
    Tuple
)
from discord.ui import (
    Button,
    View, 
    Modal,
    TextInput,
    Select
)

EMOJIS: Dict[str, str] = {
    "edit": "✏️",
    "region": "🌍", 
    "access": "🔒",
    "kick": "👢",
    "public": "🌐",
    "private": "🔐", 
    "hidden": "👻",
    "transfer": "👑",
    "movetop": "⬆️",
    # Region emojis
    "automatic": "🌐",
    "brazil": "🇧🇷",
    "hongkong": "🇭🇰", 
    "india": "🇮🇳",
    "japan": "🇯🇵",
    "rotterdam": "🇳🇱",
    "russia": "🇷🇺",
    "singapore": "🇸🇬",
    "south-korea": "🇰🇷",
    "southafrica": "🇿🇦", 
    "sydney": "🇦🇺",
    "us-central": "🇺🇸",
    "us-east": "🇺🇸",
    "us-south": "🇺🇸",
    "us-west": "🇺🇸"
}

class VCModal(Modal, title="Edit Voice Channel"):
    vcname: TextInput = TextInput(
        label="Voice Channel Name",
        required=False
    )
    limit: TextInput = TextInput(
        label="User Limit (max 99)", 
        required=False
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ) -> None:
        tempvc_cog = interaction.client.get_cog('tempvc')
        if interaction.channel.id not in tempvc_cog.temp_channels:
            await interaction.response.send_message(
                "This channel is not recognized as a temporary voice channel.",
                ephemeral=True
            )
            return

        owner, _ = tempvc_cog.temp_channels[interaction.channel.id]
        if interaction.user.id != owner.id:
            await interaction.response.send_message(
                "Only the VC owner can edit!",
                ephemeral=True
            )
            return

        try:
            if self.vcname.value:
                await interaction.channel.edit(
                    name=self.vcname.value
                )
            
            if self.limit.value:
                limit: int = int(self.limit.value)
                if limit > 99:
                    limit = 99
                elif limit < 0:
                    limit = 0
                    
                await interaction.channel.edit(
                    user_limit=limit
                )

            message: discord.Message = (
                await interaction.channel.fetch_message(
                    interaction.message.id
                )
            )
            embed: discord.Embed = message.embeds[0]
            
            embed.set_field_at(
                0,
                name="Owner",
                value=f"{interaction.user.mention}",
                inline=True
            )
            
            await message.edit(embed=embed)
                
            await interaction.response.send_message(
                "Voice channel updated!",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                "Please enter a valid number for user limit",
                ephemeral=True
            )

class AccessControlView(View):
    def __init__(
        self,
        vc_owner: discord.Member,
        control_message_id: int
    ) -> None:
        super().__init__(timeout=None)
        self.vc_owner: discord.Member = vc_owner
        self.control_message_id: int = control_message_id

        self.allow_select: discord.ui.MentionableSelect = (
            discord.ui.MentionableSelect(
                placeholder="Select roles/users to allow access",
                min_values=1,
                max_values=25
            )
        )
        
        self.deny_select: discord.ui.MentionableSelect = (
            discord.ui.MentionableSelect(
                placeholder="Select roles/users to deny access",
                min_values=1,
                max_values=25
            )
        )
        
        async def allow_callback(
            interaction: discord.Interaction
        ) -> None:
            if interaction.user.id != self.vc_owner.id:
                await interaction.response.send_message(
                    "Only the VC owner can manage access!",
                    ephemeral=True
                )
                return

            overwrites: Dict[
                Union[discord.Role, discord.Member],
                discord.PermissionOverwrite
            ] = interaction.channel.overwrites
            
            for target in self.allow_select.values:
                overwrites[target] = discord.PermissionOverwrite(
                    connect=True,
                    view_channel=True
                )
                
            await interaction.channel.edit(
                overwrites=overwrites
            )

            message: discord.Message = (
                await interaction.channel.fetch_message(
                    self.control_message_id
                )
            )
            embed: discord.Embed = message.embeds[0]
            allowed_users: List[str] = []
            banned_users: List[str] = []
            
            for target, perms in interaction.channel.overwrites.items():
                if isinstance(target, (discord.Member, discord.Role)):
                    if perms.connect is True:
                        allowed_users.append(target.mention)
                    elif perms.connect is False:
                        banned_users.append(target.mention)
            
            access_info: str = (
                "**Allowed:** " + 
                (", ".join(allowed_users) if allowed_users else "Everyone") +
                "\n"
            )
            access_info += (
                "**Banned:** " +
                (", ".join(banned_users) if banned_users else "None")
            )
            
            embed.set_field_at(
                3,
                name="Access Control",
                value=access_info,
                inline=False
            )
            await message.edit(embed=embed)

            await interaction.response.send_message(
                "Access permissions updated!",
                ephemeral=True
            )

        async def deny_callback(
            interaction: discord.Interaction
        ) -> None:
            if interaction.user.id != self.vc_owner.id:
                await interaction.response.send_message(
                    "Only the VC owner can manage access!",
                    ephemeral=True
                )
                return

            overwrites: Dict[
                Union[discord.Role, discord.Member],
                discord.PermissionOverwrite
            ] = interaction.channel.overwrites
            
            for target in self.deny_select.values:
                overwrites[target] = discord.PermissionOverwrite(
                    connect=False,
                    view_channel=False
                )
                
            await interaction.channel.edit(
                overwrites=overwrites
            )

            message: discord.Message = (
                await interaction.channel.fetch_message(
                    self.control_message_id
                )
            )
            embed: discord.Embed = message.embeds[0]
            allowed_users: List[str] = []
            banned_users: List[str] = []
            
            for target, perms in interaction.channel.overwrites.items():
                if isinstance(target, (discord.Member, discord.Role)):
                    if perms.connect is True:
                        allowed_users.append(target.mention)
                    elif perms.connect is False:
                        banned_users.append(target.mention)
            
            access_info: str = (
                "**Allowed:** " +
                (", ".join(allowed_users) if allowed_users else "Everyone") +
                "\n"
            )
            access_info += (
                "**Banned:** " +
                (", ".join(banned_users) if banned_users else "None")
            )
            
            embed.set_field_at(
                3,
                name="Access Control", 
                value=access_info,
                inline=False
            )
            await message.edit(embed=embed)

            await interaction.response.send_message(
                "Access permissions updated!",
                ephemeral=True
            )

        self.allow_select.callback = allow_callback
        self.deny_select.callback = deny_callback
        
        self.add_item(self.allow_select)
        self.add_item(self.deny_select)

class VCControlView(View):
    def __init__(
        self,
        vc_owner: discord.Member,
        control_message_id: int
    ) -> None:
        super().__init__(timeout=None)
        self.vc_owner: discord.Member = vc_owner
        self.control_message_id: int = control_message_id
        self.visibility_state: str = "public"
        # Row 1 Buttons
        self.edit_button: Button = Button(label="Edit", emoji=EMOJIS["edit"], style=discord.ButtonStyle.grey, row=0)
        self.access_button: Button = Button(label="Access", emoji=EMOJIS["access"], style=discord.ButtonStyle.grey, row=0)
        self.transfer_button: Button = Button(label="Transfer", emoji=EMOJIS["transfer"], style=discord.ButtonStyle.grey, row=0)

        # Row 2 Buttons
        self.public_button: Button = Button(label="Public", emoji=EMOJIS["public"], style=discord.ButtonStyle.grey, row=1)
        self.private_button: Button = Button(label="Private", emoji=EMOJIS["private"], style=discord.ButtonStyle.grey, row=1)
        self.hidden_button: Button = Button(label="Hidden", emoji=EMOJIS["hidden"], style=discord.ButtonStyle.grey, row=1)

        # Row 3 Buttons
        self.region_button: Button = Button(label="Region", emoji=EMOJIS["region"], style=discord.ButtonStyle.grey, row=2)
        self.kick_button: Button = Button(label="Kick", emoji=EMOJIS["kick"], style=discord.ButtonStyle.grey, row=2)
        self.movetop_button: Button = Button(label="Move Top", emoji=EMOJIS["movetop"], style=discord.ButtonStyle.grey, row=2)

        # Add button callbacks
        self.edit_button.callback = self.edit_button_callback
        self.access_button.callback = self.access_button_callback
        self.transfer_button.callback = self.transfer_button_callback
        self.public_button.callback = self.public_button_callback
        self.private_button.callback = self.private_button_callback
        self.hidden_button.callback = self.hidden_button_callback
        self.region_button.callback = self.region_button_callback
        self.kick_button.callback = self.kick_button_callback
        self.movetop_button.callback = self.movetop_button_callback

        # Add all buttons to view
        self.add_item(self.edit_button)
        self.add_item(self.access_button)
        self.add_item(self.transfer_button)
        self.add_item(self.public_button)
        self.add_item(self.private_button)
        self.add_item(self.hidden_button)
        self.add_item(self.region_button)
        self.add_item(self.kick_button)
        self.add_item(self.movetop_button)

        # Disable public button by default
        self.public_button.disabled = True
        self.private_button.disabled = False
        self.hidden_button.disabled = False

    async def edit_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can edit!",
                ephemeral=True
            )
            return
            
        modal: VCModal = VCModal()
        await interaction.response.send_modal(modal)

    async def region_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can change region!",
                ephemeral=True
            )
            return
        regions: List[discord.SelectOption] = [
            discord.SelectOption(label=name, value=value, emoji=EMOJIS[value])
            for name, value in {
                "Automatic": "automatic",
                "Brazil": "brazil", 
                "Hong Kong": "hongkong",
                "India": "india",
                "Japan": "japan",
                "Rotterdam": "rotterdam",
                "Russia": "russia", 
                "Singapore": "singapore",
                "South Korea": "south-korea",
                "South Africa": "southafrica",
                "Sydney": "sydney",
                "US Central": "us-central",
                "US East": "us-east",
                "US South": "us-south",
                "US West": "us-west"
            }.items()
        ]
        select: Select = Select(
            placeholder="Select voice channel region",
            options=regions
        )
        
        async def region_callback(
            interaction: discord.Interaction
        ) -> None:
            region: str = select.values[0]
            await interaction.channel.edit(
                rtc_region=None if region == "automatic" else region
            )
            
            message: discord.Message = (
                await interaction.channel.fetch_message(
                    self.control_message_id
                )
            )
            embed: discord.Embed = message.embeds[0]
            region_name: str = (
                region.title() if region != "automatic" else "Automatic"
            )
            region_emoji: str = EMOJIS[region]
            
            embed.set_field_at(
                1,
                name="Region",
                value=f"{region_emoji} {region_name}",
                inline=True
            )
            await message.edit(embed=embed)
            
            await interaction.response.send_message(
                f"Voice channel region changed to {region}!",
                ephemeral=True
            )
            
        select.callback = region_callback
        await interaction.response.send_message(
            "Select region:",
            view=View().add_item(select),
            ephemeral=True
        )

    async def access_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can manage access!",
                ephemeral=True
            )
            return

        view: AccessControlView = AccessControlView(
            self.vc_owner,
            self.control_message_id
        )
        await interaction.response.send_message(
            "Manage access:",
            view=view,
            ephemeral=True
        )

    async def kick_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can kick members!",
                ephemeral=True
            )
            return

        options: List[discord.SelectOption] = []
        for member in interaction.user.voice.channel.members:
            if member.id != self.vc_owner.id:
                options.append(
                    discord.SelectOption(
                        label=member.name,
                        value=str(member.id)
                    )
                )
        
        if options:
            select: Select = Select(
                placeholder="Select member to kick",
                options=options
            )
            
            async def kick_callback(
                interaction: discord.Interaction
            ) -> None:
                member: Optional[discord.Member] = (
                    interaction.guild.get_member(
                        int(select.values[0])
                    )
                )
                if member:
                    await member.move_to(None)
                    await interaction.response.send_message(
                        f"Kicked {member.name} from the voice channel!",
                        ephemeral=True
                    )
            
            select.callback = kick_callback
            await interaction.response.send_message(
                "Select member to kick:",
                view=View().add_item(select),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No members to kick!",
                ephemeral=True
            )

    async def movetop_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        try:
            if interaction.user.id != self.vc_owner.id:
                await interaction.response.send_message(
                    "Only the VC owner can move the channel!",
                    ephemeral=True
                )
                return
            
            guild_collection: Any = (
                interaction.client.db[str(interaction.guild.id)]
            )
            tempvc_doc: Optional[Dict[str, Any]] = (
                guild_collection["config"].find_one({"_id": "tempvc"})
            )
            
            if tempvc_doc and "channel_id" in tempvc_doc:
                template_channel: Optional[discord.VoiceChannel] = (
                    interaction.guild.get_channel(tempvc_doc["channel_id"])
                )
                if template_channel:
                    await interaction.channel.edit(
                        position=template_channel.position + 1
                    )
                    await interaction.response.send_message(
                        "Channel moved to top!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Could not find template channel!",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "Template channel not set!",
                    ephemeral=True
                )
        except discord.NotFound:
            # Handle interaction timeout gracefully
            pass

    async def public_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can change visibility!",
                ephemeral=True
            )
            return

        overwrites: Dict[
            Union[discord.Role, discord.Member],
            discord.PermissionOverwrite
        ] = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                connect=True,
                view_channel=True
            )
        }
        await interaction.channel.edit(overwrites=overwrites)
        
        self.public_button.disabled = True
        self.private_button.disabled = False
        self.hidden_button.disabled = False
        self.visibility_state = "public"
        
        message: discord.Message = (
            await interaction.channel.fetch_message(
                self.control_message_id
            )
        )
        embed: discord.Embed = message.embeds[0]
        
        embed.set_field_at(
            2,
            name="State",
            value=f"{EMOJIS['public']} Public",
            inline=True
        )
        await message.edit(embed=embed, view=self)
        
        await interaction.response.send_message(
            "Channel is now public!",
            ephemeral=True
        )

    async def private_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can change visibility!",
                ephemeral=True
            )
            return

        overwrites: Dict[
            Union[discord.Role, discord.Member],
            discord.PermissionOverwrite
        ] = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                connect=False,
                view_channel=True
            )
        }
        await interaction.channel.edit(overwrites=overwrites)
        
        self.public_button.disabled = False
        self.private_button.disabled = True
        self.hidden_button.disabled = False
        self.visibility_state = "private"
        
        message: discord.Message = (
            await interaction.channel.fetch_message(
                self.control_message_id
            )
        )
        embed: discord.Embed = message.embeds[0]
        
        embed.set_field_at(
            2,
            name="State",
            value=f"{EMOJIS['private']} Private",
            inline=True
        )
        await message.edit(embed=embed, view=self)
        
        await interaction.response.send_message(
            "Channel is now private!",
            ephemeral=True
        )

    async def hidden_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        if interaction.user.id != self.vc_owner.id:
            await interaction.response.send_message(
                "Only the VC owner can change visibility!",
                ephemeral=True
            )
            return

        overwrites: Dict[
            Union[discord.Role, discord.Member],
            discord.PermissionOverwrite
        ] = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                connect=False,
                view_channel=False
            )
        }
        await interaction.channel.edit(overwrites=overwrites)
        
        self.public_button.disabled = False
        self.private_button.disabled = False
        self.hidden_button.disabled = True
        self.visibility_state = "hidden"
        
        message: discord.Message = (
            await interaction.channel.fetch_message(
                self.control_message_id
            )
        )
        embed: discord.Embed = message.embeds[0]
        
        embed.set_field_at(
            2,
            name="State",
            value=f"{EMOJIS['hidden']} Hidden",
            inline=True
        )
        await message.edit(embed=embed, view=self)
        
        await interaction.response.send_message(
            "Channel is now hidden!",
            ephemeral=True
        )

    async def transfer_button_callback(
        self,
        interaction: discord.Interaction
    ) -> None:
        try:
            if interaction.user.id != self.vc_owner.id:
                await interaction.response.send_message(
                    "Only the VC owner can transfer ownership!",
                    ephemeral=True
                )
                return

            options: List[discord.SelectOption] = []
            for member in interaction.user.voice.channel.members:
                if member.id != self.vc_owner.id:
                    options.append(
                        discord.SelectOption(
                            label=member.name,
                            value=str(member.id)
                        )
                    )
            
            if options:
                select: Select = Select(
                    placeholder="Select new owner",
                    options=options
                )
                
                async def transfer_callback(
                    interaction: discord.Interaction
                ) -> None:
                    new_owner: Optional[discord.Member] = (
                        interaction.guild.get_member(
                            int(select.values[0])
                        )
                    )
                    if new_owner:
                        # Update temp_channels dictionary
                        interaction.client.get_cog('tempvc').temp_channels[interaction.channel.id] = new_owner
                        self.vc_owner = new_owner
                        
                        message: discord.Message = (
                            await interaction.channel.fetch_message(
                                self.control_message_id
                            )
                        )
                        embed: discord.Embed = message.embeds[0]
                        
                        embed.set_field_at(
                            0,
                            name="Owner",
                            value=f"{new_owner.mention}",
                            inline=True
                        )
                        
                        # Create new control view with new owner
                        new_view = VCControlView(new_owner, self.control_message_id)
                        await message.edit(embed=embed, view=new_view)
                        
                        await interaction.response.send_message(
                            f"Voice channel ownership transferred to {new_owner.name}!",
                            ephemeral=True
                        )
                
                select.callback = transfer_callback
                await interaction.response.send_message(
                    "Select new owner:",
                    view=View().add_item(select),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "No members to transfer to!",
                    ephemeral=True
                )
        except discord.NotFound:
            pass

class SelectView(View):
    def __init__(self, select: discord.ui.Select) -> None:
        super().__init__(timeout=60)
        self.add_item(select)

class ClaimButton(discord.ui.Button):
    def __init__(self, vc_id: int, control_message_id: int):
        super().__init__(label="Claim Ownership", style=discord.ButtonStyle.green)
        self.vc_id = vc_id
        self.control_message_id = control_message_id
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel and interaction.user.voice.channel.id == self.vc_id:
            # Update temp_channels dictionary
            interaction.client.get_cog('tempvc').temp_channels[self.vc_id] = interaction.user
            
            # Update the control panel embed
            control_message = await interaction.channel.fetch_message(self.control_message_id)
            embed = control_message.embeds[0]
            embed.set_field_at(0, name="Owner", value=f"{interaction.user.mention}", inline=True)
            
            # Create new control view with new owner
            new_view = VCControlView(interaction.user, control_message.id)
            await control_message.edit(embed=embed, view=new_view)
            
            await interaction.response.send_message(f"{interaction.user.mention} is now the owner of this VC!", ephemeral=False)
            self.view.stop()
        else:
            await interaction.response.send_message("You must be in the voice channel to claim ownership!", ephemeral=True)

class ClaimView(discord.ui.View):
    def __init__(self, vc_id: int, control_message_id: int):
        super().__init__(timeout=None)
        self.add_item(ClaimButton(vc_id, control_message_id))

class Vccontrol(commands.Cog, name="tempvc"):
    """Voice Channel Control System"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.temp_channels: Dict[int, Tuple[discord.Member, int]] = {}
        self.bot.add_listener(self.on_voice_state_update)

    @commands.hybrid_group(
        name="tempvc",
        description="Temporary voice channel commands"
    )
    async def tempvc(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Invalid subcommand. Use `?help tempvc` for more info."
            )

    @tempvc.command(
        name="set",
        description="Set the template voice channel"
    )
    @app_commands.describe(
        channel="The voice channel to use as template"
    )
    @commands.has_permissions(manage_channels=True)
    async def set(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel
    ) -> None:
        guild_collection: Any = self.bot.db[str(ctx.guild.id)]
        
        guild_collection["config"].update_one(
            {"_id": "tempvc"},
            {"$set": {"channel_id": channel.id}},
            upsert=True
        )

        try:
            await ctx.guild.me.edit(deafen=True)
        except:
            pass

        # Confirm setup completion
        await ctx.reply(
            f"Temporary VC system set up using {channel.mention} as template!"
        )

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        try:
            guild_collection: Any = self.bot.db[str(member.guild.id)]
            tempvc_doc: Optional[Dict[str, Any]] = guild_collection["config"].find_one({"_id": "tempvc"})
            
            if not tempvc_doc:
                return

            template_channel: Optional[discord.VoiceChannel] = member.guild.get_channel(tempvc_doc.get("channel_id"))
            if not template_channel:
                return

            if after.channel == template_channel:
                # Check if user has permission to create channels
                if not member.guild.me.guild_permissions.manage_channels:
                    return
                    
                category: Optional[discord.CategoryChannel] = template_channel.category
                if category:
                    position: int = len(category.channels)
                else:
                    position: int = len(member.guild.channels)
                    
                new_channel: discord.VoiceChannel = await template_channel.clone(
                    name=f"{member.display_name}'s VC"
                )
                await new_channel.edit(position=position)
                await member.move_to(new_channel)

                embed: discord.Embed = discord.Embed(
                    title="Voice Channel Controls",
                    description="Use the buttons below to control your voice channel",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Owner",
                    value=f"{member.mention}",
                    inline=True
                )
                embed.add_field(
                    name="Region",
                    value=f"{EMOJIS['automatic']} Automatic",
                    inline=True
                )
                embed.add_field(
                    name="State",
                    value=f"{EMOJIS['public']} Public",
                    inline=True
                )
                
                allowed_users: List[str] = []
                banned_users: List[str] = []
                
                for target, perms in new_channel.overwrites.items():
                    if isinstance(target, (discord.Member, discord.Role)):
                        if perms.connect is True:
                            allowed_users.append(target.mention)
                        elif perms.connect is False:
                            banned_users.append(target.mention)
                
                access_info: str = (
                    "**Allowed:** " +
                    (", ".join(allowed_users) if allowed_users else "Everyone") +
                    "\n"
                )
                access_info += (
                    "**Banned:** " +
                    (", ".join(banned_users) if banned_users else "None")
                )
                embed.add_field(
                    name="Access Control",
                    value=access_info,
                    inline=False
                )

                # Send control panel and store message ID
                control_message: discord.Message = await new_channel.send(
                    embed=embed
                )
                
                view: VCControlView = VCControlView(
                    vc_owner=member,
                    control_message_id=control_message.id
                )
                
                await control_message.edit(view=view)

            # Handle owner leaving
            if before.channel and before.channel.id in self.temp_channels:
                if self.temp_channels[before.channel.id] == member:  # Owner left
                    if len(before.channel.members) > 0:  # Others still in VC
                        # Find the control message in the channel
                        async for message in before.channel.history(limit=1000):
                            if message.author == self.bot.user and message.embeds and message.embeds[0].title == "Voice Channel Controls":
                                control_message_id = message.id
                                break
                        
                        claim_message = await before.channel.send(
                            f"🔔 {member.mention} (VC Owner) has left! Click the button below to claim ownership:",
                            view=ClaimView(before.channel.id, control_message_id)
                        )
                    else:  # Channel empty
                        await before.channel.delete()
                        del self.temp_channels[before.channel.id]

            # Handle channel cleanup
            if before.channel and before.channel.id in self.temp_channels:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    del self.temp_channels[before.channel.id]

        except Exception as e:
            print(f"Error in voice state update: {e}")

    @tempvc.command(
        name="toggle",
        description="Toggle the temporary voice channel system"
    )
    @app_commands.describe(
        state="Enable or disable the system"
    )
    @app_commands.choices(
        state=[
            app_commands.Choice(name="on", value="on"),
            app_commands.Choice(name="off", value="off")
        ]
    )
    @commands.has_permissions(manage_channels=True)
    async def toggle(
        self,
        ctx: commands.Context,  
        state: str
    ) -> None:
        # Get database collection
        guild_collection: Any = self.bot.db[str(ctx.guild.id)]
        
        if state.lower() == "on":
            tempvc_doc: Optional[Dict[str, Any]] = (
                guild_collection["config"].find_one({"_id": "tempvc"})
            )
            
            if tempvc_doc and "channel_id" in tempvc_doc:
                guild_collection["config"].update_one(
                    {"_id": "tempvc"},
                    {"$set": {"enabled": True}},
                    upsert=True
                )
                await ctx.reply(
                    "Temporary VC system enabled!"
                )
            else:
                await ctx.reply(
                    "Please set up a template channel first using `?tempvc set`!"
                )
        else:
            guild_collection["config"].update_one(
                {"_id": "tempvc"},
                {"$set": {"enabled": False}},
                upsert=True
            )
            await ctx.reply(
                "Temporary VC system disabled!"
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vccontrol(bot))
