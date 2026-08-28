import { ImageResponse } from "next/og";
import { serverFetch } from "@/lib/api-client";
import type { ApiResponse, TournamentDetail } from "@/types/tournament";

/**
 * 大会ページのOGP画像（X等でリンクを共有したときのカード）。
 *
 * 主催者は結局Xで告知するため、リンクカードの見栄えがそのまま集客力になる。
 * バナー画像が設定されていればそれを敷き、大会名・日程・枠数を重ねる。
 */

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "大会情報";

// 日本語グリフ入りフォントは数MBあるため、大会名等に実際に使う文字だけの
// サブセットを Google Fonts から実行時に取得する（結果はNextがルート単位で
// キャッシュする）。取得できない環境では画像なしにフォールバック。
async function loadFont(text: string): Promise<ArrayBuffer | null> {
  try {
    const unique = Array.from(new Set(text)).join("");
    const cssUrl =
      "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@700" +
      `&text=${encodeURIComponent(unique)}`;
    const css = await fetch(cssUrl).then((r) => r.text());
    const match = css.match(/src: url\((.+?)\) format\('(?:opentype|truetype)'\)/);
    if (!match) return null;
    return await fetch(match[1]).then((r) => r.arrayBuffer());
  } catch {
    return null;
  }
}

function formatDateRange(start: string | null, end: string | null | undefined): string {
  const fmt = (value: string) => {
    const d = new Date(value);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };
  if (!start) return "";
  const s = fmt(start);
  if (!end || fmt(end) === s) return s;
  return `${s} - ${fmt(end)}`;
}

const STATUS_LABEL: Record<string, string> = {
  registration_open: "エントリー受付中",
  registration_closed: "受付終了",
  ongoing: "開催中",
  completed: "終了",
};

export default async function OgImage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let t: TournamentDetail;
  try {
    const res = await serverFetch<ApiResponse<TournamentDetail>>(
      `/api/v1/tournaments/${id}`,
      undefined,
      { cache: "force-cache", next: { revalidate: 300 } },
    );
    t = res.data;
  } catch {
    return new Response("Not Found", { status: 404 });
  }

  const status = STATUS_LABEL[t.status] ?? "";
  const dates = formatDateRange(t.start_at, t.end_at);
  const teams = `${t.registered_teams}/${t.max_teams}`;

  const textForFont = `${t.name}${status}チーム日程AXELIA  VALORANT0123456789/ -${dates}${teams}`;
  const font = await loadFont(textForFont);
  if (!font) return new Response("Font unavailable", { status: 404 });

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 64,
          background: "linear-gradient(135deg, #0b1220 0%, #101c33 55%, #16233f 100%)",
          color: "#fff",
          fontFamily: "NotoSansJP",
        }}
      >
        {/* 上段: ゲーム + ステータス */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              display: "flex",
              padding: "8px 20px",
              borderRadius: 999,
              background: "#ff4655",
              fontSize: 26,
              fontWeight: 700,
            }}
          >
            VALORANT
          </div>
          {status && (
            <div
              style={{
                display: "flex",
                padding: "8px 20px",
                borderRadius: 999,
                border: "2px solid rgba(255,255,255,0.35)",
                fontSize: 26,
              }}
            >
              {status}
            </div>
          )}
        </div>

        {/* 中段: 大会名 */}
        <div
          style={{
            display: "flex",
            fontSize: t.name.length > 16 ? 64 : 84,
            fontWeight: 700,
            lineHeight: 1.15,
            textShadow: "0 4px 24px rgba(0,0,0,0.5)",
          }}
        >
          {t.name}
        </div>

        {/* 下段: 日程・枠数 + ブランド */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
          }}
        >
          <div style={{ display: "flex", gap: 40, fontSize: 30, color: "#b9c4d8" }}>
            {dates && (
              <div style={{ display: "flex", gap: 12 }}>
                <span style={{ color: "#7f8ca3" }}>日程</span>
                <span style={{ color: "#fff", fontWeight: 700 }}>{dates}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 12 }}>
              <span style={{ color: "#7f8ca3" }}>チーム</span>
              <span style={{ color: "#fff", fontWeight: 700 }}>{teams}</span>
            </div>
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 36,
              fontWeight: 700,
              letterSpacing: 6,
              color: "#5b8cff",
            }}
          >
            AXELIA
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [{ name: "NotoSansJP", data: font, weight: 700, style: "normal" }],
    },
  );
}
