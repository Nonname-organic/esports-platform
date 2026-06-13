import { Calendar, Users, Shield, Info } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { TournamentDetail } from "@/types/tournament";

const FORMAT_LABEL: Record<string, string> = {
  single_elimination: "シングルエリミネーション",
  double_elimination: "ダブルエリミネーション",
  round_robin: "ラウンドロビン",
  swiss: "スイス式",
};

const BANPICK_LABEL: Record<string, string> = {
  team_veto: "チームVeto（交互）",
  organizer_pick: "主催者指定",
  blind_pick: "ブラインドピック",
};

const OVERTIME_LABEL: Record<string, string> = {
  sudden_death: "サドンデス",
  best_of_3: "ベスト・オブ・3",
  unlimited: "無制限",
};

const CURRENCY_SYMBOL: Record<string, string> = { JPY: "¥", USD: "$", EUR: "€" };

function formatPrizeAmount(p: { amount?: number; currency?: string }): string {
  const sym = CURRENCY_SYMBOL[p.currency ?? "JPY"] ?? "";
  return `${sym}${(p.amount ?? 0).toLocaleString()}`;
}

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

        {/* レギュレーション（rules を人間可読に整形。生JSONは表示しない） */}
        {(() => {
          const r = (tournament.rules ?? {}) as Record<string, any>;
          const gs = (r.game_settings ?? {}) as Record<string, any>;
          const mapPool: string[] = Array.isArray(gs.map_pool) ? gs.map_pool : [];
          const prizes: Array<{ rank_position?: number; amount?: number; currency?: string }> =
            Array.isArray(r.prizes) ? r.prizes : [];
          const contact = (r.contact ?? {}) as Record<string, any>;
          const discordInvite: string | undefined =
            (r.discord && typeof r.discord.invite_url === "string" && r.discord.invite_url) || undefined;

          const regItems: Array<{ label: string; value: string }> = [];
          if (r.bo_format) regItems.push({ label: "試合形式", value: String(r.bo_format) });
          if (gs.server) regItems.push({ label: "サーバー", value: String(gs.server) });
          if (gs.ban_pick_format)
            regItems.push({ label: "Ban/Pick", value: BANPICK_LABEL[gs.ban_pick_format] ?? gs.ban_pick_format });
          if (gs.overtime_rule)
            regItems.push({ label: "オーバータイム", value: OVERTIME_LABEL[gs.overtime_rule] ?? gs.overtime_rule });
          if (r.tier) regItems.push({ label: "ティア", value: String(r.tier) });

          const hasContent =
            regItems.length > 0 || mapPool.length > 0 || prizes.length > 0 ||
            discordInvite || contact.twitter || contact.discord;
          if (!hasContent) return null;

          return (
            <section className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-5">
              <h2 className="flex items-center gap-2 font-bold text-white">
                <Shield className="h-4 w-4 text-brand-400" />
                レギュレーション
              </h2>

              {regItems.length > 0 && (
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  {regItems.map(({ label, value }) => (
                    <div key={label}>
                      <dt className="text-slate-500">{label}</dt>
                      <dd className="mt-0.5 font-semibold text-white">{value}</dd>
                    </div>
                  ))}
                </dl>
              )}

              {mapPool.length > 0 && (
                <div>
                  <p className="mb-2 text-sm text-slate-500">マッププール</p>
                  <div className="flex flex-wrap gap-1.5">
                    {mapPool.map((m) => (
                      <span key={m} className="rounded-lg bg-white/5 px-2.5 py-1 text-xs font-medium text-slate-300">
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {prizes.length > 0 && (
                <div>
                  <p className="mb-2 text-sm text-slate-500">賞金</p>
                  <ul className="space-y-1 text-sm">
                    {prizes.map((p, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="text-yellow-400">{p.rank_position ?? i + 1}位</span>
                        <span className="font-semibold text-white">{formatPrizeAmount(p)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(discordInvite || contact.twitter || contact.discord) && (
                <div>
                  <p className="mb-2 text-sm text-slate-500">参加・連絡先</p>
                  <div className="flex flex-wrap gap-2 text-sm">
                    {discordInvite && (
                      <a href={discordInvite} target="_blank" rel="noopener noreferrer"
                        className="rounded-lg bg-[#5865F2]/15 px-3 py-1.5 font-medium text-[#aab2ff] hover:bg-[#5865F2]/25 transition-colors">
                        Discordに参加
                      </a>
                    )}
                    {contact.twitter && (
                      <a href={`https://twitter.com/${String(contact.twitter).replace(/^@/, "")}`} target="_blank" rel="noopener noreferrer"
                        className="rounded-lg bg-white/5 px-3 py-1.5 text-slate-300 hover:bg-white/10 transition-colors">
                        @{String(contact.twitter).replace(/^@/, "")}
                      </a>
                    )}
                    {contact.discord && (
                      <span className="rounded-lg bg-white/5 px-3 py-1.5 text-slate-300">
                        Discord: {String(contact.discord)}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </section>
          );
        })()}
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
