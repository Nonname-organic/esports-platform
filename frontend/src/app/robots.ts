import type { MetadataRoute } from "next";

/**
 * 検索エンジンのクロールを全面的に拒否する。
 *
 * 本サービスは「URLを知っている人だけに見せる限定公開デモ」であり、
 * 検索結果に載せない。一般公開へ切り替えるときはここを allow に変える。
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", disallow: "/" },
  };
}
