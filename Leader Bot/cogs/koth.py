# cogs/koth.py (Versión Completa y Corregida)
import discord
from discord import app_commands
from discord.ext import commands
import json
import re
import traceback # Necesario para imprimir errores detallados

# --- CONFIGURACIÓN DEL MÓDULO KOTH ---
# ¡MUY IMPORTANTE! Debes poner el ID del canal exclusivo para los eventos KOTH.
# Para obtenerlo, haz clic derecho en el canal y selecciona "Copiar ID del canal".
KOTH_CHANNEL_ID = 1311780242121035888  # ⚠️ REEMPLAZA ESTO
ADMIN_ROLE_ID = 1311780240435052607   # ⚠️ REEMPLAZA ESTO (debe ser el mismo que en los otros archivos)

PENDING_EMOJI = '📝'
APPROVE_EMOJI = '✅'

# Archivo para guardar el estado del evento KOTH actual
KOTH_EVENT_FILE = 'koth_event.json'
# Diccionario para envíos pendientes de este módulo
pending_koth_approvals = {}

# --- Funciones de Datos para el Evento KOTH ---
def load_koth_event():
    """Carga el estado del evento KOTH desde su archivo JSON."""
    try:
        with open(KOTH_EVENT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si no hay evento, devuelve un estado por defecto "inactivo"
        return {'active': False, 'name': None, 'points_per_tag': 0}

def save_koth_event(data):
    """Guarda el estado del evento KOTH."""
    with open(KOTH_EVENT_FILE, 'w') as f:
        json.dump(data, f, indent=4)


class Koth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Creación de un Grupo de Comandos para /koth ---
    koth_group = app_commands.Group(name="koth", description="Comandos para gestionar eventos de King of the Hill")

    # --- COMANDOS DENTRO DEL GRUPO ---
    @koth_group.command(name="start", description="Inicia un nuevo evento KOTH.")
    @app_commands.describe(nombre="El nombre del evento (ej: Asalto a Bonta)", puntos="Puntos a dar por cada etiqueta")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def koth_start(self, interaction: discord.Interaction, nombre: str, puntos: int):
        if interaction.channel.id != KOTH_CHANNEL_ID:
            return await interaction.response.send_message("Este comando solo se puede usar en el canal de KOTH.", ephemeral=True)

        event = load_koth_event()
        if event['active']:
            return await interaction.response.send_message(f"❌ Ya hay un evento KOTH activo llamado '{event['name']}'.", ephemeral=True)

        new_event = {'active': True, 'name': nombre, 'points_per_tag': puntos}
        save_koth_event(new_event)
        
        embed = discord.Embed(
            title=f"⚔️ ¡Evento KOTH Iniciado! ⚔️",
            description=f"**Nombre:** {nombre}\n**Puntos por Etiqueta:** {puntos}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @koth_group.command(name="end", description="Termina el evento KOTH actual.")
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def koth_end(self, interaction: discord.Interaction):
        if interaction.channel.id != KOTH_CHANNEL_ID: return
        event = load_koth_event()
        if not event['active']:
            return await interaction.response.send_message("❌ No hay ningún evento KOTH activo para terminar.", ephemeral=True)

        nombre_evento_terminado = event['name']
        save_koth_event({'active': False, 'name': None, 'points_per_tag': 0})
        await interaction.response.send_message(f"✅ El evento KOTH **'{nombre_evento_terminado}'** ha finalizado.")

    @koth_group.command(name="status", description="Muestra el estado del evento KOTH actual.")
    async def koth_status(self, interaction: discord.Interaction):
        if interaction.channel.id != KOTH_CHANNEL_ID: return
        event = load_koth_event()
        if event['active']:
            await interaction.response.send_message(f"▶️ Evento KOTH activo: **'{event['name']}'**. Puntos por etiqueta: **{event['points_per_tag']}**.")
        else:
            await interaction.response.send_message("⏹️ No hay ningún evento KOTH activo en este momento.")
    
    # --- MANEJADOR DE ERRORES PARA ESTE COG ---
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Manejador de errores para los comandos de este Cog."""
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("❌ No tienes el rol de administrador necesario para usar este comando.", ephemeral=True)
            print(f"Intento de uso de comando admin por {interaction.user.name} (no tiene el rol).")
        else:
            # Para otros errores, envía un mensaje genérico y muestra el error completo en la consola
            await interaction.response.send_message("Ocurrió un error inesperado al procesar el comando.", ephemeral=True)
            print(f"Error en un comando de KOTH. Usuario: {interaction.user.name}")
            traceback.print_exc()

    # --- LÓGICA DE ENVÍO Y APROBACIÓN ---

    @commands.Cog.listener()
    async def on_message(self, message):
        """Escucha mensajes para registrar envíos de KOTH."""
        if message.author.bot or message.channel.id != KOTH_CHANNEL_ID: return
        if message.content.startswith(self.bot.command_prefix): return

        event = load_koth_event()
        if not event['active']: return

        all_mentions_in_text = re.findall(r'<@!?(\d+)>', message.content)
        if not message.attachments or not all_mentions_in_text or not any(att.content_type.startswith('image/') for att in message.attachments):
            return
        
        pending_koth_approvals[message.id] = {'allies': all_mentions_in_text}
        await message.add_reaction(PENDING_EMOJI)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Escucha reacciones para aprobar envíos de KOTH."""
        if payload.channel_id != KOTH_CHANNEL_ID or payload.member.bot: return
        if str(payload.emoji) != APPROVE_EMOJI or payload.message_id not in pending_koth_approvals: return
        if not any(role.id == ADMIN_ROLE_ID for role in payload.member.roles): return

        submission = pending_koth_approvals.pop(payload.message_id)
        event = load_koth_event()
        
        if not event['active']: return
        
        points_to_award = event['points_per_tag']
        
        puntos_cog = self.bot.get_cog('Puntos')
        if puntos_cog:
            for user_id_str in submission['allies']:
                await puntos_cog.add_points(user_id_str, points_to_award)
        
        unique_ally_mentions = [f"<@{uid}>" for uid in set(submission['allies'])]
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            await channel.send(f"{APPROVE_EMOJI} Envío de KOTH **'{event['name']}'** aprobado por {payload.member.mention}!\n"
                               f"Se han otorgado **`{points_to_award}`** puntos por mención a: {', '.join(unique_ally_mentions)}.")

async def setup(bot):
    await bot.add_cog(Koth(bot))