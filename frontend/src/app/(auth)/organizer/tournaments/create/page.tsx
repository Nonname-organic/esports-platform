"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Trophy, Calendar, Users, Shield, Gamepad2, DollarSign, Radio,
  MessageSquare, Star, Mail, Eye, BarChart2, ChevronLeft, ChevronRight,
  Save, AlertCircle, Check, Plus, Trash2, Info,
} from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import { ImageUpload } from "@/components/image-upload";
import { cn } from "@/lib/utils";
import {
  DEFAULT_FORM_VALUES, FORM_STEPS, SUPPORTED_GAMES,
  type TournamentCreateForm, type SupportedGame, type FormStepId,
} from "@/types/tournament-create";

// ── バリデーション ────────────────────────────────────────────────────────────
const schema = z.object({
  name: z.string().min(2, "2文字以上入力してください").max(200),
  subtitle: z.string().max(200).optional(),
  description: z.string().max(5000).optional(),
  thumbnail_url: z.string().optional(),
  banner_url: z.string().optional(),
  game: z.string().min(1),
  season: z.string().max(50).optional(),
  split: z.string().max(50).optional(),
  tier: z.enum(["community", "amateur", "semi_pro", "professional"]),
  registration_start_at: z.string().min(1, "募集開始日時を入力してください"),
  registration_end_at: z.string().min(1, "募集締切日時を入力してください"),
  check_in_start_at: z.string().optional(),
  check_in_end_at: z.string().optional(),
  start_at: z.string().min(1, "大会開始日時を入力してください"),
  end_at: z.string().min(1, "大会終了予定を入力してください"),
  max_teams: z.number().int().min(2).max(512),
  min_teams: z.number().int().min(2),
  require_team_membership: z.boolean(),
  require_check_in: z.boolean(),
  format: z.string().min(1),
  bo_format: z.string().min(1),
  seeding_type: z.enum(["auto", "manual"]),
  game_settings: z.record(z.unknown()),
  prize_pool: z.coerce.number().min(0).optional(),
  prize_currency: z.enum(["JPY", "USD"]),
  prizes: z.array(z.object({
    rank_position: z.number(),
    amount: z.coerce.number().min(0),
    currency: z.enum(["JPY", "USD"]),
    description: z.string().optional(),
  })),
  is_streamed: z.boolean(),
  twitch_url: z.string().optional(),
  youtube_url: z.string().optional(),
  commentators: z.array(z.string()),
  casters: z.array(z.string()),
  discord_invite_url: z.string().optional(),
  discord_webhook_url: z.string().optional(),
  notify_entry: z.boolean(),
  notify_checkin: z.boolean(),
  notify_match_start: z.boolean(),
  notify_match_end: z.boolean(),
  sponsors: z.array(z.object({
    name: z.string().min(1),
    logo_url: z.string().optional(),
    website_url: z.string().optional(),
    display_order: z.number(),
  })),
  contact_email: z.string().email("正しいメールアドレスを入力してください").optional().or(z.literal("")),
  contact_discord: z.string().optional(),
  contact_twitter: z.string().optional(),
  visibility: z.enum(["public", "limited", "private"]),
  is_public: z.boolean(),
  analytics_season: z.string().optional(),
  analytics_split: z.string().optional(),
  analytics_region: z.string().optional(),
  analytics_tier: z.string().optional(),
  analytics_enabled: z.boolean(),
  player_stats_enabled: z.boolean(),
  ranking_enabled: z.boolean(),
}).refine((d) => d.min_teams <= d.max_teams, {
  message: "最小チーム数は最大チーム数以下にしてください",
  path: ["min_teams"],
});

type FormValues = z.infer<typeof schema>;

const FIELD_LABELS: Record<string, string> = {
  name: "大会名",
  game: "ゲーム",
  format: "形式",
  min_teams: "最小チーム数",
  max_teams: "最大チーム数",
  registration_start_at: "募集開始日時",
  registration_end_at: "募集締切日時",
  start_at: "大会開始日時",
  end_at: "大会終了予定",
  contact_email: "連絡先メール",
};

// ── UIユーティリティ ──────────────────────────────────────────────────────────
const DRAFT_KEY = "tournament_create_draft";

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="mb-1.5 block text-sm font-medium text-slate-400">
      {children} {required && <span className="text-red-400">*</span>}
    </label>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 flex items-center gap-1 text-xs text-red-400"><AlertCircle className="h-3 w-3" />{message}</p>;
}

