"""大会ルール（Section構造Markdown）のスキーマ・固定Section・テンプレート（機能⑧）。

- 各 Section は固定 id を持つ（general/prohibited/judgment/bo/stream/discord/penalty）。
- rules_doc = {"sections": [RulesSection...]}。
- テンプレート（VALORANT標準等）は TEMPLATES に定義。将来テンプレ追加はここに1件足すだけ。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# 固定 Section id とデフォルトタイトル（順序も既定）
SECTION_DEFS: list[tuple[str, str]] = [
    ("general", "大会ルール"),
    ("prohibited", "禁止事項"),
    ("judgment", "判定方法"),
    ("bo", "BOルール"),
    ("stream", "配信ルール"),
    ("discord", "Discordルール"),
    ("penalty", "ペナルティ"),
]
SECTION_IDS = {sid for sid, _ in SECTION_DEFS}


class RulesSection(BaseModel):
    id: str = Field(..., max_length=30)          # 固定id（SECTION_IDS）
    title: str = Field(..., max_length=100)
    body_md: str = Field(default="", max_length=20000)
    order: int = 0


class RulesDoc(BaseModel):
    sections: list[RulesSection] = Field(default_factory=list)


# ── APIリクエスト ────────────────────────────────────────────────────────────
class RulesDocRequest(BaseModel):
    """PUT /tournaments/{id}/rules のボディ。固定id以外のSectionはService側で除外。"""
    sections: list[RulesSection] = Field(default_factory=list)


class ApplyTemplateRequest(BaseModel):
    template_id: str = Field(..., max_length=50)


def empty_doc() -> dict:
    """全固定Sectionを空で持つ雛形。"""
    return {"sections": [
        {"id": sid, "title": title, "body_md": "", "order": i}
        for i, (sid, title) in enumerate(SECTION_DEFS)
    ]}


# ── テンプレート（機能⑧・拡張ポイント） ─────────────────────────────────────
# 新テンプレ追加 = TEMPLATES に1件足すだけ（キー=テンプレid）。
TEMPLATES: dict[str, dict] = {
    "valorant_standard": {
        "id": "valorant_standard",
        "label": "VALORANT 標準ルール",
        "game": "VALORANT",
        "doc": {"sections": [
            {"id": "general", "title": "大会ルール", "order": 0, "body_md": (
                "- 5v5 のスタンダードモードで行います。\n"
                "- 各チームは最大7名（スターター5 + 控え2）まで登録可能です。\n"
                "- 試合開始時刻に遅刻した場合、10分の猶予後に不戦敗となる場合があります。"
            )},
            {"id": "prohibited", "title": "禁止事項", "order": 1, "body_md": (
                "- チート・マクロ・不正なサードパーティツールの使用\n"
                "- 意図的な遅延行為・不適切な言動・ハラスメント\n"
                "- アカウント共有・代理出場（Smurf/Boosting）"
            )},
            {"id": "judgment", "title": "判定方法", "order": 2, "body_md": (
                "- 勝敗は各マップの獲得ラウンド数で決定します。\n"
                "- 通信切断が発生した場合、運営の判断でラウンド巻き戻し・再戦を行うことがあります。\n"
                "- スコアの申告は両チームのキャプテンが確認し、運営へ報告してください。"
            )},
            {"id": "bo", "title": "BOルール", "order": 3, "body_md": (
                "- 予選: BO1 / 準決勝以降: BO3 / 決勝: BO5\n"
                "- マップは Ban/Pick 方式で決定します（先攻/後攻はコインフリップ）。"
            )},
            {"id": "stream", "title": "配信ルール", "order": 4, "body_md": (
                "- 公式配信がある試合は、選手個人配信は5分以上のディレイを設けてください。\n"
                "- 観戦者の視点情報を選手へ伝達する行為（Ghosting）を禁止します。"
            )},
            {"id": "discord", "title": "Discordルール", "order": 5, "body_md": (
                "- 試合前に指定のDiscordチャンネルへ集合してください。\n"
                "- 運営からの連絡はDiscordで行います。通知を有効にしておいてください。"
            )},
            {"id": "penalty", "title": "ペナルティ", "order": 6, "body_md": (
                "- 軽微な違反: 警告\n"
                "- 重大な違反・繰り返しの違反: ラウンド/マップ没収、失格\n"
                "- 不正行為が発覚した場合、大会成績の抹消および今後の参加禁止となることがあります。"
            )},
        ]},
    },
}


def list_templates() -> list[dict]:
    return [{"id": t["id"], "label": t["label"], "game": t.get("game")} for t in TEMPLATES.values()]


def get_template_doc(template_id: str) -> dict | None:
    t = TEMPLATES.get(template_id)
    return t["doc"] if t else None
