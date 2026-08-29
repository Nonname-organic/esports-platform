"use client";

import { forwardRef, use, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ChevronRight, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { tournamentApi } from "@/features/tournaments/api/tournament-api";
import { ImageUpload } from "@/components/image-upload";
import { AttachmentUpload } from "@/components/attachment-upload";
import { cn } from "@/lib/utils";
import { SUPPORTED_GAMES } from "@/types/tournament-create";
import type { TournamentAttachment } from "@/types/tournament";

function toLocalInput(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
function toIso(local?: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return isNaN(d.getTime()) ? undefined : d.toISOString();
}
/** 未入力(空文字)は「変更なし」ではなく明示的に消せるよう空文字のまま送る */
function orEmpty(v?: string | null): string {
  return v ?? "";
}

const TIER_OPTIONS = [
  { value: "community", label: "Community" },
  { value: "amateur", label: "Amateur" },
  { value: "semi_pro", label: "Semi Pro" },
  { value: "professional", label: "Professional" },
];

const FORMAT_OPTIONS = [
  { value: "single_elimination", label: "シングルエリミネーション" },
  { value: "double_elimination", label: "ダブルエリミネーション" },
  { value: "swiss", label: "スイス式" },
  { value: "round_robin", label: "ラウンドロビン" },
  { value: "group_stage", label: "グループステージ" },
  { value: "league", label: "リーグ戦" },
];

const BO_OPTIONS = ["BO1", "BO3", "BO5", "BO7"];
const VISIBILITY_OPTIONS = [
  { value: "public", label: "公開" },
  { value: "limited", label: "限定公開（URLを知っている人のみ）" },
  { value: "private", label: "非公開" },
];

interface PrizeRow { rank_position: number; amount: number | string; currency: string; description?: string }
interface SponsorRow { name: string; logo_url?: string; website_url?: string; display_order: number }

interface FormValues {
  // 基本情報
  name: string;
  subtitle: string;
  description: string;
  thumbnail_url: string;
  banner_url: string;
  attachments: TournamentAttachment[];
  season: string;
  split: string;
  tier: string;
  // スケジュール
  registration_start_at: string;
  registration_end_at: string;
  check_in_start_at: string;
  check_in_end_at: string;
  start_at: string;
  end_at: string;
  // 参加条件
  max_teams: number | string;
  min_teams: number | string;
  require_team_membership: boolean;
  require_check_in: boolean;
  approval_mode: string;
  min_age: number | string;
  max_age: number | string;
  // 大会形式
  format: string;
  bo_format: string;
  seeding_type: string;
  // 競技設定
  server: string;
  map_pool: string;
  ban_pick_format: string;
  overtime_rule: string;
  // 賞金
  prize_pool: number | string;
  prize_currency: string;
  prizes: PrizeRow[];
  // 配信
  is_streamed: boolean;
  twitch_url: string;
  youtube_url: string;
  // Discord
  discord_invite_url: string;
  discord_webhook_url: string;
  notify_entry: boolean;
  notify_checkin: boolean;
  notify_match_start: boolean;
  notify_match_end: boolean;
  // スポンサー
  sponsors: SponsorRow[];
  // 問い合わせ
  contact_email: string;
  contact_discord: string;
  contact_twitter: string;
  // 公開設定
  visibility: string;
  is_public: boolean;
  // 分析設定
  analytics_enabled: boolean;
  player_stats_enabled: boolean;
  ranking_enabled: boolean;
}

export default function TournamentEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();

  const { data: t, isLoading } = useQuery({
    queryKey: ["tournament", id],
    queryFn: () => tournamentApi.get(id),
    select: (res) => res.data,
  });

  const { register, handleSubmit, reset, control, watch, formState: { isSubmitting } } =
    useForm<FormValues>({ defaultValues: { prizes: [], sponsors: [], attachments: [] } });

  const prizeFields = useFieldArray({ control, name: "prizes" });
  const sponsorFields = useFieldArray({ control, name: "sponsors" });

  const update = useMutation({
    mutationFn: (data: Parameters<typeof tournamentApi.update>[1]) => tournamentApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tournament", id] });
      router.push(`/organizer/tournaments/${id}`);
    },
  });

  // 既存値の読み戻し（拡張項目は rules JSON に入っている）
  useEffect(() => {
    if (!t) return;
    const r = (t.rules ?? {}) as Record<string, any>;
    const gs = (r.game_settings ?? {}) as Record<string, any>;
    const stream = (r.stream ?? {}) as Record<string, any>;
    const discord = (r.discord ?? {}) as Record<string, any>;
    const contact = (r.contact ?? {}) as Record<string, any>;
    const analytics = (r.analytics ?? {}) as Record<string, any>;
    const age = (t.age_restriction ?? {}) as Record<string, any>;

    reset({
      name: t.name,
      subtitle: orEmpty(t.subtitle ?? r.subtitle),
      description: orEmpty(t.description),
      thumbnail_url: orEmpty(t.thumbnail_url ?? r.thumbnail_url),
      banner_url: orEmpty(t.banner_url ?? r.banner_url),
      attachments: t.attachments ?? [],
      season: orEmpty(t.season ?? r.season),
      split: orEmpty(t.split ?? r.split),
      tier: t.tier ?? r.tier ?? "community",
      registration_start_at: toLocalInput(t.registration_start_at),
      registration_end_at: toLocalInput(t.registration_end_at),
      check_in_start_at: toLocalInput(t.check_in_start_at),
      check_in_end_at: toLocalInput(t.check_in_end_at),
      start_at: toLocalInput(t.start_at),
      end_at: toLocalInput(t.end_at),
      max_teams: t.max_teams ?? "",
      min_teams: t.min_teams ?? "",
      require_team_membership: t.require_team_membership ?? false,
      require_check_in: t.require_check_in ?? false,
      approval_mode: t.approval_mode ?? "manual",
      min_age: age.min_age ?? "",
      max_age: age.max_age ?? "",
      format: t.format ?? "single_elimination",
      bo_format: r.bo_format ?? "BO3",
      seeding_type: t.seeding_type ?? r.seeding_type ?? "auto",
      server: gs.server ?? "",
      map_pool: Array.isArray(gs.map_pool) ? gs.map_pool.join(", ") : "",
      ban_pick_format: gs.ban_pick_format ?? "team_veto",
      overtime_rule: gs.overtime_rule ?? "sudden_death",
      prize_pool: (t.prize_pool as number | null) ?? "",
      prize_currency: t.prize_currency ?? "JPY",
      prizes: Array.isArray(r.prizes) ? r.prizes : [],
      is_streamed: stream.is_streamed ?? false,
      twitch_url: orEmpty(stream.twitch_url),
      youtube_url: orEmpty(stream.youtube_url),
      discord_invite_url: orEmpty(discord.invite_url),
      // Webhookは読み戻さない（APIが返さない）。空欄のまま保存すれば維持される
      discord_webhook_url: "",
      notify_entry: discord.notify_entry ?? true,
      notify_checkin: discord.notify_checkin ?? true,
      notify_match_start: discord.notify_match_start ?? true,
      notify_match_end: discord.notify_match_end ?? true,
      sponsors: Array.isArray(r.sponsors) ? r.sponsors : [],
      contact_email: orEmpty(contact.email),
      contact_discord: orEmpty(contact.discord),
      contact_twitter: orEmpty(contact.twitter),
      visibility: t.visibility ?? r.visibility ?? "public",
      is_public: t.is_public ?? true,
      analytics_enabled: t.analytics_enabled ?? analytics.enabled ?? true,
      player_stats_enabled: t.player_stats_enabled ?? analytics.player_stats ?? true,
      ranking_enabled: t.ranking_enabled ?? analytics.ranking ?? true,
    });
  }, [t, reset]);

  const onSubmit = handleSubmit((v) => {
    const num = (x: number | string) => (x !== "" && x != null ? Number(x) : undefined);
    update.mutate({
      name: v.name || undefined,
      subtitle: v.subtitle,
      description: v.description,
      thumbnail_url: v.thumbnail_url,
      banner_url: v.banner_url,
      attachments: v.attachments,
      season: v.season,
      split: v.split,
      tier: v.tier,
      registration_start_at: toIso(v.registration_start_at),
      registration_end_at: toIso(v.registration_end_at),
      check_in_start_at: toIso(v.check_in_start_at),
      check_in_end_at: toIso(v.check_in_end_at),
      start_at: toIso(v.start_at),
      end_at: toIso(v.end_at),
      max_teams: num(v.max_teams),
      min_teams: num(v.min_teams),
      require_team_membership: v.require_team_membership,
      require_check_in: v.require_check_in,
      approval_mode: v.approval_mode,
      format: v.format,
      seeding_type: v.seeding_type,
      prize_pool: num(v.prize_pool),
      prize_currency: v.prize_currency,
      discord_webhook_url: v.discord_webhook_url,
      visibility: v.visibility,
      is_public: v.is_public,
      analytics_enabled: v.analytics_enabled,
      player_stats_enabled: v.player_stats_enabled,
      ranking_enabled: v.ranking_enabled,
      age_restriction: {
        ...(num(v.min_age) != null ? { min_age: num(v.min_age) } : {}),
        ...(num(v.max_age) != null ? { max_age: num(v.max_age) } : {}),
      },
      // 作成時と同じ構造で rules を差し替える
      rules: {
        ...((t?.rules ?? {}) as Record<string, unknown>),
        bo_format: v.bo_format,
        seeding_type: v.seeding_type,
        tier: v.tier,
        subtitle: v.subtitle,
        thumbnail_url: v.thumbnail_url,
        banner_url: v.banner_url,
        season: v.season,
        split: v.split,
        game_settings: {
          server: v.server,
          map_pool: v.map_pool ? v.map_pool.split(",").map((s) => s.trim()).filter(Boolean) : [],
          ban_pick_format: v.ban_pick_format,
          overtime_rule: v.overtime_rule,
        },
        prizes: v.prizes.map((p) => ({ ...p, amount: Number(p.amount) || 0 })),
        sponsors: v.sponsors,
        stream: {
          is_streamed: v.is_streamed,
          twitch_url: v.twitch_url,
          youtube_url: v.youtube_url,
        },
        discord: {
          invite_url: v.discord_invite_url,
          webhook_url: v.discord_webhook_url,
          notify_entry: v.notify_entry,
          notify_checkin: v.notify_checkin,
          notify_match_start: v.notify_match_start,
          notify_match_end: v.notify_match_end,
        },
        contact: {
          email: v.contact_email,
          discord: v.contact_discord,
          twitter: v.contact_twitter,
        },
        visibility: v.visibility,
        analytics: {
          enabled: v.analytics_enabled,
          player_stats: v.player_stats_enabled,
          ranking: v.ranking_enabled,
        },
      },
    });
  });

  const inputCls = "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500 transition-colors";
  const selectCls = cn(inputCls, "bg-slate-800");
  const dateCls = cn(inputCls, "[color-scheme:dark]");

  if (isLoading) return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
    </div>
  );
  if (!t) return <div className="p-8 text-center text-slate-400">大会が見つかりません</div>;

  const gameMaps = (SUPPORTED_GAMES as Record<string, { maps?: readonly string[]; servers?: readonly string[] }>)[t.game];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* パンくず */}
      <nav className="mb-4 flex items-center gap-2 text-sm text-slate-400">
        <Link href={`/organizer/tournaments/${id}`} className="hover:text-white transition-colors">{t.name}</Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-white">大会情報を編集</span>
      </nav>

      <form onSubmit={onSubmit} className="space-y-5">
        {update.isError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" />
            {update.error instanceof Error ? update.error.message : "更新に失敗しました"}
          </div>
        )}

        {/* 基本情報 */}
        <Section title="基本情報">
          <Field label="大会名">
            <input {...register("name")} className={inputCls} placeholder="大会名" />
          </Field>
          <Field label="サブタイトル">
            <input {...register("subtitle")} className={inputCls} placeholder="例: Spring Season" />
          </Field>
          <Field label="大会説明">
            <textarea {...register("description")} rows={4} className={inputCls} placeholder="大会の説明..." />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="シーズン">
              <input {...register("season")} className={inputCls} placeholder="例: 2026" />
            </Field>
            <Field label="スプリット">
              <input {...register("split")} className={inputCls} placeholder="例: Spring" />
            </Field>
          </div>
          <Field label="大会ティア">
            <select {...register("tier")} className={selectCls}>
              {TIER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="ゲームタイトル">
            <input value={t.game} disabled className={cn(inputCls, "opacity-60")} />
            <p className="mt-1 text-xs text-slate-500">ゲームタイトルは作成後に変更できません</p>
          </Field>
        </Section>

        {/* ビジュアル */}
        <Section title="ビジュアル">
          <div className="flex gap-5">
            <Controller name="thumbnail_url" control={control} render={({ field }) => (
              <ImageUpload value={field.value ?? ""} onChange={field.onChange}
                purpose="team_logo" label="サムネイル" aspectRatio="square" />
            )} />
            <Controller name="banner_url" control={control} render={({ field }) => (
              <ImageUpload value={field.value ?? ""} onChange={field.onChange}
                purpose="team_banner" label="バナー画像" aspectRatio="banner" className="flex-1" />
            )} />
          </div>
          <Field label="添付ファイル">
            <Controller name="attachments" control={control} render={({ field }) => (
              <AttachmentUpload value={field.value ?? []} onChange={field.onChange} />
            )} />
          </Field>
        </Section>

        {/* スケジュール */}
        <Section title="スケジュール">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              { name: "registration_start_at" as const, label: "参加受付開始" },
              { name: "registration_end_at" as const, label: "参加受付終了" },
              { name: "check_in_start_at" as const, label: "チェックイン開始" },
              { name: "check_in_end_at" as const, label: "チェックイン終了" },
              { name: "start_at" as const, label: "大会開始" },
              { name: "end_at" as const, label: "大会終了" },
            ].map(({ name, label }) => (
              <Field key={name} label={label}>
                <input type="datetime-local" {...register(name)} className={dateCls} />
              </Field>
            ))}
          </div>
        </Section>

        {/* 参加条件 */}
        <Section title="参加条件">
          <div className="grid grid-cols-2 gap-4">
            <Field label="最大チーム数">
              <input type="number" min={2} max={256} {...register("max_teams")} className={inputCls} />
            </Field>
            <Field label="最小チーム数">
              <input type="number" min={2} {...register("min_teams")} className={inputCls} />
            </Field>
            <Field label="最低年齢">
              <input type="number" min={0} {...register("min_age")} className={inputCls} placeholder="制限なし" />
            </Field>
            <Field label="最高年齢">
              <input type="number" min={0} {...register("max_age")} className={inputCls} placeholder="制限なし" />
            </Field>
          </div>
          <Check {...register("require_team_membership")} label="チーム所属を必須にする" />
          <Check {...register("require_check_in")} label="チェックインを必須にする" />
          <Field label="参加承認の方式">
            <select {...register("approval_mode")} className={selectCls}>
              <option value="manual">手動承認（主催者が申請ごとに承認・却下）</option>
              <option value="auto">自動承認（先着順・定員超過分は補欠）</option>
              <option value="lottery">自動承認（抽選・受付終了時に決定）</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              抽選は受付終了のタイミングで行います。受付中の申請はすべて「審査中」のままです。
            </p>
          </Field>
        </Section>

        {/* 大会形式 */}
        <Section title="大会形式">
          <Field label="トーナメント形式">
            <select {...register("format")} className={selectCls}>
              {FORMAT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="試合形式">
              <select {...register("bo_format")} className={selectCls}>
                {BO_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </Field>
            <Field label="シード方式">
              <select {...register("seeding_type")} className={selectCls}>
                <option value="auto">自動</option>
                <option value="manual">手動</option>
              </select>
            </Field>
          </div>
        </Section>

        {/* 競技設定 */}
        <Section title="競技設定">
          <div className="grid grid-cols-2 gap-4">
            <Field label="サーバー">
              <select {...register("server")} className={selectCls}>
                <option value="">未設定</option>
                {(gameMaps?.servers ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Ban/Pick形式">
              <select {...register("ban_pick_format")} className={selectCls}>
                <option value="none">なし</option>
                <option value="team_veto">チームVeto（交互）</option>
                <option value="organizer_pick">主催者指定</option>
                <option value="blind_pick">ブラインドピック</option>
              </select>
            </Field>
          </div>
          <Field label="マッププール（カンマ区切り）">
            <input {...register("map_pool")} className={inputCls}
              placeholder={(gameMaps?.maps ?? []).slice(0, 4).join(", ")} />
          </Field>
          <Field label="オーバータイム">
            <select {...register("overtime_rule")} className={selectCls}>
              <option value="sudden_death">サドンデス</option>
              <option value="best_of_3">ベスト・オブ・3</option>
              <option value="unlimited">無制限</option>
            </select>
          </Field>
        </Section>

        {/* 賞金 */}
        <Section title="賞金">
          <div className="grid grid-cols-2 gap-4">
            <Field label="賞金総額">
              <input type="number" min={0} {...register("prize_pool")} className={inputCls} placeholder="0" />
            </Field>
            <Field label="通貨">
              <select {...register("prize_currency")} className={selectCls}>
                <option value="JPY">JPY</option>
                <option value="USD">USD</option>
              </select>
            </Field>
          </div>
          <div className="space-y-2">
            {prizeFields.fields.map((f, i) => (
              <div key={f.id} className="flex items-center gap-2">
                <input type="number" min={1} {...register(`prizes.${i}.rank_position`)}
                  className={cn(inputCls, "w-20")} placeholder="順位" />
                <input type="number" min={0} {...register(`prizes.${i}.amount`)}
                  className={cn(inputCls, "flex-1")} placeholder="金額" />
                <select {...register(`prizes.${i}.currency`)} className={cn(selectCls, "w-24")}>
                  <option value="JPY">JPY</option>
                  <option value="USD">USD</option>
                </select>
                <button type="button" onClick={() => prizeFields.remove(i)}
                  className="rounded-lg p-2 text-slate-500 hover:text-red-400 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            <button type="button"
              onClick={() => prizeFields.append({ rank_position: prizeFields.fields.length + 1, amount: 0, currency: watch("prize_currency") || "JPY" })}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white transition-colors">
              <Plus className="h-3.5 w-3.5" /> 賞金の順位を追加
            </button>
          </div>
        </Section>

        {/* 配信 */}
        <Section title="配信情報">
          <Check {...register("is_streamed")} label="配信あり" />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Twitch URL">
              <input {...register("twitch_url")} className={inputCls} placeholder="https://twitch.tv/..." />
            </Field>
            <Field label="YouTube URL">
              <input {...register("youtube_url")} className={inputCls} placeholder="https://youtube.com/..." />
            </Field>
          </div>
        </Section>

        {/* Discord */}
        <Section title="Discord">
          <Field label="招待URL">
            <input {...register("discord_invite_url")} className={inputCls} placeholder="https://discord.gg/..." />
          </Field>
          <Field label="Webhook URL（通知送信先）">
            {/* Webhookは秘密情報のためAPIから返さない。設定済みかどうかだけ表示し、
                変更したいときだけ新しい値を入力してもらう */}
            <input
              {...register("discord_webhook_url")}
              className={inputCls}
              placeholder={
                t?.discord_webhook_configured
                  ? "設定済み（変更する場合のみ入力）"
                  : "https://discord.com/api/webhooks/..."
              }
            />
            {t?.discord_webhook_configured && (
              <p className="mt-1 text-[11px] text-slate-500">
                空欄のまま保存すると現在の設定が維持されます
              </p>
            )}
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Check {...register("notify_entry")} label="エントリー通知" />
            <Check {...register("notify_checkin")} label="チェックイン通知" />
            <Check {...register("notify_match_start")} label="試合開始通知" />
            <Check {...register("notify_match_end")} label="試合終了通知" />
          </div>
        </Section>

        {/* スポンサー */}
        <Section title="スポンサー">
          <div className="space-y-2">
            {sponsorFields.fields.map((f, i) => (
              <div key={f.id} className="flex items-center gap-2">
                <input {...register(`sponsors.${i}.name`)} className={cn(inputCls, "flex-1")} placeholder="スポンサー名" />
                <input {...register(`sponsors.${i}.website_url`)} className={cn(inputCls, "flex-1")} placeholder="URL" />
                <button type="button" onClick={() => sponsorFields.remove(i)}
                  className="rounded-lg p-2 text-slate-500 hover:text-red-400 transition-colors">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            <button type="button"
              onClick={() => sponsorFields.append({ name: "", website_url: "", display_order: sponsorFields.fields.length })}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white transition-colors">
              <Plus className="h-3.5 w-3.5" /> スポンサーを追加
            </button>
          </div>
        </Section>

        {/* 問い合わせ */}
        <Section title="問い合わせ先">
          <Field label="メールアドレス">
            <input {...register("contact_email")} className={inputCls} placeholder="contact@example.com" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Discord">
              <input {...register("contact_discord")} className={inputCls} placeholder="username" />
            </Field>
            <Field label="Twitter">
              <input {...register("contact_twitter")} className={inputCls} placeholder="@なし" />
            </Field>
          </div>
        </Section>

        {/* 公開・分析設定 */}
        <Section title="公開・分析設定">
          <Field label="公開範囲">
            <select {...register("visibility")} className={selectCls}>
              {VISIBILITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Check {...register("is_public")} label="一般公開する（大会一覧に表示）" />
          <Check {...register("analytics_enabled")} label="統計分析を有効にする" />
          <Check {...register("player_stats_enabled")} label="プレイヤースタッツを記録する" />
          <Check {...register("ranking_enabled")} label="ランキングに反映する" />
        </Section>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || update.isPending}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            <Save className="h-4 w-4" />
            {isSubmitting || update.isPending ? "保存中..." : "変更を保存"}
          </button>
          <Link href={`/organizer/tournaments/${id}`}
            className="rounded-xl border border-white/10 px-6 py-3 text-sm text-slate-400 hover:text-white transition-colors">
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}

// ── UI ヘルパー ───────────────────────────────────────────────────────────────
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
      <h2 className="text-sm font-bold text-white">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-slate-400">{label}</label>
      {children}
    </div>
  );
}

/**
 * react-hook-form の register(...) をそのまま展開できるチェックボックス。
 * register は ref を含むため forwardRef で受け取る必要がある。
 */
const Check = forwardRef<HTMLInputElement, { label: string } & React.InputHTMLAttributes<HTMLInputElement>>(
  function Check({ label, ...props }, ref) {
    return (
      <label className="flex items-center gap-3 text-sm text-slate-300">
        <input type="checkbox" ref={ref} {...props} className="h-4 w-4 rounded accent-brand-500" />
        {label}
      </label>
    );
  },
);
