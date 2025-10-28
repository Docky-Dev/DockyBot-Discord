import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import random

# Configuration yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        # Create a local YoutubeDL instance so we can inject cookiefile if provided via env
        opts = ytdl_format_options.copy()
        cookiefile = os.getenv('YTDL_COOKIEFILE')
        if cookiefile:
            opts['cookiefile'] = cookiefile

        local_ytdl = yt_dlp.YoutubeDL(opts)

        try:
            data = await loop.run_in_executor(None, lambda: local_ytdl.extract_info(url, download=not stream))
        except Exception as e:
            # propagate a clearer error for the caller
            raise RuntimeError(f"yt-dlp extraction failed: {e}")

        if not data:
            raise RuntimeError("Aucune donnée extraite (stream non supporté ou URL invalide)")

        if 'entries' in data:
            # playlists -> take first entry
            data = data['entries'][0]

        # when streaming, data['url'] points to a direct media url for ffmpeg
        filename = data['url'] if stream else local_ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # guild_id -> [YTDLSource,...]
        self.repeat = {}  # guild_id -> bool

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        if guild_id not in self.repeat:
            self.repeat[guild_id] = False
        return self.queues[guild_id]

    @app_commands.command(name="play", description="Jouer de la musique depuis YouTube")
    @app_commands.describe(query="URL ou titre de la musique")
    async def play(self, interaction: discord.Interaction, query: str):
        """Jouer de la musique depuis YouTube"""
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Vous devez être dans un salon vocal!", ephemeral=True)
            return

        await interaction.response.defer()
        voice_client = interaction.guild.voice_client

        if not voice_client:
            try:
                voice_client = await interaction.user.voice.channel.connect()
            except RuntimeError:
                await interaction.followup.send(
                    "❌ La lecture vocale n'est pas disponible (PyNaCl manquant ou configuration audio). "
                    "Installez PyNaCl (`pip install pynacl`) et assurez-vous que FFmpeg est installé.", ephemeral=True
                )
                return
            except Exception as e:
                await interaction.followup.send(f"❌ Impossible de rejoindre le salon vocal: {e}", ephemeral=True)
                return

        try:
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            queue = self.get_queue(interaction.guild.id)
            queue.append(player)

            if not voice_client.is_playing():
                # Start playback of the first item (async helper will schedule chaining)
                await self._play_next(interaction.guild.id, voice_client)
                await interaction.followup.send(f"🎵 En train de jouer: **{player.title}**")
            else:
                await interaction.followup.send(f"✅ Ajouté à la file d'attente: **{player.title}**")
        except RuntimeError as e:
            msg = str(e).lower()
            if "cookies" in msg or "cookiefile" in msg or "sign in to confirm" in msg:
                await interaction.followup.send(
                    "❌ YouTube nécessite parfois des cookies pour cette vidéo. "
                    "Exportez cookies.txt et définissez la variable d'environnement YTDL_COOKIEFILE=/chemin/vers/cookies.txt", ephemeral=True
                )
            else:
                await interaction.followup.send(f"❌ Erreur: {e}", ephemeral=True)

    async def _play_next(self, guild_id, voice_client):
        """Internal helper: play next track from queue. The after callback schedules this on the loop."""
        queue = self.get_queue(guild_id)
        if queue:
            player = queue.pop(0)

            def _after(err):
                if err:
                    print(f"Player error: {err}")
                # if repeat enabled, recreate a source from player.data (stream case)
                try:
                    if self.repeat.get(guild_id, False):
                        # attempt to recreate source for repeating
                        try:
                            data = getattr(player, "data", None)
                            if data:
                                src = discord.FFmpegPCMAudio(data['url'], **ffmpeg_options) if data.get('url') else None
                                if src:
                                    new_player = YTDLSource(src, data=data)
                                    # append to front so it plays next
                                    self.queues[guild_id].insert(0, new_player)
                        except Exception as e:
                            print(f"repeat recreate failed: {e}")
                    asyncio.run_coroutine_threadsafe(self._play_next(guild_id, voice_client), self.bot.loop)
                except Exception as exc:
                    print(f"Failed to schedule next track: {exc}")

            voice_client.play(player, after=_after)

    @app_commands.command(name="pause", description="Mettre en pause la musique")
    async def pause(self, interaction: discord.Interaction):
        """Mettre en pause la musique"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ Musique en pause")
        else:
            await interaction.response.send_message("❌ Aucune musique en cours de lecture.", ephemeral=True)

    @app_commands.command(name="resume", description="Reprendre la musique")
    async def resume(self, interaction: discord.Interaction):
        """Reprendre la musique"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ Musique reprise")
        else:
            await interaction.response.send_message("❌ Aucune musique en pause.", ephemeral=True)

    @app_commands.command(name="stop", description="Arrêter la musique et vider la file d'attente")
    async def stop(self, interaction: discord.Interaction):
        """Arrêter la musique et vider la file d'attente"""
        voice_client = interaction.guild.voice_client
        if voice_client:
            self.queues[interaction.guild.id] = []
            voice_client.stop()
            await interaction.response.send_message("⏹️ Musique arrêtée et file d'attente vidée")
        else:
            await interaction.response.send_message("❌ Je ne suis pas dans un salon vocal.", ephemeral=True)

    @app_commands.command(name="skip", description="Passer à la musique suivante")
    async def skip(self, interaction: discord.Interaction):
        """Passer à la musique suivante"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Musique passée")
        else:
            await interaction.response.send_message("❌ Aucune musique en cours de lecture.", ephemeral=True)

    @app_commands.command(name="queue", description="Afficher la file d'attente")
    async def queue(self, interaction: discord.Interaction):
        """Afficher la file d'attente"""
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            await interaction.response.send_message("📭 La file d'attente est vide")
            return
        
        embed = discord.Embed(title="📋 File d'attente", color=0x00ff00)
        for i, player in enumerate(queue[:10], 1):
            embed.add_field(name=f"{i}.", value=player.title, inline=False)
        
        if len(queue) > 10:
            embed.set_footer(text=f"... et {len(queue) - 10} autres musiques")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Faire quitter le bot du salon vocal")
    async def leave(self, interaction: discord.Interaction):
        """Faire quitter le bot du salon vocal"""
        voice_client = interaction.guild.voice_client
        if voice_client:
            self.queues[interaction.guild.id] = []
            await voice_client.disconnect()
            await interaction.response.send_message("👋 Déconnecté du salon vocal")
        else:
            await interaction.response.send_message("❌ Je ne suis pas dans un salon vocal.", ephemeral=True)

    @app_commands.command(name="nowplaying", description="Afficher la musique en cours")
    async def nowplaying(self, interaction: discord.Interaction):
        """Afficher la musique en cours"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing() and hasattr(voice_client, "source") and getattr(voice_client.source, "title", None):
            title = getattr(voice_client.source, "title", "Inconnu")
            await interaction.response.send_message(f"🎶 En cours: **{title}**")
        else:
            await interaction.response.send_message("❌ Aucune musique en cours.", ephemeral=True)

    @app_commands.command(name="volume", description="Changer le volume du bot (0-200)")
    @app_commands.describe(value="Volume en pourcentage (ex: 50 pour 50%)")
    async def volume(self, interaction: discord.Interaction, value: app_commands.Range[int, 0, 200]):
        """Changer le volume si supporté"""
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("❌ Je ne suis pas dans un salon vocal.", ephemeral=True)
            return

        src = getattr(voice_client, "source", None)
        if src and hasattr(src, "volume"):
            src.volume = value / 100
            await interaction.response.send_message(f"🔊 Volume réglé à {value}%")
        else:
            await interaction.response.send_message("❌ Impossible de changer le volume pour cette source.", ephemeral=True)

    @app_commands.command(name="shuffle", description="Mélanger la file d'attente")
    async def shuffle(self, interaction: discord.Interaction):
        """Mélanger la file d'attente"""
        q = self.get_queue(interaction.guild.id)
        if not q:
            await interaction.response.send_message("📭 La file d'attente est vide", ephemeral=True)
            return
        random.shuffle(q)
        await interaction.response.send_message("🔀 File d'attente mélangée")

    @app_commands.command(name="remove", description="Retirer une musique de la file d'attente par index")
    @app_commands.describe(index="Index (1-based) de la musique à retirer")
    async def remove(self, interaction: discord.Interaction, index: int):
        """Retirer une musique de la file d'attente par index"""
        q = self.get_queue(interaction.guild.id)
        if not q or index < 1 or index > len(q):
            await interaction.response.send_message("❌ Index invalide", ephemeral=True)
            return
        removed = q.pop(index - 1)
        await interaction.response.send_message(f"🗑️ Retiré: **{getattr(removed, 'title', 'Inconnu')}**")

    @app_commands.command(name="repeat", description="Basculer le mode repeat pour la guild")
    async def repeat_cmd(self, interaction: discord.Interaction):
        """Basculer le mode repeat pour la guild"""
        gid = interaction.guild.id
        self.repeat[gid] = not self.repeat.get(gid, False)
        await interaction.response.send_message(f"🔁 Repeat {'activé' if self.repeat[gid] else 'désactivé'}")

async def setup(bot):
    await bot.add_cog(Music(bot))