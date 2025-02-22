from discord.ext import commands
import discord
import os
import json
from openai import OpenAI
import asyncio
from typing import Optional

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        self.CHARACTER_DESCRIPTION = os.getenv("CHARACTER_DESCRIPTION")
        # Add chat-only channel tracking
        self.chat_channels = {}

    @commands.hybrid_command(
        name="chatonly",
        description="Set a channel where the bot responds to all messages"
    )
    @commands.has_permissions(administrator=True)
    async def chatonly(
        self, 
        ctx: commands.Context, 
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        """
        Set or remove a chat-only channel where the bot responds to all messages.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            The channel to set as chat-only. Leave empty to disable.
        """
        guild_id = str(ctx.guild.id)
        
        if channel:
            self.chat_channels[guild_id] = channel.id
            await ctx.send(f"Chat-only mode enabled in {channel.mention}")
        else:
            self.chat_channels.pop(guild_id, None)
            await ctx.send("Chat-only mode disabled")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Check if message is in a chat-only channel
        chat_channel_id = self.chat_channels.get(str(message.guild.id))
        
        trigger = (
            (chat_channel_id and message.channel.id == chat_channel_id) or
            (self.bot.user.mention in message.content and 
             len(message.content.strip()) > len(self.bot.user.mention))
        )
        
        if message.reference:
            try:
                ref = await message.channel.fetch_message(message.reference.message_id)
                if ref.author == self.bot.user:
                    trigger = True
            except Exception:
                pass
                
        if not trigger:
            return

        history = []
        async for msg in message.channel.history(limit=30, oldest_first=True):
            sender = "You" if msg.author.id == self.bot.user.id else msg.author.display_name
            if msg.reference:
                try:
                    ref_message = msg.reference.resolved
                    if ref_message is None:
                        ref_message = await msg.channel.fetch_message(msg.reference.message_id)
                    sender = f"{msg.author.display_name} replied to {ref_message.author.display_name}"
                except Exception:
                    pass
            history.append({"sender": sender, "message": msg.content})
        conversation_json = json.dumps(history, ensure_ascii=False)

        prompt = (
            f"{self.CHARACTER_DESCRIPTION}\n"
            f"Conversation History:\n{conversation_json}\n"
            "Generate an appropriate reply in JSON format with a key 'text' containing only the response."
        )

        # Show typing indicator while processing the response
        async with message.channel.typing():
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
            )
            reply_text = response.choices[0].message.content.strip()
            try:
                # Try to parse the JSON response
                reply_json = json.loads(reply_text)
                reply_content = reply_json.get('text', 'Error: Invalid response format')
                await message.reply(reply_content)
            except json.JSONDecodeError:
                await message.reply(reply_text)

async def setup(bot):
    await bot.add_cog(Chat(bot))
