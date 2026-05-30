# ============================
# Stage 1: deps
# ============================
FROM node:20-alpine AS deps
WORKDIR /app

# package-lock.json をコピーして再現性を確保
COPY package.json package-lock.json ./
RUN npm install --include=optional

# ============================
# Stage 2: builder
# ============================
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# ビルド時の環境変数（Docker Compose から --build-arg で渡す）
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL

# Next.js スタンドアロン出力 (next.config.ts で output: "standalone" を設定済み前提)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ============================
# Stage 3: runner (production)
# ============================
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# セキュリティ: 非 root ユーザーで実行
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# スタンドアロンビルド成果物のみコピー
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# next start の代わりに standalone の server.js を直接起動（メモリ効率◎）
CMD ["node", "server.js"]
