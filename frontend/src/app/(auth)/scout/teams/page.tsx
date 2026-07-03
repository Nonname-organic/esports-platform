"use client";

import { useState } from "react";
import Link from "next/link";
import { Shield, Filter, ChevronRight, Trophy, Star } from "lucide-react";
import { useScoutTeams } from "@/features/scout/hooks/use-scout";
import { cn, getGameColor } from "@/lib/utils";
import type { ScoutTeamCard } from "@/features/scout/api/scout-api";

const GAMES = ["VALORANT", "APEX", "CS2", "LOL", "OVERWATCH"];

const ROLES: Record<string, string[]> = {
  VALORANT: ["Duelist", "Sentinel", "Initiator", "Controller"],
  APEX: ["Assault", "Recon", "Skirmisher", "Support", "Controller"],
  CS2: ["Entry", "AWPer", "Support", "Lurker", "IGL"],
  LOL: ["Top", "Jungle", "Mid", "ADC", "Support"],
  OVERWATCH: ["Tank", "Damage", "Support"],
};

const RANKS: Record<string, string[]> = {
  VALORANT: ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "アセンダント", "イモータル", "レディアント"],
  LOL: ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "エメラルド", "ダイヤモンド", "マスター", "グランドマスター", "チャレンジャー"],
  APEX: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "マスター", "プレデター"],
  CS2: ["シルバー", "ゴールドノバ", "MG", "MG2", "MGE", "DMG", "LEM", "SMFC", "GE"],
  OVERWATCH: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "マスター", "グランドマスター", "チャンピオン"],
};

const ACTIVITY_LEVELS = [
  { value: "casual", label: "カジュアル" },
  { value: "semi", label: "セミプロ" },
  { value: "competitive", label: "競技志向" },
  { value: "pro", label: "プロ" },
];

const ACTIVE_HOURS = [
  { value: "morning", label: "朝（6〜12時）" },
  { value: "afternoon", label: "昼（12〜18時）" },
  { value: "evening", label: "夜（18〜24時）" },
  { value: "late_night", label: "深夜（0〜6時）" },
];

const sel = "rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500";
const numIn = "w-20 rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500";

