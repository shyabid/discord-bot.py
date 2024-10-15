from discord.ext import commands
import discord
from db import db
from typing import List, Literal
from bson import ObjectId

class Auto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="auto", description="Manage auto-reactions and auto-responses")
    @commands.has_permissions(manage_guild=True)
    async def auto(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `?help auto` for more information.")

    @auto.group(name="reaction", description="Manage auto-reactions")
    @commands.has_permissions(manage_guild=True)
    async def auto_reaction(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `?help auto reaction` for more information.")

    @auto.group(name="respond", description="Manage auto-responses")
    @commands.has_permissions(manage_guild=True)
    async def auto_respond(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `?help auto respond` for more information.")
    
    
    @auto_reaction.command(name="create", description="Create a new auto-reaction")
    @commands.has_permissions(manage_guild=True)
    async def reaction_create(self, ctx: commands.Context, type: Literal["startswith", "contains", "exact", "endswith"], trigger: str, emojis: str):
        guild_id = str(ctx.guild.id)
        autoreact_data = db[guild_id]["autoreact"].find_one() or {}
        
        if trigger.startswith('"') and trigger.endswith('"'):
            trigger = trigger[1:-1] 
        elif ' ' in trigger:
            await ctx.send("Trigger must be one word unless enclosed in quotes.")
            return
        
        emoji_list = emojis.split()
        autoreact_data[trigger] = {"emojis": emoji_list, "type": type}
        db[guild_id]["autoreact"].update_one({}, {"$set": autoreact_data}, upsert=True)
        await ctx.send(f"Auto-reaction created for trigger: {trigger}")

    @auto_respond.command(name="create", description="Create a new auto-response")
    @commands.has_permissions(manage_guild=True)
    async def respond_create(self, ctx: commands.Context, type: Literal["startswith", "contains", "exact", "endswith"], trigger: str, reply: str):
        guild_id = str(ctx.guild.id)
        autorespond_data = db[guild_id]["autorespond"].find_one() or {}
        
        if trigger.startswith('"') and trigger.endswith('"'):
            trigger = trigger[1:-1]  
        elif ' ' in trigger:
            await ctx.send("Trigger must be one word unless enclosed in quotes.")
            return
        
        autorespond_data[trigger] = {"reply": reply, "type": type}
        db[guild_id]["autorespond"].update_one({}, {"$set": autorespond_data}, upsert=True)
        await ctx.send(f"Auto-response created for trigger: {trigger}")

    @auto_reaction.command(name="delete", description="Delete an auto-reaction")
    @commands.has_permissions(manage_guild=True)
    async def reaction_delete(self, ctx: commands.Context, trigger: str):
        guild_id = str(ctx.guild.id)
        autoreact_data = db[guild_id]["autoreact"].find_one() or {}
        if trigger in autoreact_data:
            del autoreact_data[trigger]
            db[guild_id]["autoreact"].update_one({}, {"$set": autoreact_data}, upsert=True)
            await ctx.send(f"Auto-reaction deleted for trigger: {trigger}")
        else:
            await ctx.send(f"No auto-reaction found for trigger: {trigger}")

    @auto_respond.command(name="delete", description="Delete an auto-response")
    @commands.has_permissions(manage_guild=True)
    async def respond_delete(self, ctx: commands.Context, trigger: str):
        guild_id = str(ctx.guild.id)
        autorespond_data = db[guild_id]["autorespond"].find_one() or {}
        if trigger in autorespond_data:
            del autorespond_data[trigger]
            db[guild_id]["autorespond"].update_one({}, {"$set": autorespond_data}, upsert=True)
            await ctx.send(f"Auto-response deleted for trigger: {trigger}")
        else:
            await ctx.send(f"No auto-response found for trigger: {trigger}")

    @auto_reaction.command(name="list", description="List all auto-reactions")
    @commands.has_permissions(manage_guild=True)
    async def reaction_list(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        autoreact_data = db[guild_id]["autoreact"].find_one() or {}
        if autoreact_data:
            response = "Auto-reactions:\n"
            for trigger, data in autoreact_data.items():
                if isinstance(data, dict) and 'emojis' in data and 'type' in data:
                    emoji_list = [str(emoji) for emoji in data['emojis']]
                    response += f"{trigger}: {emoji_list} ({data['type']})\n"
            await ctx.send(response)
        else:
            await ctx.send("No auto-reactions set up.")

    @auto_respond.command(name="list", description="List all auto-responses")
    @commands.has_permissions(manage_guild=True)
    async def respond_list(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        autorespond_data = db[guild_id]["autorespond"].find_one() or {}
        if autorespond_data:
            response = "Auto-responses:\n"
            for trigger, data in autorespond_data.items():
                if isinstance(data, dict) and 'reply' in data and 'type' in data:
                    response += f"{trigger}: {data['reply']} ({data['type']})\n"
            await ctx.send(response)
        else:
            await ctx.send("No auto-responses set up.")

    @commands.command(name="ar", aliases=["autoreact", "autorespond"])
    @commands.has_permissions(manage_guild=True)
    async def ar(self, ctx: commands.Context, action: str, *args):
        try:
            action = action.lower()
            guild_id = str(ctx.guild.id)

            if action in ["create", "add", "make", "+", "c", "mk"]:
                if args[0].lower() in ["startswith", "contains", "exact", "endswith"]:
                    trigger_type = args[0].lower()
                    trigger = args[1]
                    response_or_emoji = args[2:]
                else:
                    trigger_type = "contains"
                    trigger = args[0]
                    response_or_emoji = args[1:]

                if not response_or_emoji:
                    raise ValueError("Response or emoji is missing")

                is_reaction = all(self.is_emoji(emoji) for emoji in response_or_emoji)

                if is_reaction:
                    autoreact_data = db[guild_id]["autoreact"].find_one() or {}
                    autoreact_data[trigger] = {
                        "emojis": list(response_or_emoji),
                        "type": trigger_type
                    }
                    db[guild_id]["autoreact"].update_one({}, {"$set": autoreact_data}, upsert=True)
                    await ctx.send(embed=discord.Embed(title="Auto-reaction Created", description=f"Trigger: {trigger}", color=discord.Color.dark_grey()))
                else:
                    autorespond_data = db[guild_id]["autorespond"].find_one() or {}
                    autorespond_data[trigger] = {
                        "reply": " ".join(response_or_emoji),
                        "type": trigger_type
                    }
                    db[guild_id]["autorespond"].update_one({}, {"$set": autorespond_data}, upsert=True)
                    await ctx.send(embed=discord.Embed(title="Auto-response Created", description=f"Trigger: {trigger}", color=discord.Color.dark_grey()))

            elif action in ["del", "delete", "rm", "-", "remove"]:
                if len(args) < 1:
                    raise ValueError("Trigger to delete is missing")
                
                trigger = args[0]
                autoreact_data = db[guild_id]["autoreact"].find_one() or {}
                autorespond_data = db[guild_id]["autorespond"].find_one() or {}

                if trigger in autoreact_data:
                    del autoreact_data[trigger]
                    db[guild_id]["autoreact"].update_one({}, {"$set": autoreact_data}, upsert=True)
                    await ctx.send(embed=discord.Embed(title="Auto-reaction Deleted", description=f"Trigger: {trigger}", color=discord.Color.dark_grey()))
                elif trigger in autorespond_data:
                    del autorespond_data[trigger]
                    db[guild_id]["autorespond"].update_one({}, {"$set": autorespond_data}, upsert=True)
                    await ctx.send(embed=discord.Embed(title="Auto-response Deleted", description=f"Trigger: {trigger}", color=discord.Color.dark_grey()))
                else:
                    await ctx.send(embed=discord.Embed(title="Error", description=f"No auto-reaction or auto-response found for trigger: {trigger}", color=discord.Color.dark_grey()))

            elif action in ["list", "show", "display"]:
                autoreact_data = db[guild_id]["autoreact"].find_one() or {}
                autorespond_data = db[guild_id]["autorespond"].find_one() or {}

                embed = discord.Embed(title="Auto-reactions and Auto-responses", color=discord.Color.dark_grey())

                if autoreact_data:
                    autoreact_list = "\n".join([f"{trigger}: {data['emojis']} ({data['type']})" for trigger, data in autoreact_data.items() if isinstance(data, dict) and 'emojis' in data and 'type' in data])
                    embed.add_field(name="Auto-reactions", value=autoreact_list or "None", inline=False)

                if autorespond_data:
                    autorespond_list = "\n".join([f"{trigger}: {data['reply']} ({data['type']})" for trigger, data in autorespond_data.items() if isinstance(data, dict) and 'reply' in data and 'type' in data])
                    embed.add_field(name="Auto-responses", value=autorespond_list or "None", inline=False)

                if not autoreact_data and not autorespond_data:
                    embed.description = "No auto-reactions or auto-responses set up."

                await ctx.send(embed=embed)

            elif action in ["reset"]:
                embed = discord.Embed(
                    title="Reset Confirmation",
                    description="Are you sure you want to remove all auto-reactions and auto-responses from this server?",
                    color=discord.Color.dark_grey()
                )
                
                confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Confirm Reset")
                cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel")

                async def confirm_callback(interaction):
                    guild_id = str(interaction.guild_id)
                    db[guild_id]["autoreact"].delete_many({})
                    db[guild_id]["autorespond"].delete_many({})
                    await interaction.response.edit_message(content="", embed=discord.Embed(title="Reset Complete", description="All auto-reactions and auto-responses have been removed.", color=discord.Color.dark_grey()), view=None)

                async def cancel_callback(interaction):
                    await interaction.response.edit_message(content="", embed=discord.Embed(title="Reset Cancelled", description="No changes were made.", color=discord.Color.dark_grey()), view=None)

                confirm_button.callback = confirm_callback
                cancel_button.callback = cancel_callback

                view = discord.ui.View()
                view.add_item(confirm_button)
                view.add_item(cancel_button)

                await ctx.send(embed=embed, view=view)

            else:
                raise ValueError("Invalid action")

        except Exception as e:
            missing_param = self.get_missing_param(action, args)
            error_message = (
                f"An error occurred: {str(e)}\n"
                f"Missing parameter: {missing_param}\n\n"
                "Please use the command in this format:\n"
                "?ar <create/add/make/+/c/mk> [startswith/contains/exact/endswith] \"trigger\" \"response/emoji\"\n"
                "?ar <del/delete/rm/-/remove> \"trigger\"\n"
                "?ar <list/show/display>\n"
                "?ar reset\n"
                "Examples:\n"
                "?ar add startswith \"hello\" \"👋\" \"😊\"\n"
                "?ar create \"good morning\" \"Good morning to you too!\"\n"
                "?ar + exact \"lol\" \"😂\" \"🤣\"\n"
                "?ar mk endswith \"bye\" \"Goodbye!\"\n"
                "?ar del \"hello\"\n"
                "?ar list\n"
                "?ar reset"
            )
            await ctx.send(embed=discord.Embed(title="Error", description=error_message, color=discord.Color.dark_grey()))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)
        content = message.content.lower()
        # Auto-reaction
        autoreact_data = db[guild_id]["autoreact"].find_one() or {}
        for trigger, data in autoreact_data.items():
            if isinstance(data, dict) and 'emojis' in data and 'type' in data:
                if self.check_trigger(content, trigger, data['type']):
                    for emoji in data['emojis']:
                        try:
                            await message.add_reaction(emoji)
                        except discord.errors.HTTPException:
                            custom_emoji = discord.utils.get(message.guild.emojis, name=emoji.strip(':'))
                            if custom_emoji:
                                await message.add_reaction(custom_emoji)

        autorespond_data = db[guild_id]["autorespond"].find_one() or {}
        for trigger, data in autorespond_data.items():
            if isinstance(data, dict) and 'reply' in data and 'type' in data:
                if self.check_trigger(content, trigger, data['type']):
                    await message.channel.send(data['reply'])

    def check_trigger(self, content: str, trigger: str, trigger_type: str) -> bool:
        if trigger_type == "startswith":
            return content.startswith(trigger.lower())
        elif trigger_type == "contains":
            return trigger.lower() in content
        elif trigger_type == "exact":
            return content == trigger.lower()
        elif trigger_type == "endswith":
            return content.endswith(trigger.lower())
        return False
    
    
    def is_emoji(self, s):
        return s.startswith(':') and s.endswith(':') or len(s) == 1

    def get_missing_param(self, action, args):
        if action in ["create", "add", "make", "+", "c", "mk"]:
            if len(args) == 0:
                return "trigger"
            elif len(args) == 1:
                return "response or emoji"
        elif action in ["del", "delete", "rm", "-", "remove"]:
            if len(args) == 0:
                return "trigger"
        return "None"

async def setup(bot):
    await bot.add_cog(Auto(bot))
