import discord
from discord.ext import commands
from discord import app_commands
import math
import random
import time
import json
import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import string
from typing import Optional, List, Dict, Literal, Union
from pymongo import ReturnDocument
from utils import PaginationView, WaifuImagePagination
from datetime import datetime, timezone

RANK_COLORS = {
    # Default rarity colors
    'SS': (215, 0, 64),   # red
    'S': (255, 215, 0),   # Gold
    'A': (93, 63, 211),   # Purple
    'B': (8, 143, 143),   # Blue
    'C': (80, 200, 120),  # green
    'D': (169, 169, 169), # gray
    
    # Custom rank colors can be added here
    'SPECIAL': (255, 128, 0),  # Example: Orange for special rank
    'LIMITED': (255, 0, 255),  # Example: Pink for limited rank
    # Add more custom ranks and colors as needed
}

def generate_card_code(rarity: str) -> str:
    """Generate a unique card code based on rarity"""
    timestamp = hex(int(time.time()))[2:]  # Remove '0x' prefix
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{rarity}-{timestamp}-{random_chars}"

def load_waifu_data() -> Dict:
    """Load waifu data from json file"""
    with open("waifu_list_final.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_rarity_color(rarity: str) -> tuple:
    """Get color tuple for rarity"""
    return RANK_COLORS.get(rarity, (255, 255, 255))  # White as default

def get_rarity_percentage(rarity: str) -> float:
    """Get rarity percentage for display"""
    percentages = {
        'SS': 0.01,
        'S': 0.1,
        'A': 1,
        'B': 10, 
        'C': 30,
        'D': 58.98
         
    }
    return percentages.get(rarity, 0.0)

def get_tier_frame(tier: str) -> Image.Image:
    """Get frame overlay for card tier"""
    frame_paths = {
        'SS': 'assets/frames/ss_frame.png',
        'S': 'assets/frames/s_frame.png',
        'A': 'assets/frames/a_frame.png',
        'B': 'assets/frames/b_frame.png',
        'C': 'assets/frames/c_frame.png'
    }
    
    try:
        frame = Image.open(frame_paths.get(tier, frame_paths['C']))
        return frame.convert('RGBA')
    except:
        # Create default frame if file not found
        frame = Image.new('RGBA', (600, 960), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        
        # Get color from get_rarity_color and add alpha
        base_color = get_rarity_color(tier)
        color = (*base_color, 180)  # Add alpha value of 180
        
        # Draw border
        border_width = 10
        draw.rectangle([0, 0, 599, 959], outline=color, width=border_width)
        
        return frame

def load_font(font_path: str, size: int, default_size: int = None) -> ImageFont.FreeTypeFont:
    """Load a font with fallbacks"""
    try:
        # Try relative path first
        return ImageFont.truetype(f"fonts/{font_path}", size)
    except:
        try:
            # Try system path
            return ImageFont.truetype(font_path, size)
        except:
            try:
                # Try DejaVu as Linux fallback
                return ImageFont.truetype("DejaVuSans.ttf", size if default_size is None else default_size)
            except:
                # Last resort: default font
                return ImageFont.load_default()

def create_waifu_card(waifu_data: dict, card_code: str, owner_name: str) -> BytesIO:
    """Create a waifu card image"""
    # Download and open image
    response = requests.get(waifu_data['image_link'])
    img = Image.open(BytesIO(response.content))
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate dimensions for 10:16 ratio while maintaining aspect ratio
    target_width = 600
    target_height = 960
    
    # Calculate scaling factors
    width_ratio = target_width / img.width
    height_ratio = target_height / img.height
    
    # Use the larger ratio to ensure image fills the frame
    scale_factor = max(width_ratio, height_ratio)
    
    # Calculate new dimensions
    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)
    
    # Resize image
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Center crop
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    img = img.crop((left, top, left + target_width, top + target_height))
    
    # Create draw object
    draw = ImageDraw.Draw(img)
    
    # Initialize fonts with better fallback system
    name_font = load_font("arial.ttf", 56, 24)
    name_font_bold = load_font("arialbd.ttf", 56, 24)
    info_font = load_font("arial.ttf", 32, 16)
    owner_font = load_font("arial.ttf", 20, 12)
    rarity_font = load_font("arialbd.ttf", 120, 36)
    rank_font = load_font("arial.ttf", 48, 20)
    percent_font = load_font("arialbd.ttf", 42, 18)
    
    # Add gradient overlay (dark bottom to transparent top)
    gradient = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    
    
    start_y = target_height - 300  # Top of the gradient area
    for i in range(300):
        
        alpha = int((i / 300) * 255)
        y_pos = start_y + i
        gradient_draw.line([(0, y_pos), (target_width, y_pos)], fill=(0, 0, 0, alpha))
        
        
    img.paste(gradient, (0, 0), gradient)
    # Get rarity color
    rarity_color = get_rarity_color(waifu_data['rarity_tier'])
    
    # Draw large rarity tier at top right
    rarity_text = waifu_data['rarity_tier']
    rarity_bbox = draw.textbbox((0, 0), rarity_text, font=rarity_font)
    rarity_width = rarity_bbox[2] - rarity_bbox[0]
    
    # Draw rarity tier with outline
    rarity_pos = (target_width - rarity_width - 30, 20)
    for offset in [(2,2), (-2,-2), (2,-2), (-2,2)]:
        draw.text((rarity_pos[0]+offset[0], rarity_pos[1]+offset[1]), 
                 rarity_text, font=rarity_font, fill=(0, 0, 0))
    draw.text(rarity_pos, rarity_text, font=rarity_font, fill=rarity_color)

    # Draw character rank below tier
    rank = waifu_data.get('popularity_rank')  
    rank_text = f"#{rank}"
    rank_bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
    rank_width = rank_bbox[2] - rank_bbox[0]
    
    # Center rank under rarity tier
    rank_x = rarity_pos[0] + (rarity_width - rank_width) // 2
    rank_y = rarity_pos[1] + 130
    
    # Draw rank with shadow
    draw.text((rank_x+2, rank_y+2), rank_text, font=rank_font, fill=(0, 0, 0))
    draw.text((rank_x, rank_y), rank_text, font=rank_font, fill=(255, 255, 255))

    # # Draw rarity percentage at top left with improved styling
    # percentage = get_rarity_percentage(waifu_data['rarity_tier'])
    # percentage_text = f"{percentage:.2f}%"
    
    # # Position for percentage
    # percent_pos = (25, 25)
    
    # # Draw drop shadow for percentage
    # shadow_offset = 2
    # for dx, dy in [(1,1), (1,-1), (-1,1), (-1,-1)]:
    #     draw.text((percent_pos[0] + dx * shadow_offset, percent_pos[1] + dy * shadow_offset),
    #              percentage_text, font=percent_font, fill=(0, 0, 0))
    
    # # Draw main percentage text in rarity color
    # draw.text(percent_pos, percentage_text, font=percent_font, fill=rarity_color)

    # Draw character name at bottom
    name_text = waifu_data['name']
    name_position = (30, target_height - 140)
    
    # Draw outline
    for offset in [(2,2), (-2,-2), (2,-2), (-2,2)]:
        draw.text((name_position[0]+offset[0], name_position[1]+offset[1]), 
                 name_text, font=name_font_bold, fill=(0, 0, 0))
        
    draw.text(name_position, name_text, font=name_font_bold, fill=(255, 255, 255))
    
    # Draw card code and anime name at bottom
    from_text = f"{waifu_data.get('series', 'Unknown')}"
    draw.text((30, target_height - 80), from_text, font=info_font, fill=(255, 255, 255))
    
    owner_text = f"{owner_name}"
    owner_bbox = draw.textbbox((0, 0), owner_text, font=owner_font)
    owner_width = owner_bbox[2] - owner_bbox[0]
    draw.text((target_width - owner_width - 20, target_height - 45), 
              owner_text, font=owner_font, fill=(255, 255, 255))
    
    # Add tier frame
    frame = get_tier_frame(waifu_data['rarity_tier'])
    img.paste(frame, (0, 0), frame)
    
    # Save to BytesIO
    output = BytesIO()
    img.save(output, 'PNG')
    output.seek(0)
    return output

def calculate_card_value(rarity: str, popularity_rank: int) -> int:
    """Calculate card value based on rarity and popularity rank"""
    value_ranges = {
        'D': (1, 4),      # $1-4
        'C': (4, 15),     # $4-15
        'B': (15, 50),    # $15-50
        'A': (50, 200),   # $50-200
        'S': (400, 2000), # $400-2,000
        'SS': (2000, 6000)# $2,000-6,000
    }
    
    if rarity not in value_ranges:
        return 1
    
    min_value, max_value = value_ranges[rarity]
    
    if not popularity_rank:
        return min_value
        
    # Scale value based on popularity rank (lower rank = higher value)
    # Using log scale to smooth out the differences
    import math
    max_rank = 2500  # Approximate max rank in database
    rank_factor = 1 - (math.log(popularity_rank + 1) / math.log(max_rank + 1))
    value = min_value + (max_value - min_value) * rank_factor
    
    return round(value)

def calculate_resale_value(rarity: str, popularity_rank: int) -> int:
    """Calculate resale value based on rarity and rank"""
    # Define minimum resale values by tier
    min_values = {
        'SS': 1500,  # SS cards minimum $1500
        'S': 400,    # S cards minimum $400
        'A': 60,     # 60% of $100 draw cost
        'B': 18,     # 60% of $30 draw cost
        'C': 6,      # 60% of $10 draw cost
        'D': 1.8     # 60% of $3 draw cost
    }
    
    max_values = {
        'SS': 3000,  # SS cards up to $3000
        'S': 1000,   # S cards up to $1000
        'A': 90,     # 90% of $100
        'B': 27,     # 90% of $30
        'C': 9,      # 90% of $10
        'D': 2.7     # 90% of $3
    }
    
    min_value = min_values.get(rarity, 1.8)
    max_value = max_values.get(rarity, 2.7)
    
    if not popularity_rank:
        return round(min_value)
    
    # Scale between min and max based on rank
    max_rank = 2500
    rank_factor = 1 - (math.log(popularity_rank + 1) / math.log(max_rank + 1))
    value = min_value + (max_value - min_value) * rank_factor
    
    return round(value)

class Waifu(commands.Cog):
    """
    Waifu Card Collection System
    
    This cog implements a gacha-style card collection system with the following features:
    - Card rolling with different rarity tiers (SS, S, A, B, C, D)
    - Trading system between users
    - Card locking to prevent accidental sales
    - Inventory management
    
    Rarity Probabilities:
    Normal Roll ($3):
        SS: 0.01%, S: 0.1%, A: 1%, B: 10%, C: 30%, D: 58.89%
    
    Targeted Rolls:
        C-Tier ($10): SS: 0.04%, S: 0.4%, A: 4%, B: 40%, C: 55.56%
        B-Tier ($30): SS: 0.1%, S: 1%, A: 10%, B: 88.9%
        A-Tier ($100): SS: 1%, S: 10%, A: 89%
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.waifu_data = load_waifu_data()
        # Adjust cost mapping if desired:
        self.rarity_costs = {
            None: 3,   # normal roll costs $3
            'C': 10,   # roll for C costs $10
            'B': 30,   # roll for B costs $30
            'A': 100   # roll for A costs $100
        }
        # Available tiers for normal roll include all:
        self.available_rarities = ['SS','S','A','B','C','D']
        self.collection = self.bot.db["waifu"]["cards"]
        self.serial_collection = self.bot.db["waifu"]["serials"]
        self.active_draws = set()  # Track user IDs that are currently drawing a card

    def roll_rarity(self, cost_type: Optional[str] = None) -> str:
        """Returns a rarity string based on cost type using preset weights"""
        probabilities = {
            'normal': {
                'tiers': ['SS', 'S', 'A', 'B', 'C', 'D'],
                'weights': [0.01, 0.1, 1, 10, 30, 100]
            },
            'C': {
                'tiers': ['SS', 'S', 'A', 'B', 'C'],
                'weights': [0.04, 0.4, 4, 40, 100]
            },
            'B': {
                'tiers': ['SS', 'S', 'A', 'B'],
                'weights': [0.1, 1, 10, 100]
            },
            'A': {
                'tiers': ['SS', 'S', 'A'],
                'weights': [1, 10, 100]
            }
        }
        if cost_type is None:
            prob = probabilities['normal']
        else:
            cost_type = cost_type.upper()
            if cost_type in probabilities:
                prob = probabilities[cost_type]
            else:
                prob = probabilities['normal']
        return random.choices(prob['tiers'], weights=prob['weights'], k=1)[0]

    async def get_random_waifu(self, cost_type: Optional[str] = None) -> tuple[dict, str]:
        """Get a random waifu matching the rolled rarity from cost type probabilities"""
        rolled_rarity = self.roll_rarity(cost_type)
        available_waifus = [
            dict(wdata, id=wid) for wid, wdata in self.waifu_data.items()
            if wdata.get('rarity_tier') == rolled_rarity
        ]
        if not available_waifus:
            return None, None
        chosen_waifu = random.choice(available_waifus)
        serial = await self.get_next_serial(chosen_waifu['rarity_tier'])
        return chosen_waifu, serial

    async def get_next_serial(self, rarity: str) -> str:
        """Atomically retrieve and update the next card code for a given tier"""
        try:
            operation = self.serial_collection.find_one_and_update(
                {"_id": rarity},
                {"$inc": {"count": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            # Only await if the result is awaitable:
            if hasattr(operation, "__await__"):
                result = await operation
            else:
                result = operation
            return f"{rarity}-{result['count']:06d}"
        except Exception as e:
            print(f"Error generating serial: {e}")
            return f"{rarity}-000001"
    
    def save_card(self, user_id: int, waifu: dict, serial: str):
        """Save card to waifu collection"""
        try:
            self.collection.insert_one({
                "serial_number": serial,
                "owner_id": user_id,
                "waifu_id": waifu['id'],
                "name": waifu['name'],
                "rarity": waifu['rarity_tier'],
                "rank": waifu.get('popularity_rank'),
                "series": waifu.get('series', 'Unknown'),
                "obtained_at": time.time()
            })
        except Exception as e:
            print(f"Error saving card: {e}")

    @commands.hybrid_command(name="draw", aliases=["roll"], description="Roll for a random waifu card")
    @app_commands.describe(rarity="Minimum rarity tier to roll for (A/B/C)")
    async def draw(self, ctx: commands.Context, rarity: Optional[str] = None) -> None:
        """
        Waifu Card Collection System
        
        This cog implements a gacha-style card collection system with the following features:
        - Card rolling with different rarity tiers (SS, S, A, B, C, D)
        - Trading system between users
        - Card locking to prevent accidental sales
        - Inventory management
        
        Rarity Probabilities:
        Normal Roll ($3):
            SS: 0.01%, S: 0.1%, A: 1%, B: 10%, C: 30%, D: 58.89%
        
        Targeted Rolls:
            C-Tier ($10): SS: 0.04%, S: 0.4%, A: 4%, B: 40%, C: 55.56%
            B-Tier ($30): SS: 0.1%, S: 1%, A: 10%, B: 88.9%
            A-Tier ($100): SS: 1%, S: 10%, A: 89%
    
        Roll for a random waifu card. Optionally specify minimum rarity.
        Costs: A=100$, B=30$, C=10$
        Default roll (any rarity) costs $3
        """
        # Check if user is already drawing
        if ctx.author.id in self.active_draws:
            return await ctx.reply("You already have an active draw. Please try again after it finishes.")
        self.active_draws.add(ctx.author.id)
        
        # Instantly reply with a placeholder message
        placeholder = await ctx.reply("Drawing a card...")
        
        try:
            # Validate and normalize rarity input
            if rarity:
                rarity = rarity.upper()
                if rarity not in self.available_rarities:
                    await placeholder.edit(content="Invalid rarity! Use A, B, or C")
                    return

            # Check if user has enough money
            cost = self.rarity_costs[rarity]
            economy_cog = self.bot.get_cog('Economy')
            if not economy_cog:
                await placeholder.edit(content="Economy system is not available!")
                return
                
            balance = await economy_cog.get_user_balance(ctx.guild.id, ctx.author.id)
            if balance < cost:
                await placeholder.edit(content=f"You need ${cost} to roll for this rarity! (Balance: ${balance:.2f})")
                return
                
            # Get random waifu
            waifu, serial = await self.get_random_waifu(rarity)
            if not waifu:
                await placeholder.edit(content="No waifus available for this rarity!")
                return
            
            # Add some suspense with delay
            await asyncio.sleep(2)
                
            # Create card image
            card_image = await asyncio.to_thread(create_waifu_card, waifu, serial, ctx.author.name)
            
            # Deduct cost and save card to user's collection
            await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, -cost)
            await asyncio.to_thread(self.save_card, ctx.author.id, waifu, serial)
            
            # Create congratulations message based on rarity
            congrats_messages = {
                'SS': f"🎉🎉🎉 INCREDIBLE! {ctx.author.mention} just pulled an **SS-TIER** card! 🎉🎉🎉\n",
                'S': f"🎉🎉 AMAZING! {ctx.author.mention} pulled an **S-TIER** card! 🎉🎉\n",
                'A': f"🎉 Wow! {ctx.author.mention} got an **A-TIER** card! 🎉\n",
                'B': f"Nice! {ctx.author.mention} found a **B-TIER** card!\n",
                'C': f"{ctx.author.mention} drew a **C-TIER** card.\n",
                'D': f"{ctx.author.mention} got a **D-TIER** card.\n"
            }
            
            # Calculate card value
            card_value = calculate_card_value(waifu['rarity_tier'], waifu.get('popularity_rank'))
            
            congrats = congrats_messages.get(waifu['rarity_tier'], '')
            message = (
                f"{congrats}You rolled **{waifu['name']}** ({waifu['rarity_tier']}) for ${cost}!\n"
                f"Serial: `{serial}`\n"
                f"Card Value: **${card_value:,}**"
            )
            
            # Send card
            file = discord.File(fp=card_image, filename=f"waifu_card_{serial}.png")
            await placeholder.edit(content=message, attachments=[file])
        finally:
            self.active_draws.discard(ctx.author.id)

    @commands.hybrid_command(name="waifu", description="View waifu cards")
    @app_commands.describe(query="Rarity tier (SS/S/A/B/C/D) or card code")
    async def waifu(self, ctx: commands.Context, query: Optional[str] = None) -> None:
        """View waifu cards that have been collected."""
        try:
            if not query:
                # Get random card from all cards
                cursor = self.collection.aggregate([{"$sample": {"size": 1}}])
                card = cursor.to_list(length=1)
                if not card:
                    return await ctx.reply("No cards have been drawn yet!")
                card = card[0]
            
            elif query.upper() in self.available_rarities:
                # Get random card from specified tier
                cursor = self.collection.aggregate([
                    {"$match": {"rarity": query.upper()}},
                    {"$sample": {"size": 1}}
                ])
                card = cursor.to_list(length=1)
                if not card:
                    return await ctx.reply(f"No {query.upper()}-tier cards have been drawn yet!")
                card = card[0]
            
            else:
                # Try to find specific card by code
                card = self.collection.find_one({"serial_number": query})
                if not card:
                    return await ctx.reply("Card not found!")
            
            # Get original waifu data
            waifu_data = self.waifu_data.get(str(card['waifu_id']), {})
            waifu_data['rarity_tier'] = card['rarity']
            waifu_data['popularity_rank'] = card['rank']
            
            # Get owner name
            owner = await self.bot.fetch_user(card['owner_id'])
            owner_name = owner.name if owner else "Unknown"
            
            # Create card image
            card_image = create_waifu_card(waifu_data, card['serial_number'], owner_name)

            # Get rarity color for embed
            rarity_rgb = get_rarity_color(card['rarity'])
            embed_color = discord.Color.from_rgb(*rarity_rgb)
            
            # Create simplified embed
            embed = discord.Embed(color=embed_color)
            embed.add_field(name="Owner", value=owner_name, inline=True)
            embed.add_field(name="Serial", value=f"`{card['serial_number']}`", inline=True)
            value = calculate_card_value(card['rarity'], card['rank'])
            embed.add_field(name="Value", value=f"${value:,}", inline=True)
            
            # Send image and embed separately
            card_image.seek(0)
            file = discord.File(fp=card_image, filename="card.png")
            await ctx.reply(file=file, embed=embed) 
                    
        except Exception as e:
            print(f"Error in waifu command: {e}")
            await ctx.reply("An error occurred while fetching the card.")

    class WaifuImageView(discord.ui.View):
        def __init__(self, cards: list, author: discord.Member):
            super().__init__(timeout=300)
            self.cards = cards
            self.index = 0
            self.author = author
            self.message = None
            self.update_buttons()

        def update_buttons(self):
            self.previous_button.disabled = (self.index == 0)
            self.next_button.disabled = (self.index == len(self.cards) - 1)
            self.page_indicator.label = f"{self.index + 1}/{len(self.cards)}"

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.author:
                await interaction.response.send_message("This button is not for you", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="<", style=discord.ButtonStyle.gray)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.index -= 1
            self.update_buttons()
            card_data = self.cards[self.index]
            
            # Create new card image
            card_image = create_waifu_card(card_data["waifu_data"], 
                                        card_data["serial"], 
                                        card_data["owner"])
            
            # Update message with new image
            file = discord.File(fp=card_image, filename="card.png")
            await interaction.response.edit_message(attachments=[file], view=self)

        @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
        async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
            pass

        @discord.ui.button(label=">", style=discord.ButtonStyle.gray)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.index += 1
            self.update_buttons()
            card_data = self.cards[self.index]
            
            # Create new card image
            card_image = create_waifu_card(card_data["waifu_data"], 
                                        card_data["serial"], 
                                        card_data["owner"])
            
            # Update message with new image
            file = discord.File(fp=card_image, filename="card.png")
            await interaction.response.edit_message(attachments=[file], view=self)

    @commands.hybrid_command(name="waifulist")
    async def waifulist(self, ctx: commands.Context, query: str = None):
        """Shows list of all waifus or specific waifus"""
        if isinstance(query, discord.Member):
            # Show user's waifu collection
            cards = list(self.collection.find({"owner_id": query.id}))
            if not cards:
                return await ctx.reply(f"{query.display_name} has no waifu cards!")

            card_data_list = []
            for card in cards:
                waifu_data = self.waifu_data.get(str(card['waifu_id']), {})
                waifu_data['rarity_tier'] = card['rarity']
                waifu_data['popularity_rank'] = card['rank']
                
                # Create card image in memory
                card_image = create_waifu_card(waifu_data, card['serial_number'], query.name)
                
                card_data_list.append({
                    "image": card_image,  # Store the BytesIO object directly
                    "serial": card['serial_number'],
                    "owner": query.name
                })

            # Create and send first card with pagination
            view = WaifuImagePagination(card_data_list, ctx.author)
            first_card = card_data_list[0]["image"]
            file = discord.File(fp=first_card, filename="card.png")
            message = await ctx.reply(file=file, view=view)
            view.message = message
            return

        elif isinstance(query, str):
            # Search for specific waifu
            matches = []
            query_lower = query.lower()
            for wid, wdata in self.waifu_data.items():
                if query_lower in wdata['name'].lower():
                    wdata['id'] = wid
                    matches.append(wdata)

            if not matches:
                return await ctx.reply(f"No waifus found matching '{query}'")

            # Create demo card for first match
            waifu = matches[0]
            card_image = create_waifu_card(waifu, "DEMO-000000", "Demo Card")
            
            file = discord.File(fp=card_image, filename="card.png")
            await ctx.reply(f"Found {len(matches)} matches. Showing first match:", file=file)
            return

        # Default behavior - show all waifus list
        try:
            # Get all waifus and their counts from database
            pipeline = [
                {"$group": {
                    "_id": "$waifu_id",
                    "count": {"$sum": 1},
                    "name": {"$first": "$name"}
                }},
                {"$sort": {"name": 1}}
            ]
            
            waifu_counts = {
                str(doc["_id"]): (doc["name"], doc["count"]) 
                for doc in self.collection.aggregate(pipeline)
            }
            
            # Build lines for each waifu including those with 0 cards
            lines = []
            for waifu_id, waifu_data in self.waifu_data.items():
                name = waifu_data.get('name', 'Unknown')
                count = waifu_counts.get(waifu_id, (name, 0))[1]
                rank = waifu_data.get('popularity_rank', '?')
                lines.append(f"#{rank}. {name} ({count})")
            
            # Sort by rank (convert ? to infinity for sorting)
            lines.sort(key=lambda x: float('inf') if x.split('.')[0] == '#?' else int(x.split('.')[0][1:]))
            
            # Create paginated embeds
            pages = [lines[i:i+20] for i in range(0, len(lines), 20)]
            embeds = []
            
            for idx, page in enumerate(pages, start=1):
                embed = discord.Embed(
                    title="Waifu List",
                    description="\n".join(page),
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"Page {idx} of {len(pages)}")
                embeds.append(embed)
            
            view = PaginationView(embeds, ctx.author)
            await ctx.reply(embed=embeds[0], view=view, ephemeral=True)
            
        except Exception as e:
            print(f"Error in waifulist command: {e}")
            await ctx.reply("An error occurred while fetching the waifu list.", ephemeral=True)

    @commands.command(name="inventory")
    async def inventory(self, ctx: commands.Context, target: Optional[discord.Member] = None) -> None:
        """Display a user's waifu cards inventory."""
        member = target if target is not None else ctx.author
        import asyncio
        # Obtain all cards for the member (using to_thread to avoid blocking)
        cursor = self.collection.find({"owner_id": member.id})
        cards = await asyncio.to_thread(lambda: list(cursor))
        
        if not cards:
            return await ctx.reply(f"{member.display_name} does not have any waifu cards yet.")
        
        # Group cards by (waifu_id, name, rarity, rank)
        groups = {}
        for card in cards:
            key = (
                str(card.get("waifu_id", "")),
                str(card.get("name", "")),
                str(card.get("rarity", "")),
                card.get("rank")
            )
            groups.setdefault(key, []).append(str(card.get("serial_number", "")))
        
        # Define ordering based on rarity and rank
        rarity_order = {"SS": 1, "S": 2, "A": 3, "B": 4, "C": 5, "D": 6}
        sorted_groups = sorted(
            groups.items(),
            key=lambda item: (rarity_order.get(item[0][2], 99), item[0][3] if item[0][3] is not None else 999)
        )
        
        # Calculate total values
        tier_values = {tier: 0 for tier in self.available_rarities}
        total_value = 0
        
        # Build message lines
        lines = []
        current_rarity = None
        for (waifu_id, name, rarity, rank), serials in sorted_groups:
            if rarity != current_rarity:
                if current_rarity:  # Add tier total if not first tier
                    lines.append(f"**Tier {current_rarity} Total: ${tier_values[current_rarity]:,}**\n")
                lines.append(f"**Tier {rarity}:**")
                current_rarity = rarity

            # Get locked status and calculate values for each card
            locked_cards = []
            unlocked_cards = []
            tier_value = 0
            
            for serial in serials:
                card = self.collection.find_one({"serial_number": serial})
                card_value = calculate_card_value(rarity, rank)
                tier_value += card_value
                tier_values[rarity] += card_value
                total_value += card_value
                
                if card and card.get("locked", False):
                    locked_cards.append(f"{serial}(${card_value:,})")
                else:
                    unlocked_cards.append(f"{serial}(${card_value:,})")

            rank_str = f"**#{rank}** " if rank is not None else ""
            
            # Format cards with lock indicators and values
            cards_str = ""
            if unlocked_cards:
                cards_str += f"`{', '.join(unlocked_cards)}`"
            if locked_cards:
                if cards_str:
                    cards_str += " "
                cards_str += f"[`{', '.join(locked_cards)}`🔒]"

            line = f"{rank_str}{name} {cards_str}"
            if len(serials) > 1:
                line += f" ({len(serials)}) - Total: ${tier_value:,}"
            lines.append(line)
        
        # Add final tier total and grand total
        if current_rarity:
            lines.append(f"**Tier {current_rarity} Total: ${tier_values[current_rarity]:,}**\n")
        lines.append(f"**Total Inventory Value: ${total_value:,}**")
        
        # Paginate lines; 20 lines per embed
        pages = [lines[i:i+20] for i in range(0, len(lines), 20)]
        embeds = []
        for idx, page in enumerate(pages, start=1):
            embed = discord.Embed(
                title=f"{member.display_name}'s Inventory",
                description="\n".join(page),
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Page {idx} of {len(pages)}")
            embeds.append(embed)
        
        view = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=view)

    @commands.command(name="sell")
    async def sell(self, ctx: commands.Context, arg: str) -> None:
        """
        Sell a card by card code or sell all cards in a given tier.
        Resale values:
        - SS: $1500-$3000
        - S: $400-$1000
        - A: 60-90% of $100
        - B: 60-90% of $30
        - C: 60-90% of $10
        - D: 60-90% of $3
        Higher ranked cards (lower rank number) sell for better values.
        """
        import asyncio
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            return await ctx.reply("Economy system is not available!")
            
        # First check ownership regardless of sell type
        cards = await asyncio.to_thread(lambda: list(self.collection.find({"owner_id": ctx.author.id})))
        
        if not cards:
            return await ctx.reply("You don't have any cards to sell.")
            
        if arg.upper() in self.available_rarities:
            # Sell all cards of the given tier
            tier = arg.upper()
            sell_cards = [card for card in cards if card.get("rarity", "") == tier and not card.get("locked", False)]
            if not sell_cards:
                return await ctx.reply(f"No sellable cards found in tier {tier}.")
            
            total = 0
            details = []
            for card in sell_cards:
                original_value = calculate_card_value(tier, card.get("rank"))
                sale_value = calculate_resale_value(tier, card.get("rank"))
                percentage = (sale_value / original_value) * 100
                
                details.append(f"`{card['serial_number']}` - ${original_value:,} → ${sale_value:,} ({percentage:.1f}%)")
                total += sale_value
                self.collection.delete_one({"_id": card["_id"]})
            
            await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, total)
            
            # Create detailed embed for bulk sale
            embed = discord.Embed(
                title="Bulk Sale Complete",
                description=f"Sold {len(sell_cards)} cards from tier {tier}",
                color=discord.Color.green()
            )
            embed.add_field(name="Total Received", value=f"${total:,}", inline=False)
            
            # Split details into chunks if needed
            chunks = [details[i:i+10] for i in range(0, len(details), 10)]
            for i, chunk in enumerate(chunks):  # Changed from range(chunks) to enumerate(chunks)
                embed.add_field(
                    name=f"Sale Details {i+1}" if len(chunks) > 1 else "Sale Details",
                    value="\n".join(chunk),
                    inline=False
                )
            
            await ctx.reply(embed=embed)
            
        else:
            # Sell a single card
            card_code = arg
            card = self.collection.find_one({"owner_id": ctx.author.id, "serial_number": card_code})
            if not card:
                return await ctx.reply("Card not found or not owned by you.")
            if card.get("locked", False):
                return await ctx.reply("This card is locked and cannot be sold.")
                
            original_value = calculate_card_value(card.get("rarity", ""), card.get("rank"))
            sale_value = calculate_resale_value(card.get("rarity", ""), card.get("rank"))
            percentage = (sale_value / original_value) * 100
            
            self.collection.delete_one({"_id": card["_id"]})
            await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, sale_value)
            
            embed = discord.Embed(
                title="Sale Complete",
                description=f"Sold card `{card_code}`",
                color=discord.Color.green()
            )
            embed.add_field(name="Original Value", value=f"${original_value:,}", inline=True)
            embed.add_field(name="Sale Value", value=f"${sale_value:,}", inline=True)
            embed.add_field(name="Return Rate", value=f"{percentage:.1f}%", inline=True)
            
            await ctx.reply(embed=embed)

    @commands.command(name="lock")
    async def lock(self, ctx: commands.Context, card_code: str) -> None:
        """Lock a card so it cannot be sold."""
        result = self.collection.update_one(
            {"owner_id": ctx.author.id, "serial_number": card_code},
            {"$set": {"locked": True}}
        )
        if result.modified_count:
            await ctx.reply(f"Card {card_code} has been locked.")
        else:
            await ctx.reply("Card not found or already locked.")

    @commands.command(name="unlock")
    async def unlock(self, ctx: commands.Context, card_code: str) -> None:
        """Unlock a previously locked card."""
        result = self.collection.update_one(
            {"owner_id": ctx.author.id, "serial_number": card_code},
            {"$set": {"locked": False}}
        )
        if result.modified_count:
            await ctx.reply(f"Card {card_code} has been unlocked.")
        else:
            await ctx.reply("Card not found or already unlocked.")

    @commands.hybrid_group(name="trade")
    async def trade(self, ctx: commands.Context) -> None:
        """Trade commands for waifu card system"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @trade.command(name="create", description="Create a new trade offer")
    @app_commands.describe(
        target="User to trade with",
        your_card="Your card's serial number",
        their_card="Their card's serial number"
    )
    async def trade_create(
        self, 
        ctx: commands.Context, 
        target: discord.Member, 
        your_card: str, 
        their_card: str
    ) -> None:
        """
        Create a trade offer between two users
        
        Parameters:
        -----------
        target: The user to trade with
        your_card: Your card's serial number
        their_card: Their card's serial number
        """
        if target.bot or target == ctx.author:
            return await ctx.reply("Invalid trade target.")
            
        # Check for existing pending trades
        trade_collection = self.bot.db["waifu"]["trades"]
        existing_trade = trade_collection.find_one({
            "$or": [
                {"offerer": ctx.author.id, "status": "pending"},
                {"offeree": ctx.author.id, "status": "pending"}
            ]
        })
        
        if existing_trade:
            return await ctx.reply("You already have a pending trade. Cancel it first.")
            
        your_card_doc = self.collection.find_one({"owner_id": ctx.author.id, "serial_number": your_card})
        their_card_doc = self.collection.find_one({"owner_id": target.id, "serial_number": their_card})
        
        if not your_card_doc:
            return await ctx.reply("You don't own the offered card.")
        if not their_card_doc:
            return await ctx.reply("The target doesn't own the requested card.")
            
        if your_card_doc.get("locked"):
            return await ctx.reply("Your card is locked and cannot be traded.")
        if their_card_doc.get("locked"):
            return await ctx.reply("Their card is locked and cannot be traded.")
            
        trade_doc = {
            "offerer": ctx.author.id,
            "offeree": target.id,
            "offerer_card": your_card,
            "offeree_card": their_card,
            "status": "pending",
            "timestamp": datetime.now(timezone.utc),
            "guild_id": ctx.guild.id
        }
        
        trade_collection.insert_one(trade_doc)
        
        embed = discord.Embed(
            title="Trade Offer",
            description=(
                f"**From:** {ctx.author.mention}\n"
                f"**To:** {target.mention}\n\n"
                f"Offering: {your_card_doc['name']} [`{your_card}`]\n"
                f"Requesting: {their_card_doc['name']} [`{their_card}`]"
            ),
            color=discord.Color.blue()
        )
        
        await ctx.reply(
            f"{target.mention}, you have received a trade offer!",
            embed=embed
        )

    @trade.command(name="accept", description="Accept a pending trade offer")
    @app_commands.describe(target="User who sent you the trade offer")
    async def trade_accept(
        self, 
        ctx: commands.Context,
        target: Union[discord.Member, None] = None
    ) -> None:
        """
        Accept a pending trade offer
        
        Parameters:
        -----------
        target: Optional user who sent the trade (required if you have multiple pending trades)
        """
        trade_collection = self.bot.db["waifu"]["trades"]
        query = {"offeree": ctx.author.id, "status": "pending"}
        
        if target:
            query["offerer"] = target.id
            
        trade = trade_collection.find_one(query)
        
        if not trade:
            return await ctx.reply("No pending trade offers found.")
            
        offerer_card = self.collection.find_one({
            "owner_id": trade["offerer"],
            "serial_number": trade["offerer_card"]
        })
        offeree_card = self.collection.find_one({
            "owner_id": ctx.author.id,
            "serial_number": trade["offeree_card"]
        })
        
        if not offerer_card or not offeree_card:
            trade_collection.update_one(
                {"_id": trade["_id"]},
                {"$set": {"status": "cancelled"}}
            )
            return await ctx.reply("Trade cancelled: One or both cards are no longer available.")
            
        # Execute trade
        self.collection.update_one(
            {"_id": offerer_card["_id"]},
            {"$set": {"owner_id": ctx.author.id}}
        )
        self.collection.update_one(
            {"_id": offeree_card["_id"]},
            {"$set": {"owner_id": trade["offerer"]}}
        )
        
        trade_collection.update_one(
            {"_id": trade["_id"]},
            {"$set": {"status": "completed"}}
        )
        
        embed = discord.Embed(
            title="Trade Completed",
            description=(
                f"**{ctx.author.name}** received: {offerer_card['name']} [`{trade['offerer_card']}`]\n"
                f"**{self.bot.get_user(trade['offerer']).name}** received: {offeree_card['name']} [`{trade['offeree_card']}`]"
            ),
            color=discord.Color.green()
        )
        
        await ctx.reply(embed=embed)

    @trade.command(name="decline", description="Decline a pending trade offer")
    @app_commands.describe(target="User who sent you the trade offer")
    async def trade_decline(
        self,
        ctx: commands.Context,
        target: Union[discord.Member, None] = None
    ) -> None:
        """
        Decline a pending trade offer
        
        Parameters:
        -----------
        target: Optional user who sent the trade (required if you have multiple pending trades)
        """
        trade_collection = self.bot.db["waifu"]["trades"]
        query = {"offeree": ctx.author.id, "status": "pending"}
        
        if target:
            query["offerer"] = target.id
            
        result = trade_collection.update_one(
            query,
            {"$set": {"status": "declined"}}
        )
        
        if result.modified_count:
            await ctx.reply("Trade offer declined.")
        else:
            await ctx.reply("No pending trade offers found.")

    @trade.command(name="list", description="List all pending trade offers")
    async def trade_list(self, ctx: commands.Context) -> None:
        """List all pending trades involving you"""
        trade_collection = self.bot.db["waifu"]["trades"]
        trades = list(trade_collection.find({
            "$or": [
                {"offerer": ctx.author.id, "status": "pending"},
                {"offeree": ctx.author.id, "status": "pending"}
            ]
        }))
        
        if not trades:
            return await ctx.reply("You have no pending trades.")
            
        embeds = []
        for trade in trades:
            offerer = self.bot.get_user(trade["offerer"])
            offeree = self.bot.get_user(trade["offeree"])
            
            offerer_card = self.collection.find_one({"serial_number": trade["offerer_card"]})
            offeree_card = self.collection.find_one({"serial_number": trade["offeree_card"]})
            
            if not all([offerer, offeree, offerer_card, offeree_card]):
                continue
                
            embed = discord.Embed(
                title=f"Trade Offer {'(Sent)' if trade['offerer'] == ctx.author.id else '(Received)'}",
                description=(
                    f"**From:** {offerer.mention}\n"
                    f"**To:** {offeree.mention}\n\n"
                    f"Offering: {offerer_card['name']} [`{trade['offerer_card']}`]\n"
                    f"Requesting: {offeree_card['name']} [`{trade['offeree_card']}`]"
                ),
                timestamp=trade.get("timestamp", datetime.now(timezone.utc)),
                color=discord.Color.blue()
            )
            embeds.append(embed)
        
        if not embeds:
            return await ctx.reply("No valid pending trades found.")
            
        view = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=view)

    @commands.command(name="gift")
    async def gift(self, ctx: commands.Context, target: discord.Member, card_code: str) -> None:
        """
        Gift a card to another user.
        Usage: /gift @user card_code
        """
        if target.bot or target == ctx.author:
            return await ctx.reply("Invalid gift target.")
        card = self.collection.find_one({"owner_id": ctx.author.id, "serial_number": card_code})
        if not card:
            return await ctx.reply("You do not own that card.")
        self.collection.update_one({"_id": card["_id"]}, {"$set": {"owner_id": target.id}})
        await ctx.reply(f"Card {card_code} has been gifted to {target.mention}.")

    @commands.command(name="waifulb", aliases=["waifu-lb", "waifu-leaderboard"])
    async def waifu_leaderboard(self, ctx: commands.Context):
        """Shows the top 5 users with highest value waifu collections"""
        # Get all cards and group by owner
        pipeline = [
            {"$match": {"owner_id": {"$exists": True}}},
            {"$group": {
                "_id": "$owner_id",
                "total_cards": {"$sum": 1},
                "cards_by_tier": {
                    "$push": "$rarity"
                }
            }}
        ]
        
        results = list(self.collection.aggregate(pipeline))
        
        # Calculate total value and tier counts for each user
        user_stats = []
        for result in results:
            owner_id = result["_id"]
            tier_counts = {tier: result["cards_by_tier"].count(tier) for tier in self.available_rarities}
            
            # Calculate total value
            total_value = 0
            for card in self.collection.find({"owner_id": owner_id}):
                card_value = calculate_card_value(card.get("rarity", ""), card.get("rank"))
                total_value += card_value
                
            user_stats.append({
                "user_id": owner_id,
                "total_value": total_value,
                "tier_counts": tier_counts,
                "total_cards": result["total_cards"]
            })
        
        # Sort by total value and get top 5
        user_stats.sort(key=lambda x: x["total_value"], reverse=True)
        top_5 = user_stats[:5]
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Waifu Collection Leaderboard 🏆",
            color=discord.Color.gold()
        )
        
        for i, stats in enumerate(top_5, 1):
            user = self.bot.get_user(stats["user_id"])
            if not user:
                continue
                
            # Format tier counts
            tier_text = " | ".join(f"{tier}: {count}" for tier, count in stats["tier_counts"].items() if count > 0)
            
            embed.add_field(
                name=f"{i}. {user.name}",
                value=f"💰 Total Value: ${stats['total_value']:,}\n"
                      f"📊 Cards: {stats['total_cards']}\n"
                      f"📦 Tiers: {tier_text}",
                inline=False
            )
        
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Waifu(bot))

