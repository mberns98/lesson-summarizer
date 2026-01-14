from __future__ import annotations

from io import BytesIO
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.units import cm
from reportlab.lib import enums


def markdown_to_pdf_bytes(md: str, *, title: str = "Resumen") -> bytes:
    """
    Convert a subset of Markdown to PDF bytes.
    Supports:
      - Headings: #, ##, ###
      - Bullets: "- " or "* "
      - Paragraphs
      - Horizontal separators '---' (rendered as spacing)
    """
    md = (md or "").strip()

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], spaceAfter=12)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceAfter=10)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], spaceAfter=8)
    h4 = ParagraphStyle("H4", parent=styles["Heading3"], fontSize=11, spaceAfter=6)
    h5 = ParagraphStyle("H5", parent=styles["Heading3"], fontSize=10, spaceAfter=5)
    h6 = ParagraphStyle("H6", parent=styles["Heading3"], fontSize=9, spaceAfter=4)

    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        leading=14,
        alignment=enums.TA_JUSTIFY,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
    )

    story = []
    raw_lines = md.splitlines()
    lines = []
    for ln in raw_lines:
        s = ln.rstrip()
        s = s.replace("• ", "- ").replace("– ", "- ").replace("— ", "- ")
        lines.append(s)


    pending_bullets: list[str] = []

    def esc(s: str) -> str:
        # Minimal escaping for ReportLab Paragraph XML-ish markup
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def md_inline_to_rl(s: str) -> str:
        """
        Convert a small subset of Markdown inline formatting to ReportLab tags.
        Robust against code blocks containing * or other markdown chars.
        """
        s = esc(s)

        # 1) extract inline code first
        code_spans: list[str] = []

        def _code_repl(match):
            code_spans.append(match.group(1))
            return f"@@CODE{len(code_spans) - 1}@@"

        s = re.sub(r"`([^`]+)`", _code_repl, s)

        # 2) bold
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

        # 3) italic (single *)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)

        # 4) restore code spans (NO formatting inside)
        for i, code in enumerate(code_spans):
            s = s.replace(
                f"@@CODE{i}@@",
                f'<font face="Courier">{code}</font>'
            )

        return s



    def flush_bullets() -> None:
        nonlocal pending_bullets
        if not pending_bullets:
            return
        story.append(
            ListFlowable(
                [ListItem(Paragraph(md_inline_to_rl(item), body)) for item in pending_bullets],
                bulletType="bullet",
                leftIndent=18,
            )
        )
        story.append(Spacer(1, 8))
        pending_bullets = []

    for raw in lines:
        line = raw.strip()

        if not line:
            flush_bullets()
            story.append(Spacer(1, 10))
            continue

        if line == "---":
            flush_bullets()
            story.append(Spacer(1, 14))
            continue

        if line.startswith(("- ", "* ")):
            pending_bullets.append(line[2:].strip())
            continue

        flush_bullets()

        if line.startswith("# "):
            story.append(Paragraph(md_inline_to_rl(line[2:]), h1))
            continue
        if line.startswith("## "):
            story.append(Paragraph(md_inline_to_rl(line[3:]), h2))
            continue
        if line.startswith("### "):
            story.append(Paragraph(md_inline_to_rl(line[4:]), h3))
            continue
        if line.startswith("#### "):
            story.append(Paragraph(md_inline_to_rl(line[5:]), h4))
            continue
        if line.startswith("##### "):
            story.append(Paragraph(md_inline_to_rl(line[6:]), h5))
            continue
        if line.startswith("###### "):
            story.append(Paragraph(md_inline_to_rl(line[7:]), h6))
            continue

        story.append(Paragraph(md_inline_to_rl(line), body))


    flush_bullets()
    doc.build(story)
    return buf.getvalue()
