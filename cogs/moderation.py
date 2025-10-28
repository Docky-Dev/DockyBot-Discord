import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.warns_file = os.path.join(data_dir, "warnings.json")
        self.warnings = self.load_warnings()

    def load_warnings(self):
        if os.path.exists(self.warns_file):
            try:
                with open(self.warns_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def save_warnings(self):
        os.makedirs(os.path.dirname(self.warns_file), exist_ok=True)
        with open(self.warns_file, "w", encoding="utf-8") as f:
            json.dump(self.warnings, f, indent=4, ensure_ascii=False)

    def _ensure_guild(self, guild_id):
        gid = str(guild_id)
        if gid not in self.warnings:
            self.warnings[gid] = {}
        return gid

    @app_commands.command(name="ban", description="Bannir un membre du serveur")
    @app_commands.describe(member="Le membre à bannir", reason="La raison du bannissement")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée"):
        """Bannir un membre du serveur"""
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous bannir vous-même!", ephemeral=True)
            return

        # allow server owner to bypass role comparison
        if interaction.guild.owner_id != interaction.user.id and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ Vous ne pouvez pas bannir un membre avec un rôle égal ou supérieur au vôtre!", ephemeral=True)
            return

        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Membre banni",
            description=f"{member.mention} a été banni du serveur.",
            color=0xff0000
        )
        embed.add_field(name="Raison", value=reason)
        embed.add_field(name="Modérateur", value=interaction.user.mention)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kick", description="Expulser un membre du serveur")
    @app_commands.describe(member="Le membre à expulser", reason="La raison de l'expulsion")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée"):
        """Expulser un membre du serveur"""
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous expulser vous-même!", ephemeral=True)
            return

        if interaction.guild.owner_id != interaction.user.id and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ Vous ne pouvez pas expulser un membre avec un rôle égal ou supérieur au vôtre!", ephemeral=True)
            return

        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Membre expulsé",
            description=f"{member.mention} a été expulsé du serveur.",
            color=0xffa500
        )
        embed.add_field(name="Raison", value=reason)
        embed.add_field(name="Modérateur", value=interaction.user.mention)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Supprimer un nombre spécifié de messages (optionnellement avec raison)")
    @app_commands.describe(amount="Nombre de messages à supprimer (1-100)", reason="Raison du purge (optionnel)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100], reason: str = None):
        """Supprimer un nombre spécifié de messages"""
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="🗑️ Purge", description=f"{len(deleted)} messages supprimés.", color=0xffa500)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=True)
        if reason:
            embed.add_field(name="Raison", value=reason, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mute", description="Rendre muet un membre")
    @app_commands.describe(member="Le membre à rendre muet", reason="La raison", duration="Durée en minutes (optionnel)")
    @app_commands.default_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée", duration: int = None):
        """Rendre muet un membre"""
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous rendre muet vous-même!", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ Vous ne pouvez pas rendre muet un membre avec un rôle égal ou supérieur au vôtre!", ephemeral=True)
            return
        
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        
        if not muted_role:
            # Créer le rôle Muted s'il n'existe pas
            muted_role = await interaction.guild.create_role(name="Muted", reason="Création du rôle Muted par le bot")

            # Désactiver les permissions pour tous les salons (texte + voix)
            for channel in interaction.guild.channels:
                try:
                    await channel.set_permissions(
                        muted_role,
                        send_messages=False,
                        add_reactions=False,
                        speak=False,
                        connect=False
                    )
                except Exception:
                    # certaines permissions peuvent échouer selon le type de salon; ignorer
                    continue

        await member.add_roles(muted_role, reason=reason)
        embed = discord.Embed(
            title="🔇 Membre rendu muet",
            description=f"{member.mention} a été rendu muet.",
            color=0xffff00
        )
        embed.add_field(name="Raison", value=reason)
        if duration:
            embed.add_field(name="Durée", value=f"{duration} minutes")
        embed.add_field(name="Modérateur", value=interaction.user.mention)
        
        await interaction.response.send_message(embed=embed)
        
        # Si une durée est spécifiée, programmer le unmute
        if duration:
            await asyncio.sleep(duration * 60)
            if muted_role in member.roles:
                await member.remove_roles(muted_role)
                try:
                    await member.send(f"🔊 Vous n'êtes plus muet sur **{interaction.guild.name}**!")
                except:
                    pass

    @app_commands.command(name="unmute", description="Retirer le muet d'un membre")
    @app_commands.describe(member="Le membre à unmute")
    @app_commands.default_permissions(manage_roles=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        """Retirer le muet d'un membre"""
        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(f"🔊 {member.mention} n'est plus muet!")
        else:
            await interaction.response.send_message("❌ Ce membre n'est pas muet.", ephemeral=True)

    @app_commands.command(name="warn", description="Avertir un membre")
    @app_commands.describe(member="Le membre à avertir", reason="La raison de l'avertissement")
    @app_commands.default_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison spécifiée"):
        """Avertir un membre et stocker l'avertissement"""
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous avertir vous-même!", ephemeral=True)
            return

        gid = self._ensure_guild(interaction.guild.id)
        uid = str(member.id)
        self.warnings[gid].setdefault(uid, []).append({
            "moderator": str(interaction.user.id),
            "reason": reason,
            "timestamp": discord.utils.utcnow().isoformat()
        })
        self.save_warnings()

        await interaction.response.send_message(f"⚠️ {member.mention} a été averti. Raison: {reason}")

        # Optionnel: actions automatisées selon le nombre d'avertissements
        count = len(self.warnings[gid][uid])
        if count >= 3:
            try:
                await member.kick(reason="Trop d'avertissements")
                await interaction.followup.send(f"🔨 {member.mention} a été expulsé automatiquement (3+ avertissements).")
            except Exception:
                pass

    @app_commands.command(name="warnings", description="Voir les avertissements d'un membre")
    @app_commands.describe(member="Le membre à consulter")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        """Afficher les avertissements d'un membre"""
        if not member:
            member = interaction.user
        gid = str(interaction.guild.id)
        uid = str(member.id)
        guild_warns = self.warnings.get(gid, {})
        user_warns = guild_warns.get(uid, [])
        if not user_warns:
            await interaction.response.send_message("✅ Aucun avertissement pour ce membre.", ephemeral=True)
            return

        embed = discord.Embed(title=f"⚠️ Avertissements de {member.display_name}", color=0xffd700)
        for i, w in enumerate(user_warns, 1):
            mod = self.bot.get_user(int(w["moderator"]))
            ts = w.get("timestamp", "")[:19].replace('T', ' ')
            embed.add_field(name=f"{i}. Par {mod or w['moderator']} • {ts}", value=f"{w['reason']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearwarnings", description="Effacer les avertissements d'un membre")
    @app_commands.describe(member="Le membre dont vous voulez effacer les avertissements")
    @app_commands.default_permissions(kick_members=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        """Effacer tous les avertissements d'un membre"""
        gid = str(interaction.guild.id)
        uid = str(member.id)
        if gid in self.warnings and uid in self.warnings[gid]:
            del self.warnings[gid][uid]
            self.save_warnings()
            await interaction.response.send_message(f"✅ Tous les avertissements de {member.mention} ont été effacés.")
        else:
            await interaction.response.send_message("❌ Ce membre n'a aucun avertissement.", ephemeral=True)

    @app_commands.command(name="tempban", description="Bannir temporairement un membre")
    @app_commands.describe(member="Le membre à bannir", duration="Durée en minutes", reason="Raison")
    @app_commands.default_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: int = 60, reason: str = "Aucune raison spécifiée"):
        """Bannir temporairement un membre puis le débannir après duration (minutes)"""
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous bannir vous-même!", ephemeral=True)
            return
        if interaction.guild.owner_id != interaction.user.id and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ Vous ne pouvez pas bannir un membre avec un rôle égal ou supérieur au vôtre!", ephemeral=True)
            return

        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} banni pendant {duration} minutes. Raison: {reason}")
        # schedule unban
        async def _unban_later(guild, user_id, wait):
            await asyncio.sleep(wait)
            try:
                await guild.unban(discord.Object(id=user_id))
            except Exception:
                pass
        self.bot.loop.create_task(_unban_later(interaction.guild, member.id, duration * 60))

async def setup(bot):
    await bot.add_cog(Moderation(bot))