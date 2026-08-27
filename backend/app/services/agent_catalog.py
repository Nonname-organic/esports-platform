"""
VALORANTエージェント名の対応表。

日本語クライアントのスコアボードでは、エージェントは選手名の下に
カタカナ（「フェニックス」「ソーヴァ」等）で表示される。アイコン画像の
照合より文字として読むほうが確実なため、カタカナ表記から正式名称
（英語表記）へ変換する対応表をここで持つ。

対応表は valorant-api.com（無料・APIキー不要）から日英を取得して
キャッシュする。新エージェント追加に自動追従させるためだが、取得できない
環境でも動くよう内蔵表をフォールバックとして持つ。
"""
from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_API_URL = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
_CACHE_DIR = Path("/app/uploads/agent_catalog")
_CACHE_FILE = _CACHE_DIR / "agents.json"
# あいまい一致の下限。カタカナの1文字違い程度は許容する
_FUZZY_THRESHOLD = 0.72

# API取得に失敗した場合のフォールバック。日本語表記 -> 正式名称
_BUILTIN_JA_TO_EN: dict[str, str] = {
    "ブリムストーン": "Brimstone",
    "フェニックス": "Phoenix",
    "セージ": "Sage",
    "ソーヴァ": "Sova",
    "ヴァイパー": "Viper",
    "サイファー": "Cypher",
    "レイナ": "Reyna",
    "キルジョイ": "Killjoy",
    "ブリーチ": "Breach",
    "オーメン": "Omen",
    "ジェット": "Jett",
    "レイズ": "Raze",
    "スカイ": "Skye",
    "ヨル": "Yoru",
    "アストラ": "Astra",
    "ケイオー": "KAY/O",
    "チェンバー": "Chamber",
    "ネオン": "Neon",
    "フェイド": "Fade",
    "ハーバー": "Harbor",
    "ゲッコー": "Gekko",
    "デッドロック": "Deadlock",
    "アイソ": "Iso",
    "クローヴ": "Clove",
    "ヴァイス": "Vyse",
    "テホ": "Tejo",
    "ウェイレイ": "Waylay",
    "ヴェト": "Veto",
}

# プロセス内キャッシュ: 正規化表記 -> 正式名称
_lookup: dict[str, str] | None = None


def _normalize(value: str) -> str:
    """比較用の正規化。記号・空白を除き、英字は小文字化する。"""
    cleaned = re.sub(r"[\s・･/／\-—_.,|]", "", value)
    return cleaned.lower()


def _fetch_from_api() -> dict[str, str]:
    """日英のエージェント名を取得する。失敗時は空dict。"""
    mapping: dict[str, str] = {}
    try:
        with httpx.Client(timeout=15.0) as client:
            english = client.get(_API_URL)
            english.raise_for_status()
            japanese = client.get(f"{_API_URL}&language=ja-JP")
            japanese.raise_for_status()

            # uuid をキーに日英を突き合わせる
            en_by_uuid = {
                a["uuid"]: a["displayName"]
                for a in english.json().get("data", [])
                if a.get("uuid") and a.get("displayName")
            }
            for agent in japanese.json().get("data", []):
                uuid_ = agent.get("uuid")
                ja_name = agent.get("displayName")
                en_name = en_by_uuid.get(uuid_)
                if ja_name and en_name:
                    mapping[ja_name] = en_name
    except Exception as exc:  # noqa: BLE001 - ネットワーク環境依存のため広く捕捉
        logger.warning("エージェント名の取得に失敗したため内蔵表を使用します: %s", exc)
    return mapping


def _load_catalog() -> dict[str, str]:
    """日本語表記 -> 正式名称 の対応表を返す（キャッシュ優先）。"""
    if _CACHE_FILE.exists():
        try:
            cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if cached:
                return cached
        except (OSError, json.JSONDecodeError):
            logger.warning("エージェント名キャッシュが壊れているため取得し直します")

    fetched = _fetch_from_api()
    if fetched:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(
                json.dumps(fetched, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("エージェント名キャッシュの保存に失敗: %s", exc)
        return fetched

    return dict(_BUILTIN_JA_TO_EN)


def _build_lookup() -> dict[str, str]:
    global _lookup
    if _lookup is not None:
        return _lookup

    catalog = _load_catalog()
    # 内蔵表も必ず併合しておく（APIに無い表記ゆれの保険）
    merged = {**_BUILTIN_JA_TO_EN, **catalog}

    lookup: dict[str, str] = {}
    for ja_name, en_name in merged.items():
        lookup[_normalize(ja_name)] = en_name
        # 英語表記でそのまま書かれている場合（KAY/O 等）にも対応する
        lookup[_normalize(en_name)] = en_name

    _lookup = lookup
    return lookup


def all_agents() -> list[str]:
    """正式名称の一覧（重複なし）。"""
    return sorted(set(_build_lookup().values()))


def resolve(text: Optional[str]) -> Optional[str]:
    """
    スコアボードから読み取った表記を正式名称に変換する。

    OCRのカタカナは濁点や長音で誤りが出やすいため、完全一致で引けない場合は
    あいまい一致にフォールバックする。判定できなければ None を返し、
    画面側で手動選択させる。
    """
    if not text:
        return None

    lookup = _build_lookup()
    key = _normalize(text)
    if not key:
        return None

    exact = lookup.get(key)
    if exact:
        return exact

    best_name, best_score = None, 0.0
    for candidate, en_name in lookup.items():
        score = SequenceMatcher(None, key, candidate).ratio()
        if score > best_score:
            best_name, best_score = en_name, score

    return best_name if best_score >= _FUZZY_THRESHOLD else None
