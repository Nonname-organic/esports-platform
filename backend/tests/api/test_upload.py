"""アップロード（multipart）の受け口。

python-multipart を上げるにあたって足した。これまで multipart を通る
テストが1件も無く、依存を差し替えても壊れたかどうかが分からなかった。

ここで確かめたいのは保存先の挙動ではなく、multipart のボディが正しく
解析されてファイル名・content_type・中身がハンドラまで届くこと。
保存は _store をモックして外部依存を切る。
"""
import time

import pytest
from httpx import AsyncClient

from app.api.v1 import upload as upload_api

# 1x1 の PNG。中身が壊れていないことより、バイト列がそのまま届くかを見る。
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100ffff0300000600"
    "0557bfabd40000000049454e44ae426082"
)


@pytest.fixture
def stub_store(monkeypatch):
    """保存処理を差し替える。S3 にもディスクにも触らない。"""
    captured: dict = {}

    def _fake(key, contents, content_type, disposition=None):
        captured["key"] = key
        captured["bytes"] = contents
        captured["content_type"] = content_type
        captured["disposition"] = disposition
        return f"https://storage.test/{key}"

    monkeypatch.setattr(upload_api, "_store", _fake)
    return captured


class TestUploadImage:
    @pytest.mark.asyncio
    async def test_未認証では401(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/upload/image",
            files={"file": ("a.png", PNG_1PX, "image/png")},
        )
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_正常な画像を受け取り中身がそのまま渡る(
        self, client: AsyncClient, player_token, stub_store
    ):
        res = await client.post(
            "/api/v1/upload/image?purpose=team_logo",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("logo.png", PNG_1PX, "image/png")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["key"].startswith("uploads/team_logo/")
        assert body["key"].endswith(".png")
        # multipart が正しく解析されていれば、バイト列が欠けずに届く
        assert stub_store["bytes"] == PNG_1PX
        assert stub_store["content_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_許可されない形式は400(self, client: AsyncClient, player_token):
        """content_type がハンドラまで届いていないとこの判定は成立しない。"""
        res = await client.post(
            "/api/v1/upload/image",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("x.svg", b"<svg/>", "image/svg+xml")},
        )
        assert res.status_code == 400
        assert "JPEG" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_サイズ超過は400(self, client: AsyncClient, player_token):
        """ボディを最後まで読めていないとサイズ判定ができない。"""
        big = b"\x00" * (upload_api.MAX_SIZE + 1)
        res = await client.post(
            "/api/v1/upload/image",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("big.png", big, "image/png")},
        )
        assert res.status_code == 400
        # content_type は許可済みなので、この400はサイズ判定によるものでなければ
        # おかしい。形式判定で弾かれていたら、ボディを読めていないことになる。
        assert "5MB" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_ファイル部が無ければ422(self, client: AsyncClient, player_token):
        res = await client.post(
            "/api/v1/upload/image",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"notfile": ("a.png", PNG_1PX, "image/png")},
        )
        assert res.status_code == 422


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_添付ファイルを受け取り名前とサイズを返す(
        self, client: AsyncClient, player_token, stub_store
    ):
        content = b"%PDF-1.4\n" + b"x" * 100
        res = await client.post(
            "/api/v1/upload/file?purpose=tournament_attachment",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("規約.pdf", content, "application/pdf")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["name"] == "規約.pdf"          # 非ASCIIのファイル名も壊れない
        assert body["size"] == len(content)
        assert stub_store["bytes"] == content
        assert 'filename="規約.pdf"' in (stub_store["disposition"] or "")

    @pytest.mark.asyncio
    async def test_許可されない形式は400(self, client: AsyncClient, player_token):
        res = await client.post(
            "/api/v1/upload/file",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("a.exe", b"MZ", "application/x-msdownload")},
        )
        assert res.status_code == 400


class TestMultipartRobustness:
    @pytest.mark.asyncio
    async def test_巨大なパート見出しを受理せず待たされない(
        self, client: AsyncClient, player_token, stub_store
    ):
        """0.0.27 で塞がれた「multipart ヘッダ長に上限が無い」件の回帰確認。

        上限が無い実装では見出しの長さに比例して解析時間が伸びる。
        ライブラリ単体で測ると 0.0.26 は 2MB の見出しに 547ms かかり、
        0.0.32 は 0.1ms で MultipartParseError にして捨てていた。

        閾値そのものはライブラリの実装詳細なので固定しない。代わりに
        「受理しないこと」と「待たされないこと」を見る。上限が外れると
        このリクエストは通ってしまい、応答時間も伸びる。
        """
        huge_name = "x" * 1_000_000
        started = time.perf_counter()
        res = await client.post(
            "/api/v1/upload/image",
            headers={"Authorization": f"Bearer {player_token}"},
            files={"file": ("a.png", PNG_1PX, "image/png")},
            data={huge_name: "v"},
        )
        elapsed = time.perf_counter() - started

        assert res.status_code != 200, (
            "1MB のパート見出しが受理された。ヘッダ長の上限が効いていない"
        )
        # 上限が効いていれば解析を打ち切るので待たされない。
        # CI の遅さを見込んで余裕のある上限にしてある。
        assert elapsed < 5.0, f"応答に {elapsed:.1f} 秒かかった"
        # 保存処理まで到達していないこと
        assert "bytes" not in stub_store
