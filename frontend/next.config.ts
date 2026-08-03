import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // Docker最適化
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
    ],
  },
  experimental: {
    // Server Actions 有効化
    serverActions: { allowedOrigins: ["localhost:3000"] },
  },
  async headers() {
    return [
      {
        // HTML・RSC（画面遷移データ）は CDN エッジ（CloudFront / Cloudflare 等）にキャッシュさせない。
        // これをしないと LFP/LFT 等の更新後もエッジが古いページを返し続ける。
        // _next/static（ハッシュ付き不変アセット）と _next/image は除外し、キャッシュを維持。
        source: "/((?!_next/static|_next/image|favicon.ico).*)",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
