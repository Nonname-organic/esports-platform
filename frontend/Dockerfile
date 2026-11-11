# ベースイメージは AWS ECR Public の公式ミラーから取得する。
# Docker Hub は未認証だとIP単位で絞られ、GitHub のランナーはIPを共有するため
# 429 や auth.docker.io の 504 でビルドが落ちることが繰り返し起きた。
# ECR Public は同じ公式イメージを認証不要・レート制限なしで配る。
# ============================
# Stage 1: deps
# ============================
FROM public.ecr.aws/docker/library/node:26-alpine AS deps
WORKDIR /app

# package-lock.json をコピーして再現性を確保
COPY package.json package-lock.json ./
RUN npm install --include=optional

# ============================
# Stage 2: builder
# ============================
FROM public.ecr.aws/docker/library/node:26-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# ビルド時の環境変数（Docker Compose / CI から --build-arg で渡す）
# NEXT_PUBLIC_* はビルド時にJSへ埋め込まれるため、必ずここで受け取る。
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL

# デモ環境の告知バナー。"true" のときだけ「サンプルデータです」の帯を出す
ARG NEXT_PUBLIC_DEMO_MODE
ENV NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE

# Hero 背景動画は frontend/public/hero/ に同梱したものを nginx から配信する。
# 以前は CloudFront のURLをビルド引数で埋め込んでいたが、AWS 解体後も
# 古い値がビルドキャッシュ経由で焼き込まれ、動画が表示されない事故が起きた。
# CDN を使う構成に戻すときは、ここで ARG/ENV を復活させる。

# Next.js スタンドアロン出力 (next.config.ts で output: "standalone" を設定済み前提)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ============================
# Stage 3: runner (production)
# ============================
FROM public.ecr.aws/docker/library/node:26-alpine AS runner
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
