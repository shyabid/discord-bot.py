import discord
from discord.ext import commands
from discord import app_commands
import math
import random
import time
import json
import os
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import requests
from PIL import ImageEnhance
from io import BytesIO
import string
from typing import Optional, List, Dict, Literal, Union, Tuple
from datetime import datetime, timezone
from functools import wraps
from utils import PaginationView, WaifuImagePagination

mgem = "<a:mgem:1344001728424579082>"

active_users = set()

MAX_CARDS = 100
RANK_COLORS = {
    'SS': (215, 0, 64),  
    'S': (255, 215, 0), 
    'A': (93, 63, 211), 
    'B': (8, 143, 143),  
    'C': (80, 200, 120),  
    'D': (169, 169, 169),
    
    'SPECIAL': (255, 128, 0), 
    'LIMITED': (255, 0, 255), 
}

UPGRADE_COSTS = {
    'D': 1,    
    'C': 2,   
    'B': 3,  
    'A': 4,  
    'S': 5,  
    'SS': 10 
}
def check_active_command():
    async def predicate(ctx):
        if ctx.author.id in active_users:
            await ctx.reply("Please wait until your previous command is finished.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

def track_command():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            try:
                active_users.add(ctx.author.id)
                return await func(self, ctx, *args, **kwargs)
            finally:
                active_users.discard(ctx.author.id)
        return wrapper
    return decorator


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

def get_level_enhanced_color(rarity: str, level: int) -> tuple:
    """Get color tuple for rarity, enhanced by level"""
    base_color = list(RANK_COLORS.get(rarity, (255, 255, 255)))
    
    # Enhance color saturation and brightness based on level
    if level == 1:
        return tuple(base_color)
    elif level == 2:
        # Make the color slightly richer for level 2
        return tuple([min(int(c * 1.2), 255) for c in base_color])
    elif level >= 3:
        # Make the color much richer for level 3+
        return tuple([min(int(c * 1.5), 255) for c in base_color])

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

    # Create default frame if file not found
    frame = Image.new('RGBA', (600, 960), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    # Get color from get_rarity_color and add alpha
    base_color = get_rarity_color(tier)
    color = (*base_color, 300)  # Add alpha value of 180
    
    # Draw border
    border_width = 10
    draw.rectangle([0, 0, 599, 959], outline=color, width=border_width)
    
    return frame

def load_font(font_path: str, size: int, default_size: int = None) -> ImageFont.FreeTypeFont:
    """Load a font with fallbacks"""
    try:
        return ImageFont.truetype(f"fonts/{font_path}", size)
    except:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            try:
                # Try DejaVu as Linux fallback
                return ImageFont.truetype("DejaVuSans.ttf", size if default_size is None else default_size)
            except:
                return ImageFont.load_default()

def truncate_text(text, font, max_width):
    """Truncate text to fit within max_width, adding ... if needed"""
    if not text:
        return ""
    
    ellipsis = "..."
    ellipsis_width = font.getlength(ellipsis)
    
    # If already fits, no need to truncate
    if font.getlength(text) <= max_width:
        return text
    
    # Truncate character by character until it fits
    for i in range(len(text) - 1, 0, -1):
        truncated = text[:i] + ellipsis
        if font.getlength(truncated) <= max_width:
            return truncated
    
    # If even a single character doesn't fit
    return text[0] + ellipsis

def get_level_enhancements(level: int, rarity: str):
    """Get visual enhancements based on card level"""
    enhancements = {
        "glow_intensity": min(level * 0.15, 0.8),  # More glow with higher levels
        "star_count": level,  # Stars equal to level
        "corner_radius": min(20 + (level-1) * 5, 40),  # Rounder corners with higher levels
        "additional_effects": []
    }
    
    # Add special effects based on level
    if level >= 2:
        enhancements["additional_effects"].append("inner_glow")
    if level >= 3:
        enhancements["additional_effects"].append("sparkles")
    if level >= 5:
        enhancements["additional_effects"].append("holographic")
    
    return enhancements

def create_waifu_card(waifu_data: dict, card_code: str, owner_name: str, owner_avatar_url: str = None, level: int = 1) -> BytesIO:
    """Create a waifu card image"""
    # Download and open image
    response = requests.get(waifu_data['image_link'])
    img = Image.open(BytesIO(response.content))
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    target_width = 600
    target_height = 960
    
    width_ratio = target_width / img.width
    height_ratio = target_height / img.height
    
    scale_factor = max(width_ratio, height_ratio)
    
    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    img = img.crop((left, top, left + target_width, top + target_height))
    
    # Apply level-based enhancements
    if level > 1:
        # Enhance image based on level
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0 + (level * 0.02))  # Slight brightness increase
        
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.0 + (level * 0.03))  # Slight contrast increase

    draw = ImageDraw.Draw(img, 'RGBA')
    
    name_font = load_font("arial.ttf", 50, 24)
    name_font_bold = load_font("arialbd.ttf", 50, 24)
    info_font = load_font("arialbd.ttf", 32, 16)
    owner_font = load_font("arial.ttf", 30, 15)
    rarity_font = load_font("arialbd.ttf", 120, 36)
    level_font = load_font("arialbd.ttf", 48, 38)
    rank_font = load_font("arial.ttf", 40, 14)
    code_font = load_font("arial.ttf", 18, 12)
    
    
    # Add gradient overlay (dark bottom to transparent top)
    gradient = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)

    
    # Get rarity color for effects
    rarity_color = get_rarity_color(waifu_data['rarity_tier'])
    
    # Add gradient overlay (dark bottom to transparent top) - standard for all levels
    gradient = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    # Apply level-based effects to gradient based on rarity color
    start_y = target_height - 400  
    for i in range(400):
        alpha = int((i / 400) * (100 + level * 5))  # Increase intensity with level
        y_pos = start_y + i
        gradient_draw.line([(0, y_pos), (target_width, y_pos)], fill=(0, 0, 0, alpha))
    
    # Add level-based special effects
    if level >= 2:
        # Add a subtle glow around the borders
        glow_intensity = min(0.3 * level, 1)  # Max 80% at level 4+
        glow_color = tuple([int(c * (1 + glow_intensity)) for c in rarity_color])
        for i in range(1, 10 + level * 2):
            thickness = 2 if i < 5 else 1
            alpha = max(0, int(255 * (1 - (i / (10 + level * 2)))))
            gradient_draw.rectangle(
                [i, i, target_width - i, target_height - i], 
                outline=(*glow_color, alpha), 
                width=thickness
            )
    
    if level >= 4:
        # Add subtle patterns based on rarity tier
        pattern_alpha = 15 + level * 10  # Increases with level
        pattern_spacing = 30 - level * 2  # Decreases with level
        
        # if waifu_data['rarity_tier'] in ['SS', 'S']:
        #     # Diamond pattern for high tiers
        #     for x in range(0, target_width, pattern_spacing):
        #         for y in range(0, target_height, pattern_spacing):
        #             diamond_size = 5 + level
        #             points = [
        #                 (x, y - diamond_size),
        #                 (x + diamond_size, y),
        #                 (x, y + diamond_size),
        #                 (x - diamond_size, y)
        #             ]
        #             if all(0 <= px < target_width and 0 <= py < target_height for px, py in points):
        #                 gradient_draw.polygon(points, fill=(*rarity_color, pattern_alpha))
        
        # elif waifu_data['rarity_tier'] in ['A', 'B']:
        #     # Circle pattern for mid tiers
        #     for x in range(0, target_width, pattern_spacing):
        #         for y in range(0, target_height, pattern_spacing):
        #             circle_radius = 3 + level
        #             if 0 <= x < target_width and 0 <= y < target_height:
        #                 gradient_draw.ellipse(
        #                     [x - circle_radius, y - circle_radius, 
        #                      x + circle_radius, y + circle_radius],
        #                     fill=(*rarity_color, pattern_alpha)
        #                 )
        
        # else:  # C, D tiers
            # Simple dot pattern
        for x in range(0, target_width, pattern_spacing):
            for y in range(0, target_height, pattern_spacing):
                dot_radius = 2 + level // 2
                if 0 <= x < target_width and 0 <= y < target_height:
                    gradient_draw.ellipse(
                        [x - dot_radius, y - dot_radius, 
                            x + dot_radius, y + dot_radius],
                        fill=(*rarity_color, pattern_alpha)
                    )

    if level == 5:
        # Maximum level special effects
        
        # Add animated-looking light rays emanating from center (simulated in static image)
        center_x, center_y = target_width // 2, target_height // 2
        ray_count = 12
        ray_length = min(target_width, target_height) * 0.6
        ray_width = 15
        ray_alpha = 100
        
        for i in range(ray_count):
            angle = (i / ray_count) * 2 * math.pi
            end_x = center_x + int(math.cos(angle) * ray_length)
            end_y = center_y + int(math.sin(angle) * ray_length)
            
            # Draw a line with color based on rarity
            for w in range(-ray_width//2, ray_width//2):
                # Calculate perpendicular offset
                wx = int(-math.sin(angle) * w)
                wy = int(math.cos(angle) * w)
                
                # Draw ray with fading alpha
                for t in range(10, 100, 10):
                    lerp = t / 100
                    x = int(center_x + (end_x - center_x) * lerp) + wx
                    y = int(center_y + (end_y - center_y) * lerp) + wy
                    
                    if 0 <= x < target_width and 0 <= y < target_height:
                        fade_alpha = int(ray_alpha * (1 - lerp))
                        gradient_draw.point([x, y], fill=(*rarity_color, fade_alpha))
    
    img.paste(gradient, (0, 0), gradient)
    
    # Get rarity color and draw large rarity tier at top right - standard for all levels
    rarity_text = waifu_data['rarity_tier']
    rarity_bbox = draw.textbbox((0, 0), rarity_text, font=rarity_font)
    rarity_width = rarity_bbox[2] - rarity_bbox[0]
    rarity_pos = (target_width - rarity_width - 30, 20)
    
    # Draw rank number below rarity if it exists (standard for all levels)
    if waifu_data.get('popularity_rank'):
        rank_text = f"#{waifu_data['popularity_rank']}"
        rank_bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        rank_width = rank_bbox[2] - rank_bbox[0]
        # Center the rank below the rarity text
        rank_x = rarity_pos[0] + (rarity_width - rank_width) // 2
        rank_y = rarity_pos[1] + rarity_bbox[3] - rarity_bbox[1] + 10
        # Draw rank with outline for better visibility
        for offset in [(1,1), (-1,-1), (1,-1), (-1,1)]:
            draw.text((rank_x + offset[0], rank_y + offset[1] + 35), 
                     rank_text, font=rank_font, fill=(0, 0, 0))
        draw.text((rank_x, rank_y + 35), rank_text, font=rank_font, fill=(255, 255, 255))

    # Enhanced outline for rarity text based on level
    outline_strength = 2 + level // 2
    for offset in [(outline_strength,outline_strength), (-outline_strength,-outline_strength), 
                   (outline_strength,-outline_strength), (-outline_strength,outline_strength)]:
        draw.text((rarity_pos[0]+offset[0], rarity_pos[1]+offset[1]), 
                 rarity_text, font=rarity_font, fill=(0, 0, 0))
    
    # Add glow to rarity text based on level
    if level >= 2:
        glow_color = (*rarity_color, 150)
        for i in range(1, 3 + level):
            offset = i * 0.5
            for dx, dy in [(offset,0), (-offset,0), (0,offset), (0,-offset)]:
                draw.text((rarity_pos[0]+dx, rarity_pos[1]+dy), 
                         rarity_text, font=rarity_font, fill=(*rarity_color, 90 // i))
                         
    
    # Draw the main rarity text on top
    draw.text(rarity_pos, rarity_text, font=rarity_font, fill=rarity_color)
    
    # Draw level indicator at top left corner with enhanced styling based on level
    level_text = f"LEVEL {level}"
    level_bbox = draw.textbbox((0, 0), level_text, font=level_font)
    level_pos = (40, 35)
    
    # Add background for level text with fixed size
    level_bg_padding = 10 
    level_bg_height = 50  
    level_bg_width = 220  
    
    # Fixed rectangle size
    level_bg_rect = [
        30, 
        30,
        30 + level_bg_width, 
        30 + level_bg_height + 12
    ]
    
    # Draw level background with rarity color
    bg_alpha = min(100 + level * 10, 150)  # Increases with level
    draw.rectangle(level_bg_rect, fill=(*rarity_color, bg_alpha))
    
    # Define fixed star positions based on the level rectangle
    star_size = 30
    star_spacing = 33
    star_y = level_bg_rect[3] + 10  # Fixed position below the level rectangle
    star_x_start = level_bg_rect[0] + ((level_bg_width + 20) - (star_spacing * level)) // 2
    # Add border to level background
    
    
    border_color = (*rarity_color, 200)
    border_width = level  # Thicker border for higher levels
    draw.rectangle(level_bg_rect, outline=border_color, width=border_width)
    
    # Draw level text with enhanced outline
    outline_size = 2
    for offset in [(outline_size,outline_size), (-outline_size,-outline_size), 
                  (outline_size,-outline_size), (-outline_size,outline_size)]:
        draw.text((level_pos[0]+offset[0], level_pos[1]+offset[1]), 
                 level_text, font=level_font, fill=(0, 0, 0))
    
    # Level text color gets brighter with level
    level_text_color = (255, 255, 255)
    if level >= 3:
        # Pulsating effect for higher levels (simulated in static image)
        for i in range(1, 3):
            alpha = 150 - i * 40
            offset = i * 1.5
            draw.text((level_pos[0], level_pos[1] - offset), 
                     level_text, font=level_font, fill=(*rarity_color, alpha))
    
    draw.text(level_pos, level_text, font=level_font, fill=level_text_color)
    
    # Add star indicators based on level
    star_size = 30
    star_spacing = 33
    star_y = level_pos[1] + level_bg_height + 30
    star_x_start = level_pos[0] + (level_bg_width - (star_spacing * level)) // 2
    
    # Draw stars
    for i in range(level):
        star_x = star_x_start + i * star_spacing
        
        # Calculate star points
        points = []
        for j in range(10):
            angle = math.pi/2 + j * math.pi/5
            radius = star_size/2 if j % 2 == 0 else star_size/4
            points.append((
                star_x + radius * math.cos(angle),
                star_y + radius * math.sin(angle)
            ))
        
        # Draw star outline
        draw.polygon(points, outline=(0, 0, 0, 200), fill=(*rarity_color, 220))
        
        # Add glow effect to stars
        star_img = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        star_draw = ImageDraw.Draw(star_img)
        star_draw.polygon(points, fill=(*rarity_color, 180))
        star_img = star_img.filter(ImageFilter.GaussianBlur(2 + level // 2))
        img.paste(star_img, (0, 0), star_img)
        
        # Redraw star over blur for sharper appearance
        draw.polygon(points, outline=(0, 0, 0, 200), fill=(*rarity_color, 220))

    
    
    # Draw character name at bottom
    name_text = waifu_data['name']
    name_position = (30, target_height - 140)
    
    # Use a consistent outline size (1) for character name
    name_outline_size = 1
    for offset in [(name_outline_size,name_outline_size), (-name_outline_size,-name_outline_size), 
                  (name_outline_size,-name_outline_size), (-name_outline_size,name_outline_size)]:
        draw.text((name_position[0]+offset[0], name_position[1]+offset[1]), 
                 name_text, font=name_font_bold, fill=(0, 0, 0))
    
    if level >= 3:
        name_glow_color = (*rarity_color, 120)
        name_img = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        name_draw = ImageDraw.Draw(name_img)
        name_draw.text(name_position, name_text, font=name_font_bold, fill=name_glow_color)
        name_img = name_img.filter(ImageFilter.GaussianBlur(3))
        img.paste(name_img, (0, 0), name_img)
    
    draw.text(name_position, name_text, font=name_font_bold, fill=(255, 255, 255))
    
    # Draw series name below character name with the same outline size as character name
    series_text = waifu_data.get('series', 'Unknown')
    series_position = (32, target_height - 80)
    
    # Use consistent outline size for series name (same as character name)
    series_outline_size = 1
    for offset in [(series_outline_size,series_outline_size), (-series_outline_size,-series_outline_size), 
                  (series_outline_size,-series_outline_size), (-series_outline_size,series_outline_size)]:
        draw.text((series_position[0]+offset[0], series_position[1]+offset[1]), 
                 series_text, font=info_font, fill=(0, 0, 0))
    
    draw.text(series_position, series_text, font=info_font, fill=(255, 255, 255))
    
    y_pos = target_height - 45
    
    # Draw owner name instead of card code at bottom right
    owner_display = f"{owner_name}"
    owner_bottom_position = (target_width - draw.textbbox((0, 0), owner_display, font=code_font)[2] - 30, y_pos)
    
    # Add black outline to owner name at bottom
    owner_outline_size = 1
    for offset in [(owner_outline_size,owner_outline_size), (-owner_outline_size,-owner_outline_size), 
                  (owner_outline_size,-owner_outline_size), (-owner_outline_size,owner_outline_size)]:
        draw.text((owner_bottom_position[0]+offset[0], owner_bottom_position[1]+offset[1]), 
                 owner_display, font=code_font, fill=(0, 0, 0))
    
    draw.text(owner_bottom_position, owner_display, font=code_font, fill=(255, 255, 255))
    
    # Get frame for card based on tier
    frame = get_tier_frame(waifu_data['rarity_tier'])
    
    # Enhance frame based on level
    if level >= 2:
        # Create an enhanced frame with rarity color glow
        enhanced_frame = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        enhanced_draw = ImageDraw.Draw(enhanced_frame)
        
        # Border width increases with level
        border_width = 10 + level * 2
        enhanced_draw.rectangle([0, 0, 599, 959], outline=(*rarity_color, 255), width=border_width)
        
        # Note: Corner triangle flourishes have been removed
        
        # Apply blur for glow effect
        enhanced_frame = enhanced_frame.filter(ImageFilter.GaussianBlur(2 + level))
        
        # Paste the enhanced frame
        img.paste(enhanced_frame, (0, 0), enhanced_frame)
        
        # Redraw sharp border on top
        img_draw = ImageDraw.Draw(img)
        img_draw.rectangle([0, 0, 599, 959], outline=(*rarity_color, 255), width=border_width//2)
    
    img = img.convert('RGBA')
    img.paste(frame, (0, 0), frame)
    
    # Add holographic effect for max level
    if level == 5:
        holo = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        holo_draw = ImageDraw.Draw(holo)
        
        # Create rainbow pattern
        for y in range(0, target_height, 4):
            # Create rainbow gradient based on y position
            hue = (y / target_height) * 360
            r, g, b = hsv_to_rgb(hue/360, 0.8, 1.0)
            holo_draw.line([(0, y), (target_width, y)], fill=(r, g, b, 25))
        
        # Apply light distortion pattern
        for i in range(20):
            x = random.randint(0, target_width)
            y = random.randint(0, target_height)
            size = random.randint(50, 200)
            holo_draw.ellipse(
                [x-size//2, y-size//2, x+size//2, y+size//2],
                fill=(255, 255, 255, 10)
            )
        
        img.paste(holo, (0, 0), holo)
    
    # Save to BytesIO
    output = BytesIO()
    img.save(output, 'PNG')
    output.seek(0)
    return output

# Add helper function for holographic effect
def hsv_to_rgb(h, s, v):
    """Convert HSV color to RGB color"""
    if s == 0.0:
        return (int(v * 255), int(v * 255), int(v * 255))
    
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    if i % 6 == 0:
        r, g, b = v, t, p
    elif i % 6 == 1:
        r, g, b = q, v, p
    elif i % 6 == 2:
        r, g, b = p, v, t
    elif i % 6 == 3:
        r, g, b = p, q, v
    elif i % 6 == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    
    return (int(r * 255), int(g * 255), int(b * 255))

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
        self.active_draws = set()  # Track user IDs that are currently drawing a card

    def roll_rarity(self, cost_type: Optional[str] = None) -> str:
        ...

    async def get_random_waifu(self, min_rarity: Optional[str] = None) -> Tuple[Dict, str]:
        """Get a random waifu and generate a serial number"""
        # Determine rarity based on probabilities
        if not min_rarity:
            roll = random.random() * 100
            if roll < 0.1:  # 0.1%
                rarity = "SS"
            elif roll < 1:  # 0.9%
                rarity = "S"
            elif roll < 5:  # 4%
                rarity = "A"
            elif roll < 15:  # 10%
                rarity = "B"
            elif roll < 35:  # 20%
                rarity = "C"
            else:  # 65%
                rarity = "D"
        else:
            rarity = min_rarity

        # Filter waifus by rarity
        available_waifus = [
            (wid, data) for wid, data in self.waifu_data.items()
            if data.get('rarity_tier', '') == rarity
        ]
        
        if not available_waifus:
            return None, None

        # Select random waifu
        waifu_id, waifu_data = random.choice(available_waifus)
        waifu_data['id'] = waifu_id
        
        # Generate serial number
        serial = self.bot.db.get_next_serial(rarity)
        
        return waifu_data, serial

    async def save_card(self, user_id: int, waifu: dict, serial: str) -> None:
        """Save a card to the database"""
        self.bot.db.save_waifu_card(user_id, waifu, serial)

    async def get_card_data(self, serial: str) -> Optional[Dict]:
        """Get card data with waifu details"""
        card = self.bot.db.get_card_by_serial(serial)
        if not card:
            return None
            
        waifu_data = self.waifu_data.get(str(card['waifu_id']), {})
        waifu_data['rarity_tier'] = card['rarity']
        waifu_data['popularity_rank'] = card['rank']
        return {**card, 'waifu_data': waifu_data}

    async def transfer_card(self, serial: str, from_id: int, to_id: int) -> bool:
        """Transfer card ownership"""
        card = self.bot.db.get_card_by_serial(serial)
        if not card or card['owner_id'] != from_id or card.get('locked'):
            return False
        return self.bot.db.update_card_owner(serial, to_id)

    async def delete_card(self, serial: str, owner_id: int) -> bool:
        """Delete a card (for selling)"""
        return self.bot.db.delete_card(serial, owner_id)

    async def create_trade(self, ctx: commands.Context, target: discord.Member, 
                          your_card: str, their_card: str) -> bool:
        """Create a trade offer"""
        # Verify card ownership and lock status
        your_card_data = self.bot.db.get_card_by_serial(your_card)
        their_card_data = self.bot.db.get_card_by_serial(their_card)
        
        if not your_card_data or not their_card_data:
            return False
            
        if (your_card_data['owner_id'] != ctx.author.id or 
            their_card_data['owner_id'] != target.id):
            return False
            
        if your_card_data.get('locked') or their_card_data.get('locked'):
            return False
            
        # Create the trade
        trade_id = self.bot.db.create_trade(
            ctx.author.id, target.id,
            your_card, their_card,
            ctx.guild.id
        )
        return trade_id is not None

    async def execute_trade(self, trade_id: int) -> bool:
        """Execute a pending trade"""
        # Get trade data
        trade = self.bot.db.get_pending_trades(trade_id)
        if not trade:
            return False
            
        # Transfer cards
        success1 = await self.transfer_card(
            trade['offerer_card'],
            trade['offerer_id'],
            trade['offeree_id']
        )
        success2 = await self.transfer_card(
            trade['offeree_card'],
            trade['offeree_id'],
            trade['offerer_id']
        )
        
        if success1 and success2:
            self.bot.db.update_trade_status(trade_id, 'completed')
            return True
            
        # If either transfer failed, try to revert
        if success1:
            await self.transfer_card(
                trade['offerer_card'],
                trade['offeree_id'],
                trade['offerer_id']
            )
        if success2:
            await self.transfer_card(
                trade['offeree_card'],
                trade['offerer_id'],
                trade['offeree_id']
            )
            
        self.bot.db.update_trade_status(trade_id, 'failed')
        return False

    @commands.hybrid_command(name="draw", aliases=["roll"], description="Roll for a random waifu card")
    @app_commands.describe(rarity="Minimum rarity tier to roll for (A/B/C)")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @check_active_command()
    @track_command()
    async def draw(self, ctx: commands.Context, rarity: Optional[str] = None) -> None:
        """
        Roll for a random waifu card. Optionally specify minimum rarity.
        Costs: A=100$, B=30$, C=10$
        Default roll (any rarity) costs $3
        """
        card_count = len(self.bot.db.get_user_cards(ctx.author.id))
        if card_count >= MAX_CARDS:
            return await ctx.reply(f"You have reached the maximum limit of {MAX_CARDS} cards! Please sell some cards first.")

        if ctx.author.id in self.active_draws:
            return await ctx.reply("You already have an active draw. Please try again after it finishes.")
        self.active_draws.add(ctx.author.id)
        
        placeholder = await ctx.reply("Drawing a card...")
        
        if rarity:
            rarity = rarity.upper()
            if rarity not in ['A', 'B', 'C']:
                await placeholder.edit(content="Invalid rarity! Use A, B, or C for targeted rolls.")
                self.active_draws.discard(ctx.author.id)
                return

        # Get cost for this roll
        cost = self.rarity_costs[rarity] if rarity else self.rarity_costs[None]
        
        # Check user balance
        balance = self.bot.db.get_user_balance(ctx.author.id)
        
        if balance < cost:
            await placeholder.edit(content=f"You need ${cost} to roll! (Balance: ${balance:.2f})")
            self.active_draws.discard(ctx.author.id)
            return
            
        # Get random waifu
        result = await self.get_random_waifu(rarity)
        if not result:
            await placeholder.edit(content="No waifus available for this rarity!")
            self.active_draws.discard(ctx.author.id)
            return
            
        waifu, serial = result
        
        # Update balance first
        self.bot.db.update_user_balance(ctx.author.id, -cost)
        
        # Save the card
        await self.save_card(ctx.author.id, waifu, serial)
        
        # Create card image
        card_image = await asyncio.to_thread(
            create_waifu_card,
            waifu,
            serial,
            ctx.author.display_name,
            ctx.author.display_avatar.url
        )
        value = calculate_card_value(waifu['rarity_tier'], waifu.get('popularity_rank'))
        
        if waifu['rarity_tier'] == 'SS':
            congratulation_text = f"🎉🎉🎉 HOLY SHIT! You drew a {waifu['rarity_tier']}-tier card! 🎉"
        elif waifu['rarity_tier'] == 'S':
            congratulation_text = f"🎉🎉 Amazing! You drew a {waifu['rarity_tier']}-tier card! 🎉"
        elif waifu['rarity_tier'] == 'A':
            congratulation_text = f"🎉 Woah! You drew a {waifu['rarity_tier']}-tier card! 🎉"
        else: 
            congratulation_text = f"You drew a {waifu['rarity_tier']}-tier card!"
            
        congratulation_text += f"\nValue: ${value:,} | Serial: `{serial}`"
        
        file = discord.File(fp=card_image, filename="card.png")
        await placeholder.edit(content=congratulation_text, attachments=[file])
        self.active_draws.discard(ctx.author.id)

    @commands.hybrid_command(name="waifu", description="View waifu cards")
    @app_commands.describe(query="Rarity tier (SS/S/A/B/C/D) or card code")
    @check_active_command()
    @track_command()
    async def waifu(self, ctx: commands.Context, query: Optional[str] = None) -> None:
        """View waifu cards that have been collected."""
        # Add placeholder message
        placeholder = await ctx.reply("Loading waifu card...")
        
        try:
            if not query:
                # Get random card from all cards
                cards = self.bot.db.execute_query(
                    "SELECT * FROM waifu_cards ORDER BY RANDOM() LIMIT 1",
                    fetch_all=True
                )
                if not cards:
                    return await placeholder.edit(content="No cards have been drawn yet!")
                card = cards[0]
            
            elif query.upper() in self.available_rarities:
                # Get random card from specified tier
                cards = self.bot.db.execute_query(
                    "SELECT * FROM waifu_cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1",
                    (query.upper(),),
                    fetch_all=True
                )
                if not cards:
                    return await placeholder.edit(content=f"No {query.upper()}-tier cards have been drawn yet!")
                card = cards[0]
            
            else:
                # Try to find specific card by code
                card = self.bot.db.get_card_by_serial(query)
                if not card:
                    return await placeholder.edit(content="Card not found!")
            
            # Get original waifu data
            waifu_data = self.waifu_data.get(str(card['waifu_id']), {})
            waifu_data['rarity_tier'] = card['rarity']
            waifu_data['popularity_rank'] = card['rank']
            
            # Get owner name - USE DISPLAY NAME INSTEAD OF USERNAME
            owner = await self.bot.fetch_user(card['owner_id'])
            owner_name = "Unknown"
            if owner:
                # Try to get display name from guild member
                if ctx.guild:
                    member = ctx.guild.get_member(owner.id)
                    if member:
                        owner_name = member.display_name
                    else:
                        owner_name = owner.display_name  # Fall back to global display name
                else:
                    owner_name = owner.display_name
            
            # Get card data
            level = card.get("level", 1)  # Get level, default to 1
        
            # Get owner avatar URL
            owner_avatar_url = owner.display_avatar.url if owner else None
            
            # Create card image with level and avatar
            card_image = await asyncio.to_thread(
                create_waifu_card,
                waifu_data, 
                card['serial_number'], 
                owner_name,
                owner_avatar_url,
                level
            )

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
            file = discord.File(fp=card_image, filename="card.png")
            await placeholder.edit(content=None, attachments=[file], embed=embed)
                    
        except Exception as e:
            print(f"Error in waifu command: {e}")
            await placeholder.edit(content="An error occurred while fetching the card.")

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
    @check_active_command()
    @track_command() 
    async def waifulist(self, ctx: commands.Context, query: Optional[discord.Member]= None):
        if isinstance(query, str):
            matches = []
            query_lower = query.lower()
            
            # Find closest match using substring comparison
            best_match = None
            best_ratio = 0
            
            for wid, wdata in self.waifu_data.items():
                name_lower = wdata['name'].lower()
                
                # Check if query is a substring of name
                if query_lower in name_lower:
                    ratio = len(query_lower) / len(name_lower)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        wdata['id'] = wid 
                        best_match = wdata

            if not best_match:
                return await ctx.reply(f"No waifus found matching '{query}'")

            # Create demo card for best match
            card_image = create_waifu_card(best_match, "DEMO-000000", "Demo Card")
            
            file = discord.File(fp=card_image, filename="card.png")
            await ctx.reply(f"Best match found:", attachments=[file])
            return

        try:
            # Get all waifus and their counts from database
            waifu_counts = self.bot.db.execute_query("""
                SELECT waifu_id, name, COUNT(*) as count 
                FROM waifu_cards 
                GROUP BY waifu_id, name
                ORDER BY name
            """, fetch_all=True)
            
            # Convert to dictionary for easier lookup
            waifu_counts = {
                str(row['waifu_id']): (row['name'], row['count']) 
                for row in waifu_counts
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
                    color=discord.Colour.dark_grey()
                )
                embed.set_footer(text=f"Page {idx} of {len(pages)}")
                embeds.append(embed)
            
            view = PaginationView(embeds, ctx.author)
            await ctx.reply(embed=embeds[0], view=view, ephemeral=True)
            
        except Exception as e:
            print(f"Error in waifulist command: {e}")
            await ctx.reply("An error occurred while fetching the waifu list.", ephemeral=True)

    @commands.command(name="inventory")
    @check_active_command()
    @track_command()
    async def inventory(self, ctx: commands.Context, target: Optional[discord.Member] = None) -> None:
        """Display a user's waifu cards inventory."""
        placeholder = await ctx.reply("Loading inventory...")
        
        member = target if target is not None else ctx.author

        stats = self.bot.db.get_card_stats(member.id)
        if not stats or stats['total_cards'] == 0:
            return await placeholder.edit(content=f"{member.display_name} does not have any waifu cards yet.")

        cards = self.bot.db.get_user_cards(member.id)
        
        groups = {}
        for card in cards:
            key = (
                str(card['waifu_id']),
                str(card['name']),
                str(card['rarity']),
                card['rank']
            )
            groups.setdefault(key, []).append(str(card['serial_number']))
        
        rarity_order = {"SS": 1, "S": 2, "A": 3, "B": 4, "C": 5, "D": 6}
        sorted_groups = sorted(
            groups.items(),
            key=lambda item: (rarity_order.get(item[0][2], 99), item[0][3] if item[0][3] is not None else 999)
        )
        
        # Calculate total values
        tier_values = {tier: 0 for tier in self.available_rarities}
        total_value = 0
        

        lines = [
            f"> Total Inventory Value: **${total_value:,}**",
            f"> Total Cards: `{stats['total_cards']}` [{stats['locked_cards']} locked]",
            f"> Average Level: `{stats['avg_level']:.1f}` [Max: {stats['max_level']}]",
            f"> Unique Rarities: `{stats['unique_rarities']}` [{stats['rarities']}]"
        ]

        if stats.get('first_card_date'):
            try:
                if isinstance(stats['first_card_date'], (int, float)):
                    timestamp = int(stats['first_card_date'])
                else:
                    dt = datetime.strptime(str(stats['first_card_date']), '%Y-%m-%d %H:%M:%S')
                    timestamp = int(dt.timestamp())
                lines.append(f"> Collecting Since: <t:{timestamp}:R>")
            except (ValueError, TypeError):
                pass
            
        lines.append("\n")
        
        current_rarity = None
        for (waifu_id, name, rarity, rank), serials in sorted_groups:
            if rarity != current_rarity:
                if current_rarity:
                    lines.append(f"Tier {current_rarity} Total: **${tier_values[current_rarity]:,}**\n")
                lines.append(f"`Tier {rarity}:`")
                current_rarity = rarity

            locked_cards = []
            unlocked_cards = []
            tier_value = 0
            
            for serial in serials:
                card = self.bot.db.get_card_by_serial(serial)
                card_value = calculate_card_value(rarity, card['rank'])
                tier_value += card_value
                tier_values[rarity] += card_value
                total_value += card_value
                
                if card and card.get('locked'):
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
            lines.append(f"Tier {current_rarity} Total: **${tier_values[current_rarity]:,}**\n")
        
        # Paginate lines; 20 lines per embed
        pages = [lines[i:i+20] for i in range(0, len(lines), 20)]
        embeds = []
        for idx, page in enumerate(pages, start=1):
            embed = discord.Embed(
                title=f"{member.display_name}'s Inventory",
                description="\n".join(page),
                color=discord.Colour.dark_grey()
            )
            embed.set_footer(text=f"Page {idx} of {len(pages)}")
            embeds.append(embed)
        
        view = PaginationView(embeds, ctx.author)
        await placeholder.edit(content=None, embed=embeds[0], view=view)
        
    @commands.command(name="sell")
    @check_active_command()
    @track_command()
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
        cards = self.bot.db.get_user_cards(ctx.author.id)
        if not cards: return await ctx.reply("You don't have any cards to sell.")
            
        if arg.upper() in self.available_rarities:
            tier = arg.upper()
            sell_cards = [card for card in cards if card["rarity"] == tier and not card.get("locked", False)]
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
                
                self.bot.db.delete_card(card['serial_number'], ctx.author.id)
            
            self.bot.db.update_user_balance(ctx.author.id, total)
            
            # Create paginated embeds
            embeds = []
            
            # First page - Overview
            overview = discord.Embed(
                title="Bulk Sale Complete",
                description=f"Sold {len(sell_cards)} cards from tier {tier}",
                color=discord.Colour.dark_grey()
            )
            overview.add_field(name="Total Received", value=f"${total:,}", inline=False)
            embeds.append(overview)
            
            # Subsequent pages - Card details (20 per page)
            for i in range(0, len(details), 20):
                page = discord.Embed(
                    title=f"Sale Details - Tier {tier}",
                    description="\n".join(details[i:i+20]),
                    color=discord.Colour.dark_grey()
                )
                embeds.append(page)
            
            view = PaginationView(embeds, ctx.author)
            await ctx.reply(embed=embeds[0], view=view)
            
        else:
            # Sell a single card
            card_code = arg
            card = self.bot.db.get_card_by_serial(card_code)
            if not card or card['owner_id'] != ctx.author.id:
                return await ctx.reply("Card not found or not owned by you.")
            if card.get("locked", False):
                return await ctx.reply("This card is locked and cannot be sold.")
                
            original_value = calculate_card_value(card["rarity"], card.get("rank"))
            sale_value = calculate_resale_value(card["rarity"], card.get("rank"))
            percentage = (sale_value / original_value) * 100
            
            if self.bot.db.delete_card(card_code, ctx.author.id):
                await self.bot.db.update_user_balance(ctx.author.id, sale_value)
                
                embed = discord.Embed(
                    title="Sale Complete",
                    description=f"Sold card `{card_code}`",
                    color=discord.Color.dark_grey()
                )
                embed.add_field(name="Original Value", value=f"${original_value:,}", inline=True)
                embed.add_field(name="Sale Value", value=f"${sale_value:,}", inline=True)
                embed.add_field(name="Return Rate", value=f"{percentage:.1f}%", inline=True)
                
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("Failed to sell the card. Please try again.")

    @commands.command(name="lock")
    @check_active_command()
    @track_command()
    async def lock(self, ctx: commands.Context, card_code: str) -> None:
        """Lock a card so it cannot be sold."""
        if self.bot.db.toggle_card_lock(card_code, ctx.author.id, True):
            await ctx.reply(f"Card {card_code} has been locked.")
        else:
            await ctx.reply("Card not found or already locked.")

    @commands.command(name="unlock")
    @check_active_command()
    @track_command()
    async def unlock(self, ctx: commands.Context, card_code: str) -> None:
        """Unlock a previously locked card."""
        if self.bot.db.toggle_card_lock(card_code, ctx.author.id, False):
            await ctx.reply(f"Card {card_code} has been unlocked.")
        else:
            await ctx.reply("Card not found or already unlocked.")

    @commands.command(name="upgrade")
    @check_active_command()
    @track_command()
    async def upgrade(self, ctx: commands.Context, serial: str) -> None:
        """
        Upgrade a card's level using Mgems.
        
        SS - Level 1→∞: Starts at 50 Mgems, increases 170% per level
        """
        # Add placeholder message
        placeholder = await ctx.reply("Processing upgrade...")
        
        # Get the card
        card = self.bot.db.get_card_by_serial(serial)
        if not card or card['owner_id'] != ctx.author.id:
            return await placeholder.edit(content="Card not found or you don't own it!")

        current_level = card.get('level', 1)
        current_rarity = card['rarity']

        if current_rarity == "SS":
            base_cost = UPGRADE_COSTS['SS']
            upgrade_cost = int(base_cost * (1.7 ** (current_level - 1)))
        else:
            if current_level >= 3:
                rarity_order = ["D", "C", "B", "A", "S", "SS"]
                current_index = rarity_order.index(current_rarity)
                if current_index >= len(rarity_order) - 1:
                    return await placeholder.edit(content="This card is already at maximum tier!")
                upgrade_cost = UPGRADE_COSTS[current_rarity]
            else:
                upgrade_cost = UPGRADE_COSTS[current_rarity]

        
        user_mgems = self.bot.db.get_user_mgems(ctx.author.id)
        if user_mgems < upgrade_cost:
            return await placeholder.edit(content=f"You need {upgrade_cost} {mgem} to upgrade this card! (You have {user_mgems})")

        success = False
        if current_level >= 3 and current_rarity != "SS":
            rarity_order = ["D", "C", "B", "A", "S", "SS"]
            current_index = rarity_order.index(current_rarity)
            new_rarity = rarity_order[current_index + 1]
            
            success = self.bot.db.update_card_rarity(serial, new_rarity)
            if success:
                card['rarity'] = new_rarity
                card['level'] = 1
        else:
            new_level = current_level + 1
            success = self.bot.db.update_card_level(serial, new_level)
            if success:
                card['level'] = new_level

        if not success:
            return await placeholder.edit(content="Failed to upgrade the card. Please try again.")

        self.bot.db.update_user_mgems(ctx.author.id, -upgrade_cost)

        # Get waifu data for card display
        waifu_data = self.waifu_data.get(str(card['waifu_id']), {})
        waifu_data['rarity_tier'] = card['rarity']
        waifu_data['popularity_rank'] = card['rank']
        
        # Get owner data for card display - USE DISPLAY NAME
        owner = await self.bot.fetch_user(card['owner_id'])
        owner_name = "Unknown"
        if owner:
            if ctx.guild:
                member = ctx.guild.get_member(owner.id)
                if member:
                    owner_name = member.display_name
                else:
                    owner_name = owner.display_name
            else:
                owner_name = owner.display_name
                
        owner_avatar_url = owner.display_avatar.url if owner else None

        # Create card image
        card_image = await asyncio.to_thread(
            create_waifu_card,
            waifu_data,
            card['serial_number'],
            owner_name,
            owner_avatar_url,
            card['level']
        )

        # Create response embed
        embed = discord.Embed(
            title="Card Upgraded! 🎉",
            color=discord.Color.dark_grey()
        )
        
        if current_level >= 3 and current_rarity != "SS":
            embed.description = f"Your {current_rarity}-tier card has been upgraded to {new_rarity}-tier!"
        else:
            embed.description = f"Card level increased to {card['level']}!"
            
        embed.add_field(name="Cost", value=f"{upgrade_cost} {mgem}", inline=True)
        embed.add_field(name="Remaining Mgems", value=f"{user_mgems - upgrade_cost} {mgem}", inline=True)

        if current_rarity == "SS":
            next_cost = int(upgrade_cost * 2.5)
            embed.add_field(name="Next Upgrade Cost", value=f"{next_cost} {mgem}", inline=True)

        file = discord.File(fp=card_image, filename="card.png")
        await placeholder.edit(content=None, embed=embed, attachments=[file])

    @commands.hybrid_group(name="trade")
    @check_active_command()
    @track_command()
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
    @check_active_command()
    @track_command()
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
        existing_trades = self.bot.db.get_pending_trades(ctx.author.id)
        if existing_trades:
            return await ctx.reply("You already have a pending trade. Cancel it first.")
            
        your_card_doc = self.bot.db.get_card_by_serial(your_card)
        their_card_doc = self.bot.db.get_card_by_serial(their_card)
        
        if not your_card_doc or your_card_doc['owner_id'] != ctx.author.id:
            return await ctx.reply("You don't own the offered card.")
        if not their_card_doc or their_card_doc['owner_id'] != target.id:
            return await ctx.reply("The target doesn't own the requested card.")
            
        if your_card_doc.get("locked"):
            return await ctx.reply("Your card is locked and cannot be traded.")
        if their_card_doc.get("locked"):
            return await ctx.reply("Their card is locked and cannot be traded.")
            
        # Create trade
        trade_id = self.bot.db.create_trade(
            ctx.author.id,
            target.id,
            your_card,
            their_card,
            ctx.guild.id
        )
        
        if not trade_id:
            return await ctx.reply("Failed to create trade. Please try again.")
        
        embed = discord.Embed(
            title="Trade Offer",
            description=(
                f"**From:** {ctx.author.mention}\n"
                f"**To:** {target.mention}\n\n"
                f"Offering: {your_card_doc['name']} [`{your_card}`]\n"
                f"Requesting: {their_card_doc['name']} [`{their_card}`]"
            ),
            color=discord.Color.dark_grey()
        )
        
        await ctx.reply(
            f"{target.mention}, you have received a trade offer!",
            embed=embed
        )

    @trade.command(name="accept")
    @check_active_command()
    @track_command()
    async def trade_accept(self, ctx: commands.Context, target: Union[discord.Member, None] = None) -> None:
        """Accept a pending trade offer"""
        placeholder = await ctx.reply("Processing trade...")
        
        # Get pending trades
        trades = self.bot.db.get_pending_trades_for_user(ctx.author.id, target.id if target else None)
        
        if not trades:
            return await placeholder.edit(content="No pending trade offers found.")
            
        trade = trades[0]  # Get first pending trade
        
        # Process the trade
        if self.bot.db.process_trade(trade['trade_id'], 'completed'):
            embed = discord.Embed(
                title="Trade Completed",
                description=(
                    f"**{ctx.author.name}** received: {trade['offerer_card_name']} [`{trade['offerer_card']}`]\n"
                    f"**{self.bot.get_user(trade['offerer_id']).name}** received: {trade['offeree_card_name']} [`{trade['offeree_card']}`]"
                ),
                color=discord.Color.dark_grey()
            )
            await placeholder.edit(content=None, embed=embed)
        else:
            await placeholder.edit(content="Failed to process trade. One or both cards may no longer be available.")

    @trade.command(name="decline", description="Decline a pending trade offer")
    @check_active_command()
    @track_command()
    async def trade_decline(self, ctx: commands.Context, target: Union[discord.Member, None] = None) -> None:
        trades = self.bot.db.get_pending_trades_for_user(ctx.author.id, target.id if target else None)
        
        if not trades:
            await ctx.reply("No pending trade offers found.")
            return
            
        if self.bot.db.process_trade(trades[0]['trade_id'], 'declined'):
            await ctx.reply("Trade offer declined.")
        else:
            await ctx.reply("Failed to decline trade.")

    @trade.command(name="list")
    @check_active_command()
    @track_command()
    async def trade_list(self, ctx: commands.Context) -> None:
        """List all pending trades involving you"""
        trades = self.bot.db.get_pending_trades_for_user(ctx.author.id)
        
        if not trades:
            return await ctx.reply("You have no pending trades.")
            
        embeds = []
        for trade in trades:
            offerer = self.bot.get_user(trade["offerer_id"])
            offeree = self.bot.get_user(trade["offeree_id"])
            
            embed = discord.Embed(
                title=f"Trade Offer {'(Sent)' if trade['offerer_id'] == ctx.author.id else '(Received)'}",
                description=(
                    f"**From:** {offerer.mention}\n"
                    f"**To:** {offeree.mention}\n\n"
                    f"Offering: {trade['offerer_card_name']} [`{trade['offerer_card']}`]\n"
                    f"Requesting: {trade['offeree_card_name']} [`{trade['offeree_card']}`]"
                ),
                timestamp=datetime.fromisoformat(trade["created_at"]),
                color=discord.Colour.dark_grey()
            )
            embeds.append(embed)
            
        if not embeds:
            return await ctx.reply("No valid pending trades found.")
            
        view = PaginationView(embeds, ctx.author)
        await ctx.reply(embed=embeds[0], view=view)

    @commands.command(name="gift")
    @check_active_command()
    @track_command()
    async def gift(self, ctx: commands.Context, target: discord.Member, card_code: str) -> None:
        """
        Gift a card to another user.
        Usage: /gift @user card_code
        """
        if target.bot or target == ctx.author:
            return await ctx.reply("Invalid gift target.")
            
        card = self.bot.db.get_card_by_serial(card_code)
        if not card or card['owner_id'] != ctx.author.id:
            return await ctx.reply("You do not own that card.")
            
        if self.bot.db.update_card_owner(card_code, target.id):
            await ctx.reply(f"Card {card_code} has been gifted to {target.mention}.")
        else:
            await ctx.reply("Failed to gift the card.")

    @commands.command(name="waifulb", aliases=["waifu-lb", "waifu-leaderboard"])
    @check_active_command()
    @track_command()
    async def waifu_leaderboard(self, ctx: commands.Context):
        """Shows the top 5 users with highest value waifu collections"""
        # Add placeholder message
        placeholder = await ctx.reply("Loading leaderboard...")
        
        # Get leaderboard stats using optimized SQL query
        results = self.bot.db.get_waifu_leaderboard_stats()
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Waifu Collection Leaderboard 🏆",
            color=discord.Color.gold()
        )
        
        for i, stats in enumerate(results, 1):
            user = self.bot.get_user(stats["owner_id"])
            if not user:
                continue
                
            # Count tiers from cards_by_tier string
            tier_counts = {
                tier: stats["cards_by_tier"].count(tier) 
                for tier in self.available_rarities 
                if tier in stats["cards_by_tier"]
            }
            
            # Format tier counts
            tier_text = " | ".join(f"{tier}: {count}" for tier, count in tier_counts.items() if count > 0)
            
            embed.add_field(
                name=f"{i}. {user.name}",
                value=f"💰 Total Value: ${stats['total_value']:,.2f}\n"
                      f"📊 Cards: {stats['total_cards']}\n"
                      f"📦 Tiers: {tier_text}",
                inline=False
            )
        
        await placeholder.edit(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Waifu(bot))

