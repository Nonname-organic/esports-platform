import Link from "next/link";

/**
 * デモ環境である旨の告知とサービス紹介。
 *
 * 大会が0件のとき、Hero の直下には何も出なかった（LiveTournamentPreview が
 * 0件で null を返す）。トップページが Hero だけになり、何のサービスなのか、
 * 今使えるのかが伝わらない状態だったので、ここで埋める。
 *
 * 書かないことを決めてある:
 *   - 存在しない大会名・開催日
 *   - 参加チーム数や実績の示唆（登録チームには動作確認用のものが含まれる）
 *   - 大会の件数（このコンポーネントが出る条件は「開催中が0件」で、
 *     他の状態の大会が無いことまでは意味しない。page.tsx の
 *     getFeaturedTournaments は status=ongoing だけを引き、取得に失敗しても
 *     空配列を返す）
 */

/** ログインすれば今すぐ触れるもの。大会作成は主催者機能を自分で有効にできる。 */
const AVAILABLE = [
  "アカウント登録とログイン",
  "チームの作成とメンバー管理",
  "選手プロフィールの登録",
  "大会の作成と参加者の受付（主催者機能を有効にすると使えます）",
] as const;

/** 実装はあるが、対象の大会・試合が無いと結果が出ないもの。 */
const NEEDS_TOURNAMENT = [
  "ブラケットの自動生成と試合結果の登録",
  "スコアボード画像からの成績取り込み",
  "ランキングと統計の集計",
] as const;

export function PreparingNotice() {
  return (
    <section aria-labelledby="preparing-heading" className="mx-auto max-w-3xl">
      <p className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-1 text-sm font-medium text-amber-200">
        デモ環境
      </p>

      <h2 id="preparing-heading" className="mt-4 text-2xl font-bold sm:text-3xl">
        VALORANT の大会運営を1か所にまとめるプラットフォームです
      </h2>

      <p className="mt-4 text-slate-300">
        エントリー管理・ブラケット生成・試合結果の記録・成績の集計を、スプレッドシートや
        複数のツールに分散させずに扱えるようにすることを目指しています。
      </p>

      <p className="mt-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-slate-200">
        <strong className="font-semibold">現在、運営が主催する大会は開催していません。</strong>
        <br />
        運営としての参加者の募集も行っていません。
      </p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-emerald-300">
            いま試せること
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {AVAILABLE.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden="true" className="text-emerald-400">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            大会を作成すると使える機能
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            {NEEDS_TOURNAMENT.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden="true">—</span>
                {item}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            いずれも大会と試合のデータが必要です。
          </p>
        </div>
      </div>

      <p className="mt-8 text-sm text-slate-400">
        <Link href="/terms" className="underline hover:text-slate-200">
          利用規約
        </Link>
        {" ・ "}
        <Link href="/privacy" className="underline hover:text-slate-200">
          プライバシーポリシー
        </Link>
      </p>
    </section>
  );
}
