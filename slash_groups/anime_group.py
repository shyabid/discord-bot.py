from discord import app_commands 
import discord 
import requests


class AnimeGroup(app_commands.Group):
    
    @app_commands.command(
        name="waifu",
        description="Get a random waifu image"
    )
    async def waifu(self, interaction: discord.Interaction):
        try:
            url = "https://nekos.best/api/v2/waifu"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=interaction.user.avatar.url, text=f"Command ran by {interaction.user.global_name}")
                await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")
            

    @app_commands.command(
        name="neko",
        description="Get a random neko image"
    )
    async def neko(self, interaction: discord.Interaction):
        try:
            url = "https://nekos.best/api/v2/neko"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=interaction.user.avatar.url, text=f"Command ran by {interaction.user.global_name}")
                await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")



    @app_commands.command(
        name="hubby",
        description="Get a random husbando image"
    )
    async def husbando(self, interaction: discord.Interaction):
        try:
            url = "https://nekos.best/api/v2/husbando"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                embed = discord.Embed(
                    description=f"Drawn by [{data['results'][0]['artist_name']}]({data['results'][0]['artist_href']})",
                    color=discord.Color.dark_grey()
                )
                embed.set_image(url=data['results'][0]['url'])
                embed.set_footer(icon_url=interaction.user.avatar.url, text=f"Command ran by {interaction.user.global_name}")
                await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")     
    
    # this file will be atleast 3000lines long trst