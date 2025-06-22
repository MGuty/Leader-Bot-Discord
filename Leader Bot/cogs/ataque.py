# cogs/ataque.py (VERSIÓN FINAL Y LIMPIA)
import discord
from discord.ext import commands
import re
import config # Importamos la configuración central

# Ya no definimos IDs aquí, se leen desde config.py

PENDING_EMOJI = '📝'
APPROVE_EMOJI = '✅'

# Puntos por ATAQUES con el formato solicitado
ATTACK_POINTS = [
#   0 Ene, 1 Ene, 2 Ene, 3 Ene, 4 Ene, 5 Ene
    [5,    120,   150,   180,   210,   240], # 1 Aliado
    [5,     90,   120,   150,   180,   210], # 2 Aliados
    [5,     60,    90,   120,   150,   180], # 3 Aliados
    [5,     30,    60,    90,   120,   150], # 4 Aliados
    [5,     15,    30,    60,    90,   120]  # 5 Aliados
]

pending_attacks = {}

class Ataque(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.channel.name.lower().startswith('attack-'):
            return

        all_mentions_in_text = re.findall(r'<@!?(\d+)>', message.content)
        if not message.attachments or not all_mentions_in_text or not any(att.content_type.startswith('image/') for att in message.attachments):
            return

        num_allies = len(all_mentions_in_text)
        num_enemies = 0
        match = re.search(r'vs(\d+)', message.channel.name.lower())
        if match:
            num_enemies = int(match.group(1))
        elif "no-def" in message.channel.name.lower():
            num_enemies = 0

        if not (1 <= num_allies <= 5 and 0 <= num_enemies <= 5):
            return
            
        points_to_award = ATTACK_POINTS[num_allies - 1][num_enemies]
        if points_to_award == 0:
            await message.add_reaction('🤷')
            return
        
        pending_attacks[message.id] = {'points': points_to_award, 'allies': all_mentions_in_text}
        await message.add_reaction(PENDING_EMOJI)
        await message.reply(content=f"{PENDING_EMOJI} Envío de **Ataque** recibido y pendiente de aprobación.", mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot or str(payload.emoji) != APPROVE_EMOJI or payload.message_id not in pending_attacks:
            return
        
        # Usamos la variable desde el archivo de configuración
        if not any(role.id == config.ADMIN_ROLE_ID for role in payload.member.roles):
            return

        submission = pending_attacks.pop(payload.message_id)
        
        puntos_cog = self.bot.get_cog('Puntos')
        if puntos_cog:
            for user_id_str in submission['allies']:
                await puntos_cog.add_points(user_id_str, submission['points'])
        
        unique_ally_mentions = [f"<@{uid}>" for uid in set(submission['allies'])]
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            await channel.send(f"{APPROVE_EMOJI} **Ataque** aprobado por {payload.member.mention}!\nSe han otorgado **`{submission['points']}`** puntos por mención a: {', '.join(unique_ally_mentions)}.")

async def setup(bot):
    await bot.add_cog(Ataque(bot))