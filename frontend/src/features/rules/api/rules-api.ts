import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

/** ルールSection（固定id: general/prohibited/judgment/bo/stream/discord/penalty）。 */
export interface RulesSection {
  id: string;
  title: string;
  body_md: string;
  order: number;
}

export interface RulesDoc {
  sections: RulesSection[];
}

export interface RulesTemplate {
  id: string;
  label: string;
  game: string | null;
}

export const rulesApi = {
  get: (tournamentId: string): Promise<ApiResponse<RulesDoc>> =>
    apiClient.get(`/api/v1/tournaments/${tournamentId}/rules`),
  update: (tournamentId: string, doc: RulesDoc): Promise<ApiResponse<RulesDoc>> =>
    apiClient.put(`/api/v1/tournaments/${tournamentId}/rules`, doc),
  templates: (): Promise<ApiResponse<RulesTemplate[]>> =>
    apiClient.get(`/api/v1/tournaments/rules/templates`),
  applyTemplate: (tournamentId: string, templateId: string): Promise<ApiResponse<RulesDoc>> =>
    apiClient.post(`/api/v1/tournaments/${tournamentId}/rules/apply-template`, { template_id: templateId }),
};
