from discord.ext import commands
import discord
from discord import app_commands
import random
import io
import asyncio
from typing import Optional, Dict, Any, List, Union
import time
from discord.ui import Select, View, Button
import string
from utils import parse_time_string
from datetime import datetime, timezone
import json

# Mgem emoji
MGEM = "<a:mgem:1344001728424579082>"

def generate_code() -> str:
    """Generate a unique 6-digit code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_order_id() -> str:
    """Generate a unique order ID"""
    timestamp = int(time.time())
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORDER-{timestamp}-{random_chars}"

class ShopView(discord.ui.View):
    def __init__(self, shop_data: Dict[str, Any], cog: 'Economy'):
        super().__init__(timeout=None)
        self.shop_data = shop_data
        self.cog = cog
        self.update_select_menus()

    def update_select_menus(self):
        self.clear_items()
        roles = [item for item in self.shop_data["items"] if item["type"] == "role"]
        items = [item for item in self.shop_data["items"] if item["type"] == "item"]

        # Add both select menus even if empty
        self.add_item(ShopSelect(self.cog, roles, "Roles", "Select a role to purchase"))
        self.add_item(ShopSelect(self.cog, items, "Items", "Select an item to purchase"))

class ShopSelect(discord.ui.Select):
    def __init__(self, cog: 'Economy', items: List[Dict], category: str, placeholder: str):
        self.cog = cog
        options = []
        for item in items:
            if item["stock"] > 0:
                label = f"{item['name']} (${item['price']})"
                desc = f"Stock: {item['stock']}"
                if item.get('max_per_user'):
                    desc += f" | Max: {item['max_per_user']}/user"
                options.append(discord.SelectOption(
                    label=label,
                    description=desc,
                    value=item['code']
                ))

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options if options else [discord.SelectOption(label="Sold Out", value="none")],
            disabled=not options
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return
        await self.cog.process_purchase(interaction, self.values[0])
        # Reset the select menu
        self.view.update_select_menus()
        await interaction.message.edit(view=self.view)

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.default_currency = 0.1  # Amount earned per message
        self.mgem_price = 1000  # Price per Mgem
        bot.loop.create_task(self.setup_shop_messages())
        bot.loop.create_task(self.check_expired_roles())

    async def check_expired_roles(self):
        """Check and remove expired temporary roles"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                expired_roles = self.bot.db.get_expired_temp_roles()
                for role_data in expired_roles:
                    guild = self.bot.get_guild(role_data["guild_id"])
                    if guild:
                        member = guild.get_member(role_data["user_id"])
                        role = guild.get_role(role_data["role_id"])
                        if member and role and role in member.roles:
                            await member.remove_roles(role)
                    self.bot.db.remove_temp_role(
                        role_data["user_id"],
                        role_data["guild_id"],
                        role_data["role_id"]
                    )
            except Exception as e:
                print(f"Error checking expired roles: {e}")
            await asyncio.sleep(60)  # Check every minute

    async def setup_shop_messages(self):
        """Recreate shop messages on bot restart"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            shop_data = self.bot.db.get_shop_data(guild.id)
            if shop_data and shop_data.get("channel_id"):
                channel = guild.get_channel(shop_data["channel_id"])
                if channel:
                    await channel.purge()
                    embeds = await self.create_shop_embed(guild.id)
                    message = await channel.send(embeds=embeds, view=ShopView(shop_data, self))
                    shop_data["message_id"] = message.id
                    self.bot.db.save_shop_data(guild.id, shop_data)

    async def create_shop_embed(self, guild_id: int) -> List[discord.Embed]:
        """Create shop embeds"""
        shop_data = self.bot.db.get_shop_data(guild_id)
        embeds = []

        # Main embed with instructions
        main_embed = discord.Embed(
            title="🏪 Server Shop",
            description="**Instructions**\nAll purchases are final. Items/roles may have usage limits. Contact staff for purchase issues. Use the select menu below to purchase.",
            color=discord.Color.gold()
        )

        # Process roles
        roles = [item for item in shop_data["items"] if item["type"] == "role"]
        if roles:
            roles_text = ""
            current_embed = main_embed
            
            for item in roles:
                role = self.bot.get_guild(guild_id).get_role(item["role_id"])
                role_mention = role.mention if role else "Deleted Role"
                time_limit = f" | {item['time_limit']} duration" if item.get('time_limit') else ""
                max_per_user = f" | Max: {item['max_per_user']}/user" if item.get('max_per_user') else ""
                new_line = f"{role_mention} [`{item['code']}`]\n${item['price']} | Stock: {item['stock']}{max_per_user}{time_limit}\n\n"
                
                if len(roles_text + new_line) > 1024:
                    current_embed.add_field(name="Available Roles", value=roles_text, inline=False)
                    embeds.append(current_embed)
                    current_embed = discord.Embed(title="🏪 Server Shop (Continued)", color=discord.Color.gold())
                    roles_text = new_line
                else:
                    roles_text += new_line
            
            if roles_text:
                current_embed.add_field(name="Available Roles", value=roles_text, inline=False)
                if current_embed != main_embed:
                    embeds.append(current_embed)

        # Process items
        items = [item for item in shop_data["items"] if item["type"] == "item"]
        if items:
            items_text = ""
            current_embed = main_embed if not embeds else embeds[-1]
            
            for item in items:
                max_per_user = f" | Max: {item['max_per_user']}/user" if item.get('max_per_user') else ""
                new_line = f"**{item['name']}** [`{item['code']}`]\n${item['price']} | Stock: {item['stock']}{max_per_user}\n\n"
                
                if len(items_text + new_line) > 1024:
                    current_embed.add_field(name="Available Items", value=items_text, inline=False)
                    embeds.append(current_embed)
                    current_embed = discord.Embed(title="🏪 Server Shop (Continued)", color=discord.Color.gold())
                    items_text = new_line
                else:
                    items_text += new_line
            
            if items_text:
                current_embed.add_field(name="Available Items", value=items_text, inline=False)
                if current_embed != main_embed and current_embed not in embeds:
                    embeds.append(current_embed)

        if not embeds:
            main_embed.description += "\nNo items available in the shop."
            embeds.append(main_embed)
        elif main_embed not in embeds:
            embeds.insert(0, main_embed)

        return embeds

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        self.bot.db.update_user_balance(message.author.id, self.default_currency)

    async def process_purchase(self, interaction: discord.Interaction, item_code: str):
        """Process a purchase"""
        shop_data = self.bot.db.get_shop_data(interaction.guild.id)
        item = next((item for item in shop_data["items"] if item["code"] == item_code), None)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return

        user_balance = self.bot.db.get_user_balance(interaction.user.id)
        if user_balance < item["price"]:
            await interaction.response.send_message("Insufficient funds!", ephemeral=True)
            return

        if item["stock"] <= 0:
            await interaction.response.send_message("Item out of stock!", ephemeral=True)
            return

        # Process purchase
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get the item_id from the database
            db_item = self.bot.db.get_shop_item_by_code(item_code)
            if not db_item:
                await interaction.followup.send("Error: Item not found in database!", ephemeral=True)
                return
            
            order_id = generate_order_id()
            old_balance = user_balance
            
            # Update balances and stock
            self.bot.db.update_user_balance(interaction.user.id, -item["price"])
            self.bot.db.update_item_stock(db_item["item_id"], -1)
            self.bot.db.update_shop_revenue(interaction.guild.id, item["price"])
            
            # Update shop data stock
            for shop_item in shop_data["items"]:
                if shop_item["code"] == item_code:
                    shop_item["stock"] -= 1
                    break
            self.bot.db.save_shop_data(interaction.guild.id, shop_data)
            
            # Log purchase
            self.bot.db.log_purchase(
                interaction.user.id,
                interaction.guild.id,
                db_item["item_id"],
                order_id,
                item["price"]
            )

            # Create receipt embed
            receipt = discord.Embed(
                title="🧾 Purchase Receipt",
                description=f"Order ID: `{order_id}`",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            receipt.add_field(name="Server", value=interaction.guild.name, inline=True)
            receipt.add_field(name="Buyer", value=interaction.user.mention, inline=True)
            receipt.add_field(name="Item", value=f"{item['name']} [`{item['code']}`]", inline=False)
            receipt.add_field(name="Price", value=f"${item['price']}", inline=True)
            receipt.add_field(name="New Balance", value=f"${user_balance - item['price']:.2f}", inline=True)

            # Handle role purchases
            success = True
            error_message = None
            if item["type"] == "role":
                role = interaction.guild.get_role(item["role_id"])
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        if item.get("time_limit"):
                            duration = parse_time_string(item["time_limit"])
                            removal_time = datetime.now(timezone.utc) + duration
                            self.bot.db.add_temp_role(
                                interaction.user.id,
                                interaction.guild.id,
                                role.id,
                                removal_time
                            )
                    except discord.HTTPException as e:
                        success = False
                        error_message = str(e)

            # Update shop message
            try:
                shop_message = await interaction.channel.fetch_message(shop_data["message_id"])
                embeds = await self.create_shop_embed(interaction.guild.id)
                await shop_message.edit(embeds=embeds, view=ShopView(shop_data, self))
            except discord.NotFound:
                pass  # Ignore if shop message not found

            # Send receipt to DM
            try:
                await interaction.user.send(embed=receipt)
                dm_sent = True
            except discord.HTTPException:
                dm_sent = False

            # Send response in channel
            if success:
                await interaction.followup.send(
                    f"Successfully purchased {item['name']}! " + 
                    ("Receipt sent to your DMs." if dm_sent else "Could not send receipt to DMs - please enable DMs."),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Purchase completed but failed to deliver item: {error_message}\nPlease contact an admin with your receipt.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"Error processing purchase: {e}")
            await interaction.followup.send(
                "An error occurred while processing your purchase. Please contact an admin.",
                ephemeral=True
            )

    @commands.hybrid_group(name="mgem", description="Mgem related commands")
    async def mgem(self, ctx: commands.Context):
        """Premium currency management system for special purchases
        
        This command group provides functionality for managing Mgems, the bot's
        premium currency. Mgems can be purchased with server currency and
        transferred between users. They're used for exclusive purchases and
        premium features in the server economy.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @mgem.command(name="buy", description="Buy Mgems with server currency")
    @app_commands.describe(count="Number of Mgems to buy")
    async def mgem_buy(self, ctx: commands.Context, count: int) -> None:
        """Convert server currency to premium Mgem currency
        
        This command allows you to purchase Mgems using your regular server currency.
        Mgems are a premium currency that can be used for special purchases and
        features. The exchange rate is fixed, and you'll receive a digital receipt
        confirming your purchase transaction.
        """
        if count <= 0:
            await ctx.reply("Please specify a positive number of Mgems to buy!")
            return

        total_cost = count * self.mgem_price
        user_balance = self.bot.db.get_user_balance(ctx.author.id)

        if user_balance < total_cost:
            await ctx.reply(f"Insufficient funds! You need ${total_cost:,} to buy {count} Mgems.")
            return

        # Process purchase
        self.bot.db.update_user_balance(ctx.author.id, -total_cost)
        self.bot.db.update_user_mgems(ctx.author.id, count)

        # Create receipt embed
        receipt = discord.Embed(
            title="🧾 Mgem Purchase Receipt",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        receipt.add_field(name="Buyer", value=ctx.author.mention, inline=True)
        receipt.add_field(name="Mgems Bought", value=f"{count} {MGEM}", inline=True)
        receipt.add_field(name="Total Cost", value=f"${total_cost:,}", inline=True)
        receipt.add_field(name="New Balance", value=f"${user_balance - total_cost:,.2f}", inline=True)
        receipt.add_field(name="New Mgem Balance", value=f"{self.bot.db.get_user_mgems(ctx.author.id)} {MGEM}", inline=True)

        await ctx.reply(embed=receipt)

    @mgem.command(name="give", description="Give Mgems to another user")
    @app_commands.describe(
        user="The user to give Mgems to",
        count="Number of Mgems to give"
    )
    async def mgem_give(self, ctx: commands.Context, user: discord.Member, count: int) -> None:
        """Transfer Mgems to another server member
        
        This command allows you to give your Mgems to another user in the server.
        The transfer is immediate, and both parties receive confirmation of the
        transaction. This feature enables a player-driven economy where premium
        currency can circulate between members.
        """
        if count <= 0:
            await ctx.reply("Please specify a positive number of Mgems to give!")
            return

        if user == ctx.author:
            await ctx.reply("You can't give Mgems to yourself!")
            return

        sender_mgems = self.bot.db.get_user_mgems(ctx.author.id)
        if sender_mgems < count:
            await ctx.reply(f"You don't have enough Mgems! You have {sender_mgems} {MGEM}")
            return

        # Transfer the Mgems
        self.bot.db.update_user_mgems(ctx.author.id, -count)
        self.bot.db.update_user_mgems(user.id, count)

        # Create transfer embed
        transfer = discord.Embed(
            title="💎 Mgem Transfer",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        transfer.add_field(name="From", value=ctx.author.mention, inline=True)
        transfer.add_field(name="To", value=user.mention, inline=True)
        transfer.add_field(name="Amount", value=f"{count} {MGEM}", inline=True)
        transfer.add_field(name="Your New Balance", value=f"{self.bot.db.get_user_mgems(ctx.author.id)} {MGEM}", inline=True)

        await ctx.reply(embed=transfer)

    @commands.hybrid_command(name="shop", description="View the server shop")
    async def shop(self, ctx: commands.Context):
        """Browse available items and roles for purchase
        
        This command displays the server's shop interface, showing all available
        items and roles that can be purchased with server currency. The shop
        includes detailed information about pricing, stock availability, and
        any usage limitations for each item.
        """
        # Acknowledge the command immediately
        await ctx.defer(ephemeral=True)
        
        # Show ephemeral shop message
        shop_data = self.bot.db.get_shop_data(ctx.guild.id)
        embeds = await self.create_shop_embed(ctx.guild.id)
        await ctx.reply(embeds=embeds, view=ShopView(shop_data, self), ephemeral=True)

    @commands.hybrid_group(name="shopadmin", description="Shop management commands")
    @commands.has_permissions(administrator=True)
    async def shopadmin(self, ctx: commands.Context):
        """Administrative tools for managing the server shop
        
        This command group provides powerful tools for server administrators to
        manage the shop system. It includes functionality for adding/removing items,
        setting up shop channels, configuring prices, and managing stock levels.
        These commands require administrator permissions.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    
    @shopadmin.command(name="setchannel", description="Set the shop channel")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Shop channel (leave empty to remove shop channel)",
        log_channel="Purchase log channel (optional)"
    )
    async def setchannel(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        log_channel: Optional[discord.TextChannel] = None
    ):
        """Configure dedicated channels for the shop system
        
        This command sets up the main shop display channel where members can browse
        and purchase items. Optionally, you can also specify a separate logging
        channel to record all purchase transactions for administrative review.
        Setting up these channels creates a centralized shopping experience.
        """
        await ctx.defer()
        
        shop_data = self.bot.db.get_shop_data(ctx.guild.id)
        
        # If channel is None, remove the shop channel
        if channel is None:
            if shop_data.get("channel_id"):
                old_channel = ctx.guild.get_channel(shop_data["channel_id"])
                if old_channel:
                    try:
                        await old_channel.purge()
                    except discord.HTTPException:
                        pass
            
            shop_data["channel_id"] = None
            shop_data["message_id"] = None
            shop_data["log_channel_id"] = None
            self.bot.db.save_shop_data(ctx.guild.id, shop_data)
            await ctx.reply("Shop channel has been removed.")
            return

        # Set up new shop channel
        shop_data["channel_id"] = channel.id
        shop_data["log_channel_id"] = log_channel.id if log_channel else None
        
        await channel.purge()
        embeds = await self.create_shop_embed(ctx.guild.id)
        message = await channel.send(embeds=embeds, view=ShopView(shop_data, self))
        shop_data["message_id"] = message.id
        
        self.bot.db.save_shop_data(ctx.guild.id, shop_data)
        await ctx.reply(f"Shop channel set to {channel.mention}!")
        
    @shopadmin.command(name="additem", description="Add a new item to the shop")
    @app_commands.describe(
        name="Item name",
        price="Item price",
        stock="Initial stock",
        max_per_user="Maximum purchases per user (optional)"
    )
    async def additem(self, ctx: commands.Context, name: str, price: float, stock: int, max_per_user: Optional[int] = None):
        """Create a new purchasable item in the server shop
        
        This command adds a new general item to the server shop with customizable
        properties such as name, price, stock quantity, and optional purchase limits.
        Each item receives a unique code for tracking purchases and inventory.
        Added items appear immediately in the shop for members to purchase.
        """
        await ctx.defer()
        
        item = {
            "type": "item",
            "code": generate_code(),
            "name": name,
            "price": price,
            "stock": stock,
            "max_per_user": max_per_user
        }
        
        item_id = self.bot.db.save_shop_item(ctx.guild.id, item)
        
        shop_data = self.bot.db.get_shop_data(ctx.guild.id)
        if "items" not in shop_data:
            shop_data["items"] = []
        shop_data["items"].append(item)
        self.bot.db.save_shop_data(ctx.guild.id, shop_data)
        
        await self._update_shop_message(ctx.guild.id, shop_data)
        await ctx.reply(f"Added item {name} to the shop!")

    @shopadmin.command(name="addrole", description="Add a new role to the shop")
    @app_commands.describe(
        role="Role to add",
        price="Role price",
        stock="Initial stock",
        max_per_user="Maximum purchases per user (optional)",
        time_limit="Time limit for the role (e.g., 24h, 7d) (optional)"
    )
    async def addrole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        price: float,
        stock: int,
        max_per_user: Optional[int] = None,
        time_limit: Optional[str] = None
    ):
        """Add a purchasable role to the server shop
        
        This command creates a new role listing in the server shop that members
        can purchase with currency. The role can be configured with various options
        including price, quantity available, purchase limits per user, and optional
        time restrictions that automatically remove the role after a set duration.
        """
        await ctx.defer()
        
        item = {
            "type": "role",
            "code": generate_code(),
            "name": role.name,
            "role_id": role.id,
            "price": price,
            "stock": stock,
            "max_per_user": max_per_user,
            "time_limit": time_limit
        }
        
        item_id = self.bot.db.save_shop_item(ctx.guild.id, item)
        
        shop_data = self.bot.db.get_shop_data(ctx.guild.id)
        if "items" not in shop_data:
            shop_data["items"] = []
        shop_data["items"].append(item)
        self.bot.db.save_shop_data(ctx.guild.id, shop_data)
        
        await self._update_shop_message(ctx.guild.id, shop_data)
        await ctx.reply(f"Added role {role.name} to the shop!")

    @shopadmin.command(name="removeitem", description="Remove an item from the shop")
    @app_commands.describe(code="Item code to remove")
    async def removeitem(self, ctx: commands.Context, code: str):
        """Delete an item or role from the server shop
        
        This command permanently removes an item or role from the shop inventory
        using its unique code. Once removed, the item will no longer be available
        for purchase, though existing purchases will not be affected. Use this
        command when you want to discontinue offering specific items.
        """
        await ctx.defer()
        
        shop_data = self.bot.db.get_shop_data(ctx.guild.id)
        shop_data["items"] = [item for item in shop_data["items"] if item["code"] != code]
        self.bot.db.save_shop_data(ctx.guild.id, shop_data)
        
        await self._update_shop_message(ctx.guild.id, shop_data)
        await ctx.reply(f"Removed item with code `{code}` from the shop!")

    async def _update_shop_message(self, guild_id: int, shop_data: dict):
        """Helper method to update shop message"""
        if shop_data.get("channel_id"):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
                
            channel = guild.get_channel(shop_data["channel_id"])
            if channel and shop_data.get("message_id"):
                try:
                    message = await channel.fetch_message(shop_data["message_id"])
                    embeds = await self.create_shop_embed(guild_id)
                    await message.edit(embeds=embeds, view=ShopView(shop_data, self))
                except discord.NotFound:
                    message = await channel.send(embeds=embeds, view=ShopView(shop_data, self))
                    shop_data["message_id"] = message.id
                    self.bot.db.save_shop_data(guild_id, shop_data)

    @commands.hybrid_command(name="balance", description="Check your or another user's balance")
    @app_commands.describe(user="The user to check balance for (optional)")
    async def balance(self, ctx: commands.Context, user: Optional[discord.Member] = None) -> None:
        """View currency and Mgem balances for yourself or others
        
        This command displays the current financial standing of a user, including
        their regular currency balance and Mgem premium currency holdings. When used
        without specifying a user, it shows your own balance. This command helps
        track personal finances and economic activity within the server.
        """
        user = user or ctx.author
        balance = self.bot.db.get_user_balance(user.id)
        mgems = self.bot.db.get_user_mgems(user.id)
        
        if user == ctx.author:
            await ctx.reply(f"Your balance: `${balance:.2f}` | Mgems: {MGEM}{mgems}")
        else:
            await ctx.reply(f"{user.name}'s balance: `${balance:.2f}`")

    @commands.hybrid_command(name="give", description="Give money to another user")
    @app_commands.describe(
        user="The user to give money to",
        amount="Amount to give"
    )
    async def give(self, ctx: commands.Context, user: discord.Member, amount: float) -> None:
        """Transfer regular currency to another server member
        
        This command allows you to give some of your currency to another user
        in the server. The transfer is immediate and requires you to have sufficient
        funds. This feature enables a player-driven economy where regular currency
        can circulate freely between members for trades, services, or gifts.
        """
        if amount <= 0:
            await ctx.reply("Amount must be positive!")
            return
            
        if user == ctx.author:
            await ctx.reply("You can't give money to yourself!")
            return

        sender_balance = self.bot.db.get_user_balance(ctx.author.id)
        if sender_balance < amount:
            await ctx.reply("You don't have enough money!")
            return

        # Transfer the money
        self.bot.db.update_user_balance(ctx.author.id, -amount)
        self.bot.db.update_user_balance(user.id, amount)

        await ctx.reply(f"✅ Successfully sent `${amount:.2f}` to {user.mention}!")

    @commands.hybrid_command(name="forbes", description="View detailed wealth statistics")
    async def forbes(self, ctx: commands.Context) -> None:
        """Display comprehensive economic statistics for the server
        
        This command generates a detailed economic report showing wealth distribution
        across the server. It includes metrics such as total money in circulation,
        average balances, richest members with their wealth percentages, and Mgem
        distribution statistics. This provides transparency into the server economy.
        """
        # Get top 10 richest users who are in this guild
        rich_list = self.bot.db.get_top_balances(ctx.guild.id, 10)
        total_money = sum(user["balance"] for user in rich_list)
        
        # Get users with >$5 for average calculation
        active_users = [user for user in rich_list if user["balance"] >= 5]
        avg_balance = sum(user["balance"] for user in active_users) / len(active_users) if active_users else 0
        
        embed = discord.Embed(
            title="🏦 Economic Report",
            color=discord.Color.gold()
        )
        
        # Global stats
        stats = (
            f"**Total Money**: ${total_money:.2f}\n"
            f"**Average Balance** ($5+): ${avg_balance:.2f}\n"
            f"**Active Users** ($5+): {len(active_users)}"
        )
        embed.add_field(name="📊 Global Statistics", value=stats, inline=False)
        
        # Rich list
        rich_list_text = ""
        for i, data in enumerate(rich_list, 1):
            member = ctx.guild.get_member(data["user_id"])
            if member:
                percentage = (data["balance"] / total_money) * 100 if total_money > 0 else 0
                rich_list_text += f"**#{i}** {member.mention}: ${data['balance']:.2f} ({percentage:.1f}%)\n"
        
        embed.add_field(name="🏆 Wealthiest Members", value=rich_list_text or "No data", inline=False)
        
        # Add Mgem statistics
        total_mgems = sum(self.bot.db.get_user_mgems(user["user_id"]) for user in rich_list)
        
        # Get top 5 Mgem holders
        gem_stats = f"**Total Mgems**: {MGEM}{total_mgems}\n\n**Top Mgem Holders**:\n"
        for i, data in enumerate(rich_list[:5], 1):
            member = ctx.guild.get_member(data["user_id"])
            mgems = self.bot.db.get_user_mgems(data["user_id"])
            if member and mgems > 0:
                gem_stats += f"**#{i}** {member.mention}: {MGEM}{mgems}\n"
        
        embed.add_field(name="Mgem Statistics", value=gem_stats, inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="inflate")
    async def inflate(self, ctx: commands.Context, user: discord.Member, amount: float) -> None:
        if ctx.author.id != self.bot.owner_id:
            return

        if amount <= 0:
            await ctx.reply("Amount must be positive!")
            return

        self.bot.db.update_user_balance(user.id, amount)
        await ctx.reply(f"Added ${amount:.2f} to {user.mention}'s balance!")

    @commands.hybrid_command(name="transactions", description="View your purchase history")
    async def transactions(self, ctx: commands.Context):
        """Retrieve a complete log of your shop purchases
        
        This command generates and sends you a private record of all your transactions
        in the server shop. The log includes detailed information for each purchase
        such as item names, prices paid, purchase dates, and order IDs. For role
        purchases, it also displays role information and any time limitations.
        """
        await ctx.defer(ephemeral=True)
        transactions = self.bot.db.get_user_purchases(ctx.author.id)

        if not transactions:
            await ctx.reply("You haven't made any purchases yet!", ephemeral=True)
            return

        # Create transactions.txt
        content = "Your Transaction History\n" + "="*50 + "\n\n"
        
        for t in transactions:
            content += f"Order ID: {t['order_id']}\n"
            content += f"Date: {datetime.fromisoformat(t['purchased_at']).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            content += f"Item: {t['name']} [{t['code']}]\n"
            content += f"Price: ${t['price_paid']:.2f}\n"
            if t['type'] == 'role':
                role = ctx.guild.get_role(t['role_id'])
                content += f"Role: {role.mention if role else 'Deleted Role'}\n"
                content += f"Duration: {t.get('time_limit', 'Permanent')}\n"
            content += "="*50 + "\n\n"

        # Send as DM with file attachment
        file = discord.File(
            io.BytesIO(content.encode()),
            filename="transactions.txt"
        )
        try:
            await ctx.author.send(file=file)
            await ctx.reply("Transaction history sent to your DMs!", ephemeral=True)
        except discord.HTTPException:
            await ctx.reply("Could not send DM. Please enable DMs to receive the transaction history.", ephemeral=True)

    @commands.hybrid_command(name="daily", description="Claim your daily reward")
    async def daily(self, ctx: commands.Context) -> None:
        """Collect a free currency bonus once every 24 hours
        
        This command grants you a random amount of free currency that can be claimed
        once per day. The reward helps boost your economy participation and provides
        a consistent way to earn currency by being active in the server. If you've
        already claimed your reward today, the command will show when you can claim again.
        """
        last_claim = self.bot.db.get_last_daily_claim(ctx.author.id)
        current_time = datetime.now(timezone.utc)

        if last_claim:
            # Convert last_claim to timezone-aware if it isn't already
            if last_claim.tzinfo is None:
                last_claim = last_claim.replace(tzinfo=timezone.utc)
                
            time_elapsed = current_time - last_claim
            if time_elapsed.total_seconds() < 86400:
                time_left = 86400 - time_elapsed.total_seconds()
                hours = int(time_left // 3600)
                minutes = int((time_left % 3600) // 60)
                await ctx.reply(f"You can claim your daily reward again in `{hours}h {minutes}m`")
                return


        # Generate random reward between $2 and $5
        reward = round(random.uniform(2, 5), 2)

        # Update user's balance and claim time
        self.bot.db.update_user_balance(ctx.author.id, reward)
        self.bot.db.update_daily_claim(ctx.author.id)

        await ctx.reply(
            f"You claimed your daily reward of `${reward:.2f}`!\n"
            f"Your new balance: `${self.bot.db.get_user_balance(ctx.author.id):.2f}`"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))