import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/**
 * サイトマップ。
 *
 * 大会ページを公開対象にしていないので、載せるのは静的な3ページだけ。
 * 大会ページを公開する段になったら、ここに一覧を足す。
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
  ];
}
