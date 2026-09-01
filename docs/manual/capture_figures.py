"""操作マニュアルに載せる画面キャプチャを撮る。

ローカルの開発スタック（docker compose up、http://localhost で配信）に対して
Chrome を動かし、docs/manual/figures/ に PNG を書き出す。

    set AXELIA_CAPTURE_PW=<デモ用アカウントのパスワード>
    python docs/manual/capture_figures.py

事前に scratchpad の setup_demo.py などでデモ用アカウント
（Kaito_VLR / AXELIA_Staff）とチームを作っておくこと。撮影の途中で
チェックイン受付中の状態を作るため、DB を一時的に書き換えて元に戻す。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://localhost"
OUT = Path(__file__).with_name("figures")
PW = os.environ["AXELIA_CAPTURE_PW"]

PLAYER_EMAIL = "kaito.demo@axelia-demo.example.com"
STAFF_EMAIL = "staff.demo@axelia-demo.example.com"

TOURNAMENT_OPEN = "af57efb9-83b8-4ebf-8fca-f09d1d9ea83f"   # AXELIA CUP vol.2
MATCH_ID = "4bab561a-240e-4aae-91e5-b7c8c3500cc9"          # Crimson Vanguard vs Tempest Line

VIEWPORT = {"width": 1280, "height": 820}


def psql(sql: str) -> str:
    """ローカルの postgres コンテナに SQL を投げる。"""
    return subprocess.run(
        ["docker", "exec", "esports-platform-postgres-1",
         "psql", "-U", "esports_user", "-d", "esports_db", "-At", "-c", sql],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def shot(page: Page, name: str, height: int | None = None) -> None:
    """表示中の画面を figures/<name>.png に保存する。"""
    OUT.mkdir(exist_ok=True)
    clip = None
    if height:
        clip = {"x": 0, "y": 0, "width": VIEWPORT["width"], "height": height}
    page.screenshot(path=str(OUT / f"{name}.png"), clip=clip)
    print("saved", name)


def card_shot(page: Page, text: str, name: str) -> None:
    """その文字列を含むカードだけを切り出して保存する。

    紙面ではページ全体を貼ると文字が小さくなりすぎるので、
    説明したい部分だけを大きく載せる。
    """
    OUT.mkdir(exist_ok=True)
    el = page.get_by_text(text, exact=False).first
    card = el.locator(
        "xpath=ancestor::*[contains(@class,'rounded-xl')"
        " or contains(@class,'rounded-2xl')][1]"
    )
    target = card if card.count() > 0 else el
    target.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(500)
    target.screenshot(path=str(OUT / f"{name}.png"))
    print("saved", name)


def dismiss_banner(page: Page) -> None:
    """デモ環境バナーは1枚目だけで足りるので以降は閉じる。"""
    try:
        page.get_by_role("button", name="閉じる").first.click(timeout=1500)
    except Exception:
        page.evaluate(
            "document.querySelectorAll('[data-demo-banner],[role=\"status\"]')"
            ".forEach(e => e.remove())"
        )
    page.wait_for_timeout(200)


def login(page: Page, email: str) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', PW)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
    page.wait_for_load_state("networkidle")


def logout(page: Page) -> None:
    page.goto(f"{BASE}/", wait_until="domcontentloaded")
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.context.clear_cookies()


# --- 各図 -----------------------------------------------------------------

def fig_home(page: Page) -> None:
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1200)
    shot(page, "01_home_hero")
    # 開催中の大会カードまでスクロールした状態も撮っておく
    page.mouse.wheel(0, 900)
    page.wait_for_timeout(900)
    shot(page, "02_home_tournaments")


def fig_register(page: Page) -> None:
    page.goto(f"{BASE}/register", wait_until="networkidle")
    dismiss_banner(page)
    page.fill('input[type="text"]', "Kaito_VLR")
    page.fill('input[type="email"]', "kaito@example.com")
    for box in page.locator('input[type="password"]').all():
        box.fill("ValorantDemo1")
    page.wait_for_timeout(400)
    OUT.mkdir(exist_ok=True)
    page.locator("form").first.screenshot(path=str(OUT / "03_register.png"))
    print("saved 03_register")


def fig_tournament_entry(page: Page) -> None:
    page.goto(f"{BASE}/tournaments/{TOURNAMENT_OPEN}", wait_until="networkidle")
    dismiss_banner(page)
    page.wait_for_timeout(1200)
    card_shot(page, "エントリー受付中", "04_tournament_entry")


def fig_entry_submitted(page: Page) -> None:
    """実際に画面から申請し、申請済み表示になったところを撮る。"""
    page.get_by_placeholder("出場メンバーの補足など").fill("出場メンバーは5名、当日は21時から参加できます")
    page.wait_for_timeout(300)
    card_shot(page, "エントリー受付中", "05_entry_filled")
    page.get_by_role("button", name="エントリーする").click()
    page.wait_for_timeout(2500)
    card_shot(page, "エントリー状況", "06_entry_submitted")


def fig_check_in(page: Page) -> None:
    page.goto(f"{BASE}/tournaments/{TOURNAMENT_OPEN}", wait_until="networkidle")
    dismiss_banner(page)
    page.wait_for_timeout(1500)
    card_shot(page, "チェックイン受付中", "07_check_in")


def fig_create(page: Page) -> None:
    page.goto(f"{BASE}/organizer/tournaments/create", wait_until="networkidle")
    dismiss_banner(page)
    page.wait_for_timeout(1000)
    try:
        page.fill('input[name="name"]', "AXELIA CUP vol.3")
    except Exception:
        pass
    page.wait_for_timeout(300)
    shot(page, "08_create_tournament")


def fig_match_admin(page: Page) -> None:
    page.goto(f"{BASE}/admin/matches/{MATCH_ID}", wait_until="networkidle")
    dismiss_banner(page)
    page.wait_for_timeout(1800)
    shot(page, "09_match_admin_top")
    card_shot(page, "スコアボード取り込み", "10_scoreboard_import")


def main() -> None:
    team_id = psql(
        "SELECT id FROM teams WHERE tag = 'MRB' LIMIT 1;"
    )
    saved_window = psql(
        "SELECT coalesce(check_in_start_at::text, '') || '|' "
        "|| coalesce(check_in_end_at::text, '') "
        f"FROM tournaments WHERE id = '{TOURNAMENT_OPEN}';"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(
            viewport=VIEWPORT, device_scale_factor=2,
            color_scheme="dark", locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = ctx.new_page()

        fig_home(page)
        fig_register(page)

        # 申請前の状態から撮るため、前回の申請が残っていれば消す
        psql(
            "DELETE FROM tournament_registrations "
            f"WHERE tournament_id = '{TOURNAMENT_OPEN}' AND team_id = '{team_id}';"
        )

        login(page, PLAYER_EMAIL)
        fig_tournament_entry(page)
        fig_entry_submitted(page)

        # 当選してチェックイン受付中、という状態を一時的に作る
        psql(
            "UPDATE tournament_registrations SET status = 'approved', "
            f"checked_in_at = NULL WHERE tournament_id = '{TOURNAMENT_OPEN}' "
            f"AND team_id = '{team_id}';"
        )
        psql(
            "UPDATE tournaments SET "
            "check_in_start_at = now() - interval '2 minutes', "
            "check_in_end_at = now() + interval '5 minutes' "
            f"WHERE id = '{TOURNAMENT_OPEN}';"
        )
        try:
            fig_check_in(page)
        finally:
            start, _, end = saved_window.partition("|")
            psql(
                "UPDATE tournaments SET check_in_start_at = "
                + (f"'{start}'" if start else "NULL")
                + ", check_in_end_at = "
                + (f"'{end}'" if end else "NULL")
                + f" WHERE id = '{TOURNAMENT_OPEN}';"
            )
            psql(
                "DELETE FROM tournament_registrations "
                f"WHERE tournament_id = '{TOURNAMENT_OPEN}' AND team_id = '{team_id}';"
            )

        logout(page)
        login(page, STAFF_EMAIL)
        fig_create(page)
        fig_match_admin(page)

        ctx.close()
        browser.close()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
