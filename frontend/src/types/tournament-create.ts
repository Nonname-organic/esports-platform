/**
 * 大会作成フォーム型定義
 * ゲームタイトルは将来追加可能な設計
 */

export type TournamentTier = "community" | "amateur" | "semi_pro" | "professional";
export type TournamentVisibility = "public" | "limited" | "private";
export type SeedingType = "auto" | "manual";
export type BOFormat = "BO1" | "BO3" | "BO5" | "BO7";
export type TournamentFormat = "single_elimination" | "double_elimination" | "swiss" | "round_robin" | "group_stage" | "league";

// ── ゲーム定義（将来拡張可能）──────────────────────────────────────────────────
export const SUPPORTED_GAMES = {
  VALORANT: {
    label: "VALORANT",
    color: "#ff4655",
    ranks: ["アイアン1", "アイアン2", "アイアン3", "ブロンズ1", "ブロンズ2", "ブロンズ3",
      "シルバー1", "シルバー2", "シルバー3", "ゴールド1", "ゴールド2", "ゴールド3",
      "プラチナ1", "プラチナ2", "プラチナ3", "ダイヤモンド1", "ダイヤモンド2", "ダイヤモンド3",
      "アセンダント1", "アセンダント2", "アセンダント3",
      "イモータル1", "イモータル2", "イモータル3", "ラディアント"],
    maps: ["Ascent", "Bind", "Haven", "Icebox", "Pearl", "Lotus", "Fracture", "Breeze", "Sunset", "Abyss"],
    servers: ["Tokyo", "Singapore", "Seoul", "Hong Kong", "Mumbai"],
    gameSettings: {
      server: "Tokyo",
      map_pool: [] as string[],
      ban_pick_format: "team_veto",
      overtime_rule: "sudden_death",
    },
  },
  APEX: {
    label: "Apex Legends",
    color: "#da292a",
    ranks: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド", "マスター", "プレデター"],
    maps: ["ワールズエッジ", "ブロークンムーン", "ストームポイント", "キングスキャニオン", "オリンパス"],
    servers: ["Tokyo", "Singapore"],
    gameSettings: {
      match_point: 50,
      rounds: 6,
      lobbies: 1,
    },
  },
  CS2: {
    label: "Counter-Strike 2",
    color: "#de9b35",
    ranks: ["シルバー1〜4", "シルバーエリート", "シルバーエリートマスター",
      "ゴールドノバ1〜4", "マスターガーディアン1〜2", "マスターガーディアンエリート",
      "ディスティングイッシュドマスターガーディアン", "レジェンダリーイーグル",
      "レジェンダリーイーグルマスター", "サプリームマスターファーストクラス", "グローバルエリート"],
    maps: ["Mirage", "Inferno", "Dust2", "Overpass", "Ancient", "Nuke", "Vertigo", "Anubis"],
    servers: ["Tokyo", "Singapore", "Hong Kong"],
    gameSettings: {
      server: "Tokyo",
      map_pool: [] as string[],
      knife_round: true,
      overtime_rule: "MR3",
    },
  },
  LOL: {
    label: "League of Legends",
    color: "#c89b3c",
    ranks: ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "エメラルド",
      "ダイヤモンド", "マスター", "グランドマスター", "チャレンジャー"],
    maps: ["サモナーズリフト"],
    servers: ["JP", "KR", "EUW"],
    gameSettings: {
      server: "JP",
      side_selection_rule: "coin_flip",
    },
  },
  OVERWATCH: {
    label: "Overwatch 2",
    color: "#0093c9",
    ranks: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド",
      "マスター", "グランドマスター", "チャンピオン"],
    maps: ["Kings Row", "Dorado", "Numbani", "Watchpoint: Gibraltar",
      "Circuit Royal", "Midtown", "Esperança"],
    servers: ["Asia"],
    gameSettings: {
      server: "Asia",
      mode: "best_of",
    },
  },
  ROCKET_LEAGUE: {
    label: "Rocket League",
    color: "#0053ce",
    ranks: ["ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤモンド",
      "チャンピオン", "グランドチャンピオン", "スーパーソニックレジェンド"],
    maps: ["DFH Stadium", "Mannfield", "Champions Field", "Urban Central"],
    servers: ["Japan"],
    gameSettings: {
      server: "Japan",
      mode: "soccar",
    },
  },
} as const;

