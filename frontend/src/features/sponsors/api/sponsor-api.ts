import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface Sponsor {
  id: string;
  team_id: string;
  name: string;
  logo_url: string | null;
  url: string | null;
  sponsor_type: string | null;
  display_order: number;
  contract_start: string | null;
  contract_end: string | null;
}

export interface SponsorInput {
  name: string;
  logo_url?: string;
  url?: string;
  sponsor_type?: string;
  display_order?: number;
  contract_start?: string;
  contract_end?: string;
}

export const sponsorApi = {
  list: (teamId: string): Promise<ApiResponse<Sponsor[]>> =>
    apiClient.get(`/api/v1/teams/${teamId}/sponsors`),
  create: (teamId: string, data: SponsorInput): Promise<ApiResponse<Sponsor>> =>
    apiClient.post(`/api/v1/teams/${teamId}/sponsors`, data),
  update: (teamId: string, sponsorId: string, data: Partial<SponsorInput>): Promise<ApiResponse<Sponsor>> =>
    apiClient.patch(`/api/v1/teams/${teamId}/sponsors/${sponsorId}`, data),
  remove: (teamId: string, sponsorId: string): Promise<void> =>
    apiClient.delete(`/api/v1/teams/${teamId}/sponsors/${sponsorId}`),
};
