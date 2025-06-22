# cogs/puntos.py
import discord
from discord import app_commands
from discord.ext import commands
import json

DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class Puntos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_points(self, user_id: str, amount: int):
        if amount == 0:
            return
        data = load_data()
        data[user_id] = data.get(user_id, 0) + amount
        save_data(data)
        print(f"Se añadieron {amount} puntos al usuario {user_id}.")

    async def _build_ranking_embed(self):
        points = load_data()
        if not points:
            return None
        sorted_points = sorted(points.items(), key=lambda item: item[1], reverse=True)
        embed = discord.Embed(title="🏆 Ranking de Puntos 🏆", description="Tabla de clasificación general.", color=discord.Color.gold())
        rank_list = []
        for i, (user_id, score) in enumerate(sorted_points[:20]):
            try:
                user = await self.bot.fetch_user(int(user_id))
                rank_list.append(f"**{i+1}.** {user.mention} - `{score}` puntos")
            except discord.NotFound:
                rank_list.append(f"**{i+1}.** Usuario Desconocido (`{user_id}`) - `{score}` puntos")
        embed.add_field(name="Top 20", value="\n".join(rank_list) or "Nadie ha puntuado aún.", inline=False)
        return embed

    @app_commands.command(name="rank", description="Muestra la tabla de clasificación de puntos.")
    async def show_rank(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ranking_embed = await self._build_ranking_embed()
        if ranking_embed:
            await interaction.followup.send(embed=ranking_embed)
        else:
            await interaction.followup.send("Aún no se ha registrado ningún punto.")

async def setup(bot):
    await bot.add_cog(Puntos(bot))