import discord
from discord.ext import commands
from discord import app_commands
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
from utils import PaginationView
from datetime import datetime, timezone

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
    colors = {
        'SS': (215, 0, 64),  # red
        'S': (255, 215, 0),     # Gold
        'A': (93, 63, 211),       # Red
        'B': (8, 143, 143),       # Blue
        'C': (80, 200, 120),    # green
        'D': (169, 169, 169)          # gray
    }
    return colors.get(rarity, (255, 255, 255))

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
    
    async def save_card(self, user_id: int, waifu: dict, serial: str):
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
        await ctx.defer()  # Defer the response immediately
        
        # Validate and normalize rarity input
        if rarity:
            rarity = rarity.upper()
            if rarity not in self.available_rarities:
                await ctx.reply("Invalid rarity! Use A, B, or C")
                return

        # Check if user has enough money
        cost = self.rarity_costs[rarity]
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.reply("Economy system is not available!")
            return
            
        balance = await economy_cog.get_user_balance(ctx.guild.id, ctx.author.id)
        if balance < cost:
            await ctx.reply(f"You need ${cost} to roll for this rarity! (Balance: ${balance:.2f})")
            return
            
        # Get random waifu
        waifu, serial = await self.get_random_waifu(rarity)
        if not waifu:
            await ctx.reply("No waifus available for this rarity!")
            return
        
        # Add some suspense with delay
        await asyncio.sleep(2)
            
        # Create card image
        card_image = create_waifu_card(waifu, serial, ctx.author.name)
        
        # Deduct cost and save card to user's collection
        await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, -cost)
        await self.save_card(ctx.author.id, waifu, serial)
        
        # Create congratulations message based on rarity
        congrats_messages = {
            'SS': f"🎉🎉🎉 INCREDIBLE! {ctx.author.mention} just pulled an **SS-TIER** card! 🎉🎉🎉\n",
            'S': f"🎉🎉 AMAZING! {ctx.author.mention} pulled an **S-TIER** card! 🎉🎉\n",
            'A': f"🎉 Wow! {ctx.author.mention} got an **A-TIER** card! 🎉\n",
            'B': f"Nice! {ctx.author.mention} found a **B-TIER** card!\n",
            'C': f"{ctx.author.mention} drew a **C-TIER** card.\n",
            'D': f"{ctx.author.mention} got a **D-TIER** card.\n"
        }
        
        congrats = congrats_messages.get(waifu['rarity_tier'], '')
        message = f"{congrats}You rolled **{waifu['name']}** ({waifu['rarity_tier']}) for ${cost}!\nSerial: `{serial}`"
        
        # Send card
        file = discord.File(fp=card_image, filename=f"waifu_card_{serial}.png")
        await ctx.reply(message, file=file)

    @commands.hybrid_command(name="waifu", description="View waifu cards")
    @app_commands.describe(query="Rarity tier (SS/S/A/B/C/D) or card code")
    async def waifu(self, ctx: commands.Context, query: Optional[str] = None) -> None:
        """
        View waifu cards that have been collected.
        Usage: 
        ?waifu - Shows random card from all cards
        ?waifu <tier> - Shows random card from specified tier
        ?waifu <code> - Shows specific card by code
        """
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
            
            # Create embed with rarity color
            embed = discord.Embed(title="Waifu Card", color=embed_color)
            embed.add_field(name="Owner", value=owner_name, inline=True)
            embed.add_field(name="Rarity", value=card['rarity'], inline=True)
            embed.add_field(name="Serial", value=f"`{card['serial_number']}`", inline=True)

            # Save image to file-like object and set as embed image
            card_image.seek(0)
            file = discord.File(fp=card_image, filename="card.png")
            embed.set_image(url="attachment://card.png")
            
            await ctx.reply(file=file, embed=embed)\
                    
                    
        except Exception as e:
            print(f"Error in waifu command: {e}")
            await ctx.reply("An error occurred while fetching the card.")

    @commands.hybrid_command(name="waifulist")
    async def waifulist(self, ctx: commands.Context):
        """Shows list of all available waifus with number of cards in circulation"""
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
        
        # Build message lines
        lines = []
        current_rarity = None
        for (waifu_id, name, rarity, rank), serials in sorted_groups:
            if rarity != current_rarity:
                lines.append(f"**Tier {rarity}:**")
                current_rarity = rarity
            rank_str = f"**#{rank}** " if rank is not None else ""
            line = f"{rank_str}{name} [`{', '.join(serials)}`]"
            if len(serials) > 1:
                line += f" ({len(serials)})"
            lines.append(line)
        
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
        If arg is one of the tiers (e.g., SS), sells all unsold, unlocked cards of that tier.
        Otherwise, treats arg as a card code.
        """
        import asyncio
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            return await ctx.reply("Economy system is not available!")
        # Get user's cards
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
            for card in sell_cards:
                # Determine sale value (adjust as desired)
                if tier == "A":
                    sale_value = 150
                elif tier == "B":
                    sale_value = 30
                elif tier == "C":
                    sale_value = 10
                elif tier == "D":
                    sale_value = 2
                else:
                    sale_value = 10
                total += sale_value
                self.collection.delete_one({"_id": card["_id"]})
            await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, total)
            await ctx.reply(f"Sold {len(sell_cards)} cards from tier {tier} for ${total}.")
        else:
            # Sell a single card by card code
            card_code = arg
            card = self.collection.find_one({"owner_id": ctx.author.id, "serial_number": card_code})
            if not card:
                return await ctx.reply("Card not found or not owned by you.")
            if card.get("locked", False):
                return await ctx.reply("This card is locked and cannot be sold.")
            tier = card.get("rarity", "")
            if tier == "A":
                sale_value = 150
            elif tier == "B":
                sale_value = 50
            elif tier == "C":
                sale_value = 20
            elif tier == "D":
                sale_value = 5
            else:
                sale_value = 10
            self.collection.delete_one({"_id": card["_id"]})
            await economy_cog.update_user_balance(ctx.guild.id, ctx.author.id, sale_value)
            await ctx.reply(f"Sold card {card_code} for ${sale_value}.")

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
        target: Optional[discord.Member] = None
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
        target: Optional[discord.Member] = None
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

async def setup(bot):
    await bot.add_cog(Waifu(bot))
