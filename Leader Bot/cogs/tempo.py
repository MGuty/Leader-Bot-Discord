# cogs/tempo.py
import discord
from discord.ext import commands
import re
import config # Importamos la configuración central

# Ya no definimos IDs aquí, se leen desde config.py

PENDING_EMOJI = '📝'
APPROVE_EMOJI = '✅'

# CONFIGURACIÓN DE PUNTOS PARA TEMPO
# La "clave" debe coincidir con la parte del nombre del canal después de "tempo-"
TEMPO_POINTS = {
    "5-10min": 15,
    "10-15min": 25,
    "15-20min": 40,
    "20-25min": 50,
    "25-30min": 60,
    "plus-de-30": 75,
}

pending_tempo_approvals = {}

class Tempo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Escucha mensajes para registrar envíos en canales de Tempo."""
        if message.author.bot:
            return
        if not message.channel.name.lower().startswith('tempo-'):
            return

        all_mentions_in_text = re.findall(r'<@!?(\d+)>', message.content)
        if not message.attachments or not all_mentions_in_text or not any(att.content_type.startswith('image/') for att in message.attachments):
            return

        channel_name_lower = message.channel.name.lower()
        points_to_award = 0
        
        try:
            key_part = channel_name_lower.split('tempo-', 1)[1]
            if key_part in TEMPO_POINTS:
                points_to_award = TEMPO_POINTS[key_part]
        except IndexError:
            return

        if points_to_award == 0:
            return
        
        pending_tempo_approvals[message.id] = {'points': points_to_award, 'allies': all_mentions_in_text}
        await message.add_reaction(PENDING_EMOJI)
        await message.reply(content=f"{PENDING_EMOJI} Envío de **Tempo** recibido y pendiente de aprobación.", mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Escucha reacciones para aprobar envíos de Tempo."""
        if payload.member.bot or str(payload.emoji) != APPROVE_EMOJI or payload.message_id not in pending_tempo_approvals:
            return
            
        # Usamos la variable desde el archivo de configuración
        if not any(role.id == config.ADMIN_ROLE_ID for role in payload.member.roles):
            return

        submission = pending_tempo_approvals.pop(payload.message_id)
        points_awarded = submission['points']
        
        puntos_cog = self.bot.get_cog('Puntos')
        if puntos_cog:
            for user_id_str in submission['allies']:
                await puntos_cog.add_points(user_id_str, points_awarded)
        
        unique_ally_mentions = [f"<@{uid}>" for uid in set(submission['allies'])]
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            await channel.send(
                f"{APPROVE_EMOJI} **Tempo** aprobado por {payload.member.mention}!\n"
                f"Se han otorgado **`{points_awarded}`** puntos por mención a: {', '.join(unique_ally_mentions)}."
            )

async def setup(bot):
    await bot.add_cog(Tempo(bot))