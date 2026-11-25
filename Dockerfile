# Una sola imagen para los tres procesos (worker, api, bot); compose elige el comando.
FROM python:3.12-slim

# uv copiado desde su imagen oficial (versión fija para builds reproducibles)
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 1) Primero solo las dependencias: esta capa se cachea y no se reconstruye si solo
#    cambia el código (builds mucho más rápidos).
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Luego el código
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev

# No correr como root dentro del contenedor
RUN useradd --create-home --uid 1000 app
USER app

CMD ["python", "-m", "panastatus.worker"]
