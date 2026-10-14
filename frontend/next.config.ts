import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker では standalone、Netlify ではランタイムが独自に束ねるため無効化
  output: process.env.NETLIFY ? undefined : "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.amazonaws.com", // S3画像（AWS構成）
      },
      {
        protocol: "https",
        hostname: "**.r2.dev", // Cloudflare R2 公開バケット（無料構成）
      },
      {
        protocol: "https",
        hostname: "**.r2.cloudflarestorage.com", // R2 S3互換エンドポイント
      },
      {
        protocol: "https",
        hostname: "**.supabase.co", // Supabase Storage（現行の保存先）
      },
      {
        protocol: "https",
        hostname: "**.supabase.in",
      },
    ],
  },
  experimental: {
    // Server Actions 有効化
    serverActions: {
      allowedOrigins: ["localhost:3000", "localhost", "*.netlify.app", "app.axelia-esports.jp"],
    },
  },
  async headers() {
    return [
      {
        // HTML・RSC（画面遷移データ）は CDN エッジ（CloudFront / Cloudflare 等）にキャッシュさせない。
        // これをしないと LFP/LFT 等の更新後もエッジが古いページを返し続ける。
        // _next/static（ハッシュ付き不変アセット）と _next/image は除外し、キャッシュを維持。
        source: "/((?!_next/static|_next/image|favicon.ico).*)",
        headers: [{ key: "Cache-Control", value: "no-store, must-revalidate" }],
      },
      {
        // 公開する3ページ（/ /terms /privacy）以外は SSR 応答にも noindex を付ける。
        // nginx の add_header は上流のヘッダを消さないので、ここで付けたものは
        // そのまま外へ出る。公開するページに付けないよう、ここで除外しておく。
        // robots.ts の ALLOW と対応させること。
        source: "/((?!$|terms$|privacy$|sitemap\.xml$|robots\.txt$|_next/static|_next/image|favicon.ico).*)",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
    ];
  },
};

export default nextConfig;
