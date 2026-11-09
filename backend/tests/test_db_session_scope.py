"""DB セッションは応答を返す前にコミットする（scope="function"）。

既定の request スコープだと FastAPI は応答を送ってから get_db の後片付け（commit）を
行うため、登録直後の自動ログインが未コミットのユーザーを読めず失敗していた。
同じ get_db を別スコープで依存すると別セッションになるので、全箇所を揃えて確かめる。
"""
import inspect
from typing import get_args

from app.core import dependencies
from app.core.database import get_db


def test_DBSessionは応答前にコミットする():
    assert get_args(dependencies.DBSession)[1].scope == "function"


def test_get_dbを使う依存はすべて同じスコープ():
    found = 0
    for _, fn in inspect.getmembers(dependencies, inspect.isfunction):
        for p in inspect.signature(fn).parameters.values():
            dep = p.default
            if getattr(dep, "dependency", None) is get_db:
                found += 1
                assert dep.scope == "function", fn.__name__
    assert found >= 2  # get_current_user / resolve_discord_user など
