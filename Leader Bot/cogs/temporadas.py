# cogs/temporadas.py (VERSIÓN FINAL Y CORREGIDA)
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import re
from datetime import datetime, timedelta
import traceback

# --- CONFIGURACIÓN ---
ADMIN_ROLE_ID = 1311780240435052607 # ⚠️ REEMPLAZA ESTO
ANNOUNCEMENT_CHANNEL_ID = 1386147829961195720 # ⚠️ REEMPLAZA ESTO
SEASONS_CATEGORY_ID = 1311780241873830016 # ⚠️ REEMPLAZA ESTO

SEASON_DATA_FILE = 'season_data.json'
POINTS_DATA_FILE = 'data.json'

def load_season_data():
    try:
        with open(SEASON_DATA_FILE, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {'active': False, 'name': None, 'end_date': None, 'season_number': 0, 'channel_id': None}
def save_season_data(data):
    with open(SEASON_DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

class Temporadas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_season_end.start()

    def cog_unload(self):
        self.check_season_end.cancel()

    @tasks.loop(hours=1)
    async def check_season_end(self):
        await self.bot.wait_until_ready()
        season_data = load_season_data()
        if not season_data.get('active'): return
        end_date = datetime.fromisoformat(season_data['end_date'])
        if datetime.utcnow() >= end_date:
            print(f"Fin de temporada '{season_data['name']}' detectado automáticamente.")
            # Intenta obtener el servidor de alguna forma. Si el bot está en un solo servidor, esto funciona.
            if self.bot.guilds:
                guild = self.bot.guilds[0]
                channel = guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if channel:
                    await self.end_season_logic(guild, channel, season_data)

    async def archive_season_channel(self, guild: discord.Guild, season_data: dict):
        channel_id = season_data.get('channel_id')
        if not channel_id: return
        channel = guild.get_channel(channel_id)
        if not channel: return
        try:
            old_name = channel.name
            new_name = f"z-season-{season_data.get('season_number', 'X')}-{old_name}"
            everyone_role = guild.default_role
            overwrite = channel.overwrites_for(everyone_role)
            overwrite.send_messages = False
            await channel.edit(name=new_name, overwrites={everyone_role: overwrite})
            print(f"Canal '{old_name}' archivado como '{new_name}'.")
        except discord.Forbidden: print(f"Error: No tengo permisos para editar el canal {channel.name}.")
        except Exception as e: print(f"Ocurrió un error al archivar el canal: {e}")

    # --- LÓGICA DE FINALIZACIÓN (CORREGIDA) ---
    async def end_season_logic(self, guild: discord.Guild, channel: discord.TextChannel, season_data: dict):
        """Lógica centralizada para terminar una temporada."""
        await channel.send(f"🏁 **¡La Temporada '{season_data['name']}' ha finalizado!** 🏁\nAquí está el ranking final:")
        
        # --- ¡ESTA ES LA PARTE CORREGIDA Y CORRECTA! ---
        # 1. Obtenemos el Cog de Puntos
        puntos_cog = self.bot.get_cog('Puntos')
        if puntos_cog:
            # 2. Llamamos a nuestra nueva función interna para que construya el embed
            final_ranking_embed = await puntos_cog._build_ranking_embed()
            if final_ranking_embed:
                # 3. Y lo enviamos
                await channel.send(embed=final_ranking_embed)
            else:
                await channel.send("No se registraron puntos en esta temporada.")

        # El resto de la lógica para archivar y resetear
        await self.archive_season_channel(guild, season_data)

        season_number = season_data.get('season_number', 'X')
        archive_file_name = f'season-{season_number}-data.json'
        if os.path.exists(POINTS_DATA_FILE):
            os.rename(POINTS_DATA_FILE, archive_file_name)
            await channel.send(f"Los datos de esta temporada han sido archivados en `{archive_file_name}`.")
        
        with open(POINTS_DATA_FILE, 'w') as f: json.dump({}, f)
        save_season_data({'active': False, 'name': None, 'end_date': None, 'season_number': season_number, 'channel_id': None})

    # --- Grupo de Comandos /season ---
    season_group = app_commands.Group(name="season", description="Comandos para gestionar las temporadas del ranking.")

    @season_group.command(name="start", description="Inicia una nueva temporada y crea un canal para ella.")
    @app_commands.describe(duracion="Duración (ej: 30d, 4w, 24h).", nombre="El nombre para esta temporada.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def season_start(self, interaction: discord.Interaction, duracion: str, nombre: str):
        season_data = load_season_data()
        if season_data['active']:
            return await interaction.response.send_message(f"❌ Ya hay una temporada activa. Termínala primero.", ephemeral=True)
        try:
            value = int(re.match(r'(\d+)', duracion).group(1)); unit = re.search(r'([a-zA-Z])', duracion).group(1).lower()
            if unit == 'd': delta = timedelta(days=value)
            elif unit == 'w': delta = timedelta(weeks=value)
            elif unit == 'h': delta = timedelta(hours=value)
            else: raise ValueError
        except (AttributeError, ValueError):
            return await interaction.response.send_message("❌ Formato de duración inválido.", ephemeral=True)
        await interaction.response.defer()
        guild = interaction.guild
        await self.archive_season_channel(guild, season_data)
        category = guild.get_channel(SEASONS_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.followup.send("❌ Error: No se encontró la categoría de temporadas.")
        channel_name = re.sub(r'[^a-z0-9-]', '', nombre.lower().replace(' ', '-'))
        try: new_channel = await category.create_text_channel(channel_name)
        except discord.Forbidden: return await interaction.followup.send("❌ Error: No tengo permisos para crear canales.")
        if os.path.exists(POINTS_DATA_FILE):
            with open(POINTS_DATA_FILE, 'w') as f: json.dump({}, f)
        start_date = datetime.utcnow(); end_date = start_date + delta
        new_season_number = season_data.get('season_number', 0) + 1
        new_season = {'active': True, 'name': nombre, 'end_date': end_date.isoformat(),'season_number': new_season_number, 'channel_id': new_channel.id}
        save_season_data(new_season)
        embed = discord.Embed(title=f"✨ ¡Nueva Temporada Iniciada: {nombre}! ✨", color=discord.Color.brand_green())
        embed.description = f"El ranking ha sido reiniciado.\nSe ha creado un canal dedicado: {new_channel.mention}"
        embed.add_field(name="Inicio", value=start_date.strftime('%d/%m/%Y %H:%M UTC'))
        embed.add_field(name="Fin", value=end_date.strftime('%d/%m/%Y %H:%M UTC'))
        await interaction.followup.send(embed=embed)
    
    @season_group.command(name="end", description="Termina la temporada actual de forma manual.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def season_end(self, interaction: discord.Interaction):
        season_data = load_season_data()
        if not season_data['active']:
            return await interaction.response.send_message("❌ No hay ninguna temporada activa.", ephemeral=True)
        await interaction.response.defer()
        await self.end_season_logic(interaction.guild, interaction.channel, season_data)

    @season_group.command(name="status", description="Muestra el estado de la temporada actual.")
    async def season_status(self, interaction: discord.Interaction):
        season_data = load_season_data()
        if season_data['active']:
            end_date = datetime.fromisoformat(season_data['end_date'])
            embed = discord.Embed(title=f"Temporada en Curso: {season_data['name']}", color=discord.Color.blue())
            embed.description = f"La temporada actual finaliza el **{end_date.strftime('%d/%m/%Y')}**."
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No hay ninguna temporada activa en este momento.")

    # Manejador de errores para este Cog
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("❌ No tienes el rol de administrador necesario para usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message("Ocurrió un error inesperado.", ephemeral=True)
            print("Error en un comando de Temporadas:")
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(Temporadas(bot))