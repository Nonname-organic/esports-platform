"""VALORANTランクの序列定義とレンジ絞り込みヘルパー（LFT/LFP共通）。

Radiant 以外の各ティアは 1〜3 の division を持つ（"Diamond 2" 形式・全25段階）。
過去に division なしのティア名だけ（"Diamond"）で保存されたデータも存在する
ため、範囲判定はどちらの表記も受け付ける。
"""

# division を持つティア（昇順）
RANK_TIERS: list[str] = [
    "Iron",
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond",
    "Ascendant",
    "Immortal",
]

# 選択可能なランク（昇順・全25段階）
RANK_ORDER: list[str] = [
    f"{tier} {division}" for tier in RANK_TIERS for division in (1, 2, 3)
] + ["Radiant"]

_INDEX = {rank: i for i, rank in enumerate(RANK_ORDER)}


def _bound_index(rank: str | None, *, as_max: bool) -> int:
    """ランク表記を RANK_ORDER 上の位置に解決する。

    division なしのティア名は「そのティア全体」を意味するものとして、
    下限なら division 1、上限なら division 3 の位置に丸める。
    未知の表記は端として扱わない（min不明→最下位 / max不明→最上位）。
    """
    default = len(RANK_ORDER) - 1 if as_max else 0
    if not rank:
        return default
    if rank in _INDEX:
        return _INDEX[rank]
    if rank in RANK_TIERS:
        division = 3 if as_max else 1
        return _INDEX[f"{rank} {division}"]
    return default


def ranks_in_range(min_rank: str | None, max_rank: str | None) -> list[str]:
    """min〜max（両端含む）に該当するランク表記のリストを返す。

    division 付き25段階のうち範囲内のものに加え、範囲と重なるティアの
    ティア名のみ表記（旧形式データ）も含める。division 不明の旧データを
    検索から取りこぼさないための互換措置。
    min > max の逆指定は入れ替えて解釈する。
    """
    lo = _bound_index(min_rank, as_max=False)
    hi = _bound_index(max_rank, as_max=True)
    if lo > hi:
        lo, hi = hi, lo

    result = RANK_ORDER[lo : hi + 1]
    # 範囲に1つでも division がかかっているティアは、旧形式のティア名も対象にする
    legacy = [tier for tier in RANK_TIERS if any(r.startswith(f"{tier} ") for r in result)]
    return result + legacy
