# cogs/defensa.py
import discord
from discord.ext import commands
import re
import config # <-- Importamos la configuración

# Ya no definimos IDs aquí, se leen desde config.py

PENDING_EMOJI = '📝'
APPROVE_EMOJI = '✅'

# Puntos por DEFENSAS con el formato solicitado
DEFENSE_POINTS = [
#   0 Ene, 1 Ene, 2 Ene, 3 Ene, 4 Ene, 5 Ene
    [0,    120,   150,   180,   210,   240], # 1 Aliado
    [0,     90,   120,   150,   180,   210], # 2 Aliados
    [0,     60,    90,   120,   150,   180], # 3 Aliados
    [0,     15,    60,    90,   120,   150], # 4 Aliados
    [0,      0,    15,    60,    90,   120]  # 5 Aliados
]

pending_defenses = {}

class Defensa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.channel.name.lower().startswith('defenses-'):
            return

        all_mentions_in_text = re.findall(r'<@!?(\d+)>', message.content)
        if not message.attachments or not all_mentions_in_text or not any(att.content_type.startswith('image/') for att in message.attachments):
            return

        num_allies = len(all_mentions_in_text)
        num_enemies = 0
        match = re.search(r'vs(\d+)', message.channel.name.lower())
        if match:
            num_enemies = int(match.group(1))

        if not (1 <= num_allies <= 5 and 0 <= num_enemies <= 5):
            return
            
        points_to_award = DEFENSE_POINTS[num_allies - 1][num_enemies]
        if points_to_award == 0:
            await message.add_reaction('🤷')
            return
        
        pending_defenses[message.id] = {'points': points_to_award, 'allies': all_mentions_in_text}
        await message.add_reaction(PENDING_EMOJI)
        await message.reply(content=f"{PENDING_EMOJI} Envío de **Defensa** recibido y pendiente de aprobación.", mention_author=False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot or str(payload.emoji) != APPROVE_EMOJI or payload.message_id not in pending_defenses:
            return
        
        # Usamos la variable desde el archivo de configuración
        if not any(role.id == config.ADMIN_ROLE_ID for role in payload.member.roles):
            return

        submission = pending_defenses.pop(payload.message_id)
        
        puntos_cog = self.bot.get_cog('Puntos')
        if puntos_cog:
            for user_id_str in submission['allies']:
                await puntos_cog.add_points(user_id_str, submission['points'])
        
        unique_ally_mentions = [f"<@{uid}>" for uid in set(submission['allies'])]
        
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            await channel.send(f"{APPROVE_EMOJI} **Defensa** aprobada por {payload.member.mention}!\nSe han otorgado **`{submission['points']}`** puntos por mención a: {', '.join(unique_ally_mentions)}.")

async def setup(bot):
    await bot.add_cog(Defensa(bot))