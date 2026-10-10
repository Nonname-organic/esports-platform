"""参加申請の結果を知らせる通知の文面。

画面・メール・Discord DM のどれから出しても同じ文面になるよう、
本文の組み立てはここに集約する。差し込みは {} ではなく明示的な
関数引数にして、埋め忘れをその場で気付けるようにしている。

本文は改行を含む複数行になる。通知一覧では折りたたんで見せ、
開いたときに全文と導線（Discordへ参加 / 大会ページ）を出す。

件名の先頭には必ず大会名を入れる。複数の大会に応募していると、
一覧でどの大会の通知か分からなくなるため。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# 日本時間。サーバーはUTCで動くため、表示のときだけ寄せる。
JST = timezone(timedelta(hours=9))


def format_tournament_date(start_at: datetime | None) -> str:
    """開催日時を日本時間の読みやすい表記にする。未定なら「未定」。"""
    if start_at is None:
        return "未定"
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    jst = start_at.astimezone(JST)
    return f"{jst.year}年{jst.month}月{jst.day}日 {jst.hour:02d}:{jst.minute:02d}"


def approved_with_discord(tournament_name: str, tournament_date: str,
                          discord_invite_url: str) -> tuple[str, str]:
    """参加確定（Discord招待URLあり）。(件名, 本文) を返す。"""
    title = f"【{tournament_name}】大会参加確定のお知らせ"
    body = (
        "大会へのご応募ありがとうございます。\n"
        "この度、以下の大会への参加が確定いたしましたので、お知らせいたします。\n"
        "\n"
        f"・大会名： {tournament_name}\n"
        f"・開催日時： {tournament_date}\n"
        "・参加状況： 参加確定\n"
        "\n"
        "大会への参加にあたり、以下のDiscordサーバーへのご参加をお願いいたします。\n"
        "\n"
        f"Discord招待URL：\n{discord_invite_url}\n"
        "\n"
        "大会当日の進行や詳細な案内については、参加先のDiscordサーバーをご確認ください。\n"
        "それでは、大会当日よろしくお願いいたします。"
    )
    return title, body


def approved_without_discord(tournament_name: str, tournament_date: str) -> tuple[str, str]:
    """参加確定（Discord招待URLが未設定）。(件名, 本文) を返す。"""
    title = f"【{tournament_name}】大会参加確定のお知らせ"
    body = (
        "大会へのご応募ありがとうございます。\n"
        "この度、以下の大会への参加が確定いたしましたので、お知らせいたします。\n"
        "\n"
        f"・大会名： {tournament_name}\n"
        f"・開催日時： {tournament_date}\n"
        "・参加状況： 参加確定\n"
        "\n"
        "大会開催時に使用するDiscordサーバーおよび参加方法につきましては、\n"
        "現在、大会主催者へ確認を行っております。\n"
        "詳細が確認でき次第、改めてご案内いたしますので、今しばらくお待ちください。\n"
        "それでは、大会当日よろしくお願いいたします。"
    )
    return title, body


def waitlisted(tournament_name: str, tournament_date: str) -> tuple[str, str]:
    """抽選に外れた場合。(件名, 本文) を返す。

    この仕組みでは外れたチームを削除せず補欠として残し、辞退が出たときに
    主催者が繰り上げられる。「落選」と言い切ると、その後の繰り上げ連絡と
    食い違うため、補欠であることを明示した文面にしている。
    """
    title = f"【{tournament_name}】大会参加申請結果のお知らせ"
    body = (
        "大会へのご応募ありがとうございます。\n"
        "この度、以下の大会への参加申請について、選考の結果、\n"
        "誠に残念ながら今回は参加枠に入らない結果となりました。\n"
        "\n"
        f"・大会名： {tournament_name}\n"
        f"・開催日時： {tournament_date}\n"
        "・参加状況： 補欠\n"
        "\n"
        "参加チームに辞退が出た場合、補欠から繰り上げとなることがあります。\n"
        "繰り上げが決まった際は、改めてご連絡いたします。\n"
        "\n"
        "ご期待に沿えない結果となり、申し訳ございません。\n"
        "今後もさまざまな大会の開催を予定しておりますので、\n"
        "ぜひ引き続きご応募いただけますと幸いです。\n"
        "今後ともよろしくお願いいたします。"
    )
    return title, body
