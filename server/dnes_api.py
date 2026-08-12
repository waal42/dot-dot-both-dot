#!/usr/bin/env python3
"""
Python API Backend for Wedding Day App (/svatba/dnes)
Manages live announcements, URL redirects, schedule overrides, and admin authentication.
Stores state in JSON file at TARGET_DATA_PATH.
"""

import json
import os
import secrets
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone, timedelta

# Helper to load .env variables
def load_env():
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),
        '/opt/svatba-dnes/.env',
        '/opt/svatba-dashboard/.env',
        'c:/Users/filip/source/dot-dot-both-dot/.env'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, val = line.strip().split('=', 1)
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")
            break

ADMIN_USER = os.environ.get("DNES_ADMIN_USER", "").strip()
ADMIN_PASS = os.environ.get("DNES_ADMIN_PASS", "").strip()
TARGET_DATA_PATH = os.environ.get("DNES_DATA_PATH", "/var/www/mywalove/svatba/dnes_data.json")

# Fallback path if running locally or permissions differ
if not os.path.exists(os.path.dirname(TARGET_DATA_PATH)):
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(local_dir, exist_ok=True)
    TARGET_DATA_PATH = os.path.join(local_dir, 'dnes_data.json')

ACTIVE_SESSIONS = set()

DEFAULT_DATA = {
    "unlock_time": "2026-08-15T13:00:00+02:00",
    "is_locked_override": None,  # True = force lock, False = force unlock, None = check time
    "announcements": [
        {
            "id": "welcome-1",
            "text": "Vítejte na svatbě Hanky & Filipa! 💍 Všechny důležité informace a odjezdy najdete přímo zde.",
            "timestamp": "2026-08-15T13:00:00+02:00"
        }
    ],
    "schedule_overrides": {},
    "redirects": {
        "fotky": "https://photos.google.com",
        "disk": "",
        "vzkaznik": "/svatba/dnes#vzkaznik"
    }
}

def read_data():
    if not os.path.exists(TARGET_DATA_PATH):
        write_data(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(TARGET_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure keys exist
            for k, v in DEFAULT_DATA.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error reading JSON data: {e}", file=sys.stderr)
        return DEFAULT_DATA

def write_data(data):
    os.makedirs(os.path.dirname(TARGET_DATA_PATH), exist_ok=True)
    with open(TARGET_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class APIRequestHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Token')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _send_json(self, data, status=200):
        self.send_response(status)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error(self, message, status=400):
        self._send_json({"error": message}, status=status)

    def _is_authenticated(self):
        auth_header = self.headers.get('Authorization', '')
        token_header = self.headers.get('X-Admin-Token', '')
        token = auth_header.replace('Bearer ', '').strip() if auth_header else token_header.strip()
        return token in ACTIVE_SESSIONS and len(token) > 0

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ['/svatba/dnes/api/data', '/api/data']:
            data = read_data()
            is_admin = self._is_authenticated()
            
            # Check lock state
            unlock_str = data.get("unlock_time", "2026-08-15T13:00:00+02:00")
            override = data.get("is_locked_override")
            
            now_iso = datetime.now(timezone.utc).isoformat()
            
            if override is not None:
                is_locked = bool(override)
            else:
                try:
                    unlock_dt = datetime.fromisoformat(unlock_str)
                    now_dt = datetime.now(timezone.utc)
                    is_locked = now_dt < unlock_dt
                except Exception:
                    is_locked = False

            res = {
                "is_locked": is_locked and not is_admin,
                "is_admin": is_admin,
                "unlock_time": unlock_str,
                "announcements": data.get("announcements", []),
                "schedule_overrides": data.get("schedule_overrides", {}),
                "redirects": data.get("redirects", {}),
                "now": now_iso
            }
            return self._send_json(res)

        elif path.startswith('/svatba/dnes/api/redirect/') or path.startswith('/api/redirect/'):
            slug = path.split('/')[-1]
            data = read_data()
            redirects = data.get("redirects", {})
            target = redirects.get(slug, "")
            if target:
                self.send_response(302)
                self.send_header('Location', target)
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header('Location', '/svatba/dnes')
                self.end_headers()
            return

        else:
            self._send_error("Not found", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(length) if length > 0 else b'{}'
        try:
            payload = json.loads(body_bytes.decode('utf-8'))
        except Exception:
            payload = {}

        if path in ['/svatba/dnes/api/admin/login', '/api/admin/login']:
            username = payload.get('username', '').strip()
            password = payload.get('password', '').strip()

            if not ADMIN_USER or not ADMIN_PASS:
                print("ADMIN LOGIN ERROR: DNES_ADMIN_USER or DNES_ADMIN_PASS not set in environment!", file=sys.stderr)
                return self._send_error("Přihlášení selhalo: Na VPS chybí konfigurace DNES_ADMIN_USER / DNES_ADMIN_PASS v .env", 401)

            if username and password and username == ADMIN_USER and password == ADMIN_PASS:
                token = secrets.token_hex(24)
                ACTIVE_SESSIONS.add(token)
                return self._send_json({"result": "success", "token": token})
            else:
                return self._send_error("Neplatné uživatelské jméno nebo heslo", 401)

        elif path in ['/svatba/dnes/api/admin/update', '/api/admin/update']:
            if not self._is_authenticated():
                return self._send_error("Neautorizovaný přístup", 401)

            data = read_data()
            action = payload.get('action')

            if action == 'add_announcement':
                text = payload.get('text', '').strip()
                if text:
                    new_item = {
                        "id": f"msg-{secrets.token_hex(4)}",
                        "text": text,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    data.setdefault("announcements", []).insert(0, new_item)
                    write_data(data)
                    return self._send_json({"result": "success", "announcement": new_item})
                return self._send_error("Prázdný text zprávy")

            elif action == 'delete_announcement':
                msg_id = payload.get('id')
                data["announcements"] = [m for m in data.get("announcements", []) if m.get("id") != msg_id]
                write_data(data)
                return self._send_json({"result": "success"})

            elif action == 'set_redirect':
                slug = payload.get('slug', '').strip().lower()
                target_url = payload.get('target_url', '').strip()
                if slug:
                    data.setdefault("redirects", {})[slug] = target_url
                    write_data(data)
                    return self._send_json({"result": "success", "redirects": data["redirects"]})
                return self._send_error("Chybí zkratka (slug)")

            elif action == 'delete_redirect':
                slug = payload.get('slug', '').strip().lower()
                if slug in data.get("redirects", {}):
                    del data["redirects"][slug]
                    write_data(data)
                    return self._send_json({"result": "success", "redirects": data["redirects"]})
                return self._send_error("Zkratka nenalezena")

            elif action == 'toggle_lock':
                override = payload.get('override') # True, False, or None
                data["is_locked_override"] = override
                write_data(data)
                return self._send_json({"result": "success", "is_locked_override": override})

            elif action == 'override_schedule':
                item_id = payload.get('item_id')
                new_time = payload.get('time')
                new_note = payload.get('note')
                if item_id:
                    data.setdefault("schedule_overrides", {})[item_id] = {
                        "time": new_time,
                        "note": new_note
                    }
                    write_data(data)
                    return self._send_json({"result": "success", "schedule_overrides": data["schedule_overrides"]})
                return self._send_error("Chybí položka harmonogramu")

            else:
                return self._send_error("Neznámá akce")

        else:
            self._send_error("Not found", 404)

def run(port=8085):
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIRequestHandler)
    print(f"API Server running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8085))
    run(port)
