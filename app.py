from flask import Flask, jsonify, request, render_template_string, session, redirect
import datetime, sqlite3, os, hashlib

app = Flask(__name__)
app.secret_key = 'securecloud-secret-2026'
DB = '/app/data/platform.db'

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    os.makedirs('/app/data', exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT DEFAULT "user",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL, details TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute("INSERT OR IGNORE INTO users (name,email,password,role) VALUES (?,?,?,?)",
              ('Admin','admin@cloud.local',hash_password('admin123'),'admin'))
    conn.commit(); conn.close()

def get_user(email):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    u = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(u) if u else None

def log_action(action, details=''):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO logs (action,details) VALUES (?,?)", (action,details))
    conn.commit(); conn.close()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session: return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@login_required
def home():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    users = [dict(u) for u in conn.execute("SELECT * FROM users ORDER BY id").fetchall()]
    logs = [dict(l) for l in conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10").fetchall()]
    stats = {"users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
             "logs": conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]}
    conn.close()
    return render_template_string(DASHBOARD, session=session, users=users,
        logs=logs, stats=stats, now=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = get_user(request.form.get('email','').strip())
        if u and u['password'] == hash_password(request.form.get('password','')):
            session['user'] = {'id':u['id'],'name':u['name'],'email':u['email'],'role':u['role']}
            log_action('LOGIN', f"{u['name']} connecte")
            return redirect('/')
        return render_template_string(LOGIN, error='Email ou mot de passe incorrect')
    return render_template_string(LOGIN, error=None)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        confirm = request.form.get('confirm','')
        if not name or not email or not password:
            return render_template_string(REGISTER, error='Tous les champs sont obligatoires', success=None)
        if len(password) < 6:
            return render_template_string(REGISTER, error='Mot de passe min. 6 caracteres', success=None)
        if password != confirm:
            return render_template_string(REGISTER, error='Mots de passe differents', success=None)
        try:
            conn = sqlite3.connect(DB)
            conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                        (name, email, hash_password(password), 'user'))
            conn.commit(); conn.close()
            log_action('REGISTER', f"Nouveau compte: {name} ({email})")
            return render_template_string(REGISTER, error=None, success='Compte cree ! Connectez-vous.')
        except sqlite3.IntegrityError:
            return render_template_string(REGISTER, error='Email deja utilise', success=None)
    return render_template_string(REGISTER, error=None, success=None)

@app.route('/logout')
def logout():
    if 'user' in session: log_action('LOGOUT', f"{session['user']['name']} deconnecte")
    session.clear(); return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status":"ok","service":"flask-api","version":"2.0","time":str(datetime.datetime.now())})

LOGIN = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>SecureCloud</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:#09090b;color:#fafafa;min-height:100vh;display:flex;align-items:center;justify-content:center}.box{background:#111114;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:40px;width:400px}.logo{display:flex;align-items:center;gap:10px;margin-bottom:32px;justify-content:center}.li{width:40px;height:40px;border-radius:10px;background:#6366f1;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff}h2{font-size:20px;font-weight:700;margin-bottom:6px;text-align:center}.sub{font-size:13px;color:#71717a;text-align:center;margin-bottom:28px}.fg{margin-bottom:16px}label{font-size:12px;color:#a1a1aa;display:block;margin-bottom:6px}input{width:100%;padding:11px 14px;border-radius:8px;border:1px solid rgba(255,255,255,0.1);background:#18181b;color:#fafafa;font-size:14px;outline:none}.btn{width:100%;padding:12px;border-radius:8px;background:#6366f1;color:#fff;font-size:14px;font-weight:600;border:none;cursor:pointer;margin-top:8px}.err{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:#f87171;padding:10px;border-radius:8px;font-size:13px;margin-bottom:16px;text-align:center}.lnk{text-align:center;margin-top:20px;font-size:13px;color:#71717a}.lnk a{color:#818cf8}</style></head>
<body><div class="box"><div class="logo"><div class="li">SC</div><span style="font-size:18px;font-weight:700">SecureCloud</span></div>
<h2>Connexion</h2><p class="sub">Connectez-vous a votre compte</p>
{% if error %}<div class="err">{{ error }}</div>{% endif %}
<form method="POST"><div class="fg"><label>Email</label><input type="email" name="email" placeholder="admin@cloud.local" required></div>
<div class="fg"><label>Mot de passe</label><input type="password" name="password" placeholder="••••••••" required></div>
<button class="btn">Se connecter</button></form>
<div class="lnk">Pas de compte ? <a href="/register">Creer un compte</a></div></div></body></html>"""

REGISTER = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>SecureCloud — Inscription</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:#09090b;color:#fafafa;min-height:100vh;display:flex;align-items:center;justify-content:center}.box{background:#111114;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:40px;width:400px}.logo{display:flex;align-items:center;gap:10px;margin-bottom:32px;justify-content:center}.li{width:40px;height:40px;border-radius:10px;background:#6366f1;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff}h2{font-size:20px;font-weight:700;margin-bottom:6px;text-align:center}.sub{font-size:13px;color:#71717a;text-align:center;margin-bottom:28px}.fg{margin-bottom:16px}label{font-size:12px;color:#a1a1aa;display:block;margin-bottom:6px}input{width:100%;padding:11px 14px;border-radius:8px;border:1px solid rgba(255,255,255,0.1);background:#18181b;color:#fafafa;font-size:14px;outline:none}.btn{width:100%;padding:12px;border-radius:8px;background:#6366f1;color:#fff;font-size:14px;font-weight:600;border:none;cursor:pointer;margin-top:8px}.err{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:#f87171;padding:10px;border-radius:8px;font-size:13px;margin-bottom:16px;text-align:center}.suc{background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);color:#4ade80;padding:10px;border-radius:8px;font-size:13px;margin-bottom:16px;text-align:center}.lnk{text-align:center;margin-top:20px;font-size:13px;color:#71717a}.lnk a{color:#818cf8}</style></head>
<body><div class="box"><div class="logo"><div class="li">SC</div><span style="font-size:18px;font-weight:700">SecureCloud</span></div>
<h2>Creer un compte</h2><p class="sub">Rejoignez SecureCloud Platform</p>
{% if error %}<div class="err">{{ error }}</div>{% endif %}
{% if success %}<div class="suc">{{ success }}</div>{% endif %}
<form method="POST"><div class="fg"><label>Nom complet</label><input type="text" name="name" placeholder="Votre nom" required></div>
<div class="fg"><label>Email</label><input type="email" name="email" placeholder="votre@email.com" required></div>
<div class="fg"><label>Mot de passe</label><input type="password" name="password" placeholder="Min. 6 caracteres" required minlength="6"></div>
<div class="fg"><label>Confirmer</label><input type="password" name="confirm" placeholder="Repetez" required></div>
<button class="btn">Creer mon compte</button></form>
<div class="lnk">Deja un compte ? <a href="/login">Se connecter</a></div></div></body></html>"""

DASHBOARD = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>SecureCloud Dashboard</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:#09090b;color:#fafafa;min-height:100vh}.nav{background:#111114;border-bottom:1px solid rgba(255,255,255,0.08);padding:0 32px;height:56px;display:flex;align-items:center;justify-content:space-between}.nl{display:flex;align-items:center;gap:10px}.li{width:32px;height:32px;border-radius:8px;background:#6366f1;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff}.nr{display:flex;align-items:center;gap:12px}.ub{font-size:12px;color:#a1a1aa;background:#18181b;padding:5px 12px;border-radius:6px;border:1px solid rgba(255,255,255,0.08)}.lb{font-size:12px;color:#f87171;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);padding:5px 12px;border-radius:6px;text-decoration:none}.main{padding:40px 32px}.wl{margin-bottom:32px}.wl h1{font-size:26px;font-weight:700;margin-bottom:6px}.wl p{font-size:14px;color:#71717a}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:32px}.sc{background:#111114;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:20px}.sc .num{font-size:30px;font-weight:700;font-family:monospace}.sc .lbl{font-size:12px;color:#71717a;margin-top:4px;text-transform:uppercase;letter-spacing:0.06em}.sec{background:#111114;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px;margin-bottom:20px}.sec h2{font-size:14px;font-weight:600;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:16px}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;padding:8px 12px;color:#52525b;font-size:11px;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,0.06)}td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.04);color:#d4d4d8}.rb{font-size:10px;padding:2px 8px;border-radius:5px;font-weight:600}.admin{background:rgba(99,102,241,0.15);color:#818cf8}.user{background:rgba(161,161,170,0.15);color:#a1a1aa}</style></head>
<body><nav class="nav"><div class="nl"><div class="li">SC</div><span style="font-size:15px;font-weight:600">SecureCloud Platform</span></div>
<div class="nr"><span class="ub">{{ session.user.name }} — {{ session.user.role }}</span><a href="/logout" class="lb">Deconnexion</a></div></nav>
<div class="main"><div class="wl"><h1>Bonjour, {{ session.user.name }} !</h1><p>SecureCloud Platform — {{ now }}</p></div>
<div class="grid">
<div class="sc"><div class="num" style="color:#22c55e">{{ stats.users }}</div><div class="lbl">Utilisateurs</div></div>
<div class="sc"><div class="num" style="color:#60a5fa">{{ stats.logs }}</div><div class="lbl">Actions</div></div>
<div class="sc"><div class="num" style="color:#a855f7">2.0</div><div class="lbl">Version</div></div>
<div class="sc"><div class="num" style="color:#f97316">OK</div><div class="lbl">Statut</div></div>
</div>
<div class="sec"><h2>Utilisateurs</h2><table>
<tr><th>ID</th><th>Nom</th><th>Email</th><th>Role</th><th>Cree le</th></tr>
{% for u in users %}<tr><td>{{ u.id }}</td><td>{{ u.name }}</td><td>{{ u.email }}</td>
<td><span class="rb {{ u.role }}">{{ u.role }}</span></td><td>{{ u.created_at }}</td></tr>{% endfor %}
</table></div>
<div class="sec"><h2>Derniers logs</h2><table>
<tr><th>Action</th><th>Details</th><th>Timestamp</th></tr>
{% for l in logs %}<tr><td>{{ l.action }}</td><td>{{ l.details }}</td><td>{{ l.timestamp }}</td></tr>{% endfor %}
</table></div></div></body></html>"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
