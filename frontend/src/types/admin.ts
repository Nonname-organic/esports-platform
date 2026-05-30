export interface AdminOverview {
  total_tournaments: number;
  total_teams: number;
  total_matches: number;
  total_players: number;
  mau: number;
  dau: number;
  mau_trend: number;
  dau_trend: number;
}

export interface AdminOperations {
  tournaments_this_month: number;
  pending_registrations: number;
  avg_participation_rate: number;
  completed_matches_today: number;
  ongoing_tournaments: number;
  cancelled_rate: number;
}

export interface MonthlyTrend {
  month: string;
  tournaments: number;
  matches: number;
  active_users: number;
  new_teams: number;
  participation_rate: number;
}

export interface GrowthMetric {
  label: string;
  current: number;
  previous: number;
  growth_rate: number;
  unit: string;
}

export type ActivityType =
  | "tournament_created"
  | "tournament_completed"
  | "tournament_cancelled"
  | "team_registered"
  | "match_completed"
  | "result_submitted"
  | "user_joined";

export interface Activity {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  user_name: string | null;
  team_name: string | null;
  tournament_name: string | null;
  entity_id: string | null;
  entity_type: string | null;
  created_at: string;
}

export type NotificationType = "warning" | "info" | "error" | "success";

export interface AdminNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  action_url: string | null;
  created_at: string;
}

export interface AdminDashboard {
  overview: AdminOverview;
  operations: AdminOperations;
  monthly_trends: MonthlyTrend[];
  growth_metrics: GrowthMetric[];
  recent_activities: Activity[];
  notifications: AdminNotification[];
}