function SectionCard({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900 p-6">
      <div className="mb-5">
        <h2 className="text-base font-bold text-white">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

const inputCls = (err?: boolean) => cn(
  "w-full rounded-xl border bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors",
  err ? "border-red-500/50 focus:border-red-500" : "border-white/10 focus:border-brand-500",
);

const selectCls = (err?: boolean) => cn(inputCls(err), "bg-slate-800");

const TIER_OPTIONS = [
  { value: "community", label: "Community", desc: "誰でも参加できる草の根大会" },
  { value: "amateur", label: "Amateur", desc: "アマチュア向け競技大会" },
  { value: "semi_pro", label: "Semi Pro", desc: "セミプロレベルの競技大会" },
  { value: "professional", label: "Professional", desc: "プロチーム参加の公式大会" },
];

const FORMAT_OPTIONS = [
  { value: "single_elimination", label: "シングルエリミネーション", desc: "負けたら終わり" },
  { value: "double_elimination", label: "ダブルエリミネーション", desc: "敗者復活あり" },
  { value: "swiss", label: "スイス式", desc: "成績に応じた対戦相手決定" },
  { value: "round_robin", label: "ラウンドロビン", desc: "総当たり戦" },
  { value: "group_stage", label: "グループステージ", desc: "グループ戦+決勝トーナメント" },
  { value: "league", label: "リーグ戦", desc: "シーズン制リーグ" },
];

// ── ステップコンテンツ ─────────────────────────────────────────────────────────

function Step1Basic({ control, register, errors, watch }: any) {
  const game = watch("game") as SupportedGame;
  const games = Object.entries(SUPPORTED_GAMES) as [SupportedGame, typeof SUPPORTED_GAMES[SupportedGame]][];

  return (
    <div className="space-y-5">
      <SectionCard title="基本情報" subtitle="大会の基本情報を入力してください">
        <div>
          <Label required>大会名</Label>
          <input {...register("name")} className={inputCls(!!errors.name)} placeholder="例: VALORANT Japan Championship 2026" />
          <FieldError message={errors.name?.message} />
        </div>
        <div>
          <Label>サブタイトル</Label>
          <input {...register("subtitle")} className={inputCls()} placeholder="例: Spring Season" />
        </div>
        <div>
          <Label>大会説明</Label>
          <textarea {...register("description")} rows={4} className={inputCls()} placeholder="大会の概要、ルール、参加条件などを記載してください..." />
        </div>
      </SectionCard>

      <SectionCard title="画像">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <Controller name="thumbnail_url" control={control} render={({ field }) => (
            <ImageUpload value={field.value ?? ""} onChange={field.onChange}
              purpose="team_logo" label="サムネイル画像" aspectRatio="square" />
          )} />
          <Controller name="banner_url" control={control} render={({ field }) => (
            <ImageUpload value={field.value ?? ""} onChange={field.onChange}
              purpose="team_banner" label="バナー画像" aspectRatio="banner" className="flex-1" />
          )} />
        </div>
      </SectionCard>

      <SectionCard title="ゲームタイトル" subtitle="対応タイトルを選択してください">
        <div className="space-y-2">
          {games.map(([key, g]) => {
            const isSelected = game === key;
            return (
              <label key={key} className={cn(
                "flex cursor-pointer items-center gap-3 rounded-xl border p-3.5 transition-colors",
                isSelected ? "border-brand-500/50 bg-brand-500/5" : "border-white/8 hover:border-white/15",
              )}>
                <input type="radio" {...register("game")} value={key} className="sr-only" />
                <div className={cn("h-3 w-3 rounded-full border-2 transition-colors",
                  isSelected ? "border-brand-400 bg-brand-400" : "border-slate-600")} />
                <span className={cn("text-sm font-semibold", isSelected ? "text-brand-400" : "text-white")}>
                  {g.label}
                </span>
              </label>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard title="大会分類">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>シーズン</Label>
            <input {...register("season")} className={inputCls()} placeholder="例: 2026" />
          </div>
          <div>
            <Label>スプリット</Label>
            <input {...register("split")} className={inputCls()} placeholder="例: Spring" />
          </div>
        </div>
        <div>
          <Label required>大会Tier</Label>
          <div className="space-y-2">
            {TIER_OPTIONS.map((t) => (
              <label key={t.value} className={cn(
                "flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors",
                watch("tier") === t.value ? "border-brand-500/50 bg-brand-500/5" : "border-white/8 hover:border-white/15",
              )}>
                <input type="radio" {...register("tier")} value={t.value} className="mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-white">{t.label}</p>
                  <p className="text-xs text-slate-500">{t.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function Step2Schedule({ register }: any) {
  const dateInputCls = "w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-brand-500 [color-scheme:dark]";
  return (
    <SectionCard title="募集日程" subtitle="各フェーズの日時を設定してください（後から変更可能）">
      <div className="space-y-5">
        {[
          { label: "募集開始日時", field: "registration_start_at", required: true },
          { label: "募集締切日時", field: "registration_end_at", required: true },
          { label: "チェックイン開始", field: "check_in_start_at" },
          { label: "チェックイン終了", field: "check_in_end_at" },
          { label: "大会開始日時", field: "start_at", required: true },
          { label: "大会終了予定", field: "end_at", required: true },
        ].map(({ label, field, required }) => (
          <div key={field}>
            <Label>{label} {required && <span className="text-red-400">*</span>}</Label>
            <input type="datetime-local" {...register(field)} className={dateInputCls} />
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-start gap-2 rounded-xl border border-brand-500/20 bg-brand-500/5 p-3 text-xs text-slate-400">
        <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-brand-400" />
        <span className="text-red-400">*</span> は必須。日程に応じてステータス（受付→開催中→終了）が自動更新されます。
      </div>
    </SectionCard>
  );
}

function Step3Entry({ register, control, watch, errors }: any) {
  const game = watch("game") as SupportedGame;
  const gameData = SUPPORTED_GAMES[game] || SUPPORTED_GAMES.VALORANT;
  const ranks = gameData.ranks as unknown as string[];

  return (
    <div className="space-y-5">
      <SectionCard title="チーム数設定">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label required>最大チーム数</Label>
            <Controller name="max_teams" control={control} render={({ field }) => (
              <div className="flex flex-wrap gap-2">
                {[4, 8, 16, 32, 64, 128, 256].map((n) => (
                  <button key={n} type="button" onClick={() => field.onChange(n)}
                    className={cn("rounded-xl border px-3 py-2 text-sm font-bold transition-colors",
                      field.value === n ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
                    {n}
                  </button>
                ))}
              </div>
            )} />
          </div>
          <div>
            <Label required>最小チーム数</Label>
            <input type="number" {...register("min_teams", { valueAsNumber: true })}
              className={inputCls(!!errors.min_teams)} min={2} />
            <FieldError message={errors.min_teams?.message} />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="ランク制限" subtitle={`${gameData.label} のランクで制限できます`}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>最低ランク</Label>
            <select {...register("rank_restriction.min_rank")} className={selectCls()}>
              <option value="">制限なし</option>
              {ranks.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <Label>最高ランク</Label>
            <select {...register("rank_restriction.max_rank")} className={selectCls()}>
              <option value="">制限なし</option>
              {ranks.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>
        <div>
          <Label>ランク参照</Label>
          <select {...register("rank_restriction.rank_type")} className={selectCls()}>
            <option value="current">現在ランク</option>
            <option value="peak">最高ランク</option>
          </select>
        </div>
      </SectionCard>

      <SectionCard title="その他制限">
        <div className="space-y-3">
          <label className="flex cursor-pointer items-center gap-3">
            <input type="checkbox" {...register("require_team_membership")} className="h-4 w-4 rounded accent-brand-500" />
            <div>
              <p className="text-sm font-medium text-white">チーム所属を必須にする</p>
              <p className="text-xs text-slate-500">プラットフォームに登録されたチームのみ参加可能</p>
            </div>
          </label>
          <label className="flex cursor-pointer items-center gap-3">
            <input type="checkbox" {...register("require_check_in")} className="h-4 w-4 rounded accent-brand-500" />
            <div>
              <p className="text-sm font-medium text-white">チェックインを必須にする</p>
              <p className="text-xs text-slate-500">大会当日のチェックインでシード確定</p>
            </div>
          </label>
        </div>
      </SectionCard>
    </div>
  );
}

function Step4Format({ register, control, watch }: any) {
  const BO_OPTIONS = ["BO1", "BO3", "BO5", "BO7"];
  return (
    <div className="space-y-5">
      <SectionCard title="トーナメント形式">
        <div className="space-y-2">
          {FORMAT_OPTIONS.map((f) => (
            <label key={f.value} className={cn(
              "flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors",
              watch("format") === f.value ? "border-brand-500/50 bg-brand-500/5" : "border-white/8 hover:border-white/15",
            )}>
              <input type="radio" {...register("format")} value={f.value} className="mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-white">{f.label}</p>
                <p className="text-xs text-slate-500">{f.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="BO形式">
        <Controller name="bo_format" control={control} render={({ field }) => (
          <div className="flex gap-3">
            {BO_OPTIONS.map((bo) => (
              <button key={bo} type="button" onClick={() => field.onChange(bo)}
                className={cn("flex-1 rounded-xl border py-3 text-sm font-bold transition-colors",
                  field.value === bo ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
                {bo}
              </button>
            ))}
          </div>
        )} />
      </SectionCard>

      <SectionCard title="シード設定">
        <Controller name="seeding_type" control={control} render={({ field }) => (
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "auto", label: "自動シード", desc: "ランダムまたはランキングで自動設定" },
              { value: "manual", label: "手動シード", desc: "主催者が手動でシードを設定" },
            ].map((s) => (
              <label key={s.value} className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-xl border p-4 transition-colors",
                field.value === s.value ? "border-brand-500/50 bg-brand-500/5" : "border-white/8 hover:border-white/15",
              )}>
                <input type="radio" value={s.value} checked={field.value === s.value}
                  onChange={() => field.onChange(s.value)} className="sr-only" />
                <span className="text-sm font-bold text-white">{s.label}</span>
                <span className="text-xs text-slate-500">{s.desc}</span>
              </label>
            ))}
          </div>
        )} />
      </SectionCard>
    </div>
  );
}

function Step5Game({ register, control, watch }: any) {
  const game = watch("game") as SupportedGame;
  const gameData = SUPPORTED_GAMES[game] || SUPPORTED_GAMES.VALORANT;
  const maps = gameData.maps as unknown as string[];
  const servers = gameData.servers as unknown as string[];
  const selectedMaps = watch("game_settings.map_pool") as string[] || [];

  const toggleMap = (map: string, field: any) => {
    const current = field.value?.map_pool ?? [];
    const next = current.includes(map) ? current.filter((m: string) => m !== map) : [...current, map];
    field.onChange({ ...field.value, map_pool: next });
  };

  return (
    <div className="space-y-5">
      {(game === "VALORANT" || game === "CS2" || game === "LOL") && (
        <SectionCard title="サーバー設定">
          <Label>使用サーバー</Label>
          <Controller name="game_settings" control={control} render={({ field }) => (
            <select value={field.value?.server ?? ""} onChange={(e) => field.onChange({ ...field.value, server: e.target.value })} className={selectCls()}>
              {servers.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          )} />
        </SectionCard>
      )}

      {(game === "VALORANT" || game === "CS2") && maps.length > 0 && (
        <SectionCard title="マッププール" subtitle="使用するマップを選択してください">
          <Controller name="game_settings" control={control} render={({ field }) => (
            <div className="flex flex-wrap gap-2">
              {maps.map((map) => {
                const isSelected = (field.value?.map_pool ?? []).includes(map);
                return (
                  <button key={map} type="button" onClick={() => toggleMap(map, field)}
                    className={cn("rounded-xl border px-4 py-2 text-sm font-semibold transition-colors",
                      isSelected ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white")}>
                    {isSelected && <Check className="mr-1.5 inline h-3 w-3" />}
                    {map}
                  </button>
                );
              })}
            </div>
          )} />
        </SectionCard>
      )}

      {game === "VALORANT" && (
        <SectionCard title="VALORANT固有設定">
          <Label>Ban/Pickルール</Label>
          <Controller name="game_settings" control={control} render={({ field }) => (
            <select value={field.value?.ban_pick_format ?? "team_veto"} onChange={(e) => field.onChange({ ...field.value, ban_pick_format: e.target.value })} className={selectCls()}>
              <option value="none">なし</option>
              <option value="team_veto">チームVeto（交互）</option>
              <option value="organizer_pick">主催者指定</option>
              <option value="blind_pick">ブラインドピック</option>
            </select>
          )} />
          <Label>オーバータイムルール</Label>
          <Controller name="game_settings" control={control} render={({ field }) => (
            <select value={field.value?.overtime_rule ?? "sudden_death"} onChange={(e) => field.onChange({ ...field.value, overtime_rule: e.target.value })} className={selectCls()}>
              <option value="sudden_death">サドンデス</option>
              <option value="best_of_3">ベスト・オブ・3</option>
              <option value="unlimited">無制限</option>
            </select>
          )} />
        </SectionCard>
      )}

      {game === "CS2" && (
        <SectionCard title="CS2固有設定">
          <label className="flex items-center gap-3">
            <Controller name="game_settings" control={control} render={({ field }) => (
              <input type="checkbox" checked={field.value?.knife_round ?? true}
                onChange={(e) => field.onChange({ ...field.value, knife_round: e.target.checked })}
                className="h-4 w-4 rounded accent-brand-500" />
            )} />
            <span className="text-sm text-white">ナイフラウンドあり</span>
          </label>
        </SectionCard>
      )}

      {game === "APEX" && (
        <SectionCard title="Apex固有設定">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "マッチポイント", field: "match_point", default: 50 },
              { label: "ラウンド数", field: "rounds", default: 6 },
              { label: "ロビー数", field: "lobbies", default: 1 },
            ].map(({ label, field: f, default: def }) => (
              <div key={f}>
                <Label>{label}</Label>
                <Controller name="game_settings" control={control} render={({ field }) => (
                  <input type="number" value={field.value?.[f] ?? def}
                    onChange={(e) => field.onChange({ ...field.value, [f]: Number(e.target.value) })}
                    className={inputCls()} min={1} />
                )} />
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function Step6Prize({ control, watch }: any) {
  const { fields, append, remove } = useFieldArray({ control, name: "prizes" });
  const currency = watch("prize_currency");

  return (
    <div className="space-y-5">
      <SectionCard title="賞金総額">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>総賞金</Label>
            <Controller name="prize_pool" control={control} render={({ field }) => (
              <input type="number" value={field.value ?? ""} onChange={(e) => field.onChange(Number(e.target.value))}
                className={inputCls()} placeholder="0" min={0} />
            )} />
          </div>
          <div>
            <Label>通貨</Label>
            <Controller name="prize_currency" control={control} render={({ field }) => (
              <select {...field} className={selectCls()}>
                <option value="JPY">JPY（円）</option>
                <option value="USD">USD（ドル）</option>
              </select>
            )} />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="賞金配分" subtitle="順位ごとの賞金を設定してください">
        <div className="space-y-3">
          {fields.map((field, idx) => (
            <div key={field.id} className="flex items-center gap-3">
              <span className="w-12 flex-shrink-0 text-center text-sm font-bold text-slate-400">
                {idx + 1}位
              </span>
              <Controller name={`prizes.${idx}.amount`} control={control} render={({ field: f }) => (
                <input type="number" value={f.value} onChange={(e) => f.onChange(Number(e.target.value))}
                  className={cn(inputCls(), "flex-1")} placeholder="金額" min={0} />
              )} />
              <span className="text-sm text-slate-500">{currency}</span>
              <Controller name={`prizes.${idx}.description`} control={control} render={({ field: f }) => (
                <input {...f} className={cn(inputCls(), "flex-1")} placeholder="説明（任意）" />
              )} />
              <button type="button" onClick={() => remove(idx)}
                className="text-slate-600 hover:text-red-400 transition-colors">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => append({ rank_position: fields.length + 1, amount: 0, currency: currency as "JPY" | "USD" })}
          className="flex items-center gap-2 rounded-xl border border-dashed border-white/20 px-4 py-3 text-sm text-slate-400 hover:border-brand-500/50 hover:text-brand-400 transition-colors w-full justify-center"
        >
          <Plus className="h-4 w-4" />
          賞金を追加
        </button>
      </SectionCard>
    </div>
  );
}

function Step7Stream({ register, watch }: any) {
  const isStreamed = watch("is_streamed");
  return (
    <SectionCard title="配信情報" subtitle="大会の配信設定をしてください">
      <label className="flex cursor-pointer items-center gap-3">
        <input type="checkbox" {...register("is_streamed")} className="h-4 w-4 rounded accent-brand-500" />
        <div>
          <p className="text-sm font-medium text-white">配信を行う</p>
          <p className="text-xs text-slate-500">Twitch・YouTubeで配信する場合はチェック</p>
        </div>
      </label>

      {isStreamed && (
        <div className="space-y-4 pt-2">
          <div>
            <Label>Twitch URL</Label>
            <input {...register("twitch_url")} className={inputCls()} placeholder="https://twitch.tv/channel" />
          </div>
          <div>
            <Label>YouTube URL</Label>
            <input {...register("youtube_url")} className={inputCls()} placeholder="https://youtube.com/live/..." />
          </div>
          <div>
            <Label>実況者（カンマ区切り）</Label>
            <input {...register("commentators.0")} className={inputCls()} placeholder="例: 実況者A, 実況者B" />
          </div>
          <div>
            <Label>解説者（カンマ区切り）</Label>
            <input {...register("casters.0")} className={inputCls()} placeholder="例: 解説者A, 解説者B" />
          </div>
        </div>
      )}
    </SectionCard>
  );
}

function Step8Discord({ register, watch }: any) {
  return (
    <div className="space-y-5">
      <SectionCard title="Discord連携">
        <div>
          <Label>Discord招待URL</Label>
          <input {...register("discord_invite_url")} className={inputCls()} placeholder="https://discord.gg/..." />
        </div>
        <div>
          <Label>Discord Webhook URL</Label>
          <input {...register("discord_webhook_url")} className={inputCls()} placeholder="https://discord.com/api/webhooks/..." />
        </div>
      </SectionCard>
      <SectionCard title="通知設定">
        <div className="space-y-3">
          {[
            { field: "notify_entry", label: "エントリー通知", desc: "チームがエントリーした際に通知" },
            { field: "notify_checkin", label: "チェックイン通知", desc: "チェックイン完了時に通知" },
            { field: "notify_match_start", label: "試合開始通知", desc: "試合が開始された際に通知" },
            { field: "notify_match_end", label: "試合終了通知", desc: "試合結果が確定した際に通知" },
          ].map(({ field, label, desc }) => (
            <label key={field} className="flex cursor-pointer items-center gap-3">
              <input type="checkbox" {...register(field)} className="h-4 w-4 rounded accent-brand-500" />
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-slate-500">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function Step9Sponsors({ control, register }: any) {
  const { fields, append, remove } = useFieldArray({ control, name: "sponsors" });
  return (
    <SectionCard title="スポンサー" subtitle="スポンサー情報を登録してください">
      <div className="space-y-4">
        {fields.map((field, idx) => (
          <div key={field.id} className="rounded-xl border border-white/8 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-white">スポンサー {idx + 1}</span>
              <button type="button" onClick={() => remove(idx)} className="text-slate-600 hover:text-red-400 transition-colors">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <div>
              <Label required>スポンサー名</Label>
              <input {...register(`sponsors.${idx}.name`)} className={inputCls()} placeholder="株式会社〇〇" />
            </div>
            <Controller name={`sponsors.${idx}.logo_url`} control={control} render={({ field }) => (
              <ImageUpload value={field.value ?? ""} onChange={field.onChange}
                purpose="team_logo" label="ロゴ画像" aspectRatio="square" />
            )} />
            <div>
              <Label>WebサイトURL</Label>
              <input {...register(`sponsors.${idx}.website_url`)} className={inputCls()} placeholder="https://example.com" />
            </div>
          </div>
        ))}
      </div>
      <button type="button"
        onClick={() => append({ name: "", logo_url: "", website_url: "", display_order: fields.length })}
        className="flex items-center gap-2 rounded-xl border border-dashed border-white/20 px-4 py-3 text-sm text-slate-400 hover:border-brand-500/50 hover:text-brand-400 transition-colors w-full justify-center">
        <Plus className="h-4 w-4" />スポンサーを追加
      </button>
    </SectionCard>
  );
}

function Step10Contact({ register, errors }: any) {
  return (
    <SectionCard title="問い合わせ" subtitle="参加者からの問い合わせ先を設定してください">
      <div>
        <Label>メールアドレス</Label>
        <input type="email" {...register("contact_email")} className={inputCls(!!errors.contact_email)} placeholder="contact@example.com" />
        <FieldError message={errors.contact_email?.message} />
      </div>
      <div>
        <Label>Discord</Label>
        <input {...register("contact_discord")} className={inputCls()} placeholder="username" />
      </div>
      <div>
        <Label>X (Twitter)</Label>
        <input {...register("contact_twitter")} className={inputCls()} placeholder="@handle" />
      </div>
    </SectionCard>
  );
}

function Step11Visibility({ register, watch, control }: any) {
  const visibility = watch("visibility");
  return (
    <SectionCard title="公開設定">
      <div className="space-y-2">
        {[
          { value: "public", label: "公開", desc: "誰でも大会を見つけられます", icon: "🌐" },
          { value: "limited", label: "限定公開", desc: "招待コードを持つ人のみ参加可能", icon: "🔗" },
          { value: "private", label: "非公開", desc: "リストに表示されません", icon: "🔒" },
        ].map((v) => (
          <label key={v.value} className={cn(
            "flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition-colors",
            visibility === v.value ? "border-brand-500/50 bg-brand-500/5" : "border-white/8 hover:border-white/15",
          )}>
            <input type="radio" {...register("visibility")} value={v.value} className="sr-only" />
            <span className="text-xl">{v.icon}</span>
            <div>
              <p className="text-sm font-semibold text-white">{v.label}</p>
              <p className="text-xs text-slate-500">{v.desc}</p>
            </div>
            {visibility === v.value && <Check className="ml-auto h-4 w-4 text-brand-400" />}
          </label>
        ))}
      </div>
    </SectionCard>
  );
}

function Step12Analytics({ register }: any) {
  return (
    <div className="space-y-5">
      <SectionCard title="分析設定" subtitle="ランキング・統計データの収集設定">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>シーズン</Label>
            <input {...register("analytics_season")} className={inputCls()} placeholder="2026" />
          </div>
          <div>
            <Label>スプリット</Label>
            <input {...register("analytics_split")} className={inputCls()} placeholder="Spring" />
          </div>
        </div>
        <div>
          <Label>地域</Label>
          <select {...register("analytics_region")} className={selectCls()}>
            <option value="">指定なし</option>
            <option value="JP">日本</option>
            <option value="AP">アジアパシフィック</option>
            <option value="NA">北米</option>
            <option value="EU">ヨーロッパ</option>
          </select>
        </div>
        <div className="space-y-3 pt-2">
          {[
            { field: "ranking_enabled", label: "ランキング集計", desc: "この大会の結果をランキングに反映する" },
            { field: "player_stats_enabled", label: "プレイヤー統計", desc: "個人統計データを収集・表示する" },
            { field: "analytics_enabled", label: "アナリティクス", desc: "詳細な統計分析を有効にする" },
          ].map(({ field, label, desc }) => (
            <label key={field} className="flex cursor-pointer items-center gap-3">
              <input type="checkbox" {...register(field)} className="h-4 w-4 rounded accent-brand-500" />
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-slate-500">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

// ── メインコンポーネント ────────────────────────────────────────────────────────
export default function TournamentCreatePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [currentStep, setCurrentStep] = useState(0);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [draftId, setDraftId] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // ドラフト読み込み
  const loadDraft = (): Partial<FormValues> => {
    try {
      const stored = localStorage.getItem(DRAFT_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch { return {}; }
  };

  const {
    register, handleSubmit, control, watch, formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ...(DEFAULT_FORM_VALUES as any), ...loadDraft() },
  });

  const formValues = watch();

  // Autosave: localStorage + backend
  const autoSave = useCallback((values: FormValues) => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(values));
    setSavedAt(new Date());
  }, []);

  useEffect(() => {
    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => autoSave(formValues as FormValues), 1500);
    return () => clearTimeout(saveTimeoutRef.current);
  }, [formValues, autoSave]);

  // datetime-local（ローカル時刻・空可）→ ISO(UTC)。空はundefinedで送らない。
  const toIso = (v?: string) => {
    if (!v) return undefined;
    const d = new Date(v);
    return isNaN(d.getTime()) ? undefined : d.toISOString();
  };

  const create = useMutation({
    mutationFn: async (values: FormValues) => {
      const res = await tournamentApi.create({
        name: values.name,
        game: values.game as any,
        format: values.format,
        max_teams: values.max_teams,
        description: values.description,
        prize_pool: values.prize_pool,
        registration_start_at: toIso(values.registration_start_at),
        registration_end_at: toIso(values.registration_end_at),
        check_in_start_at: toIso(values.check_in_start_at),
        start_at: toIso(values.start_at),
        end_at: toIso(values.end_at),
        require_check_in: values.require_check_in,
        is_public: values.is_public,
        rules: {
          bo_format: values.bo_format,
          seeding_type: values.seeding_type,
          game_settings: values.game_settings,
          tier: values.tier,
          subtitle: values.subtitle,
          thumbnail_url: values.thumbnail_url,
          banner_url: values.banner_url,
          season: values.season,
          split: values.split,
          prizes: values.prizes,
          sponsors: values.sponsors,
          stream: {
            is_streamed: values.is_streamed,
            twitch_url: values.twitch_url,
            youtube_url: values.youtube_url,
          },
          discord: {
            invite_url: values.discord_invite_url,
            webhook_url: values.discord_webhook_url,
            notify_entry: values.notify_entry,
            notify_checkin: values.notify_checkin,
            notify_match_start: values.notify_match_start,
            notify_match_end: values.notify_match_end,
          },
          contact: {
            email: values.contact_email,
            discord: values.contact_discord,
            twitter: values.contact_twitter,
          },
          visibility: values.visibility,
          analytics: {
            enabled: values.analytics_enabled,
            player_stats: values.player_stats_enabled,
            ranking: values.ranking_enabled,
          },
        },
      });
      localStorage.removeItem(DRAFT_KEY);
      return res;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["tournaments", "mine"] });
      router.push(`/organizer/tournaments/${res.data.id}`);
    },
  });

  const steps = FORM_STEPS;
  const totalSteps = steps.length;
  const progress = ((currentStep + 1) / totalSteps) * 100;

  const stepProps = { register, control, watch, errors };

  const STEP_COMPONENTS = [
    <Step1Basic key="1" {...stepProps} />,
    <Step2Schedule key="2" {...stepProps} />,
    <Step3Entry key="3" {...stepProps} />,
    <Step4Format key="4" {...stepProps} />,
    <Step5Game key="5" {...stepProps} />,
    <Step6Prize key="6" {...stepProps} />,
    <Step7Stream key="7" {...stepProps} />,
    <Step8Discord key="8" {...stepProps} />,
    <Step9Sponsors key="9" {...stepProps} />,
    <Step10Contact key="10" {...stepProps} />,
    <Step11Visibility key="11" {...stepProps} />,
    <Step12Analytics key="12" {...stepProps} />,
  ];

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-slate-950">
      {/* ヘッダー */}
      <div className="border-b border-white/10 bg-slate-900/80 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Trophy className="h-5 w-5 text-brand-400" />
            <span className="font-bold text-white">大会を作成</span>
            <span className="text-xs text-slate-500">
              {steps[currentStep].label}
              {savedAt && <span className="ml-2 text-green-500/70">・自動保存済み</span>}
            </span>
          </div>
          <button onClick={() => router.back()} className="text-xs text-slate-500 hover:text-white transition-colors">
            キャンセル
          </button>
        </div>
      </div>

      {/* プログレスバー */}
      <div className="h-1 bg-white/5">
        <div className="h-full bg-brand-500 transition-all duration-300" style={{ width: `${progress}%` }} />
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* サイドバー */}
        <aside className="hidden w-52 flex-shrink-0 overflow-y-auto border-r border-white/10 bg-slate-900/50 py-4 lg:block">
          <nav className="space-y-0.5 px-2">
            {steps.map((step, idx) => {
              const isDone = idx < currentStep;
              const isActive = idx === currentStep;
              return (
                <button
                  key={step.id}
                  type="button"
                  onClick={() => setCurrentStep(idx)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                    isActive ? "bg-brand-500/10 text-brand-400" :
                      isDone ? "text-green-400 hover:bg-white/5" : "text-slate-500 hover:bg-white/5 hover:text-white",
                  )}
                >
                  <span className={cn("flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                    isActive ? "bg-brand-500 text-white" : isDone ? "bg-green-500/20 text-green-400" : "bg-white/5 text-slate-600")}>
                    {isDone ? <Check className="h-3 w-3" /> : idx + 1}
                  </span>
                  <span className="font-medium">{step.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* メインコンテンツ */}
        <main className="flex-1 overflow-y-auto p-4">
          <div className="mx-auto max-w-2xl">
            <form onSubmit={handleSubmit((v) => create.mutate(v))}>
              {create.isError && (
                <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {create.error instanceof Error ? create.error.message : "作成に失敗しました"}
                </div>
              )}

              {Object.keys(errors).length > 0 && (
                <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  <p className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="h-4 w-4" /> 未入力・不備の項目があります
                  </p>
                  <ul className="mt-1.5 list-disc pl-6 text-xs">
                    {Object.entries(errors).map(([k, v]) => (
                      <li key={k}>{FIELD_LABELS[k] ?? k}：{(v as { message?: string })?.message ?? "入力してください"}</li>
                    ))}
                  </ul>
                </div>
              )}

              {STEP_COMPONENTS[currentStep]}

              {/* ナビゲーション */}
              <div className="mt-6 flex items-center justify-between pb-8">
                <button
                  type="button"
                  onClick={() => currentStep > 0 ? setCurrentStep(currentStep - 1) : router.back()}
                  className="flex items-center gap-2 rounded-xl border border-white/10 px-5 py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                  {currentStep === 0 ? "キャンセル" : "前へ"}
                </button>

                <span className="text-xs text-slate-600">{currentStep + 1} / {totalSteps}</span>

                {currentStep < totalSteps - 1 ? (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(currentStep + 1)}
                    className="flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 transition-colors"
                  >
                    次へ <ChevronRight className="h-4 w-4" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={isSubmitting || create.isPending}
                    className="flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
                  >
                    <Trophy className="h-4 w-4" />
                    {create.isPending ? "作成中..." : "大会を作成する"}
                  </button>
                )}
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}