export default function TeamDiscoveryPage() {
  const [game, setGame] = useState("VALORANT");
  const [region, setRegion] = useState("");
  const [recruitingOnly, setRecruitingOnly] = useState(false);
  const [recruitingRole, setRecruitingRole] = useState("");
  const [rankRequirement, setRankRequirement] = useState("");
  const [activityLevel, setActivityLevel] = useState("");
  const [activeHours, setActiveHours] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [premierActive, setPremierActive] = useState(false);
  const [hasTournaments, setHasTournaments] = useState(false);
  const [seekingStaff, setSeekingStaff] = useState("");

  const { data: teams, isLoading } = useScoutTeams({
    game,
    region: region || undefined,
    recruiting_only: recruitingOnly,
    recruiting_role: recruitingRole || undefined,
    rank_requirement: rankRequirement || undefined,
    activity_level: activityLevel || undefined,
    active_hours: activeHours || undefined,
    team_min_age: minAge ? Number(minAge) : undefined,
    team_max_age: maxAge ? Number(maxAge) : undefined,
    premier_active: premierActive || undefined,
    has_tournaments: hasTournaments || undefined,
    seeking_staff: seekingStaff || undefined,
  });

  const roles = ROLES[game] ?? [];
  const ranks = RANKS[game] ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/scout" className="text-slate-500 hover:text-white transition-colors">Scout</Link>
        <ChevronRight className="h-4 w-4 text-slate-600" />
        <h1 className="text-xl font-black text-white">Team Discovery</h1>
      </div>

      {/* フィルター */}
      <div className="mb-6 space-y-3 rounded-2xl border border-white/10 bg-slate-900 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" />検索条件
        </div>

        {/* ゲーム */}
        <div className="flex flex-wrap gap-2">
          {GAMES.map((g) => (
            <button key={g} onClick={() => { setGame(g); setRecruitingRole(""); setRankRequirement(""); }}
              className={cn("rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                game === g ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-500 hover:text-white")}>
              {g}
            </button>
          ))}
        </div>

        {/* 行1: 募集状況・地域・活動レベル・活動時間 */}
        <div className="flex flex-wrap gap-3">
          <select value={region} onChange={(e) => setRegion(e.target.value)} className={sel}>
            <option value="">全リージョン</option>
            {["JP", "KR", "AP", "NA", "EU"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={activityLevel} onChange={(e) => setActivityLevel(e.target.value)} className={sel}>
            <option value="">全活動レベル</option>
            {ACTIVITY_LEVELS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
          <select value={activeHours} onChange={(e) => setActiveHours(e.target.value)} className={sel}>
            <option value="">全活動時間</option>
            {ACTIVE_HOURS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>

        {/* 行2: 募集ロール・募集ランク帯 */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500">募集ロール</span>
            <select value={recruitingRole} onChange={(e) => setRecruitingRole(e.target.value)} className={sel}>
              <option value="">指定なし</option>
              {roles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500">募集ランク帯</span>
            <select value={rankRequirement} onChange={(e) => setRankRequirement(e.target.value)} className={sel}>
              <option value="">指定なし</option>
              {ranks.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500">スタッフ募集</span>
            <select value={seekingStaff} onChange={(e) => setSeekingStaff(e.target.value)} className={sel}>
              <option value="">指定なし</option>
              <option value="coach">コーチ</option>
              <option value="manager">マネージャー</option>
              <option value="reserve">リザーブ</option>
            </select>
          </div>
        </div>

        {/* 行3: 年齢条件・チェックボックス群 */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-500">年齢条件</span>
            <input value={minAge} onChange={(e) => setMinAge(e.target.value)} type="number" placeholder="下限" className={numIn} min={0} max={99} />
            <span className="text-xs text-slate-600">〜</span>
            <input value={maxAge} onChange={(e) => setMaxAge(e.target.value)} type="number" placeholder="上限" className={numIn} min={0} max={99} />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input type="checkbox" checked={recruitingOnly} onChange={(e) => setRecruitingOnly(e.target.checked)} className="h-4 w-4 rounded accent-brand-500" />
            募集中のみ
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input type="checkbox" checked={hasTournaments} onChange={(e) => setHasTournaments(e.target.checked)} className="h-4 w-4 rounded accent-brand-500" />
            大会参加実績あり
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input type="checkbox" checked={premierActive} onChange={(e) => setPremierActive(e.target.checked)} className="h-4 w-4 rounded accent-yellow-500" />
            Premier参加
          </label>
        </div>
      </div>

      {/* 結果 */}
      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : !teams || teams.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-center">
          <Shield className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-500">条件に合うチームがいません</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((t) => <TeamCard key={t.team_id} team={t} />)}
        </div>
      )}
    </div>
  );
}

function TeamCard({ team }: { team: ScoutTeamCard }) {
  return (
    <Link href={`/teams/${team.team_id}`}
      className="rounded-xl border border-white/8 bg-slate-900 p-4 hover:border-brand-500/40 transition-colors">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-11 w-11 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
          {team.logo_url ? <img src={team.logo_url} alt="" className="h-full w-full object-contain" /> :
            <span className="text-xs font-bold text-slate-500">{team.tag.slice(0, 3)}</span>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="truncate font-bold text-white">{team.name}</p>
            {team.is_recruiting && <span className="rounded-full bg-green-500/10 px-1.5 py-0.5 text-[9px] font-bold text-green-400">募集中</span>}
            {team.premier_active && <span className="rounded-full bg-yellow-500/10 px-1.5 py-0.5 text-[9px] font-bold text-yellow-400">Premier</span>}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span>[{team.tag}]</span>
            {team.region && <span>· {team.region}</span>}
            {team.activity_level && <span>· {team.activity_level}</span>}
          </div>
        </div>
      </div>
      <div className="mb-3 flex items-center gap-1.5 flex-wrap">
        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(team.game))}>{team.game}</span>
        {team.active_hours && <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">{team.active_hours}</span>}
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-brand-400">{team.avg_rating?.toFixed(0) ?? "—"}</p>
          <p className="text-[9px] text-slate-600">Rating</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-white">{(team.win_rate * 100).toFixed(0)}%</p>
          <p className="text-[9px] text-slate-600">勝率</p>
        </div>
        <div className="rounded-lg bg-white/3 py-2">
          <p className="text-sm font-black text-slate-300">{team.roster_count}</p>
          <p className="text-[9px] text-slate-600">人数</p>
        </div>
      </div>
    </Link>
  );
}
