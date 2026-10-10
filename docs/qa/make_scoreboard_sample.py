"""スコアボード取り込みの動作確認に使うサンプル画像を作る。

実機のスクリーンショットではなく、取り込み処理が前提にしている構造を
再現したもの。合成画像なので「OCRが実際のスクリーンショットをどれだけ
正しく読めるか」の証明にはならない。確認できるのは
取り込み→選手紐付け→保存→表示までの経路が通るかどうか。

再現している構造（backend/app/services/scoreboard_ocr.py に対応）:
  - 上部にラウンドスコア（最初の行帯より 120px 以上うえ）
  - 列見出し: 個人成績順 / 平均バトルスコア / KDA / マネー /
              ファーストブラッド / 設置 / 解除
  - 選手行は明度で切り出すため、行を明るい帯・行間を暗い隙間にする
  - 味方は緑寄り、相手は赤寄りの行色（所属チームの判定に使われる）
  - 選手名セルは上段が選手名、下段がエージェント名（カタカナ）

使い方:
  python docs/qa/make_scoreboard_sample.py
  python docs/qa/make_scoreboard_sample.py --out /tmp/r1m1.png \n      --names "A,B,C,D,E,F,G,H,I,J" --score 5:13

--names に実在の試合の登録選手名を渡すと、取り込み後に選手へ
正しく紐付くところまで確認できる（先の5人が味方側＝緑の行）。
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "scoreboard_sample.png"

W = 1600
BG = (8, 10, 18)
ROW_ALLY = (40, 78, 60)    # 味方（緑寄り）
ROW_ENEMY = (92, 44, 52)   # 相手（赤寄り）
ICON = (18, 22, 34)
TEXT = (232, 238, 248)
DIM = (158, 172, 194)

SCORE_Y = 28
HEADER_Y = 172
BAND_TOP = 236
BAND_H = 64
BAND_GAP = 12
PITCH = BAND_H + BAND_GAP

DEFAULT_SCORE = (13, 9)

# 列見出しと、その中心X（左寄せの「個人成績順」だけ left）
COLS = [
    ("個人成績順", 96, "left"),
    ("平均バトルスコア", 620, "center"),
    ("KDA", 820, "center"),
    ("マネー", 1000, "center"),
    ("ファーストブラッド", 1200, "center"),
    ("設置", 1380, "center"),
    ("解除", 1510, "center"),
]

# (エージェント, 選手名, ACS, KDA, マネー, FB, 設置, 解除)
ROWS = [
    ("ジェット", "Shiroraven", 284, "21/12/5", 4100, 4, 1, 0),
    ("レイズ", "Naoquake", 262, "18/14/7", 3850, 3, 2, 1),
    ("セージ", "Kuroblade", 198, "11/13/12", 3200, 1, 0, 3),
    ("ソーヴァ", "Shirofrost", 187, "10/15/9", 3050, 1, 1, 0),
    ("オーメン", "Kurofox", 165, "9/16/11", 2900, 0, 2, 1),
    ("チェンバー", "Akatsuki", 301, "24/9/4", 4600, 6, 0, 2),
    ("ヴァイパー", "Hayate", 245, "17/11/8", 3900, 2, 3, 0),
    ("スカイ", "Mikazuki", 210, "13/12/14", 3400, 2, 1, 1),
    ("キルジョイ", "Tsubame", 176, "10/14/6", 3100, 1, 0, 2),
    ("フェイド", "Rindo", 158, "8/15/10", 2750, 0, 1, 0),
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise RuntimeError("日本語フォントが見つかりません")


def draw_text(d, x, y, text, font, fill, align="left") -> None:
    if align == "center":
        x -= d.textlength(text, font=font) / 2
    d.text((x, y), text, font=font, fill=fill)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT, help="出力先のPNG")
    parser.add_argument(
        "--names",
        help="選手名10件をカンマ区切りで。先の5人が緑（味方）側の行になる",
    )
    parser.add_argument(
        "--score", default="13:9", help="ラウンドスコア（例 5:13）"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows = list(ROWS)
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        if len(names) != len(rows):
            raise SystemExit(f"--names は{len(rows)}件必要です（{len(names)}件）")
        rows = [(r[0], name, *r[2:]) for r, name in zip(rows, names)]

    left, _, right = args.score.partition(":")
    score = (int(left), int(right))

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, BAND_TOP + len(rows) * PITCH + 24), BG)
    d = ImageDraw.Draw(img)

    f_score = load_font(58)
    f_result = load_font(30)
    f_head = load_font(22)
    f_name = load_font(23)
    f_agent = load_font(17)
    f_num = load_font(24)

    # ラウンドスコア。最初の行帯より十分うえに置く（取り込み側が
    # 「最初の行帯 - 120px」より上だけを見るため）
    draw_text(d, 660, SCORE_Y, str(score[0]), f_score, TEXT, "center")
    draw_text(d, 800, SCORE_Y + 14,
              "VICTORY" if score[0] >= score[1] else "DEFEAT",
              f_result, DIM, "center")
    draw_text(d, 940, SCORE_Y, str(score[1]), f_score, DIM, "center")

    for label, x, align in COLS:
        draw_text(d, x, HEADER_Y, label, f_head, DIM, align)

    for i, (agent, name, acs, kda, econ, fb, plt, dfs) in enumerate(rows):
        top = BAND_TOP + i * PITCH
        half = len(rows) // 2
        d.rectangle([0, top, W, top + BAND_H],
                    fill=ROW_ALLY if i < half else ROW_ENEMY)

        # エージェントのポートレート枠（実機にもある。名前セルの左端）
        d.rectangle([26, top + 6, 78, top + BAND_H - 6], fill=ICON)

        # 上段に選手名、下段にエージェント名。取り込み側は行の高さの
        # 52% で上下に割って別々に読むため、その境界をまたがないようにする
        draw_text(d, 96, top + 4, name, f_name, TEXT)
        draw_text(d, 96, top + 40, agent, f_agent, DIM)

        for value, (_, x, align) in zip(
            (acs, kda, str(econ), fb, plt, dfs), COLS[1:]
        ):
            draw_text(d, x, top + 18, str(value), f_num, TEXT, align)

    img.save(out)
    print(f"生成: {out}  {img.size}")


if __name__ == "__main__":
    main()
