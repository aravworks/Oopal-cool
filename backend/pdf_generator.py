"""
MindEase — Clinical Summary PDF Generator
Generates a therapist-ready referral report using ReportLab.
Does NOT include raw chat transcripts — only aggregated insights.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# ── Colour palette ────────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor("#7B9EA6")
ACCENT    = colors.HexColor("#A89BC2")
LIGHT_BG  = colors.HexColor("#F0F4F8")
TEXT      = colors.HexColor("#2D3748")
MUTED     = colors.HexColor("#718096")
DANGER    = colors.HexColor("#E53E3E")
SUCCESS   = colors.HexColor("#38A169")


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "Title", parent=base["Normal"],
            fontSize=22, textColor=PRIMARY,
            fontName="Helvetica-Bold", spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontSize=12, textColor=MUTED,
            fontName="Helvetica", spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Normal"],
            fontSize=11, textColor=PRIMARY,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10, textColor=TEXT,
            fontName="Helvetica", leading=16, spaceAfter=4,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["Normal"],
            fontSize=9, textColor=MUTED,
            fontName="Helvetica", leading=14,
        ),
        "insight": ParagraphStyle(
            "Insight", parent=base["Normal"],
            fontSize=10, textColor=TEXT,
            fontName="Helvetica-Oblique", leading=16,
            leftIndent=12, spaceAfter=6,
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", parent=base["Normal"],
            fontSize=8, textColor=MUTED,
            fontName="Helvetica", leading=12,
            alignment=TA_CENTER,
        ),
    }
    return styles


def generate_pdf(
    user_name: str,
    condition: str,
    severity_score: int,
    assessment_answers: dict,
    mood_history: list[dict],      # [{score, logged_at}]
    sessions: list[dict],          # [{insight, mood_before, mood_after, created_at, condition}]
    top_triggers: list[str],       # extracted by Gemini
) -> bytes:
    """
    Build the clinical summary PDF and return as bytes.
    Called by POST /api/v1/report/generate
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = build_styles()
    story  = []
    W      = A4[0] - 4*cm   # usable width

    # ── Header ────────────────────────────────────────────
    story.append(Paragraph("MindEase", styles["title"]))
    story.append(Paragraph("Clinical Summary Report — Confidential", styles["subtitle"]))
    story.append(Paragraph(
        f"Prepared for: {user_name}  ·  Generated: {datetime.now().strftime('%d %B %Y')}",
        styles["muted"],
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width=W, color=PRIMARY, thickness=1.5))
    story.append(Spacer(1, 10))

    # ── Disclaimer ────────────────────────────────────────
    story.append(Paragraph(
        "This document is an AI-assisted self-report summary. It is not a clinical diagnosis. "
        "Raw conversation transcripts are NOT included to protect privacy. "
        "This report is intended to assist a licensed mental health professional during initial intake.",
        styles["disclaimer"],
    ))
    story.append(Spacer(1, 14))

    # ── Section 1: Patient Overview ───────────────────────
    story.append(Paragraph("1. Patient Overview", styles["section"]))
    overview_data = [
        ["Name",             user_name],
        ["Primary Condition", condition.title()],
        ["Severity Score",   f"{severity_score} / 10"],
        ["Sessions Completed", str(len(sessions))],
        ["Report Date",      datetime.now().strftime("%d %B %Y")],
    ]
    overview_table = Table(overview_data, colWidths=[5*cm, W - 5*cm])
    overview_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("FONTNAME",    (0, 0), (0, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1),  MUTED),
        ("TEXTCOLOR",   (1, 0), (1, -1),  TEXT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 10))

    # ── Section 2: Initial Assessment ────────────────────
    story.append(Paragraph("2. Initial Self-Assessment", styles["section"]))
    for q, a in assessment_answers.items():
        story.append(Paragraph(f"<b>Q:</b> {q}", styles["body"]))
        story.append(Paragraph(f"<b>A:</b> {a}", styles["insight"]))
    story.append(Spacer(1, 10))

    # ── Section 3: Mood Trend ─────────────────────────────
    story.append(Paragraph("3. Mood Trend (Last 30 Days)", styles["section"]))
    if mood_history:
        avg_mood  = sum(m["score"] for m in mood_history) / len(mood_history)
        low_days  = sum(1 for m in mood_history if m["score"] <= 2)
        high_days = sum(1 for m in mood_history if m["score"] >= 4)
        trend_data = [
            ["Data Point",      "Value"],
            ["Days tracked",    str(len(mood_history))],
            ["Average mood",    f"{avg_mood:.1f} / 5"],
            ["Low mood days",   f"{low_days} days (score ≤ 2)"],
            ["High mood days",  f"{high_days} days (score ≥ 4)"],
        ]
        trend_table = Table(trend_data, colWidths=[6*cm, W - 6*cm])
        trend_table.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (-1, -1),  "Helvetica"),
            ("FONTNAME",     (0, 0), (-1, 0),   "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1),  10),
            ("BACKGROUND",   (0, 0), (-1, 0),   PRIMARY),
            ("TEXTCOLOR",    (0, 0), (-1, 0),   colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("TOPPADDING",   (0, 0), (-1, -1),  6),
            ("BOTTOMPADDING",(0, 0), (-1, -1),  6),
            ("LEFTPADDING",  (0, 0), (-1, -1),  10),
            ("GRID",         (0, 0), (-1, -1),  0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(trend_table)
    else:
        story.append(Paragraph("No mood data recorded yet.", styles["muted"]))
    story.append(Spacer(1, 10))

    # ── Section 4: Top Triggers ───────────────────────────
    story.append(Paragraph("4. Recurring Themes & Triggers", styles["section"]))
    story.append(Paragraph(
        "The following themes appeared most frequently across sessions "
        "(identified by AI analysis — no raw conversation content is included):",
        styles["muted"],
    ))
    story.append(Spacer(1, 6))
    for i, trigger in enumerate(top_triggers, 1):
        story.append(Paragraph(f"{i}. {trigger}", styles["body"]))
    story.append(Spacer(1, 10))

    # ── Section 5: Session Insights ───────────────────────
    story.append(Paragraph("5. Key Session Insights", styles["section"]))
    story.append(Paragraph(
        "These are the patient's own words — insights they arrived at during AI-guided "
        "cognitive therapy sessions:",
        styles["muted"],
    ))
    story.append(Spacer(1, 6))
    for s in sessions:
        if s.get("insight"):
            date_str = s.get("created_at", "")[:10]
            mood_delta = (s.get("mood_after", 3) or 3) - (s.get("mood_before", 3) or 3)
            delta_str  = f"+{mood_delta}" if mood_delta > 0 else str(mood_delta)
            story.append(KeepTogether([
                Paragraph(
                    f"<b>{date_str}</b>  ·  Mood shift: {delta_str}",
                    styles["muted"],
                ),
                Paragraph(f'"{s["insight"]}"', styles["insight"]),
                Spacer(1, 4),
            ]))
    story.append(Spacer(1, 10))

    # ── Section 6: Referral Note ──────────────────────────
    story.append(HRFlowable(width=W, color=colors.HexColor("#E2E8F0"), thickness=1))
    story.append(Spacer(1, 8))
    story.append(Paragraph("6. Referral Note", styles["section"]))
    story.append(Paragraph(
        f"{user_name} has self-referred for professional mental health support after completing "
        f"{len(sessions)} AI-assisted cognitive therapy sessions on MindEase. They present with "
        f"{condition}-related concerns rated {severity_score}/10 severity. "
        f"They have demonstrated willingness to engage in self-reflection and have shown "
        f"{'improving' if any((s.get('mood_after',0) or 0) > (s.get('mood_before',0) or 0) for s in sessions) else 'variable'} "
        f"mood patterns across sessions. "
        f"This document is provided to reduce initial diagnostic intake time. "
        f"Formal clinical assessment is required.",
        styles["body"],
    ))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Generated by MindEase · Not a substitute for clinical diagnosis · "
        "For crisis support: Tele-MANAS 14416",
        styles["disclaimer"],
    ))

    doc.build(story)
    return buffer.getvalue()
