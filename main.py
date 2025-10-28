import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv
import logging
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Chargement des variables d'environnement
load_dotenv()

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

        # charger la version depuis version.json
        self.version = "unknown"
        try:
            version_file = os.path.join(os.path.dirname(__file__), 'version.json')
            with open(version_file, 'r', encoding='utf-8') as vf:
                vdata = json.load(vf)
                self.version = vdata.get("version", self.version)
        except Exception:
            # gardez "unknown" si échec
            pass

        # Chargement des cogs
        self.initial_extensions = [
            'cogs.moderation',
            'cogs.music',
            'cogs.fun',
            'cogs.utilities',
            'cogs.economy'
        ]

    async def setup_hook(self):
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                print(f'✅ {extension} chargé avec succès')
            except Exception as e:
                print(f'❌ Erreur lors du chargement de {extension}: {e}')
        
        # Synchroniser les commandes slash
        # Par défaut : synchronisation rapide par guild pour que les commandes slash
        # (ex: /play) apparaissent immédiatement sur chaque serveur.
        # Pour désactiver ce comportement, définissez FAST_SYNC_PER_GUILD=0 dans .env
        fast_sync = os.getenv("FAST_SYNC_PER_GUILD", "1").lower() not in ("0", "false", "no")
        if fast_sync:
            for guild in self.guilds:
                try:
                    # sync for this guild to make commands instantly available
                    await self.tree.sync(guild=discord.Object(id=guild.id))
                    print(f"✅ Commandes synchronisées pour le serveur: {guild.name} ({guild.id})")
                except Exception as e:
                    print(f"❌ Erreur lors de la synchro pour {guild.name} ({guild.id}): {e}")
            # Optionnel : on peut aussi lancer une sync globale en arrière-plan si souhaité
            try:
                await self.tree.sync()
                print("✅ Commandes globales synchronisées (peut prendre du temps avant d'apparaître partout)")
            except Exception as e:
                print(f"⚠️ Erreur lors de la synchro globale (non bloquant): {e}")
        else:
            try:
                await self.tree.sync()
                print("✅ Commandes slash synchronisées (mode global)")
            except Exception as e:
                print(f"❌ Erreur lors de la synchro globale: {e}")

    async def on_ready(self):
        print(f'✅ {self.user} est connecté à Discord!')
        print(f'📊 Connecté à {len(self.guilds)} serveurs')
        
        # Statut du bot — inclut la version depuis version.json
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} serveurs | /help | {self.version}"
        )
        await self.change_presence(activity=activity)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Commande non trouvée. Utilisez `/help` pour voir les commandes disponibles.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour cette commande.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ Je n'ai pas les permissions nécessaires pour exécuter cette commande.")
        else:
            await ctx.send(f"❌ Une erreur s'est produite: {error}")

bot = Bot()

# Commande help avec slash
@bot.tree.command(name="help", description="Affiche l'aide complète du bot")
async def help(interaction: discord.Interaction):
    """Affiche l'aide complète"""
    embed = discord.Embed(
        title="📋 Aide du Bot",
        description="Voici toutes les commandes disponibles:",
        color=0x00ff00
    )
    
    # Modération
    embed.add_field(
        name="🛡️ Modération",
        value="`/ban`, `/kick`, `/mute`, `/clear`",
        inline=False
    )
    
    # Musique
    embed.add_field(
        name="🎵 Musique",
        value="`/play`, `/pause`, `/resume`, `/stop`, `/queue`",
        inline=False
    )
    
    # Fun
    embed.add_field(
        name="🎉 Fun",
        value="`/meme`, `/joke`, `/cat`, `/dog`, `/8ball`, `/roll`",
        inline=False
    )
    
    # Utilitaire
    embed.add_field(
        name="🔧 Utilitaire",
        value="`/ping`, `/userinfo`, `/serverinfo`, `/avatar`, `/botinfo`, `/poll`",
        inline=False
    )
    
    # Économie
    embed.add_field(
        name="💰 Économie",
        value="`/balance`, `/daily`, `/work`, `/pay`, `/leaderboard`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Commande de rechargement (keep as prefix command for security)
@bot.command()
@commands.is_owner()
async def reload(ctx, cog: str):
    """Recharge un cog (propriétaire seulement)"""
    try:
        await bot.reload_extension(f'cogs.{cog}')
        await bot.tree.sync()
        await ctx.send(f'✅ {cog} rechargé avec succès!')
    except Exception as e:
        await ctx.send(f'❌ Erreur: {e}')

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Token Discord non trouvé!")
        exit(1)
    
    bot.run(token)