export type SupportedGame = keyof typeof SUPPORTED_GAMES;

// ── フォーム型定義 ─────────────────────────────────────────────────────────────

export interface PrizeEntry {
  rank_position: number;
  amount: number;
  currency: "JPY" | "USD";
  description?: string;
}

export interface SponsorEntry {
  name: string;
  logo_url?: string;
  website_url?: string;
  display_order: number;
}

export interface TournamentCreateForm {
  // Section 1: 基本情報
  name: string;
  subtitle?: string;
  description?: string;
  thumbnail_url?: string;
  banner_url?: string;
  game: SupportedGame;
  season?: string;
  split?: string;
  tier: TournamentTier;

  // Section 2: 募集情報
  registration_start_at?: string;
  registration_end_at?: string;
  check_in_start_at?: string;
  check_in_end_at?: string;
  start_at?: string;
  end_at?: string;

  // Section 3: 参加条件
  max_teams: number;
  min_teams: number;
  age_restriction?: { min_age?: number; max_age?: number };
  region_restriction?: { allowed_regions?: string[]; blocked_regions?: string[] };
  rank_restriction?: { min_rank?: string; max_rank?: string; rank_type?: "current" | "peak" };
  require_team_membership: boolean;
  require_check_in: boolean;

  // Section 4: 大会形式
  format: TournamentFormat;
  bo_format: BOFormat;
  seeding_type: SeedingType;
  group_stage_teams?: number;
  group_count?: number;

  // Section 5: 競技設定 (game_settings as JSON per game)
  game_settings: Record<string, unknown>;

  // Section 6: 賞金
  prize_pool?: number;
  prize_currency: "JPY" | "USD";
  prizes: PrizeEntry[];

  // Section 7: 配信情報
  is_streamed: boolean;
  twitch_url?: string;
  youtube_url?: string;
  commentators: string[];
  casters: string[];

  // Section 8: Discord
  discord_invite_url?: string;
  discord_webhook_url?: string;
  notify_entry: boolean;
  notify_checkin: boolean;
  notify_match_start: boolean;
  notify_match_end: boolean;

  // Section 9: スポンサー
  sponsors: SponsorEntry[];

  // Section 10: 問い合わせ
  contact_email?: string;
  contact_discord?: string;
  contact_twitter?: string;

  // Section 11: 公開設定
  visibility: TournamentVisibility;
  is_public: boolean;

  // Section 12: 分析設定
  analytics_season?: string;
  analytics_split?: string;
  analytics_region?: string;
  analytics_tier?: string;
  analytics_enabled: boolean;
  player_stats_enabled: boolean;
  ranking_enabled: boolean;
}

export const DEFAULT_FORM_VALUES: TournamentCreateForm = {
  name: "",
  game: "VALORANT",
  tier: "community",
  max_teams: 16,
  min_teams: 2,
  require_team_membership: false,
  require_check_in: false,
  format: "single_elimination",
  bo_format: "BO3",
  seeding_type: "auto",
  game_settings: { ...SUPPORTED_GAMES.VALORANT.gameSettings },
  prize_currency: "JPY",
  prizes: [],
  is_streamed: false,
  commentators: [],
  casters: [],
  notify_entry: true,
  notify_checkin: true,
  notify_match_start: true,
  notify_match_end: true,
  sponsors: [],
  visibility: "public",
  is_public: true,
  analytics_enabled: true,
  player_stats_enabled: true,
  ranking_enabled: true,
};

// Step定義
export const FORM_STEPS = [
  { id: "basic", label: "基本情報", icon: "Trophy" },
  { id: "schedule", label: "募集日程", icon: "Calendar" },
  { id: "entry", label: "参加条件", icon: "Users" },
  { id: "format", label: "大会形式", icon: "Shield" },
  { id: "game", label: "競技設定", icon: "Gamepad2" },
  { id: "prize", label: "賞金", icon: "DollarSign" },
  { id: "stream", label: "配信情報", icon: "Radio" },
  { id: "discord", label: "Discord", icon: "MessageSquare" },
  { id: "sponsor", label: "スポンサー", icon: "Star" },
  { id: "contact", label: "問い合わせ", icon: "Mail" },
  { id: "visibility", label: "公開設定", icon: "Eye" },
  { id: "analytics", label: "分析設定", icon: "BarChart2" },
] as const;

export type FormStepId = typeof FORM_STEPS[number]["id"];
