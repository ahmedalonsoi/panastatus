# Imagen "web": Caddy + la página estática de Next.js.
# Se construye desde la RAÍZ del repo (necesita deploy/Caddyfile):
#   docker build -f frontend/Dockerfile .

# --- Etapa 1: compilar Next.js (Node solo existe aquí, NO en la imagen final) ---
FROM node:24-alpine AS build
WORKDIR /app
# Dependencias primero: esta capa se cachea mientras package-lock.json no cambie.
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci --no-audit
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- Etapa 2: imagen final, solo Caddy + archivos estáticos (~50 MB) ---
FROM caddy:2.11-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/out /srv
# Valida la sintaxis del Caddyfile al construir: un error se detecta en CI, no en producción.
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
