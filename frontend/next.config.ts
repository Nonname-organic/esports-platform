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
};

export default nextConfig;
