# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias en un layer separado para cache eficiente
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="tu-usuario"
LABEL description="Password Vault - Local password manager with AES-256-GCM encryption"
LABEL version="1.0.0"

WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copiar código fuente
COPY main.py .
COPY static/ ./static/

# Crear directorio para la base de datos (será un volumen)
RUN mkdir -p /data

# Usuario no-root por seguridad
RUN useradd -r -s /bin/false vaultuser && \
    chown -R vaultuser:vaultuser /app /data

USER vaultuser

# Puerto interno
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

# Variables de entorno
ENV DB_PATH=/data/vault.db
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Comando de inicio
CMD ["python", "-m", "uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--no-access-log"]
