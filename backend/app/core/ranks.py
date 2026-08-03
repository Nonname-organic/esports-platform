"""VALORANTランクの序列定義とレンジ絞り込みヘルパー（LFT/LFP共通）。"""

RANK_ORDER: list[str] = [
    "Iron",
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond",
    "Ascendant",
    "Immortal",
    "Radiant",
]


def ranks_in_range(min_rank: str | None, max_rank: str | None) -> list[str]:
    """min〜max（両端含む）に該当するランク名のリストを返す。

    未知のランク名は端として扱わない（min不明→最下位から / max不明→最上位まで）。
    min > max の逆指定は入れ替えて解釈する。
    """
    lo = RANK_ORDER.index(min_rank) if min_rank in RANK_ORDER else 0
    hi = RANK_ORDER.index(max_rank) if max_rank in RANK_ORDER else len(RANK_ORDER) - 1
    if lo > hi:
        lo, hi = hi, lo
    return RANK_ORDER[lo : hi + 1]
