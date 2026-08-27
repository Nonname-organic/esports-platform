"""
VALORANTスコアボードのスクリーンショットから選手成績を抽出する。

実際のスコアボード（日本語クライアント）の構造に合わせた設計:

  個人成績順 | 平均バトルスコア | KDA | マネー | ファーストブラッド | 設置 | 解除

- 「個人成績順」のとおり並び順はACS順であり、チーム順ではない。したがって
  行の位置からチームを決めてはならない。行の背景色（赤/緑）をヒントとして返し、
  最終的なチーム判定は登録選手との名前照合側で行う。
- KDAは "23 / 15 / 8" のように1セルにまとまっている。
- エージェントは選手名の下にカタカナで表示される。アイコン画像の照合より
  文字として読むほうが確実なため、そちらを採用する。

処理は「行の切り出しは画像処理、値の読み取りはセル単位のOCR」に分けている。
画像全体を一度にOCRするより、桁数の少ない数値セルを個別に読むほうが精度が高い。
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
from app.services import agent_catalog

logger = logging.getLogger(__name__)

# OCR前に画像をこの幅へ正規化する
_TARGET_WIDTH = 1920
# 行として扱う最小の高さ（正規化後ピクセル）
_MIN_BAND_HEIGHT = 20
_MAX_PLAYERS = 10
# ヘッダーの断片をひとつの見出しにまとめる横方向の許容間隔（幅1920基準）。
# 見出し内の文字間は数px、列と列の間は100px以上あるため中間の値を採る
_HEADER_CLUSTER_GAP = 40.0

# ヘッダーの表記ゆれ。日本語クライアントを主、英語クライアントを従として持つ
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("個人成績順", "PLAYER", "プレイヤー"),
    "acs": ("平均バトルスコア", "バトルスコア", "ACS", "平均"),
    "kda": ("KDA",),
    "econ": ("マネー", "ECON", "所持金"),
    "first_bloods": ("ファーストブラッド", "FB", "ファースト"),
    "plants": ("設置", "PLT", "PLANTS"),
    "defuses": ("解除", "DEF", "DEFUSES"),
    # 英語クライアントでKDAが分かれている場合
    "kills": ("K", "KILLS"),
    "deaths": ("D", "DEATHS"),
    "assists": ("A", "ASSISTS"),
}

_DIGITS_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"
_NAME_CONFIG = "--psm 6"

_CLEAN_LABEL_RE = re.compile(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠]")


@dataclass
class ScoreboardRow:
    """スコアボード1行の解析結果（DBの選手とはまだ紐付いていない）。"""

    name: str
    agent: Optional[str] = None
    acs: Optional[int] = None
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    first_bloods: Optional[int] = None
    plants: Optional[int] = None
    defuses: Optional[int] = None
    # 行の背景色から推定したチーム識別子（"red" / "green"）。順位順に並ぶため
    # 行位置ではチームを判定できず、これが唯一の画像側の手がかりになる
    team_hint: Optional[str] = None
    # 読み取れなかったセル名（画面で強調するために返す）
    missing: list[str] = field(default_factory=list)


@dataclass
class ScoreboardParseResult:
    rows: list[ScoreboardRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_score: Optional[tuple[int, int]] = None


def is_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 - 実行環境依存のため広く捕捉する
        return False


def has_japanese() -> bool:
    """日本語の学習データが入っているか（エージェント名の読み取りに必要）。"""
    try:
        return "jpn" in pytesseract.get_languages(config="")
    except Exception:  # noqa: BLE001
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


def _normalize_size(img: np.ndarray) -> np.ndarray:
    w = img.shape[1]
    if w == _TARGET_WIDTH:
        return img
    scale = _TARGET_WIDTH / w
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)


def _enhance_for_ocr(crop: np.ndarray) -> np.ndarray:
    """
    セル画像をOCRしやすい形に整える。

    スコアボードは色付き背景に明るい文字。グレースケール化して反転し
    （Tesseractは白背景・黒文字を前提）、拡大してから大津の二値化をかける。
    """
    if crop.size == 0:
        return crop
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bitwise_not(gray)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.copyMakeBorder(binary, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)


def _ocr_text(crop: np.ndarray, config: str, lang: str = "eng") -> str:
    if crop.size == 0:
        return ""
    try:
        return pytesseract.image_to_string(
            _enhance_for_ocr(crop), config=config, lang=lang
        ).strip()
    except pytesseract.TesseractError:
        return ""


def _ocr_int(crop: np.ndarray) -> Optional[int]:
    text = _ocr_text(crop, _DIGITS_CONFIG)
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def _row_brightness_profile(img: np.ndarray) -> tuple[np.ndarray, int]:
    """
    中央帯における各yの明度中央値と、行/背景を分ける閾値を返す。

    選手行は赤や青緑の塗りつぶし、ページ背景は暗い紺。色相で判別しようとすると
    青緑（B成分が高い）で破綻するため、明度で分ける。文字は面積が小さく中央値
    には出ないので、行内の文字色に影響されない。
    """
    w = img.shape[1]
    # 表は中央付近にある。左右の装飾（サイドバー等）を避けて中央帯だけ見る
    strip = img[:, int(w * 0.25) : int(w * 0.75)]
    value = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)[:, :, 2]
    profile = np.median(value, axis=1).astype(np.uint8)

    # profile を1列の画像とみなして大津の二値化で閾値を自動決定する
    threshold, _ = cv2.threshold(
        profile.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return profile, int(threshold)


def _detect_row_bands(img: np.ndarray) -> list[tuple[int, int]]:
    """明度プロファイルから選手行の縦位置を検出する。"""
    profile, threshold = _row_brightness_profile(img)
    mask = profile > threshold

    bands: list[tuple[int, int]] = []
    start = None
    for y, is_row in enumerate(mask):
        if is_row and start is None:
            start = y
        elif not is_row and start is not None:
            if y - start >= _MIN_BAND_HEIGHT:
                bands.append((start, y))
            start = None
    if start is not None and len(mask) - start >= _MIN_BAND_HEIGHT:
        bands.append((start, len(mask)))

    if not bands:
        return []

    # ヘッダーの色帯や見出しなど、選手行と明らかに高さの違う帯を除く
    heights = sorted(b - a for a, b in bands)
    median_h = heights[len(heights) // 2]
    return [
        (a, b) for a, b in bands if median_h * 0.6 <= (b - a) <= median_h * 1.8
    ]


def _detect_table_x_range(
    img: np.ndarray, bands: list[tuple[int, int]]
) -> tuple[int, int]:
    """
    塗りつぶし行の横方向の広がりから表の左右端を求める。

    「個人成績順」列の見出しはOCRで拾えないことがあるため、選手名セルの左端は
    ヘッダーではなくこの表の左端から決める。
    """
    _profile, threshold = _row_brightness_profile(img)
    lefts, rights = [], []
    for top, bottom in bands:
        middle = img[(top + bottom) // 2, :, :]
        value = cv2.cvtColor(middle.reshape(1, -1, 3), cv2.COLOR_BGR2HSV)[0, :, 2]
        filled = np.flatnonzero(value > threshold)
        if filled.size:
            lefts.append(int(filled[0]))
            rights.append(int(filled[-1]))

    if not lefts:
        return 0, img.shape[1]
    return int(np.median(lefts)), int(np.median(rights))


def _team_hint(img: np.ndarray, band: tuple[int, int]) -> Optional[str]:
    """行の背景色から所属チームのヒント（赤/緑）を返す。"""
    top, bottom = band
    w = img.shape[1]
    # 中央帯全体の中央値を見る。文字は面積が小さいため中央値なら背景色が残る
    strip = img[top:bottom, int(w * 0.25) : int(w * 0.75)].astype(np.int16)
    if strip.size == 0:
        return None
    blue, green, red = (
        float(np.median(strip[:, :, 0])),
        float(np.median(strip[:, :, 1])),
        float(np.median(strip[:, :, 2])),
    )
    if red - green > 8:
        return "red"
    if green - red > 8:
        return "green"
    return None


def _clean_label(text: str) -> str:
    return _CLEAN_LABEL_RE.sub("", text)


def _find_header_columns(
    img: np.ndarray, first_band_top: int, lang: str
) -> dict[str, float]:
    """
    選手行より上の領域をOCRしてヘッダーの列名とx中心を得る。
    """
    header_region = img[max(0, first_band_top - 120) : first_band_top, :]
    if header_region.size == 0:
        return {}

    try:
        data = pytesseract.image_to_data(
            _enhance_for_ocr(header_region),
            config="--psm 6",
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractError:
        return {}

    # _enhance_for_ocr で3倍拡大+12pxの余白を付けているため元座標へ戻す
    scale, pad = 3.0, 12

    # 日本語の見出しは「ファ」「ー」「ス」「トブ」…のように細切れに認識される。
    # 単語単位で照合しても列名にならないため、まず横方向の近さでまとめ直す
    words: list[tuple[float, float, str]] = []  # (left, right, text)
    for i, raw_text in enumerate(data["text"]):
        text = (raw_text or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 30:
            continue
        left = (int(data["left"][i]) - pad) / scale
        right = (int(data["left"][i]) + int(data["width"][i]) - pad) / scale
        words.append((left, right, text))

    columns: dict[str, float] = {}
    for label, cx in _cluster_header_words(words):
        for key, aliases in _HEADER_ALIASES.items():
            if key in columns:
                continue
            if _label_matches(label, aliases):
                columns[key] = cx
    return columns


def _cluster_header_words(
    words: list[tuple[float, float, str]]
) -> list[tuple[str, float]]:
    """
    横方向に近接する単語をひとつの見出しへまとめる。

    同じ見出しを構成する断片は隣接しているが、列と列の間には大きな空きがある。
    その差でグループを切り、連結した文字列と中心x座標を返す。
    """
    if not words:
        return []

    words = sorted(words, key=lambda w: w[0])
    clusters: list[list[tuple[float, float, str]]] = [[words[0]]]
    for word in words[1:]:
        previous_right = clusters[-1][-1][1]
        if word[0] - previous_right <= _HEADER_CLUSTER_GAP:
            clusters[-1].append(word)
        else:
            clusters.append([word])

    result: list[tuple[str, float]] = []
    for cluster in clusters:
        label = _clean_label("".join(w[2] for w in cluster))
        if not label:
            continue
        center = (cluster[0][0] + cluster[-1][1]) / 2
        result.append((label, center))
    return result


def _label_matches(label: str, aliases: tuple[str, ...]) -> bool:
    """
    OCRしたヘッダー文字列が列名に該当するか判定する。

    「ファーストブラッド」のような長い見出しはOCRが途中で分割したり一部を
    落としたりするため、完全一致ではなく部分一致で拾う。ただし "K"/"D"/"A" の
    ような1文字の別名は誤検出を招くので完全一致のみとする。
    """
    for alias in aliases:
        cleaned = _clean_label(alias)
        if not cleaned:
            continue
        if len(cleaned) <= 2:
            if label == cleaned:
                return True
            continue
        # 3文字以上なら、どちらかがどちらかを含めば同じ列とみなす。
        # 断片的な短い読み取り（"ス" など）で誤検出しないよう下限を設ける
        if cleaned in label:
            return True
        if len(label) >= 3 and label in cleaned:
            return True
    return False


def _column_bounds(
    columns: dict[str, float], key: str, width: int
) -> Optional[tuple[int, int]]:
    """列の中心座標から、隣接列との中間をセル境界として求める。"""
    if key not in columns:
        return None
    centers = sorted(columns.values())
    center = columns[key]
    index = centers.index(center)
    left = (centers[index - 1] + center) / 2 if index > 0 else max(0.0, center - 120)
    right = (
        (centers[index + 1] + center) / 2
        if index + 1 < len(centers)
        else min(float(width), center + 120)
    )
    return int(left), int(right)


def _parse_kda(text: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """"23 / 15 / 8" 形式を (K, D, A) に分解する。妥当でなければ None を返す。"""
    parts = [p for p in re.split(r"[^0-9]+", text) if p]
    # 区切りの "/" が数字に誤読されると桁が繋がる（"15/8" → "1578"）。
    # K/D/A が3桁になることは無いため、桁数で妥当性を検証する
    if len(parts) != 3 or any(len(p) > 2 for p in parts):
        return None, None, None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _ink_runs(crop: np.ndarray) -> list[tuple[int, int]]:
    """セル内の文字（インク）が存在する横方向の区間を返す。"""
    if crop.size == 0:
        return []
    gray = cv2.bitwise_not(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    has_ink = (binary == 0).any(axis=0)

    runs: list[tuple[int, int]] = []
    start = None
    for x, ink in enumerate(has_ink):
        if ink and start is None:
            start = x
        elif not ink and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, len(has_ink)))
    return runs


def _segment_kda(crop: np.ndarray) -> Optional[list[tuple[int, int]]]:
    """
    "23 / 15 / 8" を3つの数値の区間に分割する。

    "/" は数字として誤読されやすく（"15/8" が "1578" になる）、セル全体を
    まとめてOCRすると値が壊れる。そこで文字の切れ目から
    「数値・区切り・数値・区切り・数値」の5グループになる間隔のしきい値を
    探し、数値部分だけを切り出して個別にOCRする。
    """
    runs = _ink_runs(crop)
    if len(runs) < 5:
        return None

    gaps = sorted({runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)})
    for threshold in gaps:
        if threshold <= 0:
            continue
        groups: list[list[tuple[int, int]]] = [[runs[0]]]
        for previous, current in zip(runs, runs[1:]):
            if current[0] - previous[1] >= threshold:
                groups.append([current])
            else:
                groups[-1].append(current)

        # 区切り記号は必ず1文字、数値は1〜2桁
        if (
            len(groups) == 5
            and len(groups[1]) == 1
            and len(groups[3]) == 1
            and all(1 <= len(groups[i]) <= 2 for i in (0, 2, 4))
        ):
            return [groups[i] for i in (0, 2, 4)]
    return None


def _ocr_number(crop: np.ndarray, runs: list[tuple[int, int]]) -> Optional[int]:
    """
    数字の区間を読む。

    まとめて読んだ桁数が文字の塊の数と合わない場合（細い "1" が落ちるなど）は、
    塊ごとに1文字ずつ読み直して結合する。塊の数は画素から数えているので、
    OCRの結果より信頼できる。
    """
    left = max(0, runs[0][0] - 3)
    right = min(crop.shape[1], runs[-1][1] + 3)
    text = re.sub(r"\D", "", _ocr_text(crop[:, left:right], _DIGITS_CONFIG))
    if len(text) == len(runs):
        return int(text)

    digits = ""
    for x1, x2 in runs:
        single = _ocr_text(
            crop[:, max(0, x1 - 3) : min(crop.shape[1], x2 + 3)],
            "--psm 10 -c tessedit_char_whitelist=0123456789",
        )
        single = re.sub(r"\D", "", single)
        if len(single) != 1:
            break
        digits += single
    if len(digits) == len(runs):
        return int(digits)

    return int(text) if text else None


def _ocr_kda(crop: np.ndarray) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """KDAセルから (K, D, A) を読む。"""
    groups = _segment_kda(crop)
    if groups is not None:
        values = [_ocr_number(crop, runs) for runs in groups]
        if all(v is not None and v < 100 for v in values):
            return values[0], values[1], values[2]

    # 分割できなかった場合はセル全体を複数の設定で読んで妥当なものを採る
    for psm in ("--psm 7", "--psm 6", "--psm 13"):
        config = f"{psm} -c tessedit_char_whitelist=0123456789/"
        kills, deaths, assists = _parse_kda(_ocr_text(crop, config))
        if kills is not None:
            return kills, deaths, assists
    return None, None, None


def _split_name_cell(crop: np.ndarray, lang: str) -> tuple[str, Optional[str]]:
    """
    選手名セルから「選手名」と「エージェント名」を取り出す。

    1行目が選手名、2行目がエージェント（カタカナ）。行の高さで上下に分けてから
    それぞれOCRする。1度に読むと2行が連結されて分離できないため。
    """
    h = crop.shape[0]
    if h < 12:
        return _ocr_text(crop, _NAME_CONFIG, lang), None

    # 上下の分割位置。エージェント名は選手名よりやや小さく下段に置かれる
    split = int(h * 0.52)
    name = _ocr_text(crop[:split, :], "--psm 7", lang)
    agent_text = _ocr_text(crop[split:, :], "--psm 7", lang)

    if not name:
        name = _ocr_text(crop, _NAME_CONFIG, lang)
    return name.strip(), (agent_text.strip() or None)


def _detect_score(img: np.ndarray, first_band_top: int) -> Optional[tuple[int, int]]:
    """
    上部の「12 DEFEAT 13」からラウンドスコアを読む。

    大きな装飾文字は誤読しやすいため、あくまで初期値の提案として扱う。
    """
    region = img[: max(1, first_band_top - 120), :]
    if region.size == 0:
        return None

    try:
        data = pytesseract.image_to_data(
            _enhance_for_ocr(region),
            config="--psm 6 -c tessedit_char_whitelist=0123456789",
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractError:
        return None

    candidates: list[tuple[float, int]] = []
    for i, raw_text in enumerate(data["text"]):
        digits = re.sub(r"\D", "", (raw_text or "").strip())
        if not digits:
            continue
        value = int(digits)
        if not 0 <= value <= 30:
            continue
        candidates.append((float(data["left"][i]), value))

    if len(candidates) < 2:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1], candidates[-1][1]


def parse_scoreboard(raw: bytes) -> tuple[ScoreboardParseResult, np.ndarray]:
    """スコアボード画像を解析する。戻り値は (解析結果, 正規化後のBGR画像)。"""
    if not is_available():
        raise ValidationError(
            "OCRエンジン(tesseract)が利用できません。サーバー管理者に連絡してください"
        )

    img = _normalize_size(_decode(raw))
    result = ScoreboardParseResult()

    japanese = has_japanese()
    lang = "jpn+eng" if japanese else "eng"
    if not japanese:
        result.warnings.append(
            "日本語の学習データが未導入のため、エージェント名を読み取れません"
        )

    bands = _detect_row_bands(img)
    if not bands:
        raise ValidationError(
            "スコアボードの行を検出できませんでした。"
            "スコアボードタブ全体が写った、加工していないスクリーンショットをアップロードしてください"
        )

    columns = _find_header_columns(img, bands[0][0], lang)
    if "acs" not in columns or ("kda" not in columns and "kills" not in columns):
        raise ValidationError(
            "ヘッダー（平均バトルスコア / KDA）を検出できませんでした。"
            "スコアボードの見出し行を含めて撮影してください"
        )

    width = img.shape[1]
    acs_bounds = _column_bounds(columns, "acs", width)

    # 選手名セルは「表の左端 〜 ACS列の左端」。見出し「個人成績順」はOCRで
    # 拾えないことがあるため、ヘッダーではなく塗りつぶし行の広がりから決める
    table_left, _table_right = _detect_table_x_range(img, bands)
    name_bounds: Optional[tuple[int, int]] = None
    if acs_bounds is not None:
        # アイコン部分を避けて少し内側から切り出す
        left = table_left + int((acs_bounds[0] - table_left) * 0.04)
        if acs_bounds[0] - left > 40:
            name_bounds = (left, acs_bounds[0])
    if name_bounds is None:
        name_bounds = _column_bounds(columns, "name", width)

    kda_bounds = _column_bounds(columns, "kda", width)
    fb_bounds = _column_bounds(columns, "first_bloods", width)
    plants_bounds = _column_bounds(columns, "plants", width)
    defuses_bounds = _column_bounds(columns, "defuses", width)

    if fb_bounds is None:
        result.warnings.append(
            "ファーストブラッド列を検出できませんでした。手動で入力してください"
        )

    def cell(band: tuple[int, int], bounds: Optional[tuple[int, int]]):
        """行帯と列境界からセル画像を切り出す。"""
        if bounds is None:
            return np.empty((0, 0, 3), np.uint8)
        # 行間は数pxしかないため、上下に広げると隣接行を巻き込んで
        # 二値化の閾値が狂う。塗りつぶし範囲そのままで切り出す
        return img[band[0] : band[1], bounds[0] : bounds[1]]

    for band in bands[:_MAX_PLAYERS]:
        name, agent_text = _split_name_cell(cell(band, name_bounds), lang)
        if not name:
            continue

        row = ScoreboardRow(name=name, team_hint=_team_hint(img, band))
        row.agent = agent_catalog.resolve(agent_text)

        row.acs = _ocr_int(cell(band, acs_bounds))
        if kda_bounds is not None:
            row.kills, row.deaths, row.assists = _ocr_kda(cell(band, kda_bounds))
        else:
            row.kills = _ocr_int(cell(band, _column_bounds(columns, "kills", width)))
            row.deaths = _ocr_int(cell(band, _column_bounds(columns, "deaths", width)))
            row.assists = _ocr_int(cell(band, _column_bounds(columns, "assists", width)))

        row.first_bloods = _ocr_int(cell(band, fb_bounds))
        row.plants = _ocr_int(cell(band, plants_bounds))
        row.defuses = _ocr_int(cell(band, defuses_bounds))

        for label, value in (
            ("ACS", row.acs), ("K", row.kills), ("D", row.deaths),
            ("A", row.assists), ("エージェント", row.agent),
        ):
            if value is None:
                row.missing.append(label)

        result.rows.append(row)

    if not result.rows:
        raise ValidationError("スコアボードから選手行を読み取れませんでした")

    if len(result.rows) < _MAX_PLAYERS:
        result.warnings.append(
            f"検出できた行が{len(result.rows)}行でした（通常は{_MAX_PLAYERS}行）。"
            "不足分は手動で追加してください"
        )

    result.detected_score = _detect_score(img, bands[0][0])
    if result.detected_score is not None:
        result.warnings.append(
            f"ラウンドスコアを {result.detected_score[0]} - {result.detected_score[1]} と読み取りました。"
            "大きな装飾文字は誤読しやすいため必ず確認してください"
        )

    return result, img
