import Link from "next/link";

/**
 * 全ページ共通のフッター。
 *
 * VALORANTの名称・エージェント名・ゲーム内映像を扱うため、Riot Gamesの
 * ファンコンテンツ方針が求める「非公認である旨」の表示をここで行う。
 */
export function Footer() {
  return (
    <footer className="mt-16 border-t border-white/10 bg-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black tracking-wide text-white">AXELIA</p>
            <p className="mt-1.5 text-xs text-slate-500">
              VALORANT大会の運営・記録・統計を一元化するプラットフォーム
            </p>
          </div>

          <nav className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
            <Link href="/terms" className="text-slate-400 transition-colors hover:text-white">
              利用規約
            </Link>
            <Link href="/privacy" className="text-slate-400 transition-colors hover:text-white">
              プライバシーポリシー
            </Link>
            <Link href="/tournaments" className="text-slate-400 transition-colors hover:text-white">
              大会一覧
            </Link>
          </nav>
        </div>

        <div className="mt-8 space-y-2 border-t border-white/5 pt-6">
          <p className="text-[11px] leading-relaxed text-slate-600">
            AXELIA は Riot Games が承認・公認したものではなく、Riot Games または
            その関係者の見解や意見を反映するものではありません。VALORANT および
            Riot Games は Riot Games, Inc. の商標または登録商標です。
          </p>
          <p className="text-[11px] text-slate-600">
            © {new Date().getFullYear()} AXELIA
          </p>
        </div>
      </div>
    </footer>
  );
}
