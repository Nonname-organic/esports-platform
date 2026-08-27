import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "プライバシーポリシー",
  description: "AXELIA における個人情報の取り扱いについて",
};

const SECTIONS: { heading: string; body: string[]; list?: string[] }[] = [
  {
    heading: "1. 取得する情報",
    body: ["本サービスは、以下の情報を取得します。"],
    list: [
      "アカウント情報: メールアドレス、ユーザー名、パスワード（ハッシュ化して保存）",
      "プロフィール情報: プレイヤー名、Riot ID、ランク、ロール、所属チーム、自己紹介",
      "任意の連絡先: Discord ID（入力した場合のみ）",
      "大会関連データ: 参加申請、試合結果、選手成績",
      "アップロードされた画像: チームロゴ、バナー、スコアボードのスクリーンショット",
    ],
  },
  {
    heading: "2. 利用目的",
    body: [
      "取得した情報は、アカウント認証、大会の運営（参加受付・組み合わせ生成・結果記録）、戦績および統計の集計・表示、ならびに本サービスの改善のために利用します。",
    ],
  },
  {
    heading: "3. 公開範囲",
    body: [
      "本サービスは大会結果を公開することを目的としているため、以下の情報は未ログインの利用者を含め誰でも閲覧できます。",
    ],
    list: [
      "プレイヤー名（IGN）、Riot ID、ランク、ロール、所属チーム",
      "大会の参加記録、試合結果、選手成績、ランキング",
    ],
  },
  {
    heading: "4. 公開しない情報",
    body: ["以下の情報は公開ページおよび公開APIには含めていません。"],
    list: [
      "メールアドレス",
      "本名",
      "Discord ID（本人の編集画面でのみ表示）",
      "パスワード（ハッシュ化して保存し、復元できません）",
    ],
  },
  {
    heading: "5. 第三者提供",
    body: [
      "法令に基づく場合を除き、取得した情報を本人の同意なく第三者に提供することはありません。",
      "エージェント名等のゲーム内データの参照のため、外部の公開API（valorant-api.com）へアクセスすることがありますが、利用者の個人情報を送信することはありません。",
    ],
  },
  {
    heading: "6. スクリーンショットの取り扱い",
    body: [
      "スコアボードのスクリーンショットは選手成績の読み取りのために解析されます。解析後、抽出された数値のみがデータベースに保存されます。",
    ],
  },
  {
    heading: "7. デモ環境における注意",
    body: [
      "本サービスは現在デモンストレーション環境として提供されています。予告なくデータベースを初期化する場合があるため、登録された情報の保全は保証されません。実在の個人情報や機微な情報の入力はお控えください。",
    ],
  },
  {
    heading: "8. 削除の請求",
    body: [
      "アカウントおよび登録情報の削除をご希望の場合は、運営者までご連絡ください。合理的な期間内に対応します。",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-black text-white">プライバシーポリシー</h1>
      <p className="mt-2 text-xs text-slate-500">最終更新日: 2026年8月28日</p>

      <div className="mt-8 space-y-8">
        {SECTIONS.map(({ heading, body, list }) => (
          <section key={heading}>
            <h2 className="text-sm font-bold text-white">{heading}</h2>
            <div className="mt-2 space-y-2">
              {body.map((paragraph) => (
                <p key={paragraph} className="text-sm leading-relaxed text-slate-400">
                  {paragraph}
                </p>
              ))}
              {list && (
                <ul className="mt-2 space-y-1.5">
                  {list.map((item) => (
                    <li
                      key={item}
                      className="flex gap-2 text-sm leading-relaxed text-slate-400"
                    >
                      <span className="text-slate-600">・</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
