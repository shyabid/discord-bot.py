from bot import Morgana
import asyncio 

plguins = [
    "plugins.ungrouped",
    "plugins.prefix",
    "plugins.afk",
    "plugins.alias",
    "plugins.anime",
    "plugins.auto",
    "plugins.botto",
    "plugins.leveling",
    "plugins.news",
    "plugins.fun",
    "plugins.reminder",
    "plugins.economy",
    "plugins.quiz",
    "plugins.welcomer",
    "plugins.snipe",
    "plugins.waifu",
    "plugins.role",
    "plugins.purge",
    "plugins.vccontrol",
    "plugins.mod",
    "plugins.goblet",
    "plugins.interactions",
    "plugins.misc",
    "plugins.meta",
    "plugins.help",
#     "plugins.audio",
    "plugins.holy",
    "plugins.bookmark"
]

bot = Morgana(plguins=plguins)

bot.status_messages = [
    ("watching", "over {guild_count} servers"),
    ("playing", "with {member_count} users"),
    ("custom", "You earn 0.1$ on every message"),
    ("custom", "Try ?roll to roll a waifu card"),
    ("custom", "Do ?quiz to start a quiz"),
    ("custom", "Run ?rank to check your level"),
    ("watching", "{channel_count} channels"),
    ("watching", "{role_count} roles"),
    ("watching", "{emoji_count} emojis"),
    ("playing", "{command_count} commands")
]
bot.run()
