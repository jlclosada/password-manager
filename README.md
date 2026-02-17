# 🔐 Password Vault

> Gestor de contraseñas local con encriptación AES-256-GCM. Sin nube, sin cuentas, sin telemetría. Tus contraseñas nunca salen de tu equipo.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Encryption-AES--256--GCM-red?logo=shield&logoColor=white" />
  <img src="https://img.shields.io/badge/Storage-100%25_Local-green" />
  <img src="https://img.shields.io/badge/License-MIT-purple" />
</p>

---

## ✨ Características

- 🔒 **AES-256-GCM** — encriptación autenticada, estándar bancario/militar
- 🧠 **PBKDF2-SHA256** — 600.000 iteraciones para derivar la clave maestra
- 🏠 **100% local** — SQLite embebido, cero dependencias externas
- 🐳 **Docker ready** — levanta con un solo comando
- ⚡ **Generador integrado** — contraseñas seguras configurables
- 📋 **Copia con un clic** — usuario y contraseña al portapapeles
- 🗂️ **Categorías** — General, Trabajo, Finanzas, Redes Sociales, Streaming
- 🔍 **Búsqueda en tiempo real**
- 📡 **API REST** con Swagger automático en `/docs`

---

## 🚀 Inicio rápido

### Opción 1 — Docker (recomendado)

```bash
git clone https://github.com/tu-usuario/password-vault.git
cd password-vault
docker compose up -d
```

Abre http://localhost:8000. Los datos se persisten en un volumen Docker.

```bash
docker compose logs -f       # Ver logs
docker compose down          # Detener
docker compose down -v       # Detener y borrar datos (cuidado)
```

### Opción 2 — Python local (macOS / Linux)

```bash
git clone https://github.com/tu-usuario/password-vault.git
cd password-vault
chmod +x start.sh && ./start.sh
```

El script crea el entorno virtual, instala dependencias y abre el navegador.

### Opción 3 — Manual (cualquier OS)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

---

## 🏗️ Arquitectura

```
password-vault/
├── main.py              # FastAPI: rutas, encriptación, lógica de negocio
├── static/
│   └── index.html       # Frontend completo (HTML + CSS + JS vanilla)
├── Dockerfile           # Multi-stage build optimizado
├── docker-compose.yml   # Orquestación con volumen persistente
├── requirements.txt     # Dependencias Python
├── start.sh             # Script de inicio para macOS/Linux
└── vault.db             # SQLite (generado automáticamente, NO en git)
```

**Decisiones de diseño:**
- **Sin framework frontend** — HTML/CSS/JS puro, zero build step, zero node_modules
- **Sin ORM** — SQLite directo, menos capas = más transparencia de seguridad
- **Multi-stage Dockerfile** — imagen final ~80MB en lugar de ~400MB
- **Usuario no-root en Docker** — principio de menor privilegio

---

## 🔐 Modelo de seguridad

| Capa | Implementación | Detalle |
|---|---|---|
| Encriptación | AES-256-GCM | Autenticada: detecta cualquier modificación |
| Derivación de clave | PBKDF2-SHA256 | 600.000 iteraciones (NIST SP 800-132) |
| Salt | 256 bits aleatorios | Único por vault, protege contra rainbow tables |
| Nonce | 96 bits aleatorios | Único por operación de encriptación |
| Sesión | RAM únicamente | La clave nunca toca el disco |
| Red | `127.0.0.1` only | No expuesto a red local ni a internet |
| Docker | `no-new-privileges` | El contenedor no puede escalar permisos |

> ⚠️ La contraseña maestra no tiene recuperación. Si la pierdes, los datos son irrecuperables.

---

## 📡 API Reference

Disponible en `http://localhost:8000/docs` (Swagger UI automático).

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/status` | Estado del vault |
| `POST` | `/api/setup` | Configuración inicial |
| `POST` | `/api/login` | Iniciar sesión |
| `POST` | `/api/logout` | Cerrar sesión |
| `GET` | `/api/passwords` | Listar todas las entradas |
| `POST` | `/api/passwords` | Crear entrada |
| `PUT` | `/api/passwords/{id}` | Actualizar entrada |
| `DELETE` | `/api/passwords/{id}` | Eliminar entrada |
| `GET` | `/api/generate-password` | Generar contraseña segura |

---

## 🐳 Docker — detalles

El `Dockerfile` usa **multi-stage build**:
1. **Stage `builder`** — instala dependencias
2. **Stage `runtime`** — imagen limpia, solo lo necesario

```bash
# Construir y correr manualmente
docker build -t password-vault .
docker run -d \
  -p 127.0.0.1:8000:8000 \
  -v vault-data:/data \
  -e DB_PATH=/data/vault.db \
  --name password-vault \
  password-vault
```

---

## 💾 Backup

```bash
# Con Docker
docker run --rm \
  -v password-vault_vault-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/vault-backup-$(date +%Y%m%d).tar.gz -C /data .

# Con Python local: simplemente copia vault.db
cp vault.db vault-backup-$(date +%Y%m%d).db
```

---

## 📄 Licencia

MIT © 2024
