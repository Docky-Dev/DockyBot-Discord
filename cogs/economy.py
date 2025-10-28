import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import asyncio
import os
from datetime import datetime, timedelta

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # place data files in a dedicated data/ folder inside the project
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.data_file = os.path.join(data_dir, 'economy_data.json')
        self.data = self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                # If file is corrupted or unreadable, start fresh but keep file path
                return {}
        return {}

    def save_data(self):
        # ensure directory exists
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user_data(self, user_id):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {
                'balance': 100,
                'last_daily': None,
                'last_work': None,
                'transactions': []  # historique simple
            }
        # ensure transactions key exists for older files
        if 'transactions' not in self.data[str(user_id)]:
            self.data[str(user_id)]['transactions'] = []
        return self.data[str(user_id)]

    def _add_transaction(self, user_id, ttype, amount, note=None):
        uid = str(user_id)
        user = self.get_user_data(user_id)
        user['transactions'].append({
            'time': datetime.utcnow().isoformat(),
            'type': ttype,
            'amount': amount,
            'note': note or ""
        })
        # keep history reasonable length
        if len(user['transactions']) > 200:
            user['transactions'] = user['transactions'][-200:]
        self.save_data()

    @app_commands.command(name="balance", description="Afficher le solde d'un utilisateur")
    @app_commands.describe(member="L'utilisateur dont vous voulez voir le solde")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        """Afficher le solde d'un utilisateur"""
        if not member:
            member = interaction.user
        
        user_data = self.get_user_data(member.id)
        embed = discord.Embed(title=f"💰 Solde de {member}", color=0xffd700)
        embed.add_field(name="Balance", value=f"{user_data['balance']} 💰")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Récupérer sa récompense quotidienne")
    async def daily(self, interaction: discord.Interaction):
        """Récupérer sa récompense quotidienne"""
        user_data = self.get_user_data(interaction.user.id)
        now = datetime.now()
        
        if user_data['last_daily']:
            last_daily = datetime.fromisoformat(user_data['last_daily'])
            if now - last_daily < timedelta(hours=24):
                next_daily = last_daily + timedelta(hours=24)
                await interaction.response.send_message(f"❌ Vous avez déjà récupéré votre récompense quotidienne! Prochaine récompense: {next_daily.strftime('%H:%M')}", ephemeral=True)
                return
        
        reward = random.randint(50, 150)
        user_data['balance'] += reward
        user_data['last_daily'] = now.isoformat()
        self._add_transaction(interaction.user.id, "daily", reward, "Récompense quotidienne")
        self.save_data()
        
        embed = discord.Embed(title="🎁 Récompense quotidienne!", color=0xffd700)
        embed.add_field(name="Montant reçu", value=f"{reward} 💰")
        embed.add_field(name="Nouveau solde", value=f"{user_data['balance']} 💰")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Travailler pour gagner de l'argent")
    async def work(self, interaction: discord.Interaction):
        """Travailler pour gagner de l'argent"""
        user_data = self.get_user_data(interaction.user.id)
        now = datetime.now()
        
        if user_data['last_work']:
            last_work = datetime.fromisoformat(user_data['last_work'])
            if now - last_work < timedelta(hours=1):
                next_work = last_work + timedelta(hours=1)
                await interaction.response.send_message(f"❌ Vous devez attendre avant de retravailler! Prochain travail: {next_work.strftime('%H:%M')}", ephemeral=True)
                return
        
        jobs = [
            "développeur",
            "cuisinier",
            "médecin",
            "professeur",
            "artiste",
            "musicien",
            "streamer",
            "youtuber"
        ]
        
        job = random.choice(jobs)
        salary = random.randint(20, 80)
        user_data['balance'] += salary
        user_data['last_work'] = now.isoformat()
        self._add_transaction(interaction.user.id, "work", salary, f"Travail en tant que {job}")
        self.save_data()
        
        embed = discord.Embed(title="💼 Travail", color=0x00ff00)
        embed.add_field(name="Métier", value=job.title(), inline=True)
        embed.add_field(name="Salaire", value=f"{salary} 💰", inline=True)
        embed.add_field(name="Nouveau solde", value=f"{user_data['balance']} 💰", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="Envoyer de l'argent à un autre utilisateur")
    @app_commands.describe(member="L'utilisateur à qui envoyer de l'argent", amount="Le montant à envoyer")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 10000]):
        """Envoyer de l'argent à un autre utilisateur"""
        if amount <= 0:
            await interaction.response.send_message("❌ Le montant doit être positif!", ephemeral=True)
            return
        
        sender_data = self.get_user_data(interaction.user.id)
        receiver_data = self.get_user_data(member.id)
        
        if sender_data['balance'] < amount:
            await interaction.response.send_message("❌ Solde insuffisant!", ephemeral=True)
            return
        
        if member == interaction.user:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous envoyer de l'argent à vous-même!", ephemeral=True)
            return
        
        sender_data['balance'] -= amount
        receiver_data['balance'] += amount
        self._add_transaction(interaction.user.id, "pay_sent", -amount, f"À {member.id}")
        self._add_transaction(member.id, "pay_received", amount, f"De {interaction.user.id}")
        self.save_data()
        
        embed = discord.Embed(title="💸 Transfert d'argent", color=0x00ff00)
        embed.add_field(name="De", value=interaction.user.mention, inline=True)
        embed.add_field(name="À", value=member.mention, inline=True)
        embed.add_field(name="Montant", value=f"{amount} 💰", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Afficher le classement des richesses")
    async def leaderboard(self, interaction: discord.Interaction):
        """Afficher le classement des richesses"""
        sorted_users = sorted(
            self.data.items(),
            key=lambda x: x[1]['balance'],
            reverse=True
        )[:10]
        
        embed = discord.Embed(title="🏆 Classement des richesses", color=0xffd700)
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            user = self.bot.get_user(int(user_id))
            username = user.name if user else f"Utilisateur {user_id}"
            embed.add_field(
                name=f"{i}. {username}",
                value=f"{data['balance']} 💰",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gamble", description="Parier une somme pour tenter de gagner")
    @app_commands.describe(amount="Montant à parier (1-10000)")
    async def gamble(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 10000]):
        """Parier une somme: possibilité de doubler ou de tout perdre"""
        user_data = self.get_user_data(interaction.user.id)
        if amount > user_data['balance']:
            await interaction.response.send_message("❌ Solde insuffisant!", ephemeral=True)
            return

        # retirer la mise initiale
        user_data['balance'] -= amount

        # Probabilités: 10% jackpot x5, 45% double (x2), reste perte
        roll = random.random()
        if roll < 0.10:
            # Jackpot x5 (le joueur récupère 5x sa mise)
            payout = amount * 5
            user_data['balance'] += payout
            net = payout - amount
            result_text = f"🎉 JACKPOT! Vous gagnez {payout} 💰 (net +{net} 💰)"
        elif roll < 0.55:
            # Double
            payout = amount * 2
            user_data['balance'] += payout
            net = payout - amount
            result_text = f"✅ Vous doublez votre mise et gagnez {payout} 💰 (net +{net} 💰)"
        else:
            # Perte (la mise est déjà retirée)
            result_text = f"💥 Vous perdez votre mise de {amount} 💰"

        # après calcul final des gains/pertes, enregistrer
        if "Perte" in result_text or roll >= 0.55:
            self._add_transaction(interaction.user.id, "gamble_loss", -amount, "Gamble perte")
        else:
            # net = (payout - amount) déjà calculé dans result_text; enregistrer net gain
            net_change = user_data['balance'] - (user_data['balance'] - (payout if 'payout' in locals() else 0))
            # simpler: store total effect
            if roll < 0.10:
                self._add_transaction(interaction.user.id, "gamble_jackpot", payout - amount, "Jackpot x5")
            else:
                self._add_transaction(interaction.user.id, "gamble_win", payout - amount, "Double x2")
        self.save_data()
        embed = discord.Embed(title="🎲 Gamble", description=result_text, color=0x00ff00)
        embed.add_field(name="Nouveau solde", value=f"{user_data['balance']} 💰")
        await interaction.response.send_message(embed=embed)

    # --- nouveaux admin commands ---

    @app_commands.command(name="give", description="Donner de l'argent à un utilisateur (admin)")
    @app_commands.default_permissions(administrator=True)
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 100000]):
        """Donner de l'argent à un utilisateur (admin)"""
        user_data = self.get_user_data(member.id)
        user_data['balance'] += amount
        self._add_transaction(member.id, "admin_give", amount, f"Par {interaction.user.id}")
        self.save_data()
        await interaction.response.send_message(f"✅ {amount} 💰 ajoutés à {member.mention}")

    @app_commands.command(name="setbalance", description="Définir le solde d'un utilisateur (admin)")
    @app_commands.default_permissions(administrator=True)
    async def setbalance(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 0, 10_000_000]):
        """Définir le solde exact d'un utilisateur (admin)"""
        user_data = self.get_user_data(member.id)
        old = user_data['balance']
        user_data['balance'] = amount
        self._add_transaction(member.id, "admin_set", amount - old, f"Set by {interaction.user.id}")
        self.save_data()
        await interaction.response.send_message(f"✅ Solde de {member.mention} réglé sur {amount} 💰 (ancien: {old})")

    @app_commands.command(name="resetbalance", description="Remettre le solde à la valeur initiale (admin)")
    @app_commands.default_permissions(administrator=True)
    async def resetbalance(self, interaction: discord.Interaction, member: discord.Member):
        user_data = self.get_user_data(member.id)
        old = user_data['balance']
        user_data['balance'] = 100
        self._add_transaction(member.id, "admin_reset", 100 - old, f"Reset by {interaction.user.id}")
        self.save_data()
        await interaction.response.send_message(f"✅ Solde de {member.mention} remis à 100 💰")

    @app_commands.command(name="statement", description="Afficher les dernières transactions d'un utilisateur")
    @app_commands.describe(member="Optionnel: le membre à consulter")
    async def statement(self, interaction: discord.Interaction, member: discord.Member = None):
        if not member:
            member = interaction.user
        user_data = self.get_user_data(member.id)
        tx = user_data.get('transactions', [])[-10:]
        if not tx:
            await interaction.response.send_message("📄 Aucune transaction récente.", ephemeral=True)
            return
        desc_lines = []
        for t in reversed(tx):
            ts = t['time'].replace('T', ' ')[:19]
            amt = t['amount']
            desc_lines.append(f"[{ts}] {t['type']} {amt:+} — {t.get('note','')}")
        embed = discord.Embed(title=f"📄 Historique de {member}", description="\n".join(desc_lines), color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))