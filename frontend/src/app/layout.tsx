import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Header } from "@/components/header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "EsportsPlatform | e-スポーツ大会管理",
    template: "%s | EsportsPlatform",
  },
  description:
    "e-スポーツ大会のエントリー・ブラケット生成・スコア管理・統計分析を一元化するプラットフォーム",
  keywords: ["eスポーツ", "大会", "VALORANT", "LOL", "ゲーム大会"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className="dark">
      <body className={`${inter.variable} font-sans bg-slate-950 text-white antialiased`}>
        <Providers>
          <Header />
          <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
