import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { DemoBanner } from "@/components/demo-banner";

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
