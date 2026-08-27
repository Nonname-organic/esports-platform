"""
スコアボード上のエージェントアイコンを画像照合で判定する。

エージェント名はスコアボードにテキストとして存在せずアイコンでしか表示されない
ため、文字OCRでは取得できない。ここではエージェントのアイコン画像を一度だけ
取得してディスクにキャッシュし、行の左端を切り出してテンプレートマッチングする。

アイコンを取得できない環境（オフライン等）ではエージェントは None のまま返り、
運営が画面上で手動選択できるようにフォールバックする。判定できないことは
エラーではなく「未確定」として扱う。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import httpx
import numpy as np

logger = logging.getLogger(__name__)

# valorant-api.com はRiot公式アセットを配信する無料の公開API（APIキー不要）
_AGENT_API_URL = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
_CACHE_DIR = Path("/app/uploads/agent_icons")
# 正規化相関がこの値を下回る場合は判定不能として None にする
_MATCH_THRESHOLD = 0.55
# テンプレートを正規化する一辺のピクセル数
_TEMPLATE_SIZE = 64

# プロセス内キャッシュ: エージェント名 -> グレースケールテンプレート
_templates: dict[str, np.ndarray] | None = None


def _icon_path(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    return _CACHE_DIR / f"{safe}.png"


def _download_icons() -> None:
    """エージェント一覧とアイコンを取得してキャッシュする。失敗しても例外は投げない。"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(_AGENT_API_URL)
            response.raise_for_status()
            agents = response.json().get("data", [])

            for agent in agents:
                name = agent.get("displayName")
                icon_url = agent.get("displayIcon")
                if not name or not icon_url:
                    continue
                path = _icon_path(name)
                if path.exists():
                    continue
                try:
                    icon = client.get(icon_url)
                    icon.raise_for_status()
                    path.write_bytes(icon.content)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("エージェントアイコンの取得に失敗: %s (%s)", name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("エージェント一覧の取得に失敗したため画像照合を無効化します: %s", exc)


def _normalize(image: np.ndarray) -> np.ndarray:
    """アイコンを固定サイズのグレースケールに揃える。"""
    if image.ndim == 3:
        # 透過PNGは黒背景に合成する（スコアボード側も暗背景のため相関が安定する）
        if image.shape[2] == 4:
            alpha = image[:, :, 3:4].astype(np.float32) / 255.0
            image = (image[:, :, :3].astype(np.float32) * alpha).astype(np.uint8)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(
        image, (_TEMPLATE_SIZE, _TEMPLATE_SIZE), interpolation=cv2.INTER_AREA
    )
    return cv2.equalizeHist(resized)


def _load_templates() -> dict[str, np.ndarray]:
    global _templates
    if _templates is not None:
        return _templates

    if not _CACHE_DIR.exists() or not any(_CACHE_DIR.glob("*.png")):
        _download_icons()

    templates: dict[str, np.ndarray] = {}
    if _CACHE_DIR.exists():
        for path in sorted(_CACHE_DIR.glob("*.png")):
            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if image is None:
                continue
            templates[path.stem] = _normalize(image)

    if not templates:
        logger.warning("エージェントアイコンのキャッシュが空のため画像照合をスキップします")
    _templates = templates
    return templates


def is_available() -> bool:
    return bool(_load_templates())


def identify(crop: np.ndarray) -> Optional[str]:
    """切り出したアイコン領域から最も近いエージェント名を返す。判定不能なら None。"""
    templates = _load_templates()
    if not templates or crop.size == 0:
        return None

    try:
        target = _normalize(crop)
    except cv2.error:
        return None

    best_name, best_score = None, -1.0
    for name, template in templates.items():
        score = float(cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)[0][0])
        if score > best_score:
            best_name, best_score = name, score

    if best_score < _MATCH_THRESHOLD:
        return None
    return best_name


def crop_agent_icon(
    image: np.ndarray, box: tuple[int, int, int, int]
) -> Optional[np.ndarray]:
    """
    選手行のバウンディングボックスから左側のエージェントアイコン領域を切り出す。

    アイコンは名前の左に、行の高さとほぼ同じ正方形で置かれている。ランクバッジが
    間に入るレイアウトもあるため、行高の2倍ぶんを候補域として広めに取る。
    """
    left, top, _right, bottom = box
    height = bottom - top
    if height <= 0:
        return None

    # 行の上下に少し余白を足してアイコン全体を含める
    pad = int(height * 0.25)
    y1 = max(0, top - pad)
    y2 = min(image.shape[0], bottom + pad)
    x2 = max(0, left)
    x1 = max(0, x2 - int(height * 2.2))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None

    return image[y1:y2, x1:x2]


def identify_in_row(
    image: np.ndarray, box: tuple[int, int, int, int]
) -> Optional[str]:
    """行のアイコン候補域を走査して最も一致するエージェントを返す。"""
    region = crop_agent_icon(image, box)
    if region is None:
        return None

    height = region.shape[0]
    if height < 8:
        return None

    # 候補域内をアイコン1個ぶんの窓でスライドさせ、最良スコアを採用する
    best_name, best_score = None, -1.0
    step = max(4, height // 4)
    for x in range(0, max(1, region.shape[1] - height + 1), step):
        window = region[:, x : x + height]
        if window.shape[1] < 8:
            continue
        name = identify(window)
        if name is None:
            continue
        # identify は閾値未満を None にするため、ここに来た時点で候補として妥当
        best_name, best_score = name, 1.0
        break

    return best_name if best_score > 0 else None
