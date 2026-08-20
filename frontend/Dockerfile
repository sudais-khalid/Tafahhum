# Tafahhum web — multi-stage build
#
# Next.js standalone output ships a minimal server plus only the node_modules
# actually reachable at runtime, so the final image carries no build toolchain.

# --------------------------------------------------------------- deps --------
FROM node:22-alpine AS deps
WORKDIR /app

# Lockfile first so the install layer is cached until dependencies change.
COPY package.json package-lock.json ./
# `npm ci` installs exactly what the lockfile pins, unlike `npm install`.
RUN npm ci --no-audit --no-fund

# --------------------------------------------------------------- builder -----
FROM node:22-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# The API base URL is inlined into the client bundle at build time. It defaults
# to empty, which means same-origin: the reverse proxy serves the API under
# /api on the same host, so no cross-origin request is made.
ARG NEXT_PUBLIC_TAFAHHUM_API=""
ENV NEXT_PUBLIC_TAFAHHUM_API=${NEXT_PUBLIC_TAFAHHUM_API} \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --------------------------------------------------------------- runtime -----
FROM node:22-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10001 tafahhum \
    && adduser --system --uid 10001 --ingroup tafahhum tafahhum

# Standalone bundles the server and its reachable dependencies; public/ and
# .next/static are served alongside it.
COPY --from=builder --chown=tafahhum:tafahhum /app/.next/standalone ./
COPY --from=builder --chown=tafahhum:tafahhum /app/.next/static ./.next/static

USER tafahhum

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
