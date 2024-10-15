from discord.ext import commands
import discord 
import html
import asyncio
import datetime
import aiohttp
import random
from db import db


class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = db
        self.question_cache = {}
        self.last_fetch_time = None

    async def fetch_questions(self, type):
        categories = {
            "history": 22, "gk": 9, "music": 12, "anime": 31,
            "science": random.choice([17, 18, 19]), "games": 15
        }

        category_id = categories.get(type, random.choice(list(categories.values())))
        category_name = next((name for name, id in categories.items() if id == category_id), "Unknown")

        if category_name not in self.question_cache or not self.question_cache[category_name]:
            if self.last_fetch_time is None or (datetime.datetime.now() - self.last_fetch_time).total_seconds() >= 4:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://opentdb.com/api.php?amount=45&category={category_id}&type=multiple") as response:
                        if response.status != 200:
                            return None
                        data = await response.json()

                if data["response_code"] != 0:
                    return None

                self.question_cache[category_name] = data["results"]
                self.last_fetch_time = datetime.datetime.now()

        if not self.question_cache[category_name]:
            return None

        quiz_question = self.question_cache[category_name].pop(0)
        question_text = html.unescape(quiz_question["question"])
        correct_answer = html.unescape(quiz_question["correct_answer"])
        options = [html.unescape(option) for option in quiz_question["incorrect_answers"] + [correct_answer]]
        random.shuffle(options)
        return question_text, correct_answer, options, category_name

    async def update_score(self, user_id, correct, category):
        user_id_str = str(user_id)
        quiz_data = self.db["userdata"]["quiz"].find_one({"userid": user_id_str}) or {
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

        self.db["userdata"]["quiz"].update_one({"userid": user_id_str}, {"$set": quiz_data}, upsert=True)

    @commands.hybrid_group(name="quiz", description="Take a quiz!")
    async def quiz(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await self.quiz_random(ctx)

    @quiz.command(name="random", description="Take a random quiz!")
    async def quiz_random(self, ctx: commands.Context, category: str = None):
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
            selected_answer = select.values[0]
            correct = selected_answer == correct_answer
            await self.update_score(interaction.user.id, correct, category_name)

            result_message = f"**Result:** {'Correct!' if correct else f'Wrong! The correct answer was: {correct_answer}'}"
            result_embed = discord.Embed(title=f"Quiz - {category_name.capitalize()}", description=f"{question_text}\n\n{result_message}", color=discord.Color.green() if correct else discord.Color.red())
            await interaction.response.edit_message(embed=result_embed, view=None)

        select.callback = select_callback

        view = discord.ui.View(timeout=15)
        view.add_item(select)

        end_time = datetime.datetime.now() + datetime.timedelta(seconds=15)
        embed = discord.Embed(title=f"Quiz - {category_name.capitalize()}", description=f"{question_text}\n\nQuiz ends {discord.utils.format_dt(end_time, 'R')}", color=discord.Color.dark_grey())
        message = await ctx.reply(embed=embed, view=view)

        await asyncio.sleep(15)

        if not select.disabled:
            times_up_embed = discord.Embed(title=f"Quiz - {category_name.capitalize()}", description=f"{question_text}\n\nTimes Up! The correct answer was: {correct_answer}", color=discord.Color.dark_grey())
            await message.edit(embed=times_up_embed, view=None)

    @quiz.command(name="score", description="Show your quiz score")
    async def quiz_score(self, ctx: commands.Context):
        user_id_str = str(ctx.author.id)
        quiz_data = self.db["userdata"]["quiz"].find_one({"userid": user_id_str})

        if not quiz_data:
            await ctx.reply("You haven't taken any quizzes yet!")
            return

        total_quizzes = quiz_data["total_quizzes"]
        correct_answers = quiz_data["correct_answers"]
        accuracy = (correct_answers / total_quizzes) * 100 if total_quizzes > 0 else 0

        embed = discord.Embed(title="Your Quiz Score", color=discord.Color.dark_grey())
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
        for member in ctx.guild.members:
            user_id_str = str(member.id)
            quiz_data = self.db["userdata"]["quiz"].find_one({"userid": user_id_str})
            if quiz_data and quiz_data.get("total_quizzes", 0) > 0:
                total_quizzes = quiz_data["total_quizzes"]
                correct_answers = quiz_data["correct_answers"]
                accuracy = (correct_answers / total_quizzes) * 100
                leaderboard.append((user_id_str, total_quizzes, correct_answers, accuracy))

        leaderboard.sort(key=lambda x: (x[3], x[2]), reverse=True)

        embed = discord.Embed(title="Quiz Leaderboard", color=discord.Color.dark_grey())
        for i, (user_id, total, correct, accuracy) in enumerate(leaderboard[:10], start=1):
            user = ctx.guild.get_member(int(user_id))
            if user:
                embed.add_field(
                    name=f"{i}. {user.name}",
                    value=f"Total: {total}, Correct: {correct}, Accuracy: {accuracy:.2f}%",
                    inline=False
                )

        await ctx.reply(embed=embed)




async def setup(bot):
    await bot.add_cog(Quiz(bot))