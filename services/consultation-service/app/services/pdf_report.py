"""就诊报告 PDF 生成服务。"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _register_chinese_font() -> str:
    """注册中文字体，返回可用的字体名称。"""
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont("ChineseFont", path))
            return "ChineseFont"
        except Exception:
            continue
    return "Helvetica"


FONT_NAME = _register_chinese_font()

COLOR_PRIMARY = colors.HexColor("#4F46E5")
COLOR_SUCCESS = colors.HexColor("#059669")
COLOR_WARNING = colors.HexColor("#D97706")
COLOR_DANGER = colors.HexColor("#DC2626")
COLOR_TEXT = colors.HexColor("#1E293B")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#E2E8F0")

STATUS_LABELS = {
    "draft": "草稿",
    "in_progress": "进行中",
    "paused": "已暂停",
    "completed": "已完成",
}


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName=FONT_NAME,
            fontSize=20, textColor=COLOR_PRIMARY, spaceAfter=6 * mm,
        ),
        "heading": ParagraphStyle(
            "Heading", parent=base["Heading2"], fontName=FONT_NAME,
            fontSize=14, textColor=COLOR_PRIMARY, spaceBefore=6 * mm, spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=10, textColor=COLOR_TEXT, leading=14,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=9, textColor=COLOR_MUTED,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=9, textColor=COLOR_MUTED,
        ),
        "value": ParagraphStyle(
            "Value", parent=base["Normal"], fontName=FONT_NAME,
            fontSize=10, textColor=COLOR_TEXT,
        ),
    }


def _format_datetime(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return str(iso)


def generate_encounter_pdf(encounter_data: dict[str, Any]) -> bytes:
    """根据 encounter 详情数据生成 PDF 报告，返回 PDF 字节流。"""
    encounter = encounter_data.get("encounter", encounter_data)
    styles = _build_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    story: list[Any] = []

    # 标题
    story.append(Paragraph("就诊报告", styles["title"]))
    story.append(Paragraph(
        f"报告生成时间：{_format_datetime(datetime.now().isoformat())}",
        styles["muted"],
    ))
    story.append(Spacer(1, 4 * mm))

    # 就诊信息
    story.append(Paragraph("就诊信息", styles["heading"]))
    status = encounter.get("status", "")
    info_data = [
        [Paragraph("就诊时间", styles["label"]), Paragraph(_format_datetime(encounter.get("created_at")), styles["value"])],
        [Paragraph("就诊状态", styles["label"]), Paragraph(STATUS_LABELS.get(status, status), styles["value"])],
        [Paragraph("就诊阶段", styles["label"]), Paragraph(
            "量表评估" if encounter.get("current_flow_type") == "assessment" else "问诊", styles["value"],
        )],
    ]
    consultation = encounter.get("consultation")
    if consultation:
        info_data.append([Paragraph("主诉摘要", styles["label"]), Paragraph(
            consultation.get("chief_complaint_summary") or "暂无摘要", styles["value"],
        )])
        info_data.append([Paragraph("医生", styles["label"]), Paragraph(
            consultation.get("assigned_doctor_persona") or "—", styles["value"],
        )])

    info_table = Table(info_data, colWidths=[30 * mm, 130 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLOR_BG_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)

    # 评估结果
    assessment_results = encounter.get("assessment_results", [])
    if assessment_results:
        story.append(Paragraph("评估结果", styles["heading"]))
        result_data = [[
            Paragraph("量表", styles["label"]),
            Paragraph("得分", styles["label"]),
            Paragraph("解读", styles["label"]),
            Paragraph("风险", styles["label"]),
        ]]
        for r in assessment_results:
            risk_flags = r.get("risk_flags") or []
            risk_text = f"{len(risk_flags)} 个标记" if risk_flags else "无"
            result_data.append([
                Paragraph(r.get("scale_slug", "").upper(), styles["value"]),
                Paragraph(str(r.get("raw_score", "—")), styles["value"]),
                Paragraph(r.get("interpretation_label") or "—", styles["value"]),
                Paragraph(risk_text, styles["value"]),
            ])
        result_table = Table(result_data, colWidths=[30 * mm, 25 * mm, 60 * mm, 45 * mm])
        result_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(result_table)
    else:
        story.append(Paragraph("评估结果", styles["heading"]))
        story.append(Paragraph("本次就诊尚未进入量表评估阶段。", styles["muted"]))

    # 问诊摘要
    if consultation:
        story.append(Paragraph("问诊摘要", styles["heading"]))
        story.append(Paragraph(consultation.get("chief_complaint_summary") or "暂无摘要", styles["body"]))

    # 时间线
    timeline = encounter.get("timeline", [])
    if timeline:
        story.append(Paragraph("就诊时间线", styles["heading"]))
        event_labels = {
            "encounter_created": "就诊创建", "encounter_started": "就诊开始",
            "consultation_created": "问诊创建", "consultation_started": "开始问诊",
            "consultation_completed": "完成问诊", "assessment_created": "量表创建",
            "assessment_started": "开始量表评估", "assessment_completed": "完成量表评估",
            "encounter_completed": "就诊完成",
        }
        timeline_data = [[Paragraph("事件", styles["label"]), Paragraph("时间", styles["label"])]]
        for event in timeline:
            timeline_data.append([
                Paragraph(event_labels.get(event.get("event", ""), event.get("event", "")), styles["value"]),
                Paragraph(_format_datetime(event.get("at")), styles["value"]),
            ])
        timeline_table = Table(timeline_data, colWidths=[60 * mm, 100 * mm])
        timeline_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(timeline_table)

    doc.build(story)
    return buffer.getvalue()
