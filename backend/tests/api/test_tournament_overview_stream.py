"""overview API の配信URL解決（500 回帰防止）。

`GET /api/v1/tournaments/{id}/overview` が全大会で 500 を返していた。
原因は rules JSONB の配信設定が辞書なのに文字列として扱っていたこと。
作成フォームは配信を使わない大会でも
`{"is_streamed": false, "twitch_url": "", "youtube_url": ""}` を保存する
ため、空判定をすり抜けて dict.lower() に到達していた。

ここでは DB を使わない。_stream_url_from_rules / _stream_platform は純粋
関数で、_overview はリポジトリ呼び出しだけ差し替えれば検証できる。
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.enums import MatchStatus, TournamentStatus
from app.services.tournament_immersion import (
    TournamentImmersionService,
    _stream_platform,
    _stream_url_from_rules,
)

# 本番DBに実際に入っていた形。配信を設定していない大会はこれになる。
PRODUCTION_SHAPE = {"twitch_url": "", "is_streamed": False, "youtube_url": ""}


# ── _stream_url_from_rules ───────────────────────────────────────────────────
class TestStreamUrlFromRules:
    def test_dict_takes_twitch_url(self):
        rules = {"stream": {"is_streamed": True,
                            "twitch_url": "https://twitch.tv/axelia",
                            "youtube_url": ""}}
        assert _stream_url_from_rules(rules) == "https://twitch.tv/axelia"

    def test_dict_falls_back_to_youtube(self):
        rules = {"stream": {"is_streamed": True, "twitch_url": "",
                            "youtube_url": "https://youtube.com/live/abc"}}
        assert _stream_url_from_rules(rules) == "https://youtube.com/live/abc"

    def test_twitch_wins_when_both_present(self):
        # 明文化された仕様は無く、入力欄・送信ペイロード・型定義・
        # _stream_platform の判定順がいずれも twitch 先であることに合わせている。
        rules = {"stream": {"is_streamed": True,
                            "twitch_url": "https://twitch.tv/axelia",
                            "youtube_url": "https://youtube.com/live/abc"}}
        assert _stream_url_from_rules(rules) == "https://twitch.tv/axelia"

    def test_string_form_still_works(self):
        assert _stream_url_from_rules(
            {"stream_url": "https://twitch.tv/legacy"}
        ) == "https://twitch.tv/legacy"
        assert _stream_url_from_rules(
            {"stream": "https://youtube.com/live/legacy"}
        ) == "https://youtube.com/live/legacy"

    def test_stream_url_key_wins_over_stream_dict(self):
        rules = {"stream_url": "https://twitch.tv/direct",
                 "stream": {"is_streamed": True,
                            "twitch_url": "https://twitch.tv/nested"}}
        assert _stream_url_from_rules(rules) == "https://twitch.tv/direct"

    def test_is_streamed_false_means_no_stream(self):
        rules = {"stream": {"is_streamed": False,
                            "twitch_url": "https://twitch.tv/axelia"}}
        assert _stream_url_from_rules(rules) is None

    def test_missing_is_streamed_falls_back_to_url_presence(self):
        rules = {"stream": {"twitch_url": "https://twitch.tv/axelia"}}
        assert _stream_url_from_rules(rules) == "https://twitch.tv/axelia"

    def test_production_shape_is_none_and_does_not_raise(self):
        assert _stream_url_from_rules({"stream": PRODUCTION_SHAPE}) is None

    @pytest.mark.parametrize("rules", [
        None,
        {},
        {"stream": None},
        {"stream": ""},
        {"stream": {}},
        {"stream": {"is_streamed": True}},
        {"stream": {"is_streamed": True, "twitch_url": "", "youtube_url": ""}},
        {"stream": {"is_streamed": True, "twitch_url": "   "}},
        {"stream_url": ""},
        {"stream_url": None},
    ])
    def test_unset_or_empty_returns_none(self, rules):
        assert _stream_url_from_rules(rules) is None

    @pytest.mark.parametrize("rules", [
        "plain string",
        123,
        [],
        ["https://twitch.tv/x"],
        {"stream": 123},
        {"stream": []},
        {"stream": True},
        {"stream": {"twitch_url": 123, "youtube_url": None}},
        {"stream": {"twitch_url": ["https://twitch.tv/x"]}},
        {"stream_url": {"nested": "dict"}},
    ])
    def test_unexpected_types_do_not_raise(self, rules):
        assert _stream_url_from_rules(rules) is None

    def test_surrounding_whitespace_is_trimmed(self):
        rules = {"stream": {"twitch_url": "  https://twitch.tv/axelia  "}}
        assert _stream_url_from_rules(rules) == "https://twitch.tv/axelia"


# ── _stream_platform ─────────────────────────────────────────────────────────
class TestStreamPlatform:
    @pytest.mark.parametrize("url,expected", [
        ("https://twitch.tv/axelia", "twitch"),
        ("https://www.TWITCH.tv/axelia", "twitch"),
        ("https://youtube.com/live/abc", "youtube"),
        ("https://youtu.be/abc", "youtube"),
        ("https://kick.com/axelia", "kick"),
        ("https://example.com/stream", "other"),
    ])
    def test_detects_platform(self, url, expected):
        assert _stream_platform(url) == expected

    @pytest.mark.parametrize("value", [None, 123, {}, [], {"twitch_url": "x"}, True])
    def test_non_string_does_not_raise(self, value):
        # 解決側で文字列まで落としているが、ここでも守る（二重の防御）
        assert _stream_platform(value) == "other"


# ── _overview（リポジトリのみ差し替え。DBは使わない） ──────────────────────
class _FakeCache:
    """RedisCache の get/set だけを持つ最小の代用品。"""

    def __init__(self):
        self.store: dict = {}
        self.set_calls = 0

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, ttl=None):
        self.store[key] = value
        self.set_calls += 1


def _tournament(rules, status=TournamentStatus.ONGOING):
    return SimpleNamespace(
        id=uuid.uuid4(), name="AXELIA CUP", game="VALORANT",
        format="single_elimination", status=status,
        banner_url=None, prize_pool=None, prize_currency="JPY",
        start_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        end_at=None, registration_end_at=None, max_teams=16,
        rules=rules,
    )


def _ongoing_match(stream_url=None):
    return SimpleNamespace(
        status=MatchStatus.ONGOING, stream_url=stream_url, id=uuid.uuid4(),
        round_number=1, match_number=1, format="BO1",
        team1=None, team2=None, games=[], scheduled_at=None,
    )


def _service(tournament, matches=()):
    svc = TournamentImmersionService(None, _FakeCache())  # type: ignore[arg-type]

    async def get_by_id(_):
        return tournament

    async def get_registered_teams_count(_):
        return 16

    async def get_tournament_matches_full(_):
        return list(matches)

    svc._repo = SimpleNamespace(
        get_by_id=get_by_id,
        get_registered_teams_count=get_registered_teams_count,
    )
    svc._matches = SimpleNamespace(
        get_tournament_matches_full=get_tournament_matches_full,
    )
    return svc


class TestOverview:
    @pytest.mark.asyncio
    async def test_production_shape_does_not_500(self):
        svc = _service(_tournament({"stream": PRODUCTION_SHAPE}))
        data = await svc._overview(uuid.uuid4())
        assert data["stream"] is None

    @pytest.mark.asyncio
    async def test_returns_stream_when_configured(self):
        rules = {"stream": {"is_streamed": True,
                            "twitch_url": "https://twitch.tv/axelia"}}
        data = await _service(_tournament(rules))._overview(uuid.uuid4())
        assert data["stream"] == {
            "url": "https://twitch.tv/axelia",
            "platform": "twitch",
            "is_live": False,
        }

    @pytest.mark.asyncio
    async def test_is_live_when_a_match_is_ongoing(self):
        rules = {"stream": {"is_streamed": True,
                            "twitch_url": "https://twitch.tv/axelia"}}
        data = await _service(
            _tournament(rules), [_ongoing_match()]
        )._overview(uuid.uuid4())
        assert data["stream"]["is_live"] is True

    @pytest.mark.asyncio
    async def test_falls_back_to_match_stream_url(self):
        svc = _service(
            _tournament({"stream": PRODUCTION_SHAPE}),
            [_ongoing_match("https://youtube.com/live/match")],
        )
        data = await svc._overview(uuid.uuid4())
        assert data["stream"]["url"] == "https://youtube.com/live/match"
        assert data["stream"]["platform"] == "youtube"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("rules", [
        None, {}, "plain string", 123, {"stream": 123}, {"stream": []},
        {"stream": {"twitch_url": 123}}, {"stream_url": {"nested": "x"}},
    ])
    async def test_unexpected_types_do_not_break_overview(self, rules):
        data = await _service(_tournament(rules))._overview(uuid.uuid4())
        assert data["stream"] is None

    @pytest.mark.asyncio
    async def test_response_keys_unchanged(self):
        data = await _service(
            _tournament({"stream": PRODUCTION_SHAPE})
        )._overview(uuid.uuid4())
        assert set(data) == {
            "id", "name", "game", "format", "status", "banner_url",
            "prize_pool", "prize_currency", "start_at", "end_at",
            "registration_end_at", "max_teams", "registered_teams",
            "current_match", "stream", "result", "updated_at",
        }

    @pytest.mark.asyncio
    async def test_only_successful_responses_are_cached(self):
        svc = _service(_tournament({"stream": PRODUCTION_SHAPE}))
        tid = uuid.uuid4()
        first = await svc.overview(tid)
        assert svc._cache.set_calls == 1
        second = await svc.overview(tid)
        # 2回目はキャッシュから返るので set は増えない
        assert svc._cache.set_calls == 1
        assert second == first
