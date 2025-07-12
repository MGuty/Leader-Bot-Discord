# apy.py o cogs/api.py (Versión Corregida)
from flask import Flask, jsonify, redirect, request, session
from discord.ext import commands
from threading import Thread
import os
import requests # Solo necesitamos esta librería

# --- CONFIGURACIÓN DE OAUTH2 (Leída desde .env) ---
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = 'http://127.0.0.1:5000/callback'
API_BASE_URL = 'https://discord.com/api'
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'

# --- Aplicación Flask ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# --- Rutas de la API ---

@app.route('/')
def index():
    if 'user' in session:
        return f"¡Hola, {session['user']['username']}! <a href='/dashboard'>Ir al Panel de Control</a> | <a href='/logout'>Cerrar sesión</a>"
    return '<a href="/login">Iniciar sesión con Discord</a>'

@app.route('/login')
def login():
    scope = ['identify', 'guilds']
    return redirect(f'{AUTHORIZATION_BASE_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={" ".join(scope)}')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('access_token', None)
    return redirect('/')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify guilds'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_response = requests.post(TOKEN_URL, data=data, headers=headers)
    token_response.raise_for_status()
    
    access_token = token_response.json()['access_token']
    session['access_token'] = access_token
    
    with requests.get(f'{API_BASE_URL}/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as user_response:
        session['user'] = user_response.json()
    
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return "<h2>Panel de Control</h2><p>Bienvenido, {}.</p><a href='/api/guilds'>Ver mis servidores en común con el bot (en formato JSON)</a>".format(session['user']['username'])

@app.route('/api/guilds')
def get_guilds():
    if 'user' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    access_token = session['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    
    bot_guild_ids = {guild.id for guild in ApiCog.bot.guilds}
    
    with requests.get(f'{API_BASE_URL}/users/@me/guilds', headers=headers) as user_guilds_response:
        user_guilds = user_guilds_response.json()

    mutual_guilds = []
    for guild in user_guilds:
        if int(guild['id']) in bot_guild_ids and (guild['permissions'] & 0x8) == 0x8:
            mutual_guilds.append({
                'id': guild['id'],
                'name': guild['name'],
                'icon_url': f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png?size=128"
            })
    return jsonify(mutual_guilds)

# --- Cog de Discord ---
class ApiCog(commands.Cog):
    bot = None
    
    def __init__(self, bot_instance):
        ApiCog.bot = bot_instance
        self.start_flask_server()

    def start_flask_server(self):
        flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
        flask_thread.daemon = True
        flask_thread.start()

async def setup(bot):
    await bot.add_cog(ApiCog(bot))