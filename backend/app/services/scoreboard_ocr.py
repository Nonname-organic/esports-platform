"""
VALORANTスコアボードのスクリーンショットから選手成績を抽出する。

固定ピクセル座標に依存すると解像度・アスペクト比・UIスケールの違いで簡単に
破綻するため、OCRの単語単位バウンディングボックスから「行」と「ヘッダー列」を
検出して自己校正する方式を採っている。

抽出対象はスコアボードに実際に表示されている項目のみ:
    プレイヤー名 / ACS / K / D / A / FB
HS% はスコアボードに存在しないため対象外。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
import pytesseract

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# OCR前に画像をこの幅まで拡大する（小さいスクショでの文字潰れ対策）
_OCR_TARGET_WIDTH = 1920
# これ以下の信頼度の単語は雑音として捨てる
_MIN_WORD_CONF = 30.0
# 1行として扱う選手行の最低数値トークン数（ACS/K/D/A）
_MIN_STAT_TOKENS = 4
# 想定する最大選手数（5人 × 2チーム）
_MAX_PLAYERS = 10

# ヘッダーの表記ゆれ。クライアント言語やOCRの誤読を吸収する
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "acs": ("ACS", "AGS", "AC5", "ACSS"),
    "kills": ("K", "KILLS", "キル"),
    "deaths": ("D", "DEATHS", "デス"),
    "assists": ("A", "ASSISTS", "アシスト"),
    "first_bloods": ("FB", "F8", "FIRSTBLOOD", "FIRSTBLOODS"),
    "econ": ("ECON", "EGON", "ECONOMY", "エコノミー"),
    "plants": ("PLT", "PLANT", "PLANTS", "設置"),
    "defuses": ("DEF", "DEFUSE", "DEFUSES", "解除"),
    "diff": ("+/-", "+/−", "+-"),
}

_NUM_RE = re.compile(r"^[+\-−]?\d{1,4}$")
_LABEL_CLEAN_RE = re.compile(r"[^0-9A-Z+/\-ぁ-んァ-ヶ一-龠]")


@dataclass
class OcrWord:
    """OCRが検出した単語1つとその位置。"""

    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float

    @property
    def cx(self) -> float:
        return self.left + self.width / 2

    @property
    def cy(self) -> float:
        return self.top + self.height / 2


@dataclass
class ScoreboardRow:
    """スコアボード1行ぶんの解析結果（DBのプレイヤーとはまだ紐付いていない）。"""

    name: str
    acs: Optional[int] = None
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    first_bloods: Optional[int] = None
    agent: Optional[str] = None
    confidence: float = 0.0
    # エージェントアイコンを切り出すための行の位置（元画像スケール）
    box: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass
class ScoreboardParseResult:
    rows: list[ScoreboardRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # スコアボード上部から読めた場合のラウンドスコア
    detected_score: Optional[tuple[int, int]] = None


def is_available() -> bool:
    """tesseractバイナリが使えるか。未導入環境でも起動は落とさない。"""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 - 実行環境依存のため広く捕捉する
        return False


def _decode(raw: bytes) -> np.ndarray:
    if not raw:
        raise ValidationError("画像が空です")
    if len(raw) > 20 * 1024 * 1024:
        raise ValidationError("画像サイズが大きすぎます（20MBまで）")

    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValidationError(
            "画像を読み込めませんでした。PNG または JPEG のスクリーンショットをアップロードしてください"
        )
    h, w = img.shape[:2]
    if w < 640 or h < 360:
        raise ValidationError(
            f"画像の解像度が低すぎます（{w}x{h}）。スコアボード全体が写った縮小前のスクリーンショットが必要です"
        )
    return img


def _prepare_for_ocr(img: np.ndarray) -> tuple[np.ndarray, float]:
    """OCR向けの前処理。戻り値は (処理後グレースケール, 元画像に対する拡大率)。"""
    w = img.shape[1]
    scale = max(1.0, _OCR_TARGET_WIDTH / w)
    if scale > 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # スコアボードは暗い背景に明るい文字。Tesseractは白背景・黒文字を前提とするため反転する
    gray = cv2.bitwise_not(gray)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    return gray, scale


def _ocr_words(gray: np.ndarray) -> list[OcrWord]:
    data = pytesseract.image_to_data(
        gray, config="--psm 6", output_type=pytesseract.Output.DICT
    )
    words: list[OcrWord] = []
    for i, text in enumerate(data["text"]):
        t = (text or "").strip()
        if not t:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < _MIN_WORD_CONF:
            continue
        words.append(
            OcrWord(
                text=t,
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
                conf=conf,
            )
        )
    return words


def _group_rows(words: list[OcrWord]) -> tuple[list[list[OcrWord]], float]:
    """単語をy座標でクラスタリングして行にまとめる。戻り値は (行リスト, 単語高さの中央値)。"""
    if not words:
        return [], 0.0

    heights = sorted(w.height for w in words)
    median_h = float(heights[len(heights) // 2])
    tolerance = max(6.0, median_h * 0.6)

    rows: list[tuple[list[OcrWord], float]] = []
    for w in sorted(words, key=lambda x: x.cy):
        if rows and abs(w.cy - rows[-1][1]) <= tolerance:
            group = rows[-1][0]
            group.append(w)
            rows[-1] = (group, sum(x.cy for x in group) / len(group))
        else:
            rows.append(([w], w.cy))

    return [sorted(g, key=lambda x: x.left) for g, _ in rows], median_h


def _clean_label(text: str) -> str:
    return _LABEL_CLEAN_RE.sub("", text.upper())


def _find_header(rows: list[list[OcrWord]]) -> tuple[int, dict[str, float]]:
    """ヘッダー行を探し、列名 -> x中心 の対応を返す。見つからなければ (-1, {})。"""
    best_index, best_columns = -1, {}
    for index, row in enumerate(rows):
        columns: dict[str, float] = {}
        for word in row:
            label = _clean_label(word.text)
            if not label:
                continue
            for key, aliases in _HEADER_ALIASES.items():
                if label in aliases and key not in columns:
                    columns[key] = word.cx
        if len(columns) > len(best_columns):
            best_index, best_columns = index, columns

    # ACS だけ、K だけ、のような偶然の一致を弾く
    if len(best_columns) < 3:
        return -1, {}
    return best_index, best_columns


def _to_int(text: str) -> Optional[int]:
    try:
        return int(text.replace("−", "-").lstrip("+"))
    except ValueError:
        return None


def _parse_player_row(
    row: list[OcrWord], columns: dict[str, float], tolerance: float
) -> Optional[ScoreboardRow]:
    """1行から名前と各スタッツを取り出す。選手行でなければ None。"""
    acs_x = columns.get("acs")

    # 名前トークンとスタッツトークンの境界。ACS列が分かっていればそれを基準にする
    if acs_x is not None:
        boundary = acs_x - tolerance
        stat_words = [w for w in row if w.cx >= boundary and _NUM_RE.match(w.text)]
        name_words = [w for w in row if w.cx < boundary]
    else:
        # ヘッダーが読めなかった場合は「末尾に連続する数値」をスタッツとみなす
        stat_words = []
        for w in reversed(row):
            if _NUM_RE.match(w.text):
                stat_words.append(w)
            else:
                break
        stat_words.reverse()
        name_words = row[: len(row) - len(stat_words)]

    if len(stat_words) < _MIN_STAT_TOKENS:
        return None

    name = " ".join(w.text for w in name_words).strip()
    if not name:
        return None

    # ACS / K / D / A は必ずこの順で先頭に並ぶ
    values = [_to_int(w.text) for w in stat_words[:4]]
    acs, kills, deaths, assists = (values + [None] * 4)[:4]

    # FB はヘッダーが読めたときだけ、x距離が最も近いトークンを採用する
    first_bloods = None
    fb_x = columns.get("first_bloods")
    if fb_x is not None:
        candidates = [w for w in stat_words if abs(w.cx - fb_x) <= tolerance * 1.5]
        if candidates:
            nearest = min(candidates, key=lambda w: abs(w.cx - fb_x))
            first_bloods = _to_int(nearest.text)

    all_words = name_words + stat_words
    confidence = sum(w.conf for w in all_words) / len(all_words) / 100.0

    top = min(w.top for w in all_words)
    bottom = max(w.top + w.height for w in all_words)
    left = min(w.left for w in all_words)
    right = max(w.left + w.width for w in all_words)

    return ScoreboardRow(
        name=name,
        acs=acs,
        kills=kills,
        deaths=deaths,
        assists=assists,
        first_bloods=first_bloods,
        confidence=round(confidence, 3),
        box=(left, top, right, bottom),
    )


def _detect_score(
    rows: list[list[OcrWord]], median_h: float
) -> Optional[tuple[int, int]]:
    """スコアボード上部の大きな数字2つをラウンドスコアとして拾う（best effort）。"""
    if median_h <= 0:
        return None
    upper = rows[: max(1, len(rows) // 3)]
    for row in upper:
        big = [
            w
            for w in row
            if w.height >= median_h * 1.6 and _NUM_RE.match(w.text)
        ]
        values = [v for v in (_to_int(w.text) for w in big) if v is not None]
        values = [v for v in values if 0 <= v <= 30]
        if len(values) == 2:
            return values[0], values[1]
    return None


def _rescale_box(
    box: tuple[int, int, int, int], scale: float
) -> tuple[int, int, int, int]:
    if scale == 1.0:
        return box
    return tuple(int(v / scale) for v in box)  # type: ignore[return-value]


def parse_scoreboard(raw: bytes) -> tuple[ScoreboardParseResult, np.ndarray]:
    """
    スコアボード画像を解析する。

    戻り値は (解析結果, 元解像度のBGR画像)。画像はエージェントアイコンの
    照合で再利用するため呼び出し側に返している。
    """
    if not is_available():
        raise ValidationError(
            "OCRエンジン(tesseract)が利用できません。サーバー管理者に連絡してください"
        )

    original = _decode(raw)
    gray, scale = _prepare_for_ocr(original)

    words = _ocr_words(gray)
    if not words:
        raise ValidationError(
            "画像から文字を検出できませんでした。スコアボードが鮮明に写っているか確認してください"
        )

    rows, median_h = _group_rows(words)
    header_index, columns = _find_header(rows)
    tolerance = max(12.0, median_h * 1.2)

    result = ScoreboardParseResult()
    if header_index < 0:
        result.warnings.append(
            "ヘッダー行(ACS/K/D/A)を検出できませんでした。数値の並び順から推定しているため、内容を必ず確認してください"
        )
    elif "first_bloods" not in columns:
        result.warnings.append("FB列を検出できませんでした。FBは手動で入力してください")

    body = rows[header_index + 1 :] if header_index >= 0 else rows
    for row in body:
        parsed = _parse_player_row(row, columns, tolerance)
        if parsed is None:
            continue
        parsed.box = _rescale_box(parsed.box, scale)
        result.rows.append(parsed)
        if len(result.rows) >= _MAX_PLAYERS:
            break

    if not result.rows:
        raise ValidationError(
            "スコアボードの行を検出できませんでした。ACS・K・D・A の列を含む範囲が写っているか確認してください"
        )
    if len(result.rows) < _MAX_PLAYERS:
        result.warnings.append(
            f"検出できた行が{len(result.rows)}行でした（通常は{_MAX_PLAYERS}行）。不足分は手動で入力してください"
        )

    result.detected_score = _detect_score(rows, median_h)
    if result.detected_score is not None:
        # 大きな装飾文字は誤読しやすい（13→15 など）。必ず目視確認させる
        result.warnings.append(
            f"ラウンドスコアを {result.detected_score[0]} - {result.detected_score[1]} と読み取りました。"
            "誤読しやすい箇所のため必ず確認してください"
        )
    return result, original
