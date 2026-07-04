import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // Docker最適化
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.amazonaws.com", // S3画像
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
        // HTML・RSC（画面遷移データ）は CloudFront にキャッシュさせない。
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
