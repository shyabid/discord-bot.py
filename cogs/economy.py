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
from utils import parse_time_string  # Import from utils.py instead
from datetime import datetime
import json

# mgem = "<a:mgem:1343994099434520690>"
mgem = "<a:mgem:1344001728424579082>"

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
        self.add_item(ShopSelect(
            self.cog,
            roles,
            "Roles",
            "Select a role to purchase"
        ))
        self.add_item(ShopSelect(
            self.cog,
            items,
            "Items",
            "Select an item to purchase"
        ))

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
        
        item_code = self.values[0]
        await self.cog.process_purchase(interaction, item_code)

class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.default_currency = 0.1  # Amount earned per message
        bot.loop.create_task(self.setup_shop_messages())
        self.ensure_collections()
        self.daily_cooldowns = {}  # {user_id: last_claim_timestamp}
        self.load_daily_cooldowns()
        self.mgem_price = 1000  # Price per Mgem
    
    async def get_user_mgems(self, user_id: int) -> int:
        """Get user's Mgem count"""
        data = self.bot.db["userdata"]["gems"].find_one({"userid": user_id})
        return data["mgem"] if data else 0

    async def update_user_mgems(self, user_id: int, amount: int) -> None:
        """Update user's Mgem count"""
        self.bot.db["userdata"]["gems"].update_one(
            {"userid": user_id},
            {"$inc": {"mgem": amount}},
            upsert=True
        )
            

    @commands.hybrid_group(name="mgem", description="Mgem related commands")
    async def mgem(self, ctx: commands.Context):
        """
        Mgem management commands.

        **Usage:**
        ?mgem <subcommand>
        /mgem <subcommand>

        **Subcommands:**
        buy - Buy Mgems with server currency
        give - Give Mgems to another user

        **Examples:**
        ?mgem buy 10
        /mgem give @user 5
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @mgem.command(name="buy", description="Buy Mgems with server currency")
    @app_commands.describe(count="Number of Mgems to buy")
    async def mgem_buy(self, ctx: commands.Context, count: int) -> None:
        """
        Buy Mgems with server currency. Each Mgem costs $1000.

        **Usage:**
        ?mgem buy <count>
        /mgem buy <count>

        **Parameters:**
        count: Number of Mgems to buy

        **Examples:**
        ?mgem buy 5
        /mgem buy 10
        """
        if count <= 0:
            await ctx.reply("Please specify a positive number of Mgems to buy!")
            return

        total_cost = count * self.mgem_price
        user_balance = await self.get_user_balance(ctx.guild.id, ctx.author.id)

        if user_balance < total_cost:
            await ctx.reply(f"Insufficient funds! You need ${total_cost:,} to buy {count} Mgems.")
            return

        # Process purchase
        await self.update_user_balance(ctx.guild.id, ctx.author.id, -total_cost)
        await self.update_user_mgems(ctx.author.id, count)

        # Create receipt embed
        receipt = discord.Embed(
            title="🧾 Mgem Purchase Receipt",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        receipt.add_field(name="Buyer", value=ctx.author.mention, inline=True)
        receipt.add_field(name="Mgems Bought", value=f"{count} {mgem}", inline=True)
        receipt.add_field(name="Total Cost", value=f"${total_cost:,}", inline=True)
        receipt.add_field(name="New Balance", value=f"${user_balance - total_cost:,.2f}", inline=True)
        receipt.add_field(name="New Mgem Balance", value=f"{await self.get_user_mgems(ctx.author.id)} {mgem}", inline=True)

        await ctx.reply(embed=receipt)

    @mgem.command(name="give", description="Give Mgems to another user")
    @app_commands.describe(
        user="The user to give Mgems to",
        count="Number of Mgems to give"
    )
    async def mgem_give(self, ctx: commands.Context, user: discord.Member, count: int) -> None:
        """
        Give some of your Mgems to another user.

        **Usage:**
        ?mgem give <user> <count>
        /mgem give <user> <count>

        **Parameters:**
        user: The user to send Mgems to
        count: How many Mgems to send (must be positive)

        **Examples:**
        ?mgem give @username 5
        /mgem give @username 10
        """
        if count <= 0:
            await ctx.reply("Please specify a positive number of Mgems to give!")
            return

        if user == ctx.author:
            await ctx.reply("You can't give Mgems to yourself!")
            return

        sender_mgems = await self.get_user_mgems(ctx.author.id)
        if sender_mgems < count:
            await ctx.reply(f"You don't have enough Mgems! You have {sender_mgems} {mgem}")
            return

        # Transfer the Mgems
        await self.update_user_mgems(ctx.author.id, -count)
        await self.update_user_mgems(user.id, count)

        # Create transfer embed
        transfer = discord.Embed(
            title="💎 Mgem Transfer",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        transfer.add_field(name="From", value=ctx.author.mention, inline=True)
        transfer.add_field(name="To", value=user.mention, inline=True)
        transfer.add_field(name="Amount", value=f"{count} {mgem}", inline=True)
        transfer.add_field(name="Your New Balance", value=f"{await self.get_user_mgems(ctx.author.id)} {mgem}", inline=True)

        await ctx.reply(embed=transfer)

    # Regular command versions for backward compatibility
    @commands.command(name="buymgem", description="Buy Mgems with server currency")
    async def buymgem_command(self, ctx: commands.Context, count: int) -> None:
        """
        Buy Mgems with server currency. Each Mgem costs $1000.

        **Usage:**
        ?buymgem <count>

        **Parameters:**
        count: Number of Mgems to buy

        **Examples:**
        ?buymgem 5
        """
        await self.mgem_buy(ctx, count)

    @commands.command(name="givemgem", description="Give Mgems to another user")
    async def givemgem_command(self, ctx: commands.Context, user: discord.Member, count: int) -> None:
        """
        Give some of your Mgems to another user.

        **Usage:**
        ?givemgem <user> <count>

        **Parameters:**
        user: The user to send Mgems to
        count: How many Mgems to send (must be positive)

        **Examples:**
        ?givemgem @username 5
        """
        await self.mgem_give(ctx, user, count)

    def load_daily_cooldowns(self):
        """Load daily cooldowns from database"""
        for guild in self.bot.guilds:
            daily_data = self.bot.db[str(guild.id)]["daily_claims"].find()
            for data in daily_data:
                self.daily_cooldowns[data["user_id"]] = data["last_claim"]

    def ensure_collections(self):
        """Ensure all required collections exist"""
        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            self.bot.db[guild_id]["transactions"].create_index([("user_id", 1)])
            self.bot.db[guild_id]["shop_stats"].update_one(
                {"_id": "balance"},
                {"$setOnInsert": {"total": 0.0}},
                upsert=True
            )
            self.bot.db[guild_id]["user_purchases"].create_index([("user_id", 1), ("item_code", 1)])

    async def setup_shop_messages(self):
        """Recreate shop messages on bot restart"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            shop_data = await self.get_shop_data(guild.id)
            if shop_data and shop_data.get("channel_id"):
                channel = guild.get_channel(shop_data["channel_id"])
                if channel:
                    await channel.purge()
                    embeds = await self.create_shop_embed(guild.id)
                    message = await channel.send(embeds=embeds, view=ShopView(shop_data, self))
                    shop_data["message_id"] = message.id
                    await self.save_shop_data(guild.id, shop_data)

    async def get_shop_data(self, guild_id: int) -> Dict[str, Any]:
        """Get shop data from database"""
        data = self.bot.db[str(guild_id)]["config"].find_one({"_id": "shop"}) or {
            "_id": "shop",
            "channel_id": None,
            "log_channel_id": None,
            "items": [],
            "message_id": None
        }
        return data

    async def save_shop_data(self, guild_id: int, data: Dict[str, Any]) -> None:
        """Save shop data to database"""
        self.bot.db[str(guild_id)]["config"].update_one(
            {"_id": "shop"},
            {"$set": data},
            upsert=True
        )

    async def get_user_balance(self, guild_id: int, user_id: int) -> float:
        """Get user's balance"""
        data = self.bot.db[str(guild_id)]["economy"].find_one({"user_id": user_id}) or {
            "user_id": user_id,
            "balance": 0.0
        }
        return data["balance"]

    async def update_user_balance(self, guild_id: int, user_id: int, amount: float) -> None:
        """Update user's balance"""
        self.bot.db[str(guild_id)]["economy"].update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}},
            upsert=True
        )

    async def create_shop_embed(self, guild_id: int) -> List[discord.Embed]:
        """Create shop embeds"""
        shop_data = await self.get_shop_data(guild_id)
        embeds = []

        # Main embed with instructions and items
        main_embed = discord.Embed(
            title="🏪 Server Shop",
            description=(
                "**Instructions**\n"
                "All purchases are final. Items/roles may have usage limits. Contact staff for purchase issues. "
                "Use the select menu bellow to purchase. Additionally, you can use /buy too.\n"
            ),
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
                
                # Check if adding this would exceed character limit
                if len(roles_text + new_line) > 1024:
                    current_embed.add_field(name="Available Roles", value=roles_text, inline=False)
                    embeds.append(current_embed)
                    
                    # Create new embed for overflow
                    current_embed = discord.Embed(
                        title="🏪 Server Shop (Continued)",
                        color=discord.Color.gold()
                    )
                    roles_text = new_line
                else:
                    roles_text += new_line
            
            # Add remaining roles
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
                
                # Check if adding this would exceed character limit
                if len(items_text + new_line) > 1024:
                    current_embed.add_field(name="Available Items", value=items_text, inline=False)
                    embeds.append(current_embed)
                    
                    # Create new embed for overflow
                    current_embed = discord.Embed(
                        title="🏪 Server Shop (Continued)",
                        color=discord.Color.gold()
                    )
                    items_text = new_line
                else:
                    items_text += new_line
            
            # Add remaining items
            if items_text:
                current_embed.add_field(name="Available Items", value=items_text, inline=False)
                if current_embed != main_embed and current_embed not in embeds:
                    embeds.append(current_embed)

        # If no items were added to the embeds list, add the main embed
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
        
        await self.update_user_balance(message.guild.id, message.author.id, self.default_currency)

    async def log_transaction(self, guild_id: int, transaction: dict) -> None:
        """Log a transaction to database"""
        transaction["timestamp"] = datetime.utcnow()
        self.bot.db[str(guild_id)]["transactions"].insert_one(transaction)

    async def check_purchase_limit(self, guild_id: int, user_id: int, item: dict) -> bool:
        """Check if user has reached purchase limit"""
        if not item.get('max_per_user'):
            return True
            
        # For roles, only check limit if user currently has the role
        if item["type"] == "role":
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(user_id)
            role = guild.get_role(item["role_id"])
            
            if not role or not member:
                return True
                
            # If user doesn't have the role, they can buy it
            if role not in member.roles:
                return True
                
            # If it's a temporary role, check if it's expired in temp_roles
            if item.get("time_limit"):
                temp_role = self.bot.db[str(guild_id)]["temp_roles"].find_one({
                    "user_id": user_id,
                    "role_id": role.id
                })
                
                # If no temp role entry or role has expired, they can buy again
                if not temp_role or temp_role["removal_time"] <= time.time():
                    return True

        # For regular items or if user has active role, check normal limit
        purchases = self.bot.db[str(guild_id)]["user_purchases"].find_one({
            "user_id": user_id,
            "item_code": item["code"]
        })
        
        return not purchases or purchases.get("count", 0) < item["max_per_user"]

    async def update_purchase_count(self, guild_id: int, user_id: int, item: dict) -> None:
        """Update user's purchase count for an item"""
        self.bot.db[str(guild_id)]["user_purchases"].update_one(
            {"user_id": user_id, "item_code": item["code"]},
            {"$inc": {"count": 1}},
            upsert=True
        )

    async def process_purchase(self, interaction: discord.Interaction, item_code: str):
        """Process a purchase"""
        shop_data = await self.get_shop_data(interaction.guild.id)
        item = next((item for item in shop_data["items"] if item["code"] == item_code), None)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return

        user_balance = await self.get_user_balance(interaction.guild.id, interaction.user.id)
        if user_balance < item["price"]:
            await interaction.response.send_message("Insufficient funds!", ephemeral=True)
            return

        if item["stock"] <= 0:
            await interaction.response.send_message("Item out of stock!", ephemeral=True)
            return

        # Check purchase limit
        if not await self.check_purchase_limit(interaction.guild.id, interaction.user.id, item):
            await interaction.response.send_message(
                f"You've reached the maximum purchase limit ({item['max_per_user']}) for this item!",
                ephemeral=True
            )
            return

        # Send response in channel first
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Process purchase
            order_id = generate_order_id()
            item["stock"] -= 1
            old_balance = await self.get_user_balance(interaction.guild.id, interaction.user.id)
            await self.update_user_balance(interaction.guild.id, interaction.user.id, -item["price"])
            
            # Update shop balance properly
            self.bot.db[str(interaction.guild.id)]["shop_stats"].update_one(
                {"_id": "balance"},
                {"$inc": {"total": item["price"]}},
                upsert=True
            )

            # Update user's purchase count
            await self.update_purchase_count(interaction.guild.id, interaction.user.id, item)

            # Create receipt embed
            receipt = discord.Embed(
                title="🧾 Purchase Receipt",
                description=f"Order ID: `{order_id}`\nKeep this receipt safe! If you didn't receive your item automatically, show this receipt to an admin.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            receipt.add_field(name="Server", value=interaction.guild.name, inline=True)
            receipt.add_field(name="Buyer", value=interaction.user.mention, inline=True)
            receipt.add_field(name="Item", value=f"{item['name']} [`{item['code']}`]", inline=False)
            receipt.add_field(name="Price", value=f"${item['price']}", inline=True)
            receipt.add_field(name="New Balance", value=f"${user_balance - item['price']:.2f}", inline=True)
            
            if item["type"] == "role":
                receipt.add_field(
                    name="Type", 
                    value=f"Role | Duration: {item.get('time_limit', 'Permanent')}", 
                    inline=False
                )

            receipt.set_footer(text="If you didn't receive your item, contact an admin with this receipt")

            # Create log embed with more details
            log_embed = discord.Embed(
                title="📝 Purchase Log",
                description=f"Order ID: `{order_id}`",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Item", value=f"{item['name']} [`{item['code']}`]", inline=False)
            log_embed.add_field(name="Buyer", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            log_embed.add_field(name="Price", value=f"${item['price']}", inline=True)
            log_embed.add_field(name="Stock Left", value=str(item['stock']), inline=True)
            
            if item["type"] == "role":
                log_embed.add_field(
                    name="Role Details",
                    value=f"Role: {interaction.guild.get_role(item['role_id']).mention}\nDuration: {item.get('time_limit', 'Permanent')}",
                    inline=False
                )

            # Handle role purchases with proper duration tracking
            success = True
            error_message = None
            if item["type"] == "role":
                role = interaction.guild.get_role(item["role_id"])
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        if item.get("time_limit"):
                            duration = parse_time_string(item["time_limit"])
                            # Store role removal time in database
                            removal_time = datetime.utcnow().timestamp() + duration
                            self.bot.db[str(interaction.guild.id)]["temp_roles"].insert_one({
                                "user_id": interaction.user.id,
                                "role_id": role.id,
                                "removal_time": removal_time
                            })
                            self.bot.loop.create_task(self.remove_role_after_duration(
                                interaction.user, role, duration
                            ))
                    except discord.HTTPException as e:
                        success = False
                        error_message = str(e)
                        log_embed.add_field(name="Error", value=f"Failed to assign role: {e}", inline=False)

            # Log transaction
            transaction = {
                "order_id": order_id,
                "user_id": interaction.user.id,
                "item_code": item["code"],
                "item_name": item["name"],
                "price": item["price"],
                "old_balance": old_balance,
                "new_balance": old_balance - item["price"],
                "type": item["type"]
            }
            if item["type"] == "role":
                transaction["role_id"] = item["role_id"]
                transaction["duration"] = item.get("time_limit")
                
            await self.log_transaction(interaction.guild.id, transaction)

            # Update shop message
            await self.save_shop_data(interaction.guild.id, shop_data)
            shop_message = await interaction.channel.fetch_message(shop_data["message_id"])
            embeds = await self.create_shop_embed(interaction.guild.id)
            await shop_message.edit(embeds=embeds, view=ShopView(shop_data, self))

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

            # Log purchase
            if shop_data.get("log_channel_id"):
                log_channel = interaction.guild.get_channel(shop_data["log_channel_id"])
                if log_channel:
                    await log_channel.send(embed=log_embed)

        except Exception as e:
            # Log error and notify user
            print(f"Error processing purchase: {e}")
            try:
                await interaction.followup.send(
                    "An error occurred while processing your purchase. Please contact an admin.",
                    ephemeral=True
                )
            except:
                pass

    async def remove_role_after_duration(self, member: discord.Member, role: discord.Role, duration: int):
        """Remove role after specified duration"""
        await asyncio.sleep(duration)
        if role in member.roles:
            try:
                await member.remove_roles(role)
            except discord.HTTPException:
                pass

    @commands.hybrid_group(name="shop")
    @commands.has_permissions(manage_guild=True)
    async def shop(self, ctx: commands.Context):
        """Shop management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @shop.command(name="additem")
    @app_commands.describe(
        name="Item name",
        price="Item price",
        stock="Initial stock",
        max_per_user="Maximum purchases per user (optional)"
    )
    async def additem(self, ctx: commands.Context, name: str, price: float, stock: int, max_per_user: Optional[int] = None):
        """
        Add a new item to the shop.

        **Usage:**
        ?shop additem <name> <price> <stock> [max_per_user]
        /shop additem <name> <price> <stock> [max_per_user]

        **Parameters:**
        name: The name of the item
        price: How much it costs
        stock: How many can be bought
        max_per_user (optional): Limit per user

        **Examples:**
        ?shop additem "VIP Pass" 100 50
        ?shop additem "Special Item" 25.5 100 2
        """
        shop_data = await self.get_shop_data(ctx.guild.id)
        
        item = {
            "type": "item",
            "code": generate_code(),
            "name": name,
            "price": price,
            "stock": stock,
            "max_per_user": max_per_user
        }
        
        shop_data["items"].append(item)
        await self.save_shop_data(ctx.guild.id, shop_data)
        
        if shop_data.get("channel_id"):
            channel = ctx.guild.get_channel(shop_data["channel_id"])
            if channel:
                message = await channel.fetch_message(shop_data["message_id"])
                embeds = await self.create_shop_embed(ctx.guild.id)
                await message.edit(embeds=embeds, view=ShopView(shop_data, self))
        
        await ctx.reply(f"Added item {name} to the shop!")

    @shop.command(name="addrole")
    @app_commands.describe(
        role="Role to add",
        price="Role price",
        stock="Initial stock",
        max_per_user="Maximum purchases per user (optional)",
        time_limit="Time limit for the role (e.g., 24h, 7d) (optional)"
    )
    async def addrole(
        self, ctx: commands.Context,
        role: discord.Role,
        price: float,
        stock: int,
        max_per_user: Optional[int] = None,
        time_limit: Optional[str] = None
    ):
        """
        Add a purchasable role to the shop.

        **Usage:**
        ?shop addrole <role> <price> <stock> [max_per_user] [time_limit]
        /shop addrole <role> <price> <stock> [max_per_user] [time_limit]

        **Parameters:**
        role: The role to sell
        price: How much it costs
        stock: How many can be bought
        max_per_user (optional): Limit per user
        time_limit (optional): How long the role lasts (e.g. 24h, 7d)

        **Examples:**
        ?shop addrole @VIP 100 50
        ?shop addrole @Special 25.5 100 2 24h
        """
        shop_data = await self.get_shop_data(ctx.guild.id)
        
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
        
        shop_data["items"].append(item)
        await self.save_shop_data(ctx.guild.id, shop_data)
        
        if shop_data.get("channel_id"):
            channel = ctx.guild.get_channel(shop_data["channel_id"])
            if channel:
                message = await channel.fetch_message(shop_data["message_id"])
                embeds = await self.create_shop_embed(ctx.guild.id)
                await message.edit(embeds=embeds, view=ShopView(shop_data, self))
        
        await ctx.reply(f"Added role {role.name} to the shop!")

    @shop.command(name="setchannel")
    @app_commands.describe(
        channel="Shop channel",
        log_channel="Purchase log channel (optional)"
    )
    async def setchannel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        log_channel: Optional[discord.TextChannel] = None
    ):
        """Set the shop channel and optional log channel"""
        shop_data = await self.get_shop_data(ctx.guild.id)
        
        shop_data["channel_id"] = channel.id
        shop_data["log_channel_id"] = log_channel.id if log_channel else None
        
        # Clear existing shop messages
        await channel.purge()
        
        # Create new shop message with all embeds
        embeds = await self.create_shop_embed(ctx.guild.id)
        message = await channel.send(embeds=embeds, view=ShopView(shop_data, self))
        shop_data["message_id"] = message.id
        
        await self.save_shop_data(ctx.guild.id, shop_data)
        await ctx.reply(f"Shop channel set to {channel.mention}!")

    @shop.command(name="removeitem")
    @app_commands.describe(code="Item code to remove")
    async def removeitem(self, ctx: commands.Context, code: str):
        """
        Remove an item from the shop.

        **Usage:**
        ?shop removeitem <code>
        /shop removeitem <code>

        **Parameters:**
        code: The unique code of the item to remove

        **Examples:**
        ?shop removeitem ABC123
        /shop removeitem XYZ789
        """
        shop_data = await self.get_shop_data(ctx.guild.id)
        
        shop_data["items"] = [item for item in shop_data["items"] if item["code"] != code]
        await self.save_shop_data(ctx.guild.id, shop_data)
        
        if shop_data.get("channel_id"):
            channel = ctx.guild.get_channel(shop_data["channel_id"])
            if channel:
                message = await channel.fetch_message(shop_data["message_id"])
                embeds = await self.create_shop_embed(ctx.guild.id)
                await message.edit(embeds=embeds, view=ShopView(shop_data, self))
        
        await ctx.reply(f"Removed item with code `{code}` from the shop!")
        
        
    @commands.hybrid_command(name="balance", description="Check your or another user's balance")
    @app_commands.describe(user="The user to check balance for (optional)")
    async def balance(self, ctx: commands.Context, user: Optional[discord.Member] = None) -> None:
        """
        Check your balance or another user's balance.

        **Usage:**
        ?balance [user]
        /balance [user]

        **Parameters:**
        user (optional): The user whose balance to check. Shows your own balance if not specified.

        **Examples:**
        ?balance
        ?balance @username
        /balance @username
        """
        user = user or ctx.author
        balance = await self.get_user_balance(ctx.guild.id, user.id)
        mgems = await self.get_user_mgems(user.id)
        
        if user == ctx.author:
            await ctx.reply(f"Your balance: `${balance:.2f}` | Mgems: {mgem}{mgems}")
        else:
            await ctx.reply(f"{user.name}'s balance: `${balance:.2f}`")

    @commands.hybrid_command(name="give", description="Give money to another user")
    @app_commands.describe(
        user="The user to give money to",
        amount="Amount to give"
    )
    async def give(self, ctx: commands.Context, user: discord.Member, amount: float) -> None:
        """
        Give some of your money to another user.

        **Usage:**
        ?give <user> <amount>
        /give <user> <amount>

        **Parameters:**
        user: The user to send money to
        amount: How much money to send (must be positive)

        **Examples:**
        ?give @username 100
        /give @username 50.5
        """
        if amount <= 0:
            await ctx.reply("Amount must be positive!")
            return
            
        if user == ctx.author:
            await ctx.reply("You can't give money to yourself!")
            return

        sender_balance = await self.get_user_balance(ctx.guild.id, ctx.author.id)
        if sender_balance < amount:
            await ctx.reply("You don't have enough money!")
            return

        # Transfer the money
        await self.update_user_balance(ctx.guild.id, ctx.author.id, -amount)
        await self.update_user_balance(ctx.guild.id, user.id, amount)

        await ctx.reply(f"✅ Successfully sent `${amount:.2f}` to {user.mention}!")
        
        
    @commands.hybrid_command(name="forbes", description="View detailed wealth statistics")
    async def forbes(self, ctx: commands.Context) -> None:
        """
        View detailed economic statistics and wealthiest members.

        **Usage:**
        ?forbes
        /forbes

        Displays:
        - Total money in circulation
        - Average user balance
        - Top 10 richest members
        - Economic distribution stats

        **Example:**
        ?forbes
        """
        # Get all users with balances
        all_users = list(self.bot.db[str(ctx.guild.id)]["economy"].find())
        
        # Calculate total money in circulation
        total_money = sum(user["balance"] for user in all_users)
        
        # Get users with >$5 for average calculation
        active_users = [user for user in all_users if user["balance"] >= 5]
        avg_balance = sum(user["balance"] for user in active_users) / len(active_users) if active_users else 0
        
        # Get top 10 richest
        rich_list = sorted(all_users, key=lambda x: x["balance"], reverse=True)[:10]
        top10_total = sum(user["balance"] for user in rich_list)
        
        embed = discord.Embed(
            title="🏦 Economic Report",
            color=discord.Color.gold()
        )
        
        # Global stats
        stats = (
            f"**Total Money**: ${total_money:.2f}\n"
            f"**Average Balance** ($5+): ${avg_balance:.2f}\n"
            f"**Top 10 Combined**: ${top10_total:.2f} ({(top10_total/total_money*100):.1f}% of total)\n"
            f"**Active Users** ($5+): {len(active_users)}"
        )
        embed.add_field(name="📊 Global Statistics", value=stats, inline=False)
        
        # Rich list
        rich_list_text = ""
        for i, data in enumerate(rich_list, 1):
            member = ctx.guild.get_member(data["user_id"])
            if member:
                percentage = (data["balance"] / total_money) * 100
                rich_list_text += f"**#{i}** {member.mention}: ${data['balance']:.2f} ({percentage:.1f}%)\n"
        
        embed.add_field(name="🏆 Wealthiest Members", value=rich_list_text or "No data", inline=False)
        
        # Add Mgem statistics
        all_gem_users = list(self.bot.db["userdata"]["gems"].find())
        total_mgems = sum(user.get("mgem", 0) for user in all_gem_users)
        
        # Get top 5 Mgem holders
        rich_gems = sorted(all_gem_users, key=lambda x: x.get("mgem", 0), reverse=True)[:5]
        
        gem_stats = f"**Total Mgems**: {mgem}{total_mgems}\n\n**Top Mgem Holders**:\n"
        for i, data in enumerate(rich_gems, 1):
            member = ctx.guild.get_member(data["userid"])
            if member and data.get("mgem", 0) > 0:
                gem_stats += f"**#{i}** {member.mention}: {mgem}{data['mgem']}\n"
        
        embed.add_field(name="💎 Mgem Statistics", value=gem_stats, inline=False)

        await ctx.reply(embed=embed)

    @commands.command(name="inflate")
    async def inflate(self, ctx: commands.Context, user: discord.Member, amount: float) -> None:
        """Add money to a user's balance (BOT OWNER ONLY)"""
        if ctx.author.id != 1076064221210628118: return

        if amount <= 0:
            await ctx.reply("Amount must be positive!")
            return

        await self.update_user_balance(ctx.guild.id, user.id, amount)
        await ctx.reply(f"Added ${amount:.2f} to {user.mention}'s balance!")

    @commands.hybrid_command(name="transactions")
    async def transactions(self, ctx: commands.Context) -> None:
        """
        View your complete transaction history.

        **Usage:**
        ?transactions
        /transactions

        Sends you a DM containing:
        - All your purchases
        - Order IDs
        - Prices paid
        - Balance changes
        - Timestamps

        **Example:**
        ?transactions
        """
        transactions = self.bot.db[str(ctx.guild.id)]["transactions"].find(
            {"user_id": ctx.author.id}
        ).sort("timestamp", -1)

        if not transactions:
            await ctx.reply("You haven't made any purchases yet!", ephemeral=True)
            return

        # Create transactions.txt
        content = "Your Transaction History\n" + "="*50 + "\n\n"
        
        for t in transactions:
            content += f"Order ID: {t['order_id']}\n"
            content += f"Date: {t['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            content += f"Item: {t['item_name']} [{t['item_code']}]\n"
            content += f"Price: ${t['price']:.2f}\n"
            content += f"Balance Before: ${t['old_balance']:.2f}\n"
            content += f"Balance After: ${t['new_balance']:.2f}\n"
            if t['type'] == 'role':
                role = ctx.guild.get_role(t['role_id'])
                content += f"Role: {role.mention if role else 'Deleted Role'}\n"
                content += f"Duration: {t.get('duration', 'Permanent')}\n"
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

    @shop.group(name="balance")
    @commands.has_permissions(manage_guild=True)
    async def shop_balance(self, ctx: commands.Context) -> None:
        """
        Shop balance management commands.

        **Usage:**
        ?shop balance <subcommand>
        /shop balance <subcommand>

        **Subcommands:**
        check - View total money collected by shop
        give - Give shop funds to a user

        **Examples:**
        ?shop balance check
        /shop balance give @user 100
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @shop_balance.command(name="check")
    @commands.has_permissions(administrator=True)
    async def balance_check(self, ctx: commands.Context) -> None:
        """
        Check total money collected from shop sales.

        **Usage:**
        ?shop balance check
        /shop balance check

        Shows:
        - Total money earned by shop
        - All time sales revenue

        **Example:**
        ?shop balance check
        """
        stats = self.bot.db[str(ctx.guild.id)]["shop_stats"].find_one({"_id": "balance"})
        total = stats.get("total", 0) if stats else 0
        
        embed = discord.Embed(
            title="Shop Balance",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Total Collected",
            value=f"${total:.2f}"
        )
        await ctx.reply(embed=embed)

    @shop_balance.command(name="give")
    @commands.has_permissions(administrator=True)
    async def balance_give(self, ctx: commands.Context, user: discord.Member, amount: float) -> None:
        """
        Give money from shop balance to a user.

        **Usage:**
        ?shop balance give <user> <amount>
        /shop balance give <user> <amount>

        **Parameters:**
        user: The user to receive the money
        amount: How much to give from shop funds

        **Examples:**
        ?shop balance give @username 100
        /shop balance give @username 50.5
        """
        if amount <= 0:
            await ctx.reply("Amount must be positive!")
            return

        stats = self.bot.db[str(ctx.guild.id)]["shop_stats"].find_one({"_id": "balance"})
        total = stats.get("total", 0) if stats else 0

        if amount > total:
            await ctx.reply("Not enough money in shop balance!")
            return

        # Update shop balance and user balance
        self.bot.db[str(ctx.guild.id)]["shop_stats"].update_one(
            {"_id": "balance"},
            {"$inc": {"total": -amount}}
        )
        await self.update_user_balance(ctx.guild.id, user.id, amount)

        await ctx.reply(f"Given ${amount:.2f} to {user.mention} from shop balance!")

    @commands.hybrid_command(name="daily", description="Claim your daily reward")
    async def daily(self, ctx: commands.Context) -> None:
        """
        Claim your daily reward (2$-5$). Can be claimed once every 24 hours.

        **Usage:**
        ?daily
        /daily

        **Example:**
        ?daily
        """
        user_id = ctx.author.id
        current_time = time.time()

        # Check cooldown
        if user_id in self.daily_cooldowns:
            last_claim = self.daily_cooldowns[user_id]
            time_elapsed = current_time - last_claim
            if time_elapsed < 86400:  # 24 hours in seconds
                time_left = 86400 - time_elapsed
                hours = int(time_left // 3600)
                minutes = int((time_left % 3600) // 60)
                await ctx.reply(f"You can claim your daily reward again in `{hours}h {minutes}m`")
                return

        # Generate random reward between $2 and $5
        reward = round(random.uniform(2, 5), 2)

        # Update user's balance
        await self.update_user_balance(ctx.guild.id, user_id, reward)

        # Update cooldown
        self.daily_cooldowns[user_id] = current_time
        self.bot.db[str(ctx.guild.id)]["daily_claims"].update_one(
            {"user_id": user_id},
            {"$set": {"last_claim": current_time}},
            upsert=True
        )

        # Get streak information (you can implement streak system later)
        await ctx.reply(
            f"✅ You claimed your daily reward of `${reward:.2f}`!\n"
            f"Your new balance: `${await self.get_user_balance(ctx.guild.id, user_id):.2f}`"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
