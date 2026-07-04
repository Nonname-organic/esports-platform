/** 締切までの残り時間ラベル（"あと3日" / "あと5時間" / "まもなく締切"）。過ぎていれば null。 */
export function deadlineLabel(iso: string | null): { text: string; urgent: boolean } | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms) || ms <= 0) return null;
  const days = Math.floor(ms / 86400000);
  if (days >= 1) return { text: `あと${days}日`, urgent: days <= 1 };
  const hours = Math.floor(ms / 3600000);
  if (hours >= 1) return { text: `あと${hours}時間`, urgent: true };
  const mins = Math.max(1, Math.floor(ms / 60000));
  return { text: `あと${mins}分`, urgent: true };
}
