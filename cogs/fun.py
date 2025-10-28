import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import json

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme", description="Afficher un meme aléatoire (optionnel: subreddit)")
    @app_commands.describe(subreddit="Optionnel: choisir le subreddit (ex: funny)")
    async def meme(self, interaction: discord.Interaction, subreddit: str = None):
        """Afficher un meme aléatoire"""
        await interaction.response.defer()
        url = 'https://meme-api.com/gimme' + (f'/{subreddit}' if subreddit else '')
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title=data.get('title','Meme'), color=0x00ff00)
                    embed.set_image(url=data.get('url'))
                    embed.set_footer(text=f"r/{data.get('subreddit','?')} | 👍 {data.get('ups',0)}")
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Impossible de récupérer un meme")

    @app_commands.command(name="joke", description="Raconter une blague")
    async def joke(self, interaction: discord.Interaction):
        """Raconter une blague"""
        jokes = [
            "Pourquoi les plongeurs plongent-ils toujours en arrière et pas en avant ? Parce que sinon ils tombent dans le bateau.",
            "Qu'est-ce qu'un canard en pleine forme ? Un canard en forme !",
            "Que fait une fraise sur un cheval ? De la confiture !",
            "Pourquoi les livres n'ont-ils jamais chaud ? Parce qu'ils ont des pages !",
            "Quel est le comble pour un électricien ? De ne pas être au courant !"
        ]
        await interaction.response.send_message(random.choice(jokes))

    @app_commands.command(name="cat", description="Afficher une photo de chat aléatoire")
    async def cat(self, interaction: discord.Interaction):
        """Afficher une photo de chat aléatoire"""
        await interaction.response.defer()
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.thecatapi.com/v1/images/search') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title="🐱 Voici un chat!", color=0xffa500)
                    embed.set_image(url=data[0]['url'])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Impossible de récupérer une image de chat")

    @app_commands.command(name="dog", description="Afficher une photo de chien aléatoire")
    async def dog(self, interaction: discord.Interaction):
        """Afficher une photo de chien aléatoire"""
        await interaction.response.defer()
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.thedogapi.com/v1/images/search') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title="🐶 Voici un chien!", color=0x8b4513)
                    embed.set_image(url=data[0]['url'])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Impossible de récupérer une image de chien")

    @app_commands.command(name="8ball", description="Pose une question à la magic 8-ball")
    @app_commands.describe(question="Votre question")
    async def _8ball(self, interaction: discord.Interaction, question: str):
        """Pose une question à la magic 8-ball"""
        responses = [
            "Oui, certainement.",
            "C'est décidément ainsi.",
            "Sans aucun doute.",
            "Oui, définitivement.",
            "Vous pouvez compter dessus.",
            "Comme je le vois, oui.",
            "Probablement.",
            "Les perspectives sont bonnes.",
            "Oui.",
            "Les signes indiquent que oui.",
            "Réponse floue, réessayez.",
            "Redemandez plus tard.",
            "Mieux vaut ne pas vous le dire maintenant.",
            "Impossible de prédire maintenant.",
            "Concentrez-vous et redemandez.",
            "Ne comptez pas dessus.",
            "Ma réponse est non.",
            "Mes sources disent non.",
            "Les perspectives ne sont pas bonnes.",
            "Très douteux."
        ]
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=0x000000)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Réponse", value=random.choice(responses), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="Lancer des dés")
    @app_commands.describe(dice="Format: NdM (ex: 2d6)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        """Lancer des dés (format: NdM)"""
        try:
            number, sides = map(int, dice.split('d'))
            if number > 20 or sides > 100:
                await interaction.response.send_message("❌ Maximum: 20d100", ephemeral=True)
                return
            
            rolls = [random.randint(1, sides) for _ in range(number)]
            total = sum(rolls)
            
            embed = discord.Embed(title="🎲 Lancer de dés", color=0x00ff00)
            embed.add_field(name="Lancer", value=dice, inline=True)
            embed.add_field(name="Résultats", value=', '.join(map(str, rolls)), inline=True)
            embed.add_field(name="Total", value=total, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Format invalide. Utilisez: NdM (ex: 2d6)", ephemeral=True)

    @app_commands.command(name="say", description="Faire dire quelque chose au bot")
    @app_commands.describe(message="Le texte à répéter")
    async def say(self, interaction: discord.Interaction, message: str):
        """Le bot répète le texte fourni"""
        await interaction.response.send_message(message)

    @app_commands.command(name="hug", description="Faire un câlin à un membre (gif aléatoire)")
    async def hug(self, interaction: discord.Interaction, member: discord.Member = None):
        """Envoyer un gif de câlin"""
        gifs = [
            "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
            "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif",
            "https://media.giphy.com/media/wnsgren9NtITS/giphy.gif",
            "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif"
        ]
        target = member.mention if member else "tout le monde"
        embed = discord.Embed(description=f"🤗 {interaction.user.mention} fait un câlin à {target}!", color=0xffc0cb)
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="catfact", description="Donne un fun fact sur les chats")
    async def catfact(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meowfacts.herokuapp.com/') as resp:
                if resp.status == 200:
                    d = await resp.json()
                    fact = d.get('data', [''])[0]
                    await interaction.followup.send(f"🐱 {fact}")
                else:
                    await interaction.followup.send("❌ Impossible de récupérer un catfact")

    @app_commands.command(name="dadjoke", description="Raconte une blague style dad-joke")
    async def dadjoke(self, interaction: discord.Interaction):
        await interaction.response.defer()
        headers = {"Accept":"application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get("https://icanhazdadjoke.com/", headers=headers) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    await interaction.followup.send(d.get("joke", "Pas de blague trouvée."))
                else:
                    await interaction.followup.send("❌ Impossible de récupérer une blague")

async def setup(bot):
    await bot.add_cog(Fun(bot))