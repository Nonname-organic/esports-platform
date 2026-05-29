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
  // 環境変数の型安全化
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000",
  },
};

export default nextConfig;
