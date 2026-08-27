import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "利用規約",
  description: "AXELIA の利用規約",
};

const SECTIONS: { heading: string; body: string[] }[] = [
  {
    heading: "第1条（適用）",
    body: [
      "本規約は、AXELIA（以下「本サービス」）の提供条件および利用者と運営者との権利義務関係を定めるものです。利用者は本サービスを利用することで本規約に同意したものとみなします。",
    ],
  },
  {
    heading: "第2条（本サービスの位置づけ）",
    body: [
      "本サービスは現在デモンストレーション環境として提供されています。掲載されている大会・チーム・戦績はサンプルデータであり、実在の大会の記録ではありません。",
      "デモ環境では予告なくデータの初期化・機能の変更・提供の停止を行う場合があります。登録されたデータの保全は保証されません。",
    ],
  },
  {
    heading: "第3条（アカウント）",
    body: [
      "利用者は正確な情報をもってアカウントを登録するものとし、パスワードを第三者に開示してはなりません。",
      "アカウントの管理不十分により生じた損害の責任は利用者が負うものとします。",
    ],
  },
  {
    heading: "第4条（禁止事項）",
    body: [
      "法令または公序良俗に違反する行為、他の利用者への嫌がらせ・差別的言動、なりすまし、虚偽の戦績登録、本サービスの運営を妨害する行為、および不正アクセスを禁止します。",
      "運営者は禁止事項に該当すると判断した場合、事前通知なくアカウントの停止または削除を行うことがあります。",
    ],
  },
  {
    heading: "第5条（投稿コンテンツ）",
    body: [
      "利用者がアップロードしたスクリーンショット・チームロゴ等について、利用者は必要な権利を有していることを保証するものとします。",
      "運営者は本サービスの提供・改善に必要な範囲で当該コンテンツを利用できるものとします。",
    ],
  },
  {
    heading: "第6条（免責）",
    body: [
      "運営者は本サービスの内容の正確性・完全性・有用性について保証しません。特に自動読み取り機能（スクリーンショット解析）の結果は誤りを含む可能性があり、最終的な確認は利用者の責任で行うものとします。",
      "本サービスの利用により生じた損害について、運営者は責任を負いません。",
    ],
  },
  {
    heading: "第7条（知的財産）",
    body: [
      "本サービスは Riot Games が承認・公認したものではありません。VALORANT および Riot Games は Riot Games, Inc. の商標または登録商標です。",
      "ゲーム内の名称・画像等の権利はそれぞれの権利者に帰属します。",
    ],
  },
  {
    heading: "第8条（規約の変更）",
    body: [
      "運営者は必要と判断した場合、利用者への事前告知なく本規約を変更できるものとします。変更後の規約は本ページに掲載した時点で効力を生じます。",
    ],
  },
];

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-black text-white">利用規約</h1>
      <p className="mt-2 text-xs text-slate-500">最終更新日: 2026年8月28日</p>

      <div className="mt-8 space-y-8">
        {SECTIONS.map(({ heading, body }) => (
          <section key={heading}>
            <h2 className="text-sm font-bold text-white">{heading}</h2>
            <div className="mt-2 space-y-2">
              {body.map((paragraph) => (
                <p key={paragraph} className="text-sm leading-relaxed text-slate-400">
                  {paragraph}
                </p>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
