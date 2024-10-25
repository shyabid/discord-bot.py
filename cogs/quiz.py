from discord.ext import commands
import discord 
import html
import asyncio
import datetime
import aiohttp
import random
from typing import Literal
import asyncio 


class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.question_cache = {
            "history": [],
            "gk": [],
            "music": [],
            "anime": [],
            "science": [],
            "games": []
        }
        self.last_fetch_time = None
        self.min_questions = 10
        self.refill_amount = 40
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.preload_questions()

    async def preload_questions(self):
        categories = {
            "history": 22, "gk": 9, "music": 12, "anime": 31,
            "science": random.choice([17, 18, 19]), "games": 15
        }

        for category_name, category_id in categories.items():
            if len(self.question_cache[category_name]) < self.min_questions:
                await self.fetch_and_store_questions(category_name, category_id, self.refill_amount)
                await asyncio.sleep(5)
                
    async def fetch_and_store_questions(self, category_name, category_id, refill_amount):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://opentdb.com/api.php?amount={refill_amount}&category={category_id}&type=multiple") as response:
                self.bot.logger.info(f"Fetching {refill_amount} questions for category: {category_name}")
                
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))  
                    self.bot.logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    return await self.fetch_and_store_questions(category_name, category_id, refill_amount) 
                
                if response.status != 200:
                    self.bot.logger.warning(f"Failed to fetch questions for category: {category_name} with status: {response.status}")
                    return
                data = await response.json()

        if data["response_code"] == 0:
            self.question_cache[category_name].extend(data["results"])
            self.bot.logger.info(f"Fetched and stored {len(data['results'])} questions for category: {category_name}")
        else:
            self.bot.logger.warning(f"API returned error code {data['response_code']} for category: {category_name}")
    
    
    async def fetch_questions(self, type):
        categories = {
            "history": 22, "gk": 9, "music": 12, "anime": 31,
            "science": random.choice([17, 18, 19]), "games": 15
        }

        category_id = categories.get(type, random.choice(list(categories.values())))
        category_name = next((name for name, id in categories.items() if id == category_id), "Unknown")

        if not self.question_cache[category_name]:
            self.bot.logger.warning(f"No questions available for category: {category_name}")
            return None

        quiz_question = self.question_cache[category_name].pop(0)
        question_text = html.unescape(quiz_question["question"])
        correct_answer = html.unescape(quiz_question["correct_answer"])
        options = [html.unescape(option) for option in quiz_question["incorrect_answers"] + [correct_answer]]
        random.shuffle(options)

        self.bot.logger.info(f"Retrieved question from cache for category: {category_name}")
        if len(self.question_cache[category_name]) < self.min_questions:
            self.bot.logger.info(f"Category {category_name} has fewer than {self.min_questions} questions. Fetching {self.refill_amount} more.")
            asyncio.create_task(self.fetch_and_store_questions(category_name, category_id, self.refill_amount))

        return question_text, correct_answer, options, category_name

    async def update_score(self, user_id, correct, category):
        user_id_str = str(user_id)
        quiz_data = self.bot.db["userdata"]["quiz"].find_one({"userid": user_id_str}) or {
            "userid": user_id_str,
            "total_quizzes": 0,
            "correct_answers": 0,
            "categories": {}
        }

        quiz_data["total_quizzes"] += 1
        if correct:
            quiz_data["correct_answers"] += 1

        if category not in quiz_data["categories"]:
            quiz_data["categories"][category] = {"total": 0, "correct": 0}

        quiz_data["categories"][category]["total"] += 1
        if correct:
            quiz_data["categories"][category]["correct"] += 1

        self.bot.db["userdata"]["quiz"].update_one({"userid": user_id_str}, {"$set": quiz_data}, upsert=True)

    @commands.hybrid_group(
        name="quiz", 
        description="Take a quiz!",
        aliases=["q"]
    )
    async def quiz(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            subcommand = ctx.message.content.split()[1].lower() if len(ctx.message.content.split()) > 1 else None

            category_mapping = {
                "lb": "leaderboard",    "top": "leaderboard",
                "history": "history",   "his": "history",
                "h": "history",         "hist": "history",
                "general": "gk",        "general_knowledge": "gk",
                "m": "music",           "mu": "music",
                "a": "anime",           "anim": "anime",
                "ani": "anime",         "anm": "anime",
                "s": "science",         "sci": "science",
                "tech": "science",      "technology": "science",
                "chem": "science",      "physics": "science",
                "biology": "science",   "maths": "science",
                "math": "science",      "science_and_nature": "science",
                "g": "games",           "game": "games",
                "play": "games",        "plays": "games"
            }

            category = category_mapping.get(subcommand, "random")

            if category == "leaderboard":
                await self.quiz_leaderboard(ctx)
            elif category == "random":
                await self.quiz_random(ctx)
            else:
                await self.quiz_random(ctx, category=category)

    @quiz.command(name="start", description="Take a random quiz!")
    async def quiz_random(self, ctx: commands.Context, category: Literal["history", "gk", "music", "anime", "science", "games"] = None):
        question_data = await self.fetch_questions(category)
        if question_data is None:
            await ctx.reply("Failed to fetch the quiz.")
            return
        question_text, correct_answer, options, category_name = question_data

        select = discord.ui.Select(
            placeholder="Choose your answer...",
            options=[discord.SelectOption(label=option) for option in options]
        )

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                msg = await interaction.response.send_message("You can't answer this quiz!", ephemeral=True)
                return
            selected_answer = select.values[0]
            correct = selected_answer == correct_answer
            await self.update_score(interaction.user.id, correct, category_name)

            result_message = "Correct!" if correct else f"Incorrect. The correct answer was: {correct_answer}"
            result_embed = discord.Embed(description=result_message, color=discord.Color.green() if correct else discord.Color.red())

            select.disabled = True
            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.edit_message(embed=result_embed, view=None)

        select.callback = select_callback

        view = discord.ui.View(timeout=15)
        view.add_item(select)

        end_time = discord.utils.utcnow() + datetime.timedelta(seconds=15)
        embed = discord.Embed(title=category_name.capitalize(), description=f"{question_text}\n\nQuiz ends {discord.utils.format_dt(end_time, 'R')}", color=discord.Color.dark_grey())
        message = await ctx.reply(embed=embed, view=view)

        await asyncio.sleep(15)

        if not select.disabled:
            await self.update_score(ctx.author.id, False, category_name)
            times_up_embed = discord.Embed(description=f"Times Up! The correct answer was: {correct_answer}", color=discord.Color.dark_grey())
            await message.edit(embed=times_up_embed, view=None)


    @quiz.command(name="score", description="Show your quiz score")
    async def quiz_score(self, ctx: commands.Context, *, member: discord.Member = None):

        if member is None:
            member = ctx.author
        if isinstance(member, str):
            member = await self.bot.find_member(ctx.guild, member)

        user_id_str = str(member.id)
        quiz_data = self.bot.db["userdata"]["quiz"].find_one({"userid": user_id_str})

        if not quiz_data:
            await ctx.reply(f"{member.mention} hasn't taken any quizzes yet!" if member else "You haven't taken any quizzes yet!")
            return

        total_quizzes = quiz_data["total_quizzes"]
        correct_answers = quiz_data["correct_answers"]
        accuracy = (correct_answers / total_quizzes) * 100 if total_quizzes > 0 else 0

        embed = discord.Embed(title=f"{member.display_name}'s Quiz Score", color=discord.Color.dark_grey())
        embed.add_field(name="Total", value=total_quizzes, inline=True)
        embed.add_field(name="Correct", value=correct_answers, inline=True)
        embed.add_field(name="Accuracy", value=f"{accuracy:.2f}%", inline=True)
        category_details = []
        for category, stats in quiz_data["categories"].items():
            cat_accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            category_details.append(f"{category.capitalize()}: {stats['correct']}/{stats['total']} [{cat_accuracy:.2f}%]")
        
        embed.add_field(name="Category Details", 
                        value="\n".join(category_details), 
                        inline=False)

        await ctx.reply(embed=embed)

    @quiz.command(name="leaderboard", description="Show the quiz leaderboard")
    async def quiz_leaderboard(self, ctx: commands.Context):
        leaderboard = []
        members = {str(member.id): member for member in ctx.guild.members}  
        quiz_data_list = self.bot.db["userdata"]["quiz"].find({"userid": {"$in": list(members.keys())}}) 
        for quiz_data in quiz_data_list:
            user_id_str = quiz_data["userid"]
            if quiz_data.get("total_quizzes", 0) > 0:
                total_quizzes = quiz_data["total_quizzes"]
                correct_answers = quiz_data["correct_answers"]
                accuracy = (correct_answers / total_quizzes) * 100 if total_quizzes > 0 else 0
                leaderboard.append((user_id_str, total_quizzes, correct_answers, accuracy))

        leaderboard.sort(key=lambda x: x[2], reverse=True)

        embed = discord.Embed(title="Quiz Leaderboard", color=discord.Color.dark_grey())
        embed.description = "" 
        for i, (user_id, total, correct, accuracy) in enumerate(leaderboard[:10], start=1):
            user = members.get(user_id)
            if user:
                embed.description += f"{i}. {user.mention}: {correct}/{total} correct ({accuracy:.2f}%)\n"

        await ctx.reply(embed=embed)




async def setup(bot):
    await bot.add_cog(Quiz(bot))
