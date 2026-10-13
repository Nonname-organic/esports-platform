import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { DemoBanner } from "@/components/demo-banner";
import { SITE_URL } from "@/lib/site";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "AXELIA | VALORANT大会プラットフォーム",
    template: "%s | AXELIA",
  },
  description:
    "VALORANT大会のエントリー・ブラケット生成・スコア管理・統計分析を一元化するプラットフォーム",
  keywords: ["eスポーツ", "大会", "VALORANT", "ヴァロラント", "ゲーム大会"],
  // OGP と canonical が相対パスを解決するための基点。
  metadataBase: new URL(SITE_URL),
  // robots と canonical はここに置かない。ルートに書くと全ページへ降りてきて、
  // /terms や /privacy の canonical までトップを指し（重複扱いになる）、
  // robots.txt で弾いているページにまで index を主張することになる。
  // 公開する3ページだけが自分の metadata で宣言する。
  openGraph: {
    type: "website",
    siteName: "AXELIA",
    locale: "ja_JP",
    url: "/",
    title: "AXELIA | VALORANT大会プラットフォーム",
    description:
      "VALORANT大会のエントリー・ブラケット生成・スコア管理・統計分析を一元化するプラットフォーム。現在は公開準備中で、大会の募集・開催は行っていません。",
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className="dark">
      <body className={`${inter.variable} font-sans bg-slate-950 text-white antialiased`}>
        <Providers>
          <DemoBanner />
          <Header />
          <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
