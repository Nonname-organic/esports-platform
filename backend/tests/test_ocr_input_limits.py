"""スコアボード OCR の入力制限（S1: 画像の展開によるメモリ枯渇）。

圧縮した画像はファイルが小さくても、展開後の大きさは寸法で決まる。cv2.imdecode に
渡す前に、ヘッダーだけで形式と寸法を確かめていることを確かめる。

大きな画像は実際には展開しない。寸法を宣言しただけのヘッダーか、小さい上限に
差し替えた状態で検証し、展開されなかったことは cv2.imdecode の呼び出しで確かめる。
"""
import asyncio
import io
import struct
import threading
import zlib

import numpy as np
import pytest
from PIL import Image

from app.core.exceptions import RateLimitError, ValidationError
from app.models.enums import MatchStatus, TournamentStatus, UserRole
from app.models.match import Match
from app.services import scoreboard_import, scoreboard_ocr
from tests import factories as f


def _img(w: int, h: int, fmt: str = "PNG", **kw) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (40, 60, 80)).save(buf, fmt, **kw)
    return buf.getvalue()


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def _png_header(w: int, h: int, *, bit_depth: int = 8, color_type: int = 2) -> bytes:
    """寸法だけを宣言した PNG（画素データなし）。"""
    ihdr = struct.pack(">IIBBBBB", w, h, bit_depth, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IEND", b"")


def _png_bomb(w: int, h: int) -> bytes:
    """全面が黒の 1bit グレースケール PNG を、画素を持たずに組み立てる（展開爆弾）。"""
    row = b"\x00" * (1 + (w + 7) // 8)  # フィルタ種別 + 1行分
    z = zlib.compressobj(9)
    idat = b"".join(z.compress(row) for _ in range(h)) + z.flush()
    ihdr = struct.pack(">IIBBBBB", w, h, 1, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _jpeg_with_declared_size(w: int, h: int) -> bytes:
    """本物の小さな JPEG の SOF0 に、大きな寸法を書き込む。"""
    data = bytearray(_img(64, 64, "JPEG"))
    sof = data.index(b"\xff\xc0")
    data[sof + 5:sof + 9] = struct.pack(">HH", h, w)
    return bytes(data)


def _webp_lossless_header(w: int, h: int) -> bytes:
    """寸法だけを宣言した可逆 WebP（VP8L）。Pillow は先頭30バイトで寸法を読む。"""
    payload = b"\x2f" + struct.pack("<I", (w - 1) | ((h - 1) << 14)) + b"\x00" * 16
    chunk = b"VP8L" + struct.pack("<I", len(payload)) + payload
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


@pytest.fixture
def imdecode_calls(monkeypatch) -> list[int]:
    """cv2.imdecode（実際の展開）が呼ばれた回数を記録する。"""
    calls: list[int] = []
    real = scoreboard_ocr.cv2.imdecode

    def spy(buf, flags):
        calls.append(len(buf))
        return real(buf, flags)

    monkeypatch.setattr(scoreboard_ocr.cv2, "imdecode", spy)
    return calls


class TestNormalImages:
    @pytest.mark.parametrize("fmt,kw", [("PNG", {}), ("JPEG", {"quality": 90}), ("WEBP", {"quality": 90})])
    def test_通常のスクリーンショットは従来どおり読める(self, fmt, kw, imdecode_calls):
        img = scoreboard_ocr._decode(_img(1920, 1080, fmt, **kw))
        assert img.shape == (1080, 1920, 3) and img.dtype == np.uint8
        assert len(imdecode_calls) == 1

    def test_4Kと上限ちょうどの寸法はヘッダーの確認を通る(self):
        scoreboard_ocr._check_header(_png_header(3840, 2160))
        scoreboard_ocr._check_header(_png_header(4096, 4096))  # 16,777,216 画素 = 上限
        scoreboard_ocr._check_header(_png_header(8192, 2048))  # 一辺の上限

    def test_続けて送っても毎回同じ結果になる(self, imdecode_calls):
        raw = _img(1280, 720)
        for _ in range(20):
            assert scoreboard_ocr._decode(raw).shape == (720, 1280, 3)
        assert len(imdecode_calls) == 20


class TestOversizedImagesAreRejectedBeforeDecoding:
    @pytest.mark.parametrize("w,h", [(4097, 4096), (8193, 100), (100, 8193), (20000, 20000), (2**31 - 1, 1)])
    def test_上限を超える寸法を宣言したPNG(self, w, h, imdecode_calls):
        with pytest.raises(ValidationError, match="大きすぎ"):
            scoreboard_ocr._decode(_png_header(w, h))
        assert imdecode_calls == []

    def test_圧縮率が極端に高いPNGは展開しない(self, imdecode_calls):
        bomb = _png_bomb(20000, 20000)  # 展開すると BGR で約1.2GB
        assert len(bomb) < 1024 * 1024  # ファイルは 5MB の上限よりずっと小さい
        with pytest.raises(ValidationError, match="大きすぎ"):
            scoreboard_ocr._decode(bomb)
        assert imdecode_calls == []

    def test_巨大な寸法を宣言したJPEG(self, imdecode_calls):
        with pytest.raises(ValidationError, match="大きすぎ"):
            scoreboard_ocr._decode(_jpeg_with_declared_size(60000, 60000))
        assert imdecode_calls == []

    @pytest.mark.parametrize("w,h", [(5000, 5000), (16383, 16383)])
    def test_巨大な寸法を宣言したWebPは展開用の領域を確保する前に断る(self, w, h, imdecode_calls):
        with pytest.raises(ValidationError, match="大きすぎ"):
            scoreboard_ocr._decode(_webp_lossless_header(w, h))
        assert imdecode_calls == []


class TestLimitBoundary:
    """上限を小さく差し替え、実際に展開できる大きさで境界を確かめる。"""

    @pytest.fixture(autouse=True)
    def small_limits(self, monkeypatch):
        monkeypatch.setattr(scoreboard_ocr, "_MAX_SIDE", 1000)
        monkeypatch.setattr(scoreboard_ocr, "_MAX_PIXELS", 1000 * 400)

    def test_上限ちょうどは展開する(self, imdecode_calls):
        assert scoreboard_ocr._decode(_img(1000, 400)).shape == (400, 1000, 3)
        assert len(imdecode_calls) == 1

    @pytest.mark.parametrize("w,h", [(1001, 360), (900, 450)])  # 一辺の超過 / 画素数の超過
    def test_上限を1でも超えたら展開しない(self, w, h, imdecode_calls):
        with pytest.raises(ValidationError, match="大きすぎ"):
            scoreboard_ocr._decode(_img(w, h))
        assert imdecode_calls == []


class TestBrokenOrUnsupportedImages:
    def test_途中で切れた画像は読めない画像として断る(self, imdecode_calls):
        raw = _img(1280, 720)
        with pytest.raises(ValidationError, match="読み込めません"):
            scoreboard_ocr._decode(raw[: len(raw) // 2])

    @pytest.mark.parametrize("raw", [b"not an image", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"RIFF\x00\x00\x00\x00WEBP"])
    def test_壊れたヘッダー(self, raw, imdecode_calls):
        with pytest.raises(ValidationError, match="読み込めません"):
            scoreboard_ocr._decode(raw)
        assert imdecode_calls == []

    @pytest.mark.parametrize("fmt", ["BMP", "GIF", "TIFF", "PPM"])
    def test_PNG_JPEG_WebP以外の形式は展開しない(self, fmt, imdecode_calls):
        # Content-Type を image/png と偽っても、中身の形式で判定する
        with pytest.raises(ValidationError, match="のみ対応"):
            scoreboard_ocr._decode(_img(1280, 720, fmt))
        assert imdecode_calls == []

    def test_空の画像(self):
        with pytest.raises(ValidationError, match="空"):
            scoreboard_ocr._decode(b"")


async def _ongoing_match(db):
    org = await f.make_user(db, role=UserRole.ORGANIZER)
    tour = await f.make_tournament(db, organizer=org, status=TournamentStatus.ONGOING)
    teams = [await f.make_team(db, owner=await f.make_user(db), name=f"OCR {i}", tag=f"OC{i}") for i in range(2)]
    match = Match(tournament_id=tour.id, round_number=1, match_number=1, status=MatchStatus.ONGOING,
                  team1_id=teams[0].id, team2_id=teams[1].id)
    db.add(match)
    await db.flush()
    return match


class TestConcurrentParsing:
    """同時に解析するのは2件まで。3件目は待たせずに 429 で断り、枠は必ず返す。"""

    @pytest.mark.asyncio
    async def test_3件同時なら3件目は429で断り終わった後は受け付ける(self, db, monkeypatch):
        match = await _ongoing_match(db)
        svc = scoreboard_import.ScoreboardImportService(db)
        entered, release = threading.Semaphore(0), threading.Event()

        def slow_parse(raw):  # スレッドプールで動く。解析中のまま止めておく
            entered.release()
            release.wait(10)
            raise ValidationError("テスト用の解析エラー")

        monkeypatch.setattr(scoreboard_ocr, "parse_scoreboard", slow_parse)
        first = [asyncio.create_task(svc.parse(match.id, b"img")) for _ in range(2)]
        for _ in range(2):  # 2件とも解析に入るまで待つ
            await asyncio.to_thread(entered.acquire, True, 10)
        with pytest.raises(RateLimitError):
            await svc.parse(match.id, b"img")
        release.set()
        for task in first:
            with pytest.raises(ValidationError):
                await task

        monkeypatch.setattr(scoreboard_ocr, "parse_scoreboard",
                            lambda raw: (scoreboard_ocr.ScoreboardParseResult(), None))
        for _ in range(3):  # 枠が返っていれば、続けて送っても通る
            assert (await svc.parse(match.id, b"img"))["rows"] == []
        assert not scoreboard_import._OCR_SLOTS.locked()
