#!/bin/bash
# ─── Password Vault - Script de inicio ───────────────────────────────────────
# Uso: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}🔐 Password Vault${NC}"
echo "──────────────────────────────────"

# Verificar Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo desde https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detectado"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias si no están instaladas
if ! python -c "import fastapi" &>/dev/null 2>&1; then
    echo "📥 Instalando dependencias..."
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓${NC} Dependencias instaladas"
fi

echo -e "${GREEN}✓${NC} Entorno listo"
echo ""
echo -e "${YELLOW}⚡ Iniciando servidor en http://localhost:8000${NC}"
echo "   Presiona Ctrl+C para detener"
echo ""

# Abrir el navegador después de 1.5 segundos
(sleep 1.5 && open "http://localhost:8000") &

# Iniciar FastAPI
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
