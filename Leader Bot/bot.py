# bot.py
import discord
from discord.ext import commands
import os
import asyncio
import config # Importamos nuestra nueva configuración

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- EVENTO ON_READY ---
@bot.event
async def on_ready():
    print("--- Sincronizando comandos de barra (Slash Commands) ---")
    try:
        # Usamos el ID del servidor desde nuestro archivo config.py
        synced_commands = await bot.tree.sync(guild=discord.Object(id=config.TEST_GUILD_ID))
        print(f"✅ ¡Se sincronizaron {len(synced_commands)} comandos para el servidor de pruebas!")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")
    
    print('--------------------------------------------------')
    print(f'✅ ¡Bot conectado como {bot.user}!')
    print(f'✅ ID de Usuario: {bot.user.id}')
    print('--------------------------------------------------')

# --- FUNCIÓN PRINCIPAL ASÍNCRONA ---
async def main():
    async with bot:
        print("--- Cargando Módulos (Cogs) ---")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                extension_name = f'cogs.{filename[:-3]}'
                try:
                    await bot.load_extension(extension_name)
                    print(f"✅ Módulo '{filename}' cargado exitosamente.")
                except Exception as e:
                    print(f"❌ Error al cargar el módulo '{filename}': {e}")
        
        TOKEN = "Token aqui" # ⚠️ REEMPLAZA ESTO con tu token
        await bot.start(TOKEN)

# --- PUNTO DE ENTRADA ---
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot desconectado manualmente.")