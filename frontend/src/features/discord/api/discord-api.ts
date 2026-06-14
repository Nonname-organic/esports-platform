import { apiClient } from "@/lib/api-client";
import type { ApiResponse } from "@/types/tournament";

export interface DiscordLinkStatus {
  discord_user_id: string;
  discord_username: string | null;
  linked_at: string;
}

export const discordApi = {
  getLink: (): Promise<ApiResponse<DiscordLinkStatus | null>> =>
    apiClient.get("/api/v1/discord/link"),

  unlink: (): Promise<void> =>
    apiClient.delete("/api/v1/discord/link"),

  issueCode: (): Promise<ApiResponse<{ code: string; expires_in: number }>> =>
    apiClient.post("/api/v1/discord/link-code"),

  oauthUrl: (): Promise<ApiResponse<{ url: string }>> =>
    apiClient.get("/api/v1/discord/oauth/login"),

  oauthCallback: (
    code: string,
  ): Promise<ApiResponse<{ discord_user_id: string; discord_username: string | null }>> =>
    apiClient.post("/api/v1/discord/oauth/callback", { code }),
};
