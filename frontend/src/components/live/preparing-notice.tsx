import Link from "next/link";

/**
 * 公開準備中の告知とサービス紹介。
 *
 * 大会が0件のとき、Hero の直下には何も出なかった（LiveTournamentPreview が
 * 0件で null を返す）。トップページが Hero だけになり、何のサービスなのか、
 * 今使えるのかが伝わらない状態だったので、ここで埋める。
 *
 * 書かないことを決めてある:
 *   - 存在しない大会名・開催日
 *   - 参加チーム数や実績の示唆（登録チームには動作確認用のものが含まれる）
 *   - 未実装の機能を提供中と読める表現
 */
const AVAILABLE = [
  "アカウント登録とログイン",
  "チームの作成とメンバー管理",
  "選手プロフィールの登録",
] as const;

const PLANNED = [
  "大会の募集・エントリー受付",
  "ブラケットの自動生成と試合結果の登録",
  "スコアボード画像からの成績取り込み",
  "ランキングと統計の公開",
] as const;

export function PreparingNotice() {
  return (
    <section aria-labelledby="preparing-heading" className="mx-auto max-w-3xl">
      <p className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-1 text-sm font-medium text-amber-200">
        公開準備中
      </p>

      <h2 id="preparing-heading" className="mt-4 text-2xl font-bold sm:text-3xl">
        VALORANT の大会運営を1か所にまとめるプラットフォームです
      </h2>

      <p className="mt-4 text-slate-300">
        エントリー管理・ブラケット生成・試合結果の記録・成績の集計を、スプレッドシートや
        複数のツールに分散させずに扱えるようにすることを目指しています。
      </p>

      <p className="mt-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-slate-200">
        <strong className="font-semibold">現在、大会の募集・開催は行っていません。</strong>
        <br />
        掲載している大会はなく、参加者の受付も始めていません。機能の確認のために
        作成したチーム・選手データが含まれます。
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
            提供予定（準備中）
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            {PLANNED.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden="true">—</span>
                {item}
              </li>
            ))}
          </ul>
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
