from discord.ext import commands
import discord
import html
import asyncio
import datetime
import aiohttp
import random
from typing import Literal

class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.question_cache = {
            "history": [], "gk": [], "music": [], 
            "anime": [], "science": [], "games": []
        }
        self.min_questions = 10
        self.refill_amount = 40
        self.reward_amount = 0.50 

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
                await asyncio.sleep(5)  # Rate limiting
    
    async def fetch_and_store_questions(self, category_name, category_id, refill_amount):
        """Fetch questions from OpenTDB API and store in cache"""
        async with aiohttp.ClientSession() as session:
            url = f"https://opentdb.com/api.php?amount={refill_amount}&category={category_id}&type=multiple"
            async with session.get(url) as response:
                
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))  
                    await asyncio.sleep(retry_after)
                    return await self.fetch_and_store_questions(category_name, category_id, refill_amount) 
                
                if response.status != 200: return
                    
                data = await response.json()

        if data["response_code"] == 0:
            self.question_cache[category_name].extend(data["results"])
        
    async def fetch_questions(self, type):
        """Get a question from cache or fetch new ones if needed"""
        categories = {
            "history": 22, "gk": 9, "music": 12, "anime": 31,
            "science": random.choice([17, 18, 19]), "games": 15
        }

        category_id = categories.get(type, random.choice(list(categories.values())))
        category_name = next((name for name, id in categories.items() if id == category_id), "Unknown")


        quiz_question = self.question_cache[category_name].pop(0)
        question_text = html.unescape(quiz_question["question"])
        correct_answer = html.unescape(quiz_question["correct_answer"])
        options = [html.unescape(option) for option in quiz_question["incorrect_answers"] + [correct_answer]]
        random.shuffle(options)

        if len(self.question_cache[category_name]) < self.min_questions:
            asyncio.create_task(self.fetch_and_store_questions(category_name, category_id, self.refill_amount))

        return question_text, correct_answer, options, category_name

    def update_score(self, user_id: int, correct: bool, category: str):
        """Update quiz score in database - synchronous version"""
        self.bot.db.update_quiz_stats(user_id, correct, category)

    @commands.hybrid_group(name="quiz", description="Take a quiz!", aliases=["q"])
    async def quiz(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            category_mapping = {
                "lb": "leaderboard", "top": "leaderboard",
                "history": "history", "his": "history",
                "h": "history", "hist": "history",
                "general": "gk", "general_knowledge": "gk",
                "m": "music", "mu": "music",
                "a": "anime", "anim": "anime",
                "ani": "anime", "anm": "anime",
                "s": "science", "sci": "science",
                "g": "games", "game": "games",
            }
            
            subcommand = ctx.message.content.split()[1].lower() if len(ctx.message.content.split()) > 1 else None
            category = category_mapping.get(subcommand, "random")

            if category == "leaderboard":
                await self.quiz_leaderboard(ctx)
            elif category == "random":
                await self.quiz_random(ctx)
            else:
                await self.quiz_random(ctx, category=category)

    @quiz.command(name="start", description="Take a random quiz!")
    async def quiz_random(self, ctx: commands.Context, 
                         category: Literal["history", "gk", "music", "anime", "science", "games"] = None):
        question_data = await self.fetch_questions(category)
        if question_data is None:
            return await ctx.reply("Failed to fetch the quiz.")

        question_text, correct_answer, options, category_name = question_data
        
        select = discord.ui.Select(
            placeholder="Choose your answer...",
            options=[discord.SelectOption(label=option) for option in options]
        )

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message(
                    "You can't answer this quiz!", ephemeral=True
                )

            selected_answer = select.values[0]
            correct = selected_answer == correct_answer
            
            # Remove await from database calls
            self.update_score(interaction.user.id, correct, category_name)
            
            if correct:
                self.bot.db.update_user_balance(interaction.user.id, self.reward_amount)
                reward_text = f"\nYou earned ${self.reward_amount:.2f}!"
            else:
                reward_text = ""

            result_embed = discord.Embed(
                description=f"{'Correct!' if correct else f'Incorrect. The correct answer was: {correct_answer}'}{reward_text}",
                color=discord.Color.green() if correct else discord.Color.red()
            )

            select.disabled = True
            await interaction.response.edit_message(embed=result_embed, view=None)

        select.callback = select_callback
        view = discord.ui.View(timeout=15)
        view.add_item(select)

        end_time = discord.utils.utcnow() + datetime.timedelta(seconds=15)
        embed = discord.Embed(
            title=category_name.capitalize(),
            description=f"{question_text}\n\nQuiz ends {discord.utils.format_dt(end_time, 'R')}",
            color=discord.Color.dark_grey()
        )
        
        message = await ctx.reply(embed=embed, view=view)
        await asyncio.sleep(15)

        if not select.disabled:
            self.update_score(ctx.author.id, False, category_name)
            times_up_embed = discord.Embed(
                description=f"Times Up! The correct answer was: {correct_answer}",
                color=discord.Color.dark_grey()
            )
            await message.edit(embed=times_up_embed, view=None)

    @quiz.command(name="score", description="Show your quiz score")
    async def quiz_score(self, ctx: commands.Context, *, member: discord.Member = None):
        if member is None:
            member = ctx.author

        quiz_data, category_stats = self.bot.db.get_quiz_user_stats(member.id)
        if not quiz_data:
            return await ctx.reply(f"{member.mention} hasn't taken any quizzes yet!")

        # Access tuple data by index instead of keys
        total_quizzes = quiz_data[0]  # Changed from quiz_data["total_quizzes"]
        correct_answers = quiz_data[1]  # Changed from quiz_data["correct_answers"]
        accuracy = (correct_answers / total_quizzes * 100) if total_quizzes > 0 else 0

        embed = discord.Embed(
            title=f"{member.display_name}'s Quiz Score",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Total", value=total_quizzes, inline=True)
        embed.add_field(name="Correct", value=correct_answers, inline=True)
        embed.add_field(name="Accuracy", value=f"{accuracy:.2f}%", inline=True)

        if category_stats:
            category_details = []
            for stat in category_stats:
                # Access tuple data by index
                category = stat[0]  # category name
                total_attempts = stat[1]
                cat_correct = stat[2]
                cat_accuracy = (cat_correct / total_attempts * 100) if total_attempts > 0 else 0
                category_details.append(
                    f"{category.capitalize()}: {cat_correct}/{total_attempts} [{cat_accuracy:.2f}%]"
                )
            embed.add_field(
                name="Category Details",
                value="\n".join(category_details),
                inline=False
            )

        await ctx.reply(embed=embed)

    @quiz.command(name="leaderboard", description="Show the quiz leaderboard")
    async def quiz_leaderboard(self, ctx: commands.Context):
        leaderboard_data = self.bot.db.get_quiz_leaderboard(10)
        if not leaderboard_data:
            return await ctx.reply("No quiz data available yet!")

        embed = discord.Embed(
            title="Quiz Leaderboard",
            color=discord.Color.dark_grey()
        )
        
        entries = []
        for i, data in enumerate(leaderboard_data, 1):
            # Access tuple data by index
            user_id = data[0]  # Changed from data["user_id"]
            total_quizzes = data[1]  # Changed from data["total_quizzes"]
            correct_answers = data[2]  # Changed from data["correct_answers"]
            
            member = ctx.guild.get_member(user_id)
            if member:
                accuracy = (correct_answers / total_quizzes * 100) if total_quizzes > 0 else 0
                entries.append(
                    f"{i}. {member.mention}: {correct_answers}/{total_quizzes} correct ({accuracy:.2f}%)"
                )

        embed.description = "\n".join(entries) if entries else "No data available"
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Quiz(bot))
