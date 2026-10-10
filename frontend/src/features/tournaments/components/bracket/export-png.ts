/**
 * ブラケットを PNG として書き出す。
 *
 * 画面のDOMを画像化するのではなく、同じレイアウト座標からCanvasへ描き直す。
 * こうするとズーム倍率・スクロール位置・ボタン類に影響されず、配信の
 * オーバーレイにそのまま載せられる絵が得られる。背景は透過のままにする。
 */
import type { BracketMatch } from "@/types/tournament";

export interface ExportRound {
  roundNum: number;
  label: string;
  matches: { match: BracketMatch; x: number; y: number; centerY: number }[];
}

export interface ExportOptions {
  /** 書き出し倍率。2 にすると配信で拡大しても粗くならない */
  scale?: number;
  /** 透過をやめて単色で塗る場合に指定（例 "#0b1220"） */
  background?: string | null;
}

const CARD_W = 220;
const CARD_H = 116;
const HEADER_H = 34;
const ROW_H = 40;
const PAD = 24;

// 画面の配色に合わせる。透過背景でも視認できるよう、カードは不透明で塗る。
const C = {
  card: "#0f172a",
  cardBorder: "rgba(255,255,255,0.12)",
  header: "rgba(255,255,255,0.04)",
  label: "#94a3b8",
  text: "#e2e8f0",
  textDim: "#64748b",
  winner: "#ffffff",
  winnerBg: "rgba(37,99,235,0.18)",
  accent: "#2563eb",
  line: "rgba(255,255,255,0.18)",
  stream: "#ef4444",
};

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number,
                   w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawTeamRow(
  ctx: CanvasRenderingContext2D, x: number, y: number,
  team: { name: string | null; tag: string | null } | null,
  isWinner: boolean, score: string,
) {
  if (isWinner) {
    ctx.fillStyle = C.winnerBg;
    ctx.fillRect(x + 1, y, CARD_W - 2, ROW_H);
    ctx.fillStyle = C.accent;
    ctx.fillRect(x + 1, y, 3, ROW_H);
  }
  ctx.font = isWinner ? "bold 14px sans-serif" : "14px sans-serif";
  ctx.fillStyle = team ? (isWinner ? C.winner : C.text) : C.textDim;
  ctx.textBaseline = "middle";

  const name = team?.name ?? "未定";
  const maxW = CARD_W - 60;
  let label = name;
  while (ctx.measureText(label).width > maxW && label.length > 1) {
    label = label.slice(0, -1);
  }
  if (label !== name) label = label.slice(0, -1) + "…";
  ctx.fillText(label, x + 14, y + ROW_H / 2);

  if (score) {
    ctx.font = "bold 14px sans-serif";
    ctx.fillStyle = isWinner ? C.winner : C.textDim;
    ctx.textAlign = "right";
    ctx.fillText(score, x + CARD_W - 14, y + ROW_H / 2);
    ctx.textAlign = "left";
  }
}

function drawMatch(ctx: CanvasRenderingContext2D, m: BracketMatch, x: number, y: number) {
  ctx.fillStyle = C.card;
  roundRect(ctx, x, y, CARD_W, CARD_H, 10);
  ctx.fill();
  ctx.strokeStyle = m.stream_url ? C.stream : C.cardBorder;
  ctx.lineWidth = m.stream_url ? 2 : 1;
  roundRect(ctx, x, y, CARD_W, CARD_H, 10);
  ctx.stroke();

  // ヘッダー
  ctx.fillStyle = C.header;
  ctx.fillRect(x + 1, y + 1, CARD_W - 2, HEADER_H - 1);
  ctx.font = "11px sans-serif";
  ctx.fillStyle = C.label;
  ctx.textBaseline = "middle";
  ctx.fillText(`Match ${m.match_number}`, x + 12, y + HEADER_H / 2);

  if (m.stream_url) {
    // 配信対象であることを一目で分かるようにする
    ctx.fillStyle = C.stream;
    ctx.beginPath();
    ctx.arc(x + CARD_W - 54, y + HEADER_H / 2, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "bold 10px sans-serif";
    ctx.fillText("配信", x + CARD_W - 44, y + HEADER_H / 2);
  }

  ctx.strokeStyle = C.cardBorder;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x + 1, y + HEADER_H);
  ctx.lineTo(x + CARD_W - 1, y + HEADER_H);
  ctx.stroke();

  const w1 = !!m.winner_id && m.winner_id === m.team1?.id;
  const w2 = !!m.winner_id && m.winner_id === m.team2?.id;
  drawTeamRow(ctx, x, y + HEADER_H, m.team1, w1, "");
  ctx.beginPath();
  ctx.moveTo(x + 1, y + HEADER_H + ROW_H);
  ctx.lineTo(x + CARD_W - 1, y + HEADER_H + ROW_H);
  ctx.stroke();
  drawTeamRow(ctx, x, y + HEADER_H + ROW_H, m.team2, w2, "");
}

/** ラウンド間をつなぐ線。カードの右端から次ラウンドの左端へ。 */
function drawConnectors(ctx: CanvasRenderingContext2D, rounds: ExportRound[]) {
  ctx.strokeStyle = C.line;
  ctx.lineWidth = 1.5;
  for (let r = 0; r < rounds.length - 1; r++) {
    const cur = rounds[r];
    const next = rounds[r + 1];
    for (let i = 0; i < cur.matches.length; i++) {
      const from = cur.matches[i];
      const to = next.matches[Math.floor(i / 2)];
      if (!to) continue;
      const x1 = from.x + CARD_W;
      const y1 = from.centerY;
      const x2 = to.x;
      const y2 = to.centerY;
      const mid = x1 + (x2 - x1) / 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(mid, y1);
      ctx.lineTo(mid, y2);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  }
}

/** ブラケットを描いた PNG の Blob を返す。 */
export async function renderBracketPng(
  rounds: ExportRound[],
  totalWidth: number,
  totalHeight: number,
  options: ExportOptions = {},
): Promise<Blob> {
  const scale = options.scale ?? 2;
  const w = Math.max(totalWidth + PAD * 2, 320);
  const h = Math.max(totalHeight + PAD * 2, 240);

  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(w * scale);
  canvas.height = Math.ceil(h * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas を初期化できませんでした");

  ctx.scale(scale, scale);
  if (options.background) {
    ctx.fillStyle = options.background;
    ctx.fillRect(0, 0, w, h);
  }
  ctx.translate(PAD, PAD);

  drawConnectors(ctx, rounds);

  for (const round of rounds) {
    // ラウンド名
    if (round.matches.length) {
      ctx.font = "bold 12px sans-serif";
      ctx.fillStyle = C.label;
      ctx.textBaseline = "alphabetic";
      ctx.fillText(round.label, round.matches[0].x, 14);
    }
    for (const pm of round.matches) {
      drawMatch(ctx, pm.match, pm.x, pm.y);
    }
  }

  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("PNGの生成に失敗しました"))),
      "image/png",
    );
  });
}

/** 生成した PNG をダウンロードさせる。 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // 直後に revoke するとダウンロードが始まらないブラウザがあるため少し待つ
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
