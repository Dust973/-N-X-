from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import json, os
from functools import wraps

app = Flask(__name__, static_url_path='', static_folder='.')

# Clé secrète pour les sessions Flask
app.secret_key = 'une_cle_secrete_pour_session'

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
DELETED_USERS_FILE = os.path.join(DATA_DIR, 'deleted_users.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.json')

def load_json(fp):
    if not os.path.exists(fp):
        return []
    with open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(fp, obj):
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# Décorateur pour routes admin uniquement
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'Accès refusé'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    uid, pwd = data.get('id'), data.get('password')

    users = load_json(USERS_FILE)
    for u in users:
        if u['id'] == uid and u['password'] == pwd and not u.get('archived', False):
            if u.get('grade') == 'Ω':
                session['role'] = 'admin'
                session['user_id'] = uid
                return jsonify({'role': 'admin'})
            else:
                session['role'] = 'user'
                session['user_id'] = uid
                return jsonify({'role': 'user'})

    return jsonify({'error': 'Identifiants invalides'}), 401

@app.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        return jsonify([u for u in load_json(USERS_FILE) if not u.get('archived', False)])
    data = request.json
    users = load_json(USERS_FILE)
    if any(u['id'] == data['id'] for u in users):
        return jsonify({'error': 'ID existe'}), 400
    data['archived'] = False
    users.append(data)
    save_json(USERS_FILE, users)
    return jsonify({'status': 'ok'})

@app.route('/users/<uid>', methods=['DELETE'])
def delete_user(uid):
    users = load_json(USERS_FILE)
    deleted = load_json(DELETED_USERS_FILE)
    for u in users:
        if u['id'] == uid and not u.get('archived', False):
            u['archived'] = True
            deleted.append(u)
            save_json(DELETED_USERS_FILE, deleted)
            break
    save_json(USERS_FILE, users)
    return jsonify({'status': 'deleted'})

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if request.method == 'GET':
        return jsonify(load_json(MESSAGES_FILE))
    msg = request.json
    msgs = load_json(MESSAGES_FILE)
    msgs.append(msg)
    save_json(MESSAGES_FILE, msgs)
    return jsonify({'status': 'added'})

# Dashboard accessible seulement aux admins
@app.route('/dashboard')
@admin_required
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/dashboard.css')
@admin_required
def dashboard_css():
    return send_from_directory('.', 'dashboard.css')

# Accès aux fichiers JSON critiques via dashboard (admin only)
@app.route('/dashboard_files')
@admin_required
def dashboard_files():
    file = request.args.get('file')
    if file not in ('users.json', 'deleted_users.json', 'messages.json'):
        return jsonify({'error': 'Fichier invalide'}), 400
    try:
        with open(os.path.join(DATA_DIR, file), 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Exécution de commandes console (admin only)
@app.route('/dashboard_command', methods=['POST'])
@admin_required
def dashboard_command():
    data = request.json
    cmd = data.get('command', '').strip()
    # Exemple simple, juste écho de la commande
    result = f"Commande reçue: {cmd}"
    return jsonify({'result': result})

# Servir les pages HTML et autres fichiers statiques
@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/<path:p>')
def static_proxy(p):
    return send_from_directory('.', p)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    for fp in (USERS_FILE, DELETED_USERS_FILE, MESSAGES_FILE):
        if not os.path.exists(fp):
            save_json(fp, [])
    app.run(debug=True)
