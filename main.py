"""
Password Manager - Backend Principal
Stack: FastAPI + SQLite + AES-256
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
import base64
import hashlib
import secrets
import json
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ─── Config ──────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "vault.db")
SESSION_TOKEN = None  # Token de sesión en memoria (se pierde al cerrar)
MASTER_KEY = None     # Clave AES derivada de la contraseña maestra

app = FastAPI(title="Password Vault", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Database ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT,
            username TEXT NOT NULL,
            password_encrypted TEXT NOT NULL,
            notes_encrypted TEXT,
            category TEXT DEFAULT 'General',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Crypto ──────────────────────────────────────────────────────────────────
def derive_key(password: str, salt: bytes) -> bytes:
    """Deriva una clave AES-256 desde la contraseña maestra usando PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,  # NIST recomendación 2023
    )
    return kdf.derive(password.encode())

def encrypt(text: str, key: bytes) -> str:
    """Encripta texto con AES-256-GCM."""
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, text.encode(), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode()

def decrypt(encrypted_b64: str, key: bytes) -> str:
    """Desencripta texto con AES-256-GCM."""
    combined = base64.b64decode(encrypted_b64)
    nonce = combined[:12]
    ciphertext = combined[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

# ─── Auth ────────────────────────────────────────────────────────────────────
def get_master_key() -> bytes:
    if MASTER_KEY is None:
        raise HTTPException(status_code=401, detail="Sesión no iniciada. Inicia sesión primero.")
    return MASTER_KEY

# ─── Schemas ─────────────────────────────────────────────────────────────────
class SetupRequest(BaseModel):
    master_password: str

class LoginRequest(BaseModel):
    master_password: str

class PasswordEntry(BaseModel):
    name: str
    url: Optional[str] = ""
    username: str
    password: str
    notes: Optional[str] = ""
    category: Optional[str] = "General"

class PasswordUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/status")
def get_status():
    """Verifica si el vault está configurado y si hay sesión activa."""
    conn = get_db()
    config = conn.execute("SELECT value FROM vault_config WHERE key='salt'").fetchone()
    conn.close()
    return {
        "configured": config is not None,
        "logged_in": MASTER_KEY is not None
    }

@app.post("/api/setup")
def setup_vault(req: SetupRequest):
    """Configura el vault por primera vez con una contraseña maestra."""
    global MASTER_KEY, SESSION_TOKEN

    conn = get_db()
    existing = conn.execute("SELECT value FROM vault_config WHERE key='salt'").fetchone()
    if existing:
        conn.close()
        raise HTTPException(400, "El vault ya está configurado.")

    if len(req.master_password) < 8:
        conn.close()
        raise HTTPException(400, "La contraseña maestra debe tener al menos 8 caracteres.")

    # Generar salt único
    salt = secrets.token_bytes(32)
    salt_b64 = base64.b64encode(salt).decode()

    # Derivar clave y guardar verificador
    key = derive_key(req.master_password, salt)
    MASTER_KEY = key

    # Guardamos un "verifier" encriptado para validar futuros logins
    verifier = encrypt("VAULT_OK", key)

    conn.execute("INSERT INTO vault_config VALUES ('salt', ?)", (salt_b64,))
    conn.execute("INSERT INTO vault_config VALUES ('verifier', ?)", (verifier,))
    conn.commit()
    conn.close()

    SESSION_TOKEN = secrets.token_hex(32)
    return {"message": "Vault configurado correctamente.", "token": SESSION_TOKEN}

@app.post("/api/login")
def login(req: LoginRequest):
    """Inicia sesión con la contraseña maestra."""
    global MASTER_KEY, SESSION_TOKEN

    conn = get_db()
    salt_row = conn.execute("SELECT value FROM vault_config WHERE key='salt'").fetchone()
    verifier_row = conn.execute("SELECT value FROM vault_config WHERE key='verifier'").fetchone()
    conn.close()

    if not salt_row:
        raise HTTPException(400, "El vault no está configurado.")

    salt = base64.b64decode(salt_row["value"])
    key = derive_key(req.master_password, salt)

    try:
        result = decrypt(verifier_row["value"], key)
        if result != "VAULT_OK":
            raise HTTPException(401, "Contraseña incorrecta.")
    except Exception:
        raise HTTPException(401, "Contraseña maestra incorrecta.")

    MASTER_KEY = key
    SESSION_TOKEN = secrets.token_hex(32)
    return {"message": "Sesión iniciada.", "token": SESSION_TOKEN}

@app.post("/api/logout")
def logout():
    """Cierra la sesión y borra la clave de memoria."""
    global MASTER_KEY, SESSION_TOKEN
    MASTER_KEY = None
    SESSION_TOKEN = None
    return {"message": "Sesión cerrada."}

@app.get("/api/passwords")
def list_passwords(key: bytes = Depends(get_master_key)):
    """Lista todas las contraseñas (desencriptadas)."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM passwords ORDER BY category, name").fetchall()
    conn.close()

    result = []
    for row in rows:
        try:
            result.append({
                "id": row["id"],
                "name": row["name"],
                "url": row["url"],
                "username": decrypt(row["username"], key),
                "password": decrypt(row["password_encrypted"], key),
                "notes": decrypt(row["notes_encrypted"], key) if row["notes_encrypted"] else "",
                "category": row["category"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        except Exception:
            continue  # Si falla el decrypt, omitir entrada corrupta

    return result

@app.post("/api/passwords", status_code=201)
def create_password(entry: PasswordEntry, key: bytes = Depends(get_master_key)):
    """Crea una nueva entrada de contraseña."""
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO passwords (name, url, username, password_encrypted, notes_encrypted, category, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.name,
        entry.url,
        encrypt(entry.username, key),
        encrypt(entry.password, key),
        encrypt(entry.notes or "", key),
        entry.category,
        now,
        now
    ))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": new_id, "message": "Contraseña guardada."}

@app.put("/api/passwords/{entry_id}")
def update_password(entry_id: int, entry: PasswordUpdate, key: bytes = Depends(get_master_key)):
    """Actualiza una entrada existente."""
    conn = get_db()
    row = conn.execute("SELECT * FROM passwords WHERE id=?", (entry_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Entrada no encontrada.")

    now = datetime.now().isoformat()

    name = entry.name or row["name"]
    url = entry.url if entry.url is not None else row["url"]
    username = encrypt(entry.username, key) if entry.username else row["username"]
    password = encrypt(entry.password, key) if entry.password else row["password_encrypted"]
    notes = encrypt(entry.notes, key) if entry.notes is not None else row["notes_encrypted"]
    category = entry.category or row["category"]

    conn.execute("""
        UPDATE passwords SET name=?, url=?, username=?, password_encrypted=?,
        notes_encrypted=?, category=?, updated_at=? WHERE id=?
    """, (name, url, username, password, notes, category, now, entry_id))
    conn.commit()
    conn.close()
    return {"message": "Entrada actualizada."}

@app.delete("/api/passwords/{entry_id}")
def delete_password(entry_id: int, key: bytes = Depends(get_master_key)):
    """Elimina una entrada."""
    conn = get_db()
    result = conn.execute("DELETE FROM passwords WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(404, "Entrada no encontrada.")
    return {"message": "Entrada eliminada."}

@app.get("/api/generate-password")
def generate_password(length: int = 20, symbols: bool = True):
    """Genera una contraseña segura."""
    import string
    chars = string.ascii_letters + string.digits
    if symbols:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    password = ''.join(secrets.choice(chars) for _ in range(length))
    return {"password": password}

if __name__ == "__main__":
    import uvicorn
    print("\n🔐 Password Vault iniciando en http://localhost:8000\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
