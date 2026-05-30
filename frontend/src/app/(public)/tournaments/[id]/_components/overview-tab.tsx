import { Calendar, Users, Shield, Info } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { TournamentDetail } from "@/types/tournament";

const FORMAT_LABEL: Record<string, string> = {
  single_elimination: "シングルエリミネーション",
  double_elimination: "ダブルエリミネーション",
  round_robin: "ラウンドロビン",
  swiss: "スイス式",
};

interface OverviewTabProps {
  tournament: TournamentDetail;
}

export function OverviewTab({ tournament }: OverviewTabProps) {
  const SCHEDULE = [
    { label: "参加受付開始", value: tournament.registration_start_at },
    { label: "参加受付終了", value: tournament.registration_end_at },
    ...(tournament.require_check_in
      ? [{ label: "チェックイン開始", value: tournament.check_in_start_at }]
      : []),
    { label: "大会開始", value: tournament.start_at },
    { label: "大会終了", value: tournament.end_at },
  ];

  return (
    <div className="grid grid-cols-1 gap-6 pt-6 lg:grid-cols-3">
      {/* メインコンテンツ */}
      <div className="space-y-6 lg:col-span-2">
        {/* 概要 */}
        {tournament.description && (
          <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h2 className="mb-3 flex items-center gap-2 font-bold text-white">
              <Info className="h-4 w-4 text-brand-400" />
              大会概要
            </h2>
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-slate-300">
              {tournament.description}
            </p>
          </section>
        )}

        {/* スケジュール */}
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
            <Calendar className="h-4 w-4 text-brand-400" />
            スケジュール
          </h2>
          <ol className="relative border-l border-white/10 space-y-4 pl-6">
            {SCHEDULE.map(({ label, value }) => (
              <li key={label} className="relative">
                <span className="absolute -left-[1.6rem] top-1 h-3 w-3 rounded-full border-2 border-brand-500 bg-slate-950" />
                <p className="text-xs font-medium text-slate-500">{label}</p>
                <p className="mt-0.5 text-sm font-semibold text-white">
                  {value ? formatDate(value) : "未定"}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* 大会形式 */}
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
            <Shield className="h-4 w-4 text-brand-400" />
            大会形式
          </h2>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              { label: "形式", value: FORMAT_LABEL[tournament.format] ?? tournament.format },
              { label: "最大チーム数", value: `${tournament.max_teams} チーム` },
              { label: "チェックイン", value: tournament.require_check_in ? "あり" : "なし" },
            ].map(({ label, value }) => (
              <div key={label}>
                <dt className="text-slate-500">{label}</dt>
                <dd className="mt-0.5 font-semibold text-white">{value}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ルール */}
        {tournament.rules && Object.keys(tournament.rules).length > 0 && (
          <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h2 className="mb-3 font-bold text-white">ルール</h2>
            <pre className="text-sm text-slate-400 whitespace-pre-wrap font-sans">
              {JSON.stringify(tournament.rules, null, 2)}
            </pre>
          </section>
        )}
      </div>

      {/* サイドバー */}
      <div className="space-y-4">
        {/* 参加状況カード */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-4 flex items-center gap-2 font-bold text-white">
            <Users className="h-4 w-4 text-brand-400" />
            参加状況
          </h3>
          <div className="mb-2 flex items-end justify-between">
            <div>
              <span className="text-3xl font-black text-white">{tournament.registered_teams}</span>
              <span className="text-slate-400"> / {tournament.max_teams}</span>
            </div>
            <span className="text-sm text-slate-500">チーム</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-brand-500"
              style={{
                width: `${Math.min((tournament.registered_teams / tournament.max_teams) * 100, 100)}%`,
              }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            残り {Math.max(tournament.max_teams - tournament.registered_teams, 0)} 枠
          </p>
        </div>

        {/* 作成日 */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h3 className="mb-3 font-bold text-white text-sm">その他</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">作成日</dt>
              <dd className="text-white">{formatDate(tournament.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">更新日</dt>
              <dd className="text-white">{formatDate(tournament.updated_at)}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
