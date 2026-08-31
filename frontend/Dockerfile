# Imagen del frontend en tres etapas: dependencias, compilación y ejecución.
# La etapa final solo lleva el bundle `standalone`, sin node_modules completos.
#
# Se usa `slim` (Debian) y no `alpine`: npm falla al instalar algunas dependencias
# nativas de Next sobre musl.
FROM node:22-slim AS deps
WORKDIR /app

# Escape para redes corporativas que interceptan TLS y rompen la verificación del
# certificado del registry. Vacío por defecto: la verificación queda activa.
#   docker compose build --build-arg NPM_CONFIG_STRICT_SSL=false
ARG NPM_CONFIG_STRICT_SSL=""

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund


FROM node:22-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# `NEXT_PUBLIC_*` se incrusta en el bundle del navegador durante el build,
# por eso llega como build arg y no como variable de entorno de ejecución.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build


FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

COPY --from=build /app/public ./public
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
CMD ["node", "server.js"]
