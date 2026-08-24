# ============================================================
# VLearn Research Tutor — Multi-stage production image
# Stage 1: Python dependencies (isolated venv, cacheable)
# Stage 2: Next.js web build (artifacts only)
# Stage 3: Runtime (slim — venv + web artifacts, no build tools)
# ============================================================

# ---------- Stage 1: Python deps ----------
FROM python:3.12-slim AS py-deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ---------- Stage 2: Web build ----------
FROM node:22-slim AS web-build
WORKDIR /web
# Cache layer: chỉ copy manifest trước để npm ci có cache riêng
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
# Copy source + build
COPY apps/web/ ./
RUN npm run build

# ---------- Stage 3: Runtime ----------
FROM python:3.12-slim AS runtime

# Node runtime (không build tools) — copy từ stage node để giữ slim
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node
COPY --from=web-build /usr/local/bin/npx /usr/local/bin/npx
COPY --from=web-build /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Python venv từ stage 1
COPY --from=py-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

# Web artifacts từ stage 2 (node_modules + .next production build)
COPY --from=web-build /web/node_modules /app/apps/web/node_modules
COPY --from=web-build /web/.next /app/apps/web/.next

RUN chmod +x start.sh docker-entrypoint.sh

EXPOSE 8001 3000 7860
CMD ["./docker-entrypoint.sh"]