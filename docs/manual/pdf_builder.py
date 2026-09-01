"""AXELIA ドキュメント用のPDF組版ヘルパー。

日本語マニュアルを組むための最小限の部品だけを持つ。ReportLab の Platypus は
日本語の行分割と表の高さ計算が扱いづらいため、canvas を直接使い、
文字幅を測りながら自前で流し込む。

提供する部品:
    title_page / toc / h1 / h2 / para / steps / table / callout / faq / figure

使い方は build_manual.py・build_ops_guide.py を参照。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── ブランド ─────────────────────────────────────────────────────────────────
INK = HexColor("#14213d")        # 見出し・本文（純黒を避けた濃紺）
BODY = HexColor("#2b3648")
MUTED = HexColor("#6b7688")
BRAND = HexColor("#2563eb")      # brand-600
BRAND_DARK = HexColor("#1d4ed8")
BRAND_PALE = HexColor("#eff6ff")
VALORANT = HexColor("#ff4655")
LINE = HexColor("#dde3ee")
PANEL = HexColor("#f6f8fc")
WARN_BG = HexColor("#fff7e6")
WARN_LINE = HexColor("#e0a02a")
OK_BG = HexColor("#eefaf3")
OK_LINE = HexColor("#1c9c66")
WHITE = HexColor("#ffffff")

FONT_B = "AxeliaBold"
FONT_R = "AxeliaRegular"

PAGE_W, PAGE_H = A4
MARGIN_X = 22 * 2.83465          # 22mm
MARGIN_TOP = 24 * 2.83465
MARGIN_BOTTOM = 18 * 2.83465
CONTENT_W = PAGE_W - MARGIN_X * 2

# 図の解像度。紙面1ptあたり何画素持たせるか（3.0 ≒ 216dpi）。
# 元のキャプチャは2倍解像度で撮っているため、そのまま貼るとPDFが無駄に重くなる。
FIGURE_PPP = 3.0


def _fit_raster(path: Path, width_pt: float):
    """図を紙面サイズに見合う画素数まで落として ImageReader を返す。"""
    from PIL import Image

    im = Image.open(path)
    target = int(width_pt * FIGURE_PPP)
    if im.width > target:
        h = round(im.height * target / im.width)
        im = im.resize((target, h), Image.LANCZOS)
    return ImageReader(im.convert("RGB"))


# 行末に置けない文字（行頭禁則）
NO_LINE_START = "、。，．）」』】〉》〕｝・〜ー’”ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶーぐ！？!?：:；;"
# 行末禁則（次行へ送る）
NO_LINE_END = "（「『【〈《〔｛‘“"


def register_fonts() -> None:
    """Windows 同梱の游ゴシックを埋め込む。無い場合はメイリオへ退避する。"""
    candidates = [
        (r"C:\Windows\Fonts\YuGothB.ttc", r"C:\Windows\Fonts\YuGothM.ttc"),
        (r"C:\Windows\Fonts\meiryob.ttc", r"C:\Windows\Fonts\meiryo.ttc"),
        (r"C:\Windows\Fonts\msgothic.ttc", r"C:\Windows\Fonts\msgothic.ttc"),
    ]
    for bold, regular in candidates:
        try:
            pdfmetrics.registerFont(TTFont(FONT_B, bold, subfontIndex=0))
            pdfmetrics.registerFont(TTFont(FONT_R, regular, subfontIndex=0))
            return
        except Exception:  # noqa: BLE001 - 次の候補を試す
            continue
    raise RuntimeError("日本語フォントが見つかりませんでした")


# 英数字・URLなど、途中で改行してはいけない文字の集合
_ASCII_WORD = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "._-/:@#?&=+%~"
)


def _tokenize(text: str) -> list[str]:
    """行分割の最小単位に分ける。

    日本語は1文字ずつ、英単語やURLは1かたまりとして扱う。こうしないと
    「VALORANT」が行末で分断されてしまう。
    """
    tokens: list[str] = []
    buf = ""
    for ch in text:
        if ch in _ASCII_WORD:
            buf += ch
            continue
        if buf:
            tokens.append(buf)
            buf = ""
        tokens.append(ch)
    if buf:
        tokens.append(buf)
    return tokens


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    """日本語と英単語が混在する文字列を幅に合わせて折り返す。

    英単語・URLは途中で切らない。約物の行頭・行末禁則にも簡易対応する。
    """
    lines: list[str] = []
    for raw in text.split("\n"):
        if not raw:
            lines.append("")
            continue
        line = ""
        for token in _tokenize(raw):
            if pdfmetrics.stringWidth(line + token, font, size) <= width:
                line += token
                continue
            # 行頭に置けない約物は前の行にぶら下げる
            if token in NO_LINE_START and line:
                lines.append(line + token)
                line = ""
                continue
            # 行末に置けない約物は次の行へ送る
            if line and line[-1] in NO_LINE_END:
                lines.append(line[:-1])
                line = line[-1]
            if line:
                lines.append(line)
                line = ""
            # 単体で幅を超える長い英単語・URLは文字単位で折る
            if pdfmetrics.stringWidth(token, font, size) > width:
                for ch in token:
                    if pdfmetrics.stringWidth(line + ch, font, size) <= width:
                        line += ch
                    else:
                        lines.append(line)
                        line = ch
            else:
                line = token
        if line:
            lines.append(line)
    return lines


@dataclass
class TocEntry:
    number: str
    title: str
    page: int
    level: int = 1


class Doc:
    """1冊分の状態（現在位置・ページ番号・目次）を持つ組版コンテキスト。"""

    def __init__(self, path: str, doc_title: str,
                 header_title: str | None = None) -> None:
        register_fonts()
        self.path = path
        self.doc_title = doc_title
        # 各ページ上部に出す見出し（製品名を含めた表記にする）
        self.header_title = header_title or doc_title
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle(doc_title)
        self.c.setAuthor("AXELIA")
        self.page = 1
        self.y = PAGE_H - MARGIN_TOP
        self.toc_entries: list[TocEntry] = []
        self._chrome = False        # ヘッダを描くか（表紙・目次では描かない）
        self._total_pages = 0       # 2パス目で確定させる

    # ── ページ管理 ──────────────────────────────────────────────────────────
    def _draw_chrome(self) -> None:
        if not self._chrome:
            return
        c = self.c
        c.setFont(FONT_R, 8)
        c.setFillColor(MUTED)
        c.drawString(MARGIN_X, PAGE_H - MARGIN_TOP + 26, self.header_title)
        total = self._total_pages or self.page
        c.drawRightString(
            PAGE_W - MARGIN_X, PAGE_H - MARGIN_TOP + 26, f"{self.page} / {total}"
        )
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(
            MARGIN_X, PAGE_H - MARGIN_TOP + 18,
            PAGE_W - MARGIN_X, PAGE_H - MARGIN_TOP + 18,
        )

    def new_page(self) -> None:
        self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MARGIN_TOP
        self._draw_chrome()

    def need(self, height: float) -> None:
        """残り高さが足りなければ改ページする。"""
        if self.y - height < MARGIN_BOTTOM:
            self.new_page()

    def space(self, h: float) -> None:
        self.y -= h

    # ── 表紙 ────────────────────────────────────────────────────────────────
    def title_page(self, product: str, tagline: str, description: str,
                   version: str, date: str, contact: str) -> None:
        c = self.c
        # 上部の帯
        c.setFillColor(HexColor("#0f1b33"))
        c.rect(0, PAGE_H - 250, PAGE_W, 250, stroke=0, fill=1)
        # ロゴマーク
        c.setFillColor(VALORANT)
        c.roundRect(MARGIN_X, PAGE_H - 150, 46, 46, 10, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 26)
        c.drawCentredString(MARGIN_X + 23, PAGE_H - 139, "A")
        # eyebrow
        c.setFont(FONT_B, 10)
        c.setFillColor(HexColor("#8fb0ff"))
        c.drawString(MARGIN_X + 60, PAGE_H - 118, "O P E R A T I O N   M A N U A L")
        c.setFont(FONT_R, 11)
        c.setFillColor(HexColor("#c8d4ec"))
        c.drawString(MARGIN_X + 60, PAGE_H - 135, tagline)

        # タイトル
        y = PAGE_H - 320
        c.setFillColor(INK)
        c.setFont(FONT_B, 30)
        c.drawString(MARGIN_X, y, product)
        y -= 40
        c.setFont(FONT_B, 20)
        c.setFillColor(BRAND)
        c.drawString(MARGIN_X, y, self.doc_title)

        # 説明
        y -= 46
        c.setFillColor(BODY)
        for line in wrap(description, FONT_R, 10.5, CONTENT_W * 0.82):
            c.setFont(FONT_R, 10.5)
            c.drawString(MARGIN_X, y, line)
            y -= 18

        # 罫線 + メタ情報
        y -= 24
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)
        y -= 26
        c.setFont(FONT_R, 10)
        c.setFillColor(MUTED)
        c.drawString(MARGIN_X, y, f"バージョン {version}   |   {date}   |   AXELIA")
        y -= 20
        c.drawString(MARGIN_X, y, f"お問い合わせ: {contact}")

        self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MARGIN_TOP

    # ── 見出し ──────────────────────────────────────────────────────────────
    def h1(self, number: str, title: str) -> None:
        # 見出しだけがページ末尾に取り残されないよう、続く本文の分も確保する
        self.need(190)
        self.space(14)
        c = self.c
        # 番号バッジ
        c.setFillColor(BRAND)
        c.roundRect(MARGIN_X, self.y - 24, 30, 30, 6, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 15)
        c.drawCentredString(MARGIN_X + 15, self.y - 15, number)
        # タイトル
        c.setFillColor(INK)
        c.setFont(FONT_B, 19)
        c.drawString(MARGIN_X + 42, self.y - 15, title)
        self.space(38)
        c.setStrokeColor(BRAND)
        c.setLineWidth(2)
        c.line(MARGIN_X, self.y, MARGIN_X + 46, self.y)
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(MARGIN_X + 46, self.y, PAGE_W - MARGIN_X, self.y)
        self.space(22)
        self.toc_entries.append(TocEntry(number, title, self.page, 1))

    def h2(self, number: str, title: str) -> None:
        self.need(115)
        self.space(10)
        c = self.c
        c.setFillColor(BRAND)
        c.setFont(FONT_B, 12)
        c.drawString(MARGIN_X, self.y, number)
        w = pdfmetrics.stringWidth(number, FONT_B, 12)
        c.setFillColor(INK)
        c.setFont(FONT_B, 13.5)
        c.drawString(MARGIN_X + w + 10, self.y, title)
        self.space(20)
        self.toc_entries.append(TocEntry(number, title, self.page, 2))

    # ── 本文 ────────────────────────────────────────────────────────────────
    def para(self, text: str, size: float = 10, gap: float = 12) -> None:
        lines = wrap(text, FONT_R, size, CONTENT_W)
        for line in lines:
            self.need(size + 7)
            self.c.setFont(FONT_R, size)
            self.c.setFillColor(BODY)
            self.c.drawString(MARGIN_X, self.y, line)
            self.space(size + 7)
        self.space(gap - 7)

    def bullets(self, items: list[str], size: float = 10) -> None:
        for item in items:
            lines = wrap(item, FONT_R, size, CONTENT_W - 16)
            for i, line in enumerate(lines):
                self.need(size + 7)
                if i == 0:
                    self.c.setFillColor(BRAND)
                    self.c.circle(MARGIN_X + 4, self.y + 3.4, 2, stroke=0, fill=1)
                self.c.setFont(FONT_R, size)
                self.c.setFillColor(BODY)
                self.c.drawString(MARGIN_X + 16, self.y, line)
                self.space(size + 7)
        self.space(6)

    def steps(self, items: list[str], size: float = 10) -> None:
        """丸番号つきの手順。"""
        for n, item in enumerate(items, 1):
            lines = wrap(item, FONT_R, size, CONTENT_W - 30)
            block_h = len(lines) * (size + 7)
            self.need(block_h + 4)
            top = self.y
            self.c.setFillColor(BRAND_PALE)
            self.c.circle(MARGIN_X + 8, top + 3.2, 8.5, stroke=0, fill=1)
            self.c.setFillColor(BRAND_DARK)
            self.c.setFont(FONT_B, 9)
            self.c.drawCentredString(MARGIN_X + 8, top + 0.4, str(n))
            for line in lines:
                self.c.setFont(FONT_R, size)
                self.c.setFillColor(BODY)
                self.c.drawString(MARGIN_X + 26, self.y, line)
                self.space(size + 7)
            self.space(3)
        self.space(6)

    # ── 表 ──────────────────────────────────────────────────────────────────
    def table(self, headers: list[str], rows: list[list[str]],
              widths: list[float] | None = None, size: float = 9) -> None:
        n = len(headers)
        if widths is None:
            widths = [CONTENT_W / n] * n
        else:
            total = sum(widths)
            widths = [w / total * CONTENT_W for w in widths]

        pad = 6
        line_h = size + 5

        def row_height(cells: list[str]) -> float:
            return max(
                len(wrap(str(cell), FONT_R, size, widths[i] - pad * 2)) * line_h
                for i, cell in enumerate(cells)
            ) + pad * 2

        header_h = row_height(headers)
        self.need(header_h + row_height(rows[0]) if rows else header_h)

        def draw_row(cells: list[str], bold: bool, bg) -> None:
            h = row_height(cells)
            self.need(h)
            top = self.y + line_h - 2
            if bg is not None:
                self.c.setFillColor(bg)
                self.c.rect(MARGIN_X, top - h, CONTENT_W, h, stroke=0, fill=1)
            x = MARGIN_X
            for i, cell in enumerate(cells):
                ty = top - pad - size
                for line in wrap(str(cell), FONT_R, size, widths[i] - pad * 2):
                    self.c.setFont(FONT_B if bold else FONT_R, size)
                    self.c.setFillColor(INK if bold else BODY)
                    self.c.drawString(x + pad, ty, line)
                    ty -= line_h
                x += widths[i]
            self.c.setStrokeColor(LINE)
            self.c.setLineWidth(0.6)
            self.c.line(MARGIN_X, top - h, PAGE_W - MARGIN_X, top - h)
            self.y -= h

        draw_row(headers, True, PANEL)
        for r in rows:
            draw_row(r, False, None)
        self.space(14)

    # ── 囲み ────────────────────────────────────────────────────────────────
    def callout(self, label: str, text: str, kind: str = "info") -> None:
        palette = {
            "info": (BRAND_PALE, BRAND, BRAND_DARK),
            "warn": (WARN_BG, WARN_LINE, HexColor("#8a5a00")),
            "ok": (OK_BG, OK_LINE, HexColor("#0f6b45")),
        }[kind]
        bg, bar, fg = palette
        size = 9.5
        inner_w = CONTENT_W - 34
        lines = wrap(text, FONT_R, size, inner_w)
        h = 22 + len(lines) * (size + 6) + 10
        self.need(h + 6)
        top = self.y + size
        self.c.setFillColor(bg)
        self.c.roundRect(MARGIN_X, top - h, CONTENT_W, h, 5, stroke=0, fill=1)
        self.c.setFillColor(bar)
        self.c.rect(MARGIN_X, top - h, 3.5, h, stroke=0, fill=1)
        self.c.setFillColor(fg)
        self.c.setFont(FONT_B, 9.5)
        self.c.drawString(MARGIN_X + 16, top - 16, label)
        ty = top - 32
        for line in lines:
            self.c.setFont(FONT_R, size)
            self.c.setFillColor(BODY)
            self.c.drawString(MARGIN_X + 16, ty, line)
            ty -= size + 6
        self.y = top - h - 14

    def figure(self, caption: str, image: str | None = None,
               max_h: float = 300, width: float | None = None) -> None:
        """画面キャプチャを貼る。image を省いた場合は貼り位置の指示枠を描く。

        画像は紙面幅に収まるよう縮小し、縦に長い場合は max_h に合わせる。
        小さく写ってしまう図は width で幅を指定して拡大できる。
        """
        img = Path(image) if image else None
        if img and not img.is_absolute():
            img = Path(__file__).parent / img

        if img and img.exists():
            reader = ImageReader(str(img))
            iw, ih = reader.getSize()
            w = min(width or CONTENT_W, CONTENT_W)
            h = ih * (w / iw)
            if h > max_h:                      # 縦長すぎる図は高さで抑える
                h = max_h
                w = iw * (h / ih)
            reader = _fit_raster(img, w)
            self.need(h + 26)
            top = self.y
            x = MARGIN_X + (CONTENT_W - w) / 2
            self.c.drawImage(reader, x, top - h, width=w, height=h,
                             mask="auto")
            # 背景が濃い画面なので、細い枠を付けて紙面から浮かせる
            self.c.setStrokeColor(LINE)
            self.c.setLineWidth(0.6)
            self.c.rect(x, top - h, w, h, stroke=1, fill=0)
            self.y = top - h - 13
        else:
            h = 92
            self.need(h + 24)
            top = self.y
            self.c.setFillColor(PANEL)
            self.c.setStrokeColor(LINE)
            self.c.setLineWidth(0.8)
            self.c.roundRect(MARGIN_X, top - h, CONTENT_W, h, 5, stroke=1, fill=1)
            self.c.setFillColor(MUTED)
            self.c.setFont(FONT_R, 9)
            self.c.drawCentredString(PAGE_W / 2, top - h / 2 - 3, "［ 画面キャプチャ ］")
            self.y = top - h - 14

        self.c.setFont(FONT_R, 8.5)
        self.c.setFillColor(MUTED)
        for line in wrap(f"▲ {caption}", FONT_R, 8.5, CONTENT_W):
            self.c.drawString(MARGIN_X, self.y, line)
            self.y -= 12
        self.space(12)

    def faq(self, question: str, answer: str) -> None:
        size = 9.5
        q_lines = wrap(question, FONT_B, size + 0.5, CONTENT_W - 24)
        a_lines = wrap(answer, FONT_R, size, CONTENT_W - 24)
        self.need(len(q_lines) * 15 + len(a_lines) * 15 + 22)
        for i, line in enumerate(q_lines):
            self.c.setFont(FONT_B, size + 0.5)
            self.c.setFillColor(BRAND_DARK)
            if i == 0:
                self.c.drawString(MARGIN_X, self.y, "Q.")
            self.c.setFillColor(INK)
            self.c.drawString(MARGIN_X + 20, self.y, line)
            self.space(15)
        for i, line in enumerate(a_lines):
            self.c.setFont(FONT_R, size)
            if i == 0:
                self.c.setFillColor(MUTED)
                self.c.setFont(FONT_B, size)
                self.c.drawString(MARGIN_X, self.y, "A.")
                self.c.setFont(FONT_R, size)
            self.c.setFillColor(BODY)
            self.c.drawString(MARGIN_X + 20, self.y, line)
            self.space(15)
        self.space(8)

    # ── 目次 ────────────────────────────────────────────────────────────────
    def render_toc(self, entries: list[TocEntry]) -> None:
        self.c.setFont(FONT_B, 22)
        self.c.setFillColor(INK)
        self.c.drawString(MARGIN_X, self.y - 10, "目次")
        self.space(44)
        for e in entries:
            self.need(22)
            if e.level == 1:
                self.c.setFont(FONT_B, 11)
                self.c.setFillColor(BRAND)
                self.c.drawString(MARGIN_X, self.y, e.number)
                self.c.setFillColor(INK)
                self.c.drawString(MARGIN_X + 26, self.y, e.title)
                indent = 0
            else:
                self.c.setFont(FONT_R, 9.5)
                self.c.setFillColor(MUTED)
                self.c.drawString(MARGIN_X + 26, self.y, e.number)
                self.c.setFillColor(BODY)
                self.c.drawString(MARGIN_X + 62, self.y, e.title)
                indent = 26
            self.c.setFont(FONT_R, 9.5)
            self.c.setFillColor(MUTED)
            self.c.drawRightString(PAGE_W - MARGIN_X, self.y, str(e.page))
            # リーダー罫
            self.c.setStrokeColor(HexColor("#e8edf6"))
            self.c.setLineWidth(0.5)
            self.c.line(MARGIN_X + 200 + indent, self.y + 3,
                        PAGE_W - MARGIN_X - 18, self.y + 3)
            self.space(21 if e.level == 1 else 18)

    def enable_chrome(self) -> None:
        self._chrome = True
        self._draw_chrome()

    def save(self) -> None:
        self.c.save()
