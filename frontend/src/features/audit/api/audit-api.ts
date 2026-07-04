import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface AuditLogItem {
  id: string;
  action: string;
  actor_id: string | null;
  actor_name: string | null;
  actor_type: string;
  actor_ip: string | null;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

interface Params { action?: string; entity_type?: string; limit?: number; offset?: number }

function qs(params?: Params): string {
  const s = new URLSearchParams();
  if (params?.action) s.set("action", params.action);
  if (params?.entity_type) s.set("entity_type", params.entity_type);
  if (params?.limit) s.set("limit", String(params.limit));
  if (params?.offset) s.set("offset", String(params.offset));
  const q = s.toString();
  return q ? `?${q}` : "";
}

export const auditApi = {
  admin: (params?: Params): Promise<ApiResponse<AuditLogItem[]>> =>
    apiClient.get(`/api/v1/admin/audit${qs(params)}`),
  team: (teamId: string, params?: Params): Promise<ApiResponse<AuditLogItem[]>> =>
    apiClient.get(`/api/v1/teams/${teamId}/audit${qs(params)}`),
  tournament: (tournamentId: string, params?: Params): Promise<ApiResponse<AuditLogItem[]>> =>
    apiClient.get(`/api/v1/tournaments/${tournamentId}/audit${qs(params)}`),
};
