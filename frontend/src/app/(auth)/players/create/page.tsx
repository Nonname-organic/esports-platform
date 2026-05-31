"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { User2, AlertCircle, Info, CheckCircle2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { GameType } from "@/types/tournament";

// ── ゲーム別ロール定義（APIから取得） ─────────────────────────────────────────
const GAMES: GameType[] = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

const GAME_AGENTS: Record<string, string[]> = {
  VALORANT: ["Jett", "Reyna", "Phoenix", "Raze", "Neon", "Yoru", "Iso",
    "Sage", "Cypher", "Killjoy", "Chamber", "Deadlock", "Vyse",
    "Sova", "Breach", "KAYO", "Fade", "Gekko", "Skye",
    "Omen", "Brimstone", "Viper", "Astra", "Harbor", "Clove"],
  LOL: [], CS2: [], APEX: [], OVERWATCH: [],
};

// ── バリデーションスキーマ ────────────────────────────────────────────────────
const schema = z.object({
  game: z.enum(["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"] as const),
  riot_id: z
    .string()
    .min(1, "Riot ID または IGNを入力してください")
    .max(111)
    .refine((v) => !v.includes("#") || v.split("#").length === 2, {
      message: "Riot IDの形式: Name#TAG（例: SEN Tenz#NA1）",
    }),
  discord_id: z.string().max(100).optional(),
  main_role: z.string().max(50).optional(),
  sub_roles: z.array(z.string()).default([]),
  agent_pool: z.array(z.string()).default([]),
  rank: z.string().max(50).optional(),
  region: z.string().max(20).optional(),
  bio: z.string().max(1000).optional(),
});

type FormValues = z.infer<typeof schema>;

// ── UIコンポーネント ──────────────────────────────────────────────────────────
function Field({ label, error, hint, children }: {
  label: string; error?: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-400">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 flex items-center gap-1 text-xs text-slate-600"><Info className="h-3 w-3" />{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

function TagInput({
  value, onChange, options, placeholder,
}: { value: string[]; onChange: (v: string[]) => void; options: string[]; placeholder?: string; }) {
  const [input, setInput] = useState("");
  const suggestions = options.filter((o) => o.toLowerCase().includes(input.toLowerCase()) && !value.includes(o));

  const add = (item: string) => {
    if (!value.includes(item)) onChange([...value, item]);
    setInput("");
  };

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {value.map((item) => (
          <span key={item} className="flex items-center gap-1 rounded-full bg-brand-500/10 px-2.5 py-1 text-xs font-medium text-brand-400">
            {item}
            <button type="button" onClick={() => onChange(value.filter((v) => v !== item))} className="text-brand-400/60 hover:text-brand-400">×</button>
          </span>
        ))}
      </div>
      {options.length > 0 ? (
        <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">
          {options.slice(0, 12).map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => value.includes(opt) ? onChange(value.filter((v) => v !== opt)) : add(opt)}
              className={cn(
                "rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
                value.includes(opt)
                  ? "border-brand-500/50 bg-brand-500/10 text-brand-400"
                  : "border-white/10 text-slate-500 hover:text-white",
              )}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), input.trim() && add(input.trim()))}
          placeholder={placeholder}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
        />
      )}
    </div>
  );
}

