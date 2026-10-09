"""主催者の一連の流れを本番相当の環境に対して通しで検証する。

  大会作成 → 公開 → 参加申請 → 抽選 → Discord招待の通知 → チェックイン
  → ブラケット生成 → 試合結果登録 → 戦績への反映 → 後片付け

API コンテナ内で実行する:

    docker compose exec -T api python scripts/e2e_organizer_flow.py

既存の主催者とチームを使い、認証は DB から引いたユーザーの JWT を直接
発行する（パスワードを扱わないため）。作成した大会は最後に必ず削除する
ので、本番データには残らない。

環境変数:
    E2E_BASE     検証先のURL（既定 https://app.axelia-esports.jp）
    E2E_DISCORD  大会に設定する Discord 招待URL
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

import httpx  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.models.team import Team  # noqa: E402
from app.models.user import User  # noqa: E402

BASE = os.environ.get("E2E_BASE", "https://app.axelia-esports.jp")
DISCORD_INVITE = os.environ.get("E2E_DISCORD", "https://discord.gg/VqH3PhqS7N")
TOURNAMENT_NAME = "E2Eテスト大会（自動生成・削除予定）"

ok_count = 0
ng_count = 0


def check(label: str, cond: bool, detail: str = "") -> bool:
    global ok_count, ng_count
    if cond:
        ok_count += 1
        print(f"  [OK] {label}" + (f" — {detail}" if detail else ""))
    else:
        ng_count += 1
        print(f"  [NG] {label}" + (f" — {detail}" if detail else ""))
    return cond


async def cleanup() -> int:
    async with AsyncSessionLocal() as db:
        res = await db.execute(text(
            "DELETE FROM tournaments WHERE name = :n RETURNING id"), {"n": TOURNAMENT_NAME})
        n = len(res.fetchall())
        await db.commit()
    return n


async def load_actors():
    """主催者1名と、チームを持つオーナー6名を集める。"""
    async with AsyncSessionLocal() as db:
        org = (await db.execute(
            select(User).where(text("users.role::text = 'organizer'")).limit(1)
        )).scalar_one_or_none()
        rows = (await db.execute(
            select(Team.id, Team.name, Team.tag, Team.owner_id)
            .where(Team.owner_id.is_not(None), Team.is_active.is_(True))
            .order_by(Team.name).limit(6)
        )).all()
        teams = [{
            "id": str(tid), "name": name, "tag": tag,
            "token": create_access_token(subject=str(oid)),
        } for tid, name, tag, oid in rows]
        return {"username": org.username,
                "token": create_access_token(subject=str(org.id))}, teams


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def run(c: httpx.AsyncClient, organizer, teams) -> None:
    now = datetime.now(timezone.utc)

    # ── 1. 大会作成 ───────────────────────────────────────────────────
    print("1. 大会作成")
    payload = {
        "name": TOURNAMENT_NAME,
        "game": "VALORANT",
        "format": "single_elimination",
        "max_teams": 4,
        "min_teams": 2,
        "registration_start_at": (now - timedelta(hours=1)).isoformat(),
        "registration_end_at": (now + timedelta(hours=1)).isoformat(),
        "start_at": (now + timedelta(hours=2)).isoformat(),
        "require_check_in": True,
        "approval_mode": "lottery",
        "description": "通しテスト用。終了後に削除します。",
        "rules": {"discord": {"invite_url": DISCORD_INVITE}},
    }
    r = await c.post("/api/v1/tournaments", json=payload, headers=hdr(organizer["token"]))
    if not check("大会を作成できる", r.status_code == 201, f"HTTP {r.status_code} {r.text[:100]}"):
        return
    t = r.json()["data"]
    tid = t["id"]
    check("下書きとして作られる", t["status"] == "draft", t["status"])
    check("抽選方式が保持される", t.get("approval_mode") == "lottery", str(t.get("approval_mode")))
    check("チェックイン必須が保持される", t.get("require_check_in") is True)

    # 作成しただけでは応募を受け付けない。主催者が受付中へ切り替える。
    r = await c.patch(f"/api/v1/tournaments/{tid}/status",
                      json={"status": "registration_open"}, headers=hdr(organizer["token"]))
    check("受付中へ公開できる",
          r.status_code == 200 and r.json()["data"]["status"] == "registration_open",
          f"HTTP {r.status_code}")

    # ── 2. Discord情報 ────────────────────────────────────────────────
    print("\n2. Discord情報の引き回し")
    r = await c.get(f"/api/v1/tournaments/{tid}")
    rules = r.json()["data"].get("rules") or {}
    invite = (rules.get("discord") or {}).get("invite_url")
    check("大会情報にDiscord招待URLが入る", invite == DISCORD_INVITE, str(invite))
    check("Webhookなど秘密情報が露出しない", "webhook_url" not in json.dumps(rules))

    # ── 3. 参加申請 ───────────────────────────────────────────────────
    print("\n3. 参加申請（6チーム / 定員4）")
    applied = 0
    for tm in teams:
        r = await c.post(f"/api/v1/tournaments/{tid}/register",
                         json={"team_id": tm["id"], "notes": f"{tm['tag']} から申請"},
                         headers=hdr(tm["token"]))
        if r.status_code == 201:
            applied += 1
    check("6チームすべて申請できる", applied == 6, f"{applied}/6")

    r = await c.get(f"/api/v1/tournaments/{tid}/my-registration", headers=hdr(teams[0]["token"]))
    st = r.json().get("data", {})
    check("申請者が自分の状態を見られる",
          st.get("registered") is True and st.get("status") == "pending", str(st.get("status")))

    r = await c.get(f"/api/v1/tournaments/{tid}/registrations", headers=hdr(organizer["token"]))
    check("主催者が申請一覧を取得できる",
          r.status_code == 200 and len(r.json()["data"]) == 6,
          f"{len(r.json().get('data', []))}件")

    # ── 4. 受付終了と抽選 ─────────────────────────────────────────────
    print("\n4. 受付終了と抽選")
    r = await c.patch(f"/api/v1/tournaments/{tid}/status",
                      json={"status": "registration_closed"}, headers=hdr(organizer["token"]))
    check("受付終了に変更できる", r.status_code == 200, f"HTTP {r.status_code}")
    await asyncio.sleep(3)

    r = await c.get(f"/api/v1/tournaments/{tid}/registrations", headers=hdr(organizer["token"]))
    regs = r.json()["data"]
    approved = [x for x in regs if x["status"] == "approved"]
    waitlisted = [x for x in regs if x["status"] == "waitlisted"]
    check("定員分が当選する", len(approved) == 4, f"当選{len(approved)}")
    check("残りは補欠になる", len(waitlisted) == 2, f"補欠{len(waitlisted)}")

    won_ids = {x["team_id"] for x in approved}
    won = [tm for tm in teams if tm["id"] in won_ids]
    lost = [tm for tm in teams if tm["id"] not in won_ids]
    if not won:
        check("抽選が成立する", False, "当選0のため以降を中止")
        return

    # ── 5. 当落と通知 ─────────────────────────────────────────────────
    print("\n5. 当落の確認とDiscord案内")
    r = await c.get(f"/api/v1/tournaments/{tid}/my-registration", headers=hdr(won[0]["token"]))
    check("当選チームは参加確定と表示される",
          r.json()["data"].get("status") == "approved", str(r.json()["data"].get("status")))
    if lost:
        r = await c.get(f"/api/v1/tournaments/{tid}/my-registration", headers=hdr(lost[0]["token"]))
        check("落選チームは補欠と表示される",
              r.json()["data"].get("status") == "waitlisted", str(r.json()["data"].get("status")))

    r = await c.get("/api/v1/notifications?limit=20", headers=hdr(won[0]["token"]))
    notes = r.json().get("data", []) if r.status_code == 200 else []
    blob = json.dumps(notes, ensure_ascii=False)
    check("当選チームに通知が届く", len(notes) > 0, f"{len(notes)}件")
    check("通知にDiscord招待リンクが含まれる", DISCORD_INVITE in blob,
          "含まれる" if DISCORD_INVITE in blob else "含まれない")

    # ── 6. チェックイン ───────────────────────────────────────────────
    print("\n6. チェックイン")
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE tournaments SET check_in_start_at = now() - interval '5 minutes',"
            " check_in_end_at = now() + interval '30 minutes' WHERE id = :i"), {"i": tid})
        await db.commit()

    r = await c.get(f"/api/v1/tournaments/{tid}/check-in/me", headers=hdr(won[0]["token"]))
    check("受付時間内はopenになる",
          r.json()["data"]["window"]["state"] == "open", r.json()["data"]["window"]["state"])

    done = 0
    for tm in won:
        r = await c.post(f"/api/v1/tournaments/{tid}/check-in", headers=hdr(tm["token"]))
        if r.status_code == 200:
            done += 1
    check("当選チームがチェックインできる", done == len(won), f"{done}/{len(won)}")

    if lost:
        r = await c.post(f"/api/v1/tournaments/{tid}/check-in", headers=hdr(lost[0]["token"]))
        check("補欠はチェックインできない", r.status_code >= 400, f"HTTP {r.status_code}")

    # ── 7. ブラケット生成 ─────────────────────────────────────────────
    print("\n7. ブラケット生成")
    await c.patch(f"/api/v1/tournaments/{tid}/status",
                  json={"status": "check_in"}, headers=hdr(organizer["token"]))
    r = await c.post(f"/api/v1/tournaments/{tid}/bracket", headers=hdr(organizer["token"]))
    check("ブラケットを生成できる", r.status_code == 201, f"HTTP {r.status_code} {r.text[:100]}")
    def flatten(payload: dict) -> list[dict]:
        """rounds（ラウンド番号→試合配列）を1本のリストに均す。"""
        out = []
        for rn, ms in (payload.get("rounds") or {}).items():
            for m in ms:
                m.setdefault("round_number", int(rn))
                out.append(m)
        return out

    r = await c.get(f"/api/v1/tournaments/{tid}/bracket")
    matches = flatten(r.json()["data"])
    check("4チーム＝3試合になる", len(matches) == 3, f"{len(matches)}試合")

    # ── 8. 試合結果 ───────────────────────────────────────────────────
    print("\n8. 試合結果の登録")
    await c.patch(f"/api/v1/tournaments/{tid}/status",
                  json={"status": "ongoing"}, headers=hdr(organizer["token"]))
    r1 = [m for m in matches if m.get("round_number") == 1 and m.get("team1") and m.get("team2")]
    played = 0
    for m in r1:
        await c.patch(f"/api/v1/matches/{m['id']}/start", headers=hdr(organizer["token"]))
        await c.post(f"/api/v1/matches/{m['id']}/games/1/score",
                     json={"team1_score": 13, "team2_score": 7}, headers=hdr(organizer["token"]))
        rr = await c.post(f"/api/v1/matches/{m['id']}/result",
                          json={"winner_id": m["team1"]["id"]}, headers=hdr(organizer["token"]))
        if rr.status_code == 204:
            played += 1
    check("1回戦の結果を登録できる", played == len(r1), f"{played}/{len(r1)}")

    await asyncio.sleep(3)
    r = await c.get(f"/api/v1/tournaments/{tid}/bracket")
    final = [m for m in flatten(r.json()["data"])
             if m.get("round_number") == 2 and m.get("team1") and m.get("team2")]
    check("勝者が次ラウンドへ自動で進む", len(final) == 1, f"決勝カード {len(final)}件")

    if final:
        fm = final[0]
        await c.patch(f"/api/v1/matches/{fm['id']}/start", headers=hdr(organizer["token"]))
        await c.post(f"/api/v1/matches/{fm['id']}/games/1/score",
                     json={"team1_score": 13, "team2_score": 10}, headers=hdr(organizer["token"]))
        rr = await c.post(f"/api/v1/matches/{fm['id']}/result",
                          json={"winner_id": fm["team1"]["id"]}, headers=hdr(organizer["token"]))
        check("決勝の結果を登録できる", rr.status_code == 204, f"HTTP {rr.status_code}")

    # ── 9. 反映の確認 ─────────────────────────────────────────────────
    print("\n9. 戦績への反映")
    await c.patch(f"/api/v1/tournaments/{tid}/status",
                  json={"status": "completed"}, headers=hdr(organizer["token"]))
    await asyncio.sleep(3)

    r = await c.get(f"/api/v1/tournaments/{tid}")
    check("大会が終了状態になる", r.json()["data"]["status"] == "completed",
          r.json()["data"]["status"])
    r = await c.get(f"/api/v1/tournaments/{tid}/statistics")
    check("大会統計を取得できる", r.status_code == 200, f"HTTP {r.status_code}")

    async with AsyncSessionLocal() as db:
        n = (await db.execute(text(
            "SELECT count(*) FROM matches WHERE tournament_id = :i"
            " AND status::text = 'completed'"), {"i": tid})).scalar()
        check("3試合すべてが完了として残る", n == 3, f"{n}/3")


async def main() -> int:
    organizer, teams = await load_actors()
    print(f"接続先: {BASE}")
    print(f"主催者: {organizer['username']} / 参加予定チーム: {len(teams)}")
    print(f"Discord招待URL: {DISCORD_INVITE}\n")

    await cleanup()  # 前回の残りがあれば先に消す
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as c:
            await run(c, organizer, teams)
    finally:
        print("\n10. 後片付け")
        n = await cleanup()
        check("テストで作った大会を削除", n >= 1, f"{n}件")

    print(f"\n結果: 成功 {ok_count} / 失敗 {ng_count}")
    return 0 if ng_count == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
