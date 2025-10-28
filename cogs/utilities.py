import discord
from discord.ext import commands
from discord import app_commands
import datetime
import platform
import time
import re

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="ping", description="Afficher la latence du bot")
    async def ping(self, interaction: discord.Interaction):
        """Afficher la latence du bot"""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="🏓 Pong!", color=0x00ff00)
        embed.add_field(name="Latence", value=f"{latency}ms")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Afficher les informations d'un utilisateur")
    @app_commands.describe(member="L'utilisateur dont vous voulez les informations")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        """Afficher les informations d'un utilisateur"""
        if not member:
            member = interaction.user

        display = member.display_name
        embed = discord.Embed(title=f"👤 Informations de {display}", color=member.color or 0x00ff00)
        embed.set_thumbnail(url=member.avatar.url if getattr(member, "avatar", None) else member.default_avatar.url)
        
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Surnom", value=member.nick or "Aucun", inline=True)
        embed.add_field(name="Statut", value=str(member.status).title(), inline=True)
        
        embed.add_field(
            name="Compte créé le", 
            value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"), 
            inline=True
        )
        embed.add_field(
            name="A rejoint le", 
            value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S") if member.joined_at else "N/A", 
            inline=True
        )
        
        roles = [role.mention for role in member.roles[1:]]  # Exclure @everyone
        embed.add_field(
            name=f"Rôles ({len(roles)})", 
            value=' '.join(roles) if roles else "Aucun", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Afficher les informations du serveur")
    async def serverinfo(self, interaction: discord.Interaction):
        """Afficher les informations du serveur"""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🏠 Informations de {guild.name}", color=0x00ff00)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
        embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        
        embed.add_field(name="Membres", value=guild.member_count, inline=True)
        embed.add_field(name="Salons", value=len(guild.channels), inline=True)
        embed.add_field(name="Rôles", value=len(guild.roles), inline=True)
        
        embed.add_field(name="Boost", value=f"Niveau {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverstats", description="Statistiques rapides du serveur")
    async def serverstats(self, interaction: discord.Interaction):
        """Afficher des statistiques rapides sur le serveur"""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        # Compter les membres par statut
        statuses = {"online":0, "offline":0, "idle":0, "dnd":0}
        for member in guild.members:
            s = str(member.status)
            statuses[s] = statuses.get(s,0) + 1

        # Compter les salons texte et voix
        text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])

        embed = discord.Embed(title=f"Statistiques de {guild.name}", color=0x00ff00)
        embed.add_field(name="Membres", value=guild.member_count, inline=True)
        embed.add_field(name="Online", value=statuses.get("online",0), inline=True)
        embed.add_field(name="Idle", value=statuses.get("idle",0), inline=True)
        embed.add_field(name="DND", value=statuses.get("dnd",0), inline=True)
        embed.add_field(name="Offline", value=statuses.get("offline",0), inline=True)
        embed.add_field(name="Salons texte", value=text_channels, inline=True)
        embed.add_field(name="Salons voix", value=voice_channels, inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Afficher l'avatar d'un utilisateur")
    @app_commands.describe(member="L'utilisateur dont vous voulez voir l'avatar")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        """Afficher l'avatar d'un utilisateur"""
        if not member:
            member = interaction.user
        
        embed = discord.Embed(title=f"🖼️ Avatar de {member}", color=member.color)
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Afficher les informations du bot")
    async def botinfo(self, interaction: discord.Interaction):
        """Afficher les informations du bot"""
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(title="🤖 Informations du Bot", color=0x00ff00)
        # set thumbnail only if available
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        else:
            embed.set_thumbnail(url=self.bot.user.default_avatar.url)
        
        embed.add_field(name="Version", value=getattr(self.bot, "version", "unknown"), inline=True)
        embed.add_field(name="Développeur", value="Drayko", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        
        embed.add_field(name="Serveurs", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Utilisateurs", value=len(self.bot.users), inline=True)
        embed.add_field(name="Uptime", value=f"{days}j {hours}h {minutes}m {seconds}s", inline=True)
        
        embed.add_field(name="Latence", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Créer un sondage simple")
    @app_commands.describe(question="La question du sondage")
    async def poll(self, interaction: discord.Interaction, question: str):
        """Créer un sondage simple"""
        embed = discord.Embed(title="📊 Sondage", description=question, color=0x00ff00)
        embed.set_footer(text=f"Sondage créé par {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        await message.add_reaction("❌")

    @app_commands.command(name="invite", description="Obtenir le lien d'invitation du bot")
    async def invite(self, interaction: discord.Interaction):
        """Retourne un lien pour inviter le bot sur un serveur"""
        client_id = self.bot.user.id if self.bot.user else "client_id"
        perms = 8  # administrateur par défaut; changez si nécessaire
        url = f"https://discord.com/oauth2/authorize?client_id={client_id}&scope=bot%20applications.commands&permissions={perms}"
        await interaction.response.send_message(f"🔗 Lien d'invitation: {url}", ephemeral=True)

    @app_commands.command(name="emoji", description="Afficher un emoji en grand")
    @app_commands.describe(emoji="Emoji personnalisé ou unicode")
    async def emoji(self, interaction: discord.Interaction, emoji: str):
        """Affiche un emoji personnalisé en grand (ou renvoie l'emoji unicode)"""
        # custom emoji format: <a:name:id> or <name:id>
        match = re.search(r"<a?:\w+:(\d+)>", emoji)
        if match:
            eid = int(match.group(1))
            e = discord.utils.get(interaction.guild.emojis, id=eid)
            if e:
                await interaction.response.send_message(e.url)
                return
        # else try to send the raw emoji string (unicode)
        await interaction.response.send_message(emoji)

    @app_commands.command(name="bothelp", description="Afficher l'aide du bot (liste des commandes principales)")
    async def bothelp(self, interaction: discord.Interaction):
        """Liste simple des commandes"""
        embed = discord.Embed(title="Aide - Commandes (V1)", color=0x00ff00)
        embed.add_field(name="/ping", value="Afficher la latence du bot", inline=False)
        embed.add_field(name="/userinfo [membre]", value="Afficher les informations d'un utilisateur", inline=False)
        embed.add_field(name="/serverinfo", value="Afficher les informations du serveur", inline=False)
        embed.add_field(name="/balance /daily /work /pay", value="Commandes d'économie", inline=False)
        embed.set_footer(text="Pour plus de détails, consultez les commandes du bot dans Discord.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="feedback", description="Envoyer un feedback au propriétaire du bot")
    @app_commands.describe(message="Votre message")
    async def feedback(self, interaction: discord.Interaction, message: str):
        """Envoyer un feedback au propriétaire du bot"""
        owner = (await self.bot.application_info()).owner
        try:
            await owner.send(f"Feedback de {interaction.user} ({interaction.user.id}) sur {interaction.guild.name if interaction.guild else 'DM'}:\n{message}")
            await interaction.response.send_message("✅ Feedback envoyé au propriétaire.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ Impossible d'envoyer le feedback (DM bloqué).", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utilities(bot))