// ── メインページ ──────────────────────────────────────────────────────────────
export default function PlayerCreatePage() {
  const router = useRouter();
  const qc = useQueryClient();

  // 既存プレイヤープロフィールチェック
  const { data: myPlayer } = useQuery({
    queryKey: ["players", "me"],
    queryFn: () => apiClient.get<{ data: any | null }>("/api/v1/players/me"),
    select: (res) => res.data,
  });

  // ロール一覧取得
  const { data: gameRoles } = useQuery({
    queryKey: ["game-roles"],
    queryFn: () => apiClient.get<{ data: Record<string, string[]> }>("/api/v1/players/roles"),
    select: (res) => res.data,
  });

  const createPlayer = useMutation({
    mutationFn: (data: FormValues) => apiClient.post("/api/v1/players", data),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["players"] });
      router.push(`/players/${res.data.id}`);
    },
  });

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { game: "VALORANT", sub_roles: [], agent_pool: [] },
  });

  const selectedGame = watch("game");
  const roles = gameRoles?.[selectedGame] ?? [];
  const agents = GAME_AGENTS[selectedGame] ?? [];

  const onSubmit = handleSubmit(async (values) => {
    await createPlayer.mutateAsync(values);
  });

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full rounded-lg border bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-colors",
      hasError ? "border-red-500/50" : "border-white/10 focus:border-brand-500",
    );

  // 既にプロフィールある場合
  if (myPlayer) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-400" />
        <h1 className="text-xl font-black text-white">プロフィール登録済み</h1>
        <p className="mt-2 text-sm text-slate-400">既にプレイヤープロフィールが作成されています。</p>
        <div className="mt-6 flex justify-center gap-3">
          <button onClick={() => router.push(`/players/${myPlayer.id}`)} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 transition-colors">
            プロフィールを見る
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2">
          <User2 className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">プレイヤー登録</h1>
          <p className="text-sm text-slate-500">プロフィールを作成してチームに参加できるようになります</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {createPlayer.isError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {createPlayer.error instanceof Error ? createPlayer.error.message : "登録に失敗しました"}
          </div>
        )}

        {/* ゲーム選択 */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">ゲーム情報</h2>

          <Field label="ゲーム" error={errors.game?.message}>
            <div className="flex flex-wrap gap-2">
              {GAMES.map((g) => {
                const isSelected = selectedGame === g;
                return (
                  <label key={g} className={cn(
                    "cursor-pointer rounded-lg border px-4 py-2 text-sm font-semibold transition-colors",
                    isSelected ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white",
                  )}>
                    <input type="radio" {...register("game")} value={g} className="sr-only" />
                    {g}
                  </label>
                );
              })}
            </div>
          </Field>

          <Field
            label="Riot ID / ゲーム内名前"
            error={errors.riot_id?.message}
            hint="VALORANT: Name#TAG形式推奨（例: SEN Tenz#NA1）。将来のRiot API連携で自動検証されます"
          >
            <input
              {...register("riot_id")}
              className={inputClass(!!errors.riot_id)}
              placeholder={selectedGame === "VALORANT" ? "Name#TAG（例: SEN Tenz#NA1）" : "ゲーム内名前"}
            />
          </Field>

          <Field label="ランク・段位" error={errors.rank?.message}>
            <input {...register("rank")} className={inputClass()} placeholder="例: Radiant / チャレンジャー" />
          </Field>

          <Field label="リージョン" error={errors.region?.message}>
            <select {...register("region")} className={inputClass() + " bg-slate-800"}>
              <option value="">選択してください</option>
              {["JP", "AP", "NA", "EU", "KR", "BR", "LATAM"].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </Field>
        </div>

        {/* ロール設定 */}
        {roles.length > 0 && (
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
            <h2 className="text-sm font-bold text-white">ロール設定</h2>

            <Field label="メインロール" error={errors.main_role?.message}>
              <div className="flex flex-wrap gap-2">
                {roles.map((role) => {
                  const isSelected = watch("main_role") === role;
                  return (
                    <label key={role} className={cn(
                      "cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                      isSelected ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white",
                    )}>
                      <input type="radio" {...register("main_role")} value={role} className="sr-only" />
                      {role}
                    </label>
                  );
                })}
              </div>
            </Field>

            <Field label="サブロール（複数選択可）">
              <Controller
                name="sub_roles"
                control={control}
                render={({ field }) => (
                  <div className="flex flex-wrap gap-2">
                    {roles.map((role) => (
                      <label key={role} className={cn(
                        "cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                        field.value.includes(role) ? "border-purple-500/50 bg-purple-500/10 text-purple-400" : "border-white/10 text-slate-400 hover:text-white",
                      )}>
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={field.value.includes(role)}
                          onChange={(e) => {
                            if (e.target.checked) field.onChange([...field.value, role]);
                            else field.onChange(field.value.filter((v: string) => v !== role));
                          }}
                        />
                        {role}
                      </label>
                    ))}
                  </div>
                )}
              />
            </Field>
          </div>
        )}

        {/* エージェント */}
        {agents.length > 0 && (
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h2 className="mb-3 text-sm font-bold text-white">使用エージェント（複数選択可）</h2>
            <Controller
              name="agent_pool"
              control={control}
              render={({ field }) => (
                <TagInput value={field.value} onChange={field.onChange} options={agents} />
              )}
            />
          </div>
        )}

        {/* SNS・Discord */}
        <div className="rounded-xl border border-white/10 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-bold text-white">連携情報（任意）</h2>

          <Field label="Discord ID" hint="Discordのユーザー名（例: username#1234 またはusername）">
            <input {...register("discord_id")} className={inputClass()} placeholder="username または username#1234" />
          </Field>

          <Field label="自己紹介">
            <textarea {...register("bio")} rows={3} className={inputClass()} placeholder="チームへのアピールポイントなど..." />
          </Field>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || createPlayer.isPending}
            className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors"
          >
            {isSubmitting || createPlayer.isPending ? "登録中..." : "プレイヤー登録する"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-xl border border-white/10 px-5 py-3 text-sm text-slate-400 hover:text-white transition-colors"
          >
            キャンセル
          </button>
        </div>

        {/* Riot API連携の説明 */}
        <div className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-4">
          <div className="flex items-start gap-2 text-xs text-slate-400">
            <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-brand-400" />
            <div>
              <p className="font-semibold text-brand-400">Riot API連携について（準備中）</p>
              <p className="mt-0.5">今後のアップデートでRiot IDを自動検証し、ランク・使用エージェントのデータ自動取得機能を追加予定です。現在はName#TAGを手動入力してください。</p>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
