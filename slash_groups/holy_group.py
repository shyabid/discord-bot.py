import discord 
from discord import app_commands
import random
import requests 

class HolyGroup(app_commands.Group):
    
    @app_commands.command(
        name="quran",
        description="Get a quran Verse"
    )
    @app_commands.describe(
        query="Specify the chp and verse. (e.g. 2:255)"
    )
    async def quran(self, interaction: discord.Interaction, query: str = None):
        if query is None:
            random_number = random.randint(1, 6236)
            url = f'https://api.alquran.cloud/v1/ayah/{random_number}/editions/quran-uthmani,en.pickthall'
        else:
            url = f'https://api.alquran.cloud/v1/ayah/{query}/editions/quran-uthmani,en.pickthall'
        
        try:
            response = requests.get(url)
            data = response.json()

            if data['code'] != 200:
                await interaction.response.send_message(f"Could not fetch the verse. Please check the format and try again.")
                return
            
            verse = data['data'][1]
            arbic_name = data["data"][0]["surah"]["name"]
            eng_name = data["data"][0]["surah"]["englishName"]
            ayah_number = verse['numberInSurah']
            verse_text = verse['text']
            arbic = data["data"][0]["text"]
            embed = discord.Embed(
                description=f"{arbic} \n\n{verse_text}",
                color=discord.Color.dark_grey()
            )
            embed.set_author(name=f"Surah {eng_name} [{arbic_name}] Ayah {ayah_number}")

            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")

    @app_commands.command(
        name="bible",
        description="Get a Bible Verse"
    )
    @app_commands.describe(
        query="bookName chapterNum:verseNum"
    )
    async def bible(self, interaction: discord.Interaction, query:str = None):
        if query == None:
            response = requests.get('https://bible-api.com/?random=verse')
        else:
            try:
                response = requests.get(f'https://bible-api.com/{query}')
            except Exception:
                await interaction.response.send_message(f"Invalid format. Use ?bible [book] [chapter]:[verse]")
                return
        
        data = response.json()
        
        print(data)
        if 'text' not in data:
            await interaction.response.send_message(f"Could not fetch the verse. Please check the format and try again.")
            return
        
        embed = discord.Embed(
            description=data['text'],
            color=discord.Color.dark_grey()
        )
        
        embed.set_author(name=data['reference'])
        embed.set_footer(text="taken from World English Bible")
        await interaction.response.send_message(embed=embed)
