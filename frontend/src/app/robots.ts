import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/**
 * クロール可否。
 *
 * 公開するのはサービス紹介（トップ）と規約・プライバシーの3ページだけに絞る。
 * 大会ページは公開対象にしていないので、一覧や認証後の画面を検索結果に
 * 載せない。大会を公開する段になったら allow を足す。
 *
 * 許可したものだけを載せる形にしたのは、このサイトが一度も
 * インデックスされていないため（robots.txt が Disallow: / で、nginx も
 * X-Robots-Tag: noindex を返していた）。消す対象が無いので、
 * noindex をクローラに読ませる必要がなく、disallow だけで足りる。
 *
 * 逆に、一度インデックスされたページを消すときは disallow では消えない。
 * そのときは robots.txt で許可したまま、そのページの metadata に
 * noindex を付ける（クローラが noindex を読めるようにする）。
 *
 * 認証後の画面（/dashboard /admin など）は未認証でも HTML の殻が
 * 200 で返る（認可はクライアント側で、データは API がトークンで守る）。
 * 中身は空でもクロールさせる意味がないので許可しない。
 */
// パスの一致は「長い方が勝つ」ので、トップだけを許可するには $ で終端を
// 固定する必要がある（"/" のままでは Disallow: / と同じ長さになり、
// Allow が優先されて全許可になってしまう。実際にビルド出力で確認した）。
// Allow と $ は RFC には無い拡張だが Google / Bing が解釈する。
//
// /_next/ を許可するのは、CSS と JS を弾くと許可したページの描画を
// クローラが再現できなくなるため。
const ALLOW = ["/$", "/terms", "/privacy", "/sitemap.xml", "/_next/"] as const;

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: [...ALLOW],
      disallow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
