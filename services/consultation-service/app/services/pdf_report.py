"""就诊报告 PDF 生成服务。"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_CANDIDATE_PATHS = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]


def _register_builtin_cjk_font() -> str | None:
    """注册 ReportLab 自带的 CJK 字体，避免容器缺字时退回 Helvetica。"""
    builtin_font_name = "STSong-Light"
    try:
        pdfmetrics.getFont(builtin_font_name)
    except KeyError:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(builtin_font_name))
        except Exception:
            return None
    return builtin_font_name


def _register_chinese_font() -> str:
    """注册中文字体，返回可用的字体名称。"""
    for index, path in enumerate(FONT_CANDIDATE_PATHS):
        try:
            if not path.exists():
                continue
            font_name = f"ChineseFont{index}"
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
        except Exception:
            continue

    builtin_font_name = _register_builtin_cjk_font()
    if builtin_font_name:
        return builtin_font_name

    return "Helvetica"


FONT_NAME = _register_chinese_font()

COLOR_PRIMARY = colors.HexColor("#4F46E5")
COLOR_PRIMARY_DARK = colors.HexColor("#312E81")
COLOR_PRIMARY_LIGHT = colors.HexColor("#EEF2FF")
COLOR_PANEL = colors.HexColor("#F8FAFC")
COLOR_PANEL_ALT = colors.HexColor("#F1F5F9")
COLOR_TEXT = colors.HexColor("#0F172A")
COLOR_MUTED = colors.HexColor("#475569")
COLOR_BORDER = colors.HexColor("#CBD5E1")
COLOR_SUCCESS = colors.HexColor("#059669")
COLOR_WARNING = colors.HexColor("#D97706")
COLOR_DANGER = colors.HexColor("#DC2626")

STATUS_LABELS = {
    "draft": "草稿",
    "in_progress": "进行中",
    "paused": "已暂停",
    "completed": "已完成",
}

FLOW_LABELS = {
    "consultation": "问诊阶段",
    "assessment": "量表评估阶段",
}

TIMELINE_LABELS = {
    "encounter_created": "就诊创建",
    "encounter_started": "就诊开始",
    "consultation_created": "问诊创建",
    "consultation_started": "开始问诊",
    "consultation_completed": "完成问诊",
    "assessment_created": "量表创建",
    "assessment_started": "开始量表评估",
    "assessment_completed": "完成量表评估",
    "encounter_completed": "就诊完成",
}

CONSULTATION_SECTION_DEFINITIONS = (
    ("chief_complaint_stage_summary", "主诉阶段摘要"),
    ("symptom_screening_stage_summary", "症状筛查阶段摘要"),
    ("high_risk_screening_stage_summary", "高风险筛查阶段摘要"),
    ("digital_human_consultation_summary", "整体问诊总结"),
)


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "hero_kicker": ParagraphStyle(
            "HeroKicker",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#C7D2FE"),
        ),
        "hero_title": ParagraphStyle(
            "HeroTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=28,
            textColor=colors.white,
            spaceAfter=2 * mm,
        ),
        "hero_body": ParagraphStyle(
            "HeroBody",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            textColor=colors.HexColor("#E2E8F0"),
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=18,
            textColor=COLOR_PRIMARY_DARK,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        ),
        "card_title": ParagraphStyle(
            "CardTitle",
            parent=base["Heading3"],
            fontName=FONT_NAME,
            fontSize=11,
            leading=15,
            textColor=COLOR_TEXT,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            textColor=COLOR_TEXT,
        ),
        "body_muted": ParagraphStyle(
            "BodyMuted",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=14,
            textColor=COLOR_MUTED,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=12,
            textColor=COLOR_MUTED,
        ),
        "value": ParagraphStyle(
            "Value",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=18,
            textColor=COLOR_TEXT,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
        "badge": ParagraphStyle(
            "Badge",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=11,
            textColor=colors.white,
            alignment=1,
        ),
    }


def _ensure_json_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_json_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_datetime(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(iso)


def _paragraph(text: str | None, style: ParagraphStyle) -> Paragraph:
    normalized = escape(text or "—").replace("\n", "<br/>")
    return Paragraph(normalized, style)


def _format_field_label(key: str) -> str:
    normalized = key.replace("_", " ").replace("-", " ").strip()
    return normalized.title() if normalized else key


def _format_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_format_value(item) for item in value]
        normalized = [part for part in parts if part]
        return "；".join(normalized) if normalized else None
    if isinstance(value, dict):
        parts: list[str] = []
        for nested_key, nested_value in value.items():
            nested_text = _format_value(nested_value)
            if nested_text:
                parts.append(f"{_format_field_label(str(nested_key))}: {nested_text}")
        return "；".join(parts) if parts else None
    return str(value)


def _format_risk_flags(flags: list[Any]) -> str:
    normalized: list[str] = []
    for item in flags:
        if isinstance(item, dict):
            normalized.append(
                _string(item.get("label"))
                or _string(item.get("flag"))
                or "未命名标记"
            )
        else:
            text = _string(item)
            if text:
                normalized.append(text)
    return "、".join(normalized) if normalized else "无明显风险标记"


def _flatten_record_rows(payload: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key, value in payload.items():
        text = _format_value(value)
        if text:
            rows.append((_format_field_label(str(key)), text))
    return rows


def _risk_color(level_or_label: Any) -> colors.Color:
    label = str(level_or_label or "").lower()
    if any(keyword in label for keyword in ("urgent", "high", "danger", "高", "重", "危")):
        return COLOR_DANGER
    if any(keyword in label for keyword in ("medium", "moderate", "中", "关注")):
        return COLOR_WARNING
    if any(keyword in label for keyword in ("low", "mild", "轻", "低", "正常")):
        return COLOR_SUCCESS
    return COLOR_PRIMARY


def _build_card(content: Any, *, width: float = 170 * mm, background: colors.Color = COLOR_PANEL) -> Table:
    card = Table([[content]], colWidths=[width])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return card


def _build_badge(text: str, color: colors.Color, styles: dict[str, ParagraphStyle]) -> Table:
    badge = Table([[_paragraph(text, styles["badge"])]], colWidths=[34 * mm])
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return badge


def _build_metric_cell(
    label: str,
    value: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    return _build_card(
        [_paragraph(label, styles["label"]), Spacer(1, 1.5 * mm), _paragraph(value, styles["metric_value"])],
        width=81 * mm,
        background=colors.white,
    )


def _build_score_bar(
    *,
    score: float | None,
    max_score: float | None,
    normalized_score: float | None,
    color: colors.Color,
) -> Drawing:
    width = 145 * mm
    height = 7 * mm
    ratio: float | None = None

    if normalized_score is not None:
        ratio = max(0.0, min(1.0, normalized_score / 100.0))
    elif score is not None and max_score and max_score > 0:
        ratio = max(0.0, min(1.0, score / max_score))

    drawing = Drawing(width, height + 6 * mm)
    drawing.add(
        Rect(
            0,
            2 * mm,
            width,
            height,
            rx=height / 2,
            ry=height / 2,
            fillColor=COLOR_PANEL_ALT,
            strokeColor=None,
        )
    )
    if ratio is not None:
        drawing.add(
            Rect(
                0,
                2 * mm,
                width * ratio,
                height,
                rx=height / 2,
                ry=height / 2,
                fillColor=color,
                strokeColor=None,
            )
        )
    label = (
        f"标准化得分 {normalized_score:.0f}/100"
        if normalized_score is not None
        else f"得分进度 {score:.0f}/{max_score:.0f}"
        if score is not None and max_score is not None
        else "得分进度待补充"
    )
    drawing.add(
        String(
            0,
            height + 3.5 * mm,
            label,
            fontName=FONT_NAME,
            fontSize=8.5,
            fillColor=COLOR_MUTED,
        )
    )
    return drawing


def _resolve_result_max_score(result: dict[str, Any]) -> float | None:
    score_details = _ensure_json_dict(result.get("score_details"))
    normalization = _ensure_json_dict(score_details.get("normalization"))
    maximum = _safe_float(normalization.get("maximum"))
    if maximum and maximum > 0:
        return maximum
    return None


def _build_section_header(
    title: str,
    styles: dict[str, ParagraphStyle],
    summary: str | None = None,
) -> list[Any]:
    header: list[Any] = [_paragraph(title, styles["section_title"])]
    if summary:
        header.append(_paragraph(summary, styles["body_muted"]))
    return header


def _build_banner(
    encounter: dict[str, Any],
    consultation: dict[str, Any],
    risk_summary: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> Table:
    risk_label = (
        _string(risk_summary.get("risk_level_label"))
        or _string(risk_summary.get("depression_severity_label"))
        or "待补充"
    )
    summary_message = (
        _string(_ensure_json_dict(risk_summary.get("front_display")).get("message"))
        or _string(consultation.get("digital_human_consultation_summary"))
        or _string(consultation.get("chief_complaint_summary"))
        or "本报告基于本轮数字问诊与量表评估结果自动生成。"
    )
    badge = _build_badge(risk_label, _risk_color(risk_label), styles)
    left_content = [
        _paragraph("抑郁数字人辅助评估系统", styles["hero_kicker"]),
        Spacer(1, 1 * mm),
        _paragraph("历史就诊报告", styles["hero_title"]),
        _paragraph(summary_message, styles["hero_body"]),
    ]
    right_content = [
        badge,
        Spacer(1, 5 * mm),
        _paragraph("报告生成时间", styles["hero_kicker"]),
        _paragraph(_format_datetime(datetime.now().isoformat()), styles["hero_body"]),
        Spacer(1, 2 * mm),
        _paragraph("就诊状态", styles["hero_kicker"]),
        _paragraph(
            STATUS_LABELS.get(str(encounter.get("status") or ""), str(encounter.get("status") or "—")),
            styles["hero_body"],
        ),
    ]
    table = Table([[left_content, right_content]], colWidths=[117 * mm, 53 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY_DARK),
                ("BOX", (0, 0), (-1, -1), 0.8, COLOR_PRIMARY_DARK),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_overview_section(
    encounter: dict[str, Any],
    consultation: dict[str, Any],
    assessment_results: list[dict[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    primary_metrics = Table(
        [
            [
                _build_metric_cell("创建时间", _format_datetime(encounter.get("created_at")), styles),
                _build_metric_cell("完成时间", _format_datetime(encounter.get("completed_at")), styles),
            ],
            [
                _build_metric_cell(
                    "数字医生",
                    _string(consultation.get("assigned_doctor_persona")) or "—",
                    styles,
                ),
                _build_metric_cell(
                    "量表数量",
                    str(len(assessment_results)),
                    styles,
                ),
            ],
        ],
        colWidths=[84 * mm, 84 * mm],
        rowHeights=[None, None],
    )
    primary_metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    detail_rows = [
        ("Encounter ID", _string(encounter.get("id")) or "—"),
        (
            "当前阶段",
            FLOW_LABELS.get(str(encounter.get("current_flow_type") or ""), str(encounter.get("current_flow_type") or "—")),
        ),
        (
            "主诉摘要",
            _string(consultation.get("chief_complaint_summary")) or "暂无主诉摘要",
        ),
    ]
    detail_table = Table(
        [
            [_paragraph(label, styles["label"]), _paragraph(value, styles["value"])]
            for label, value in detail_rows
        ],
        colWidths=[32 * mm, 138 * mm],
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), COLOR_PRIMARY_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return [
        *_build_section_header("一、就诊总览", styles, "从单次就诊视角汇总关键时间、状态与基础背景信息。"),
        primary_metrics,
        Spacer(1, 3 * mm),
        detail_table,
    ]


def _build_risk_summary_section(
    risk_summary: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    if not risk_summary:
        return []

    front_display = _ensure_json_dict(risk_summary.get("front_display"))
    risk_label = (
        _string(risk_summary.get("risk_level_label"))
        or _string(risk_summary.get("depression_severity_label"))
        or "待补充"
    )
    badge = _build_badge(risk_label, _risk_color(risk_label), styles)
    explanation = _ensure_json_dict(risk_summary.get("risk_explanation"))
    explanation_summary = _string(explanation.get("summary")) or "暂无进一步解释。"
    metric_table = Table(
        [
            [
                _build_metric_cell("风险等级", risk_label, styles),
                _build_metric_cell(
                    "综合抑郁得分",
                    f"{_safe_float(risk_summary.get('depression_score')):.2f}"
                    if _safe_float(risk_summary.get("depression_score")) is not None
                    else "—",
                    styles,
                ),
            ],
            [
                _build_metric_cell(
                    "抑郁严重程度",
                    _string(risk_summary.get("depression_severity_label"))
                    or _string(risk_summary.get("depression_severity"))
                    or "—",
                    styles,
                ),
                _build_metric_cell(
                    "人工复核",
                    "需要" if bool(risk_summary.get("requires_human_review")) else "否",
                    styles,
                ),
            ],
        ],
        colWidths=[84 * mm, 84 * mm],
    )
    metric_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    narrative_card = _build_card(
        [
            badge,
            Spacer(1, 4 * mm),
            _paragraph(
                _string(front_display.get("title")) or "综合风险结论",
                styles["card_title"],
            ),
            Spacer(1, 2 * mm),
            _paragraph(
                _string(front_display.get("message")) or explanation_summary,
                styles["body"],
            ),
            Spacer(1, 2 * mm),
            _paragraph(explanation_summary, styles["body_muted"]),
        ],
        background=COLOR_PRIMARY_LIGHT,
    )

    return [
        *_build_section_header("二、综合风险结论", styles, "输出整体风险等级、抑郁严重程度与是否需要人工复核。"),
        narrative_card,
        Spacer(1, 3 * mm),
        metric_table,
    ]


def _build_consultation_section(
    consultation: dict[str, Any],
    assessment: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    if not consultation:
        return []

    aggregate_payload = _ensure_json_dict(assessment.get("aggregate_payload"))
    summary_source = (
        _ensure_json_dict(consultation.get("scale_handoff_payload"))
        or _ensure_json_dict(assessment.get("scale_handoff_payload"))
        or _ensure_json_dict(aggregate_payload.get("source_handoff"))
    )

    sections: list[Any] = []
    for key, title in CONSULTATION_SECTION_DEFINITIONS:
        content = _string(consultation.get(key)) or _string(summary_source.get(key))
        if not content:
            continue
        sections.extend(
            [
                _build_card(
                    [
                        _paragraph(title, styles["card_title"]),
                        Spacer(1, 2 * mm),
                        _paragraph(content, styles["body"]),
                    ],
                    background=colors.white,
                ),
                Spacer(1, 2.5 * mm),
            ]
        )

    history_rows = _flatten_record_rows(
        _ensure_json_dict(consultation.get("current_history_structured_result"))
    )
    high_risk_rows = _flatten_record_rows(
        _ensure_json_dict(consultation.get("high_risk_screening_result"))
    )

    structured_rows: list[tuple[str, str]] = []
    if history_rows:
        structured_rows.extend([(f"症状筛查 / {label}", value) for label, value in history_rows])
    if high_risk_rows:
        structured_rows.extend([(f"高风险筛查 / {label}", value) for label, value in high_risk_rows])

    structured_table = None
    if structured_rows:
        structured_table = Table(
            [
                [_paragraph(label, styles["label"]), _paragraph(value, styles["value"])]
                for label, value in structured_rows
            ],
            colWidths=[46 * mm, 124 * mm],
        )
        structured_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), COLOR_PANEL_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

    content: list[Any] = [
        *_build_section_header("三、问诊摘要", styles, "汇总主诉、症状筛查、高风险筛查与整体数字问诊结论。"),
    ]
    if _string(consultation.get("chief_complaint_raw_text")):
        content.extend(
            [
                _build_card(
                    [
                        _paragraph("主诉原文", styles["card_title"]),
                        Spacer(1, 2 * mm),
                        _paragraph(
                            _string(consultation.get("chief_complaint_raw_text")),
                            styles["body"],
                        ),
                    ],
                    background=COLOR_PANEL,
                ),
                Spacer(1, 2.5 * mm),
            ]
        )

    content.extend(sections)
    if structured_table is not None:
        content.append(structured_table)

    required_scales = _ensure_json_list(
        consultation.get("required_scales") or summary_source.get("required_scales")
    )
    if required_scales:
        scale_line = "、".join(str(item) for item in required_scales if str(item).strip())
        content.extend(
            [
                Spacer(1, 2.5 * mm),
                _build_card(
                    [
                        _paragraph("建议关联量表", styles["card_title"]),
                        Spacer(1, 2 * mm),
                        _paragraph(scale_line, styles["body"]),
                    ],
                    background=COLOR_PRIMARY_LIGHT,
                ),
            ]
        )

    return content


def _build_assessment_section(
    assessment_results: list[dict[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    content = [
        *_build_section_header("四、量表评估结果", styles, "按量表展示得分、严重程度、风险标记与得分图表。"),
    ]

    if not assessment_results:
        content.append(_paragraph("本次就诊尚未形成量表评估结果。", styles["body_muted"]))
        return content

    header_row = [
        _paragraph("量表", styles["table_header"]),
        _paragraph("原始分", styles["table_header"]),
        _paragraph("换算分", styles["table_header"]),
        _paragraph("标准化", styles["table_header"]),
        _paragraph("结果解读", styles["table_header"]),
        _paragraph("风险标记", styles["table_header"]),
    ]
    summary_rows = [header_row]
    for result in assessment_results:
        summary_rows.append(
            [
                _paragraph((_string(result.get("scale_slug")) or "").upper(), styles["value"]),
                _paragraph(str(result.get("raw_score") or "—"), styles["value"]),
                _paragraph(str(result.get("derived_score") or "—"), styles["value"]),
                _paragraph(
                    f"{_safe_float(result.get('normalized_score')):.0f}"
                    if _safe_float(result.get("normalized_score")) is not None
                    else "—",
                    styles["value"],
                ),
                _paragraph(
                    _string(result.get("interpretation_label"))
                    or _string(result.get("interpretation_level"))
                    or "待补充",
                    styles["value"],
                ),
                _paragraph(
                    _format_risk_flags(_ensure_json_list(result.get("risk_flags"))),
                    styles["value"],
                ),
            ]
        )

    summary_table = Table(
        summary_rows,
        colWidths=[18 * mm, 18 * mm, 18 * mm, 18 * mm, 48 * mm, 50 * mm],
        repeatRows=1,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    content.extend([summary_table, Spacer(1, 3 * mm)])

    for result in assessment_results:
        risk_label = (
            _string(result.get("interpretation_label"))
            or _string(result.get("interpretation_level"))
            or "待补充"
        )
        max_score = _resolve_result_max_score(result)
        score_value = _safe_float(result.get("derived_score"))
        normalized_score = _safe_float(result.get("normalized_score"))
        card_content = [
            _paragraph(
                f"{(_string(result.get('scale_slug')) or '').upper()} 量表结果",
                styles["card_title"],
            ),
            Spacer(1, 1.5 * mm),
            _build_badge(risk_label, _risk_color(risk_label), styles),
            Spacer(1, 3 * mm),
            _paragraph(
                f"原始分 {result.get('raw_score') or '—'}，换算分 {result.get('derived_score') or '—'}，"
                + (
                    f"标准化得分 {normalized_score:.0f}。"
                    if normalized_score is not None
                    else "标准化得分待补充。"
                ),
                styles["body"],
            ),
            Spacer(1, 2 * mm),
            _build_score_bar(
                score=score_value,
                max_score=max_score,
                normalized_score=normalized_score,
                color=_risk_color(risk_label),
            ),
            Spacer(1, 2 * mm),
            _paragraph(
                f"风险标记：{_format_risk_flags(_ensure_json_list(result.get('risk_flags')))}",
                styles["body_muted"],
            ),
        ]
        content.extend(
            [
                _build_card(card_content, background=colors.white),
                Spacer(1, 2.5 * mm),
            ]
        )

    return content


def _build_recommendation_section(
    risk_summary: dict[str, Any],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    referral_recommendations = _ensure_json_list(
        risk_summary.get("referral_recommendations")
    )
    lifestyle_suggestions = _ensure_json_list(
        risk_summary.get("lifestyle_suggestions")
    )
    if not referral_recommendations and not lifestyle_suggestions:
        return []

    def build_list_card(title: str, items: list[Any], background: colors.Color) -> Table:
        flowables: list[Any] = [_paragraph(title, styles["card_title"])]
        for item in items:
            text = _string(item)
            if not text:
                continue
            flowables.extend(
                [
                    Spacer(1, 1.6 * mm),
                    _paragraph(f"• {text}", styles["body"]),
                ]
            )
        if len(flowables) == 1:
            flowables.extend([Spacer(1, 1.6 * mm), _paragraph("暂无建议。", styles["body_muted"])])
        return _build_card(flowables, width=81 * mm, background=background)

    content = [
        *_build_section_header("五、建议与后续行动", styles, "结合综合风险结论，输出就诊建议与生活方式建议。"),
    ]
    grid = Table(
        [
            [
                build_list_card("就诊建议", referral_recommendations, COLOR_PRIMARY_LIGHT),
                build_list_card("生活建议", lifestyle_suggestions, COLOR_PANEL),
            ]
        ],
        colWidths=[84 * mm, 84 * mm],
    )
    grid.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    content.append(grid)
    return content


def _build_timeline_section(
    timeline: list[dict[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    if not timeline:
        return []

    rows = [[_paragraph("事件", styles["table_header"]), _paragraph("时间", styles["table_header"])]]
    for event in timeline:
        rows.append(
            [
                _paragraph(
                    TIMELINE_LABELS.get(
                        str(event.get("event") or ""),
                        str(event.get("event") or "未命名事件"),
                    ),
                    styles["value"],
                ),
                _paragraph(_format_datetime(_string(event.get("at"))), styles["value"]),
            ]
        )

    table = Table(rows, colWidths=[62 * mm, 108 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return [
        *_build_section_header("六、就诊时间线", styles, "按照实际发生时间回看问诊、量表与就诊完成节点。"),
        table,
    ]


def _draw_page_decorations(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 12 * mm, A4[0] - doc.rightMargin, 12 * mm)
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(COLOR_MUTED)
    canvas.drawRightString(A4[0] - doc.rightMargin, 8 * mm, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


def generate_encounter_pdf(encounter_data: dict[str, Any]) -> bytes:
    """根据 encounter 详情数据生成 PDF 报告，返回 PDF 字节流。"""
    encounter = _ensure_json_dict(encounter_data.get("encounter", encounter_data))
    consultation = _ensure_json_dict(encounter.get("consultation"))
    assessment = _ensure_json_dict(encounter.get("assessment"))
    aggregate_payload = _ensure_json_dict(assessment.get("aggregate_payload"))
    risk_summary = _ensure_json_dict(aggregate_payload.get("risk_summary"))
    assessment_results = [
        _ensure_json_dict(item)
        for item in _ensure_json_list(encounter.get("assessment_results"))
        if isinstance(item, dict)
    ]
    timeline = [
        _ensure_json_dict(item)
        for item in _ensure_json_list(encounter.get("timeline"))
        if isinstance(item, dict)
    ]

    styles = _build_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
    )

    story: list[Any] = [
        _build_banner(encounter, consultation, risk_summary, styles),
        Spacer(1, 5 * mm),
        *_build_overview_section(encounter, consultation, assessment_results, styles),
        Spacer(1, 4 * mm),
    ]

    risk_section = _build_risk_summary_section(risk_summary, styles)
    if risk_section:
        story.extend(risk_section)
        story.append(Spacer(1, 4 * mm))

    consultation_section = _build_consultation_section(
        consultation,
        assessment,
        styles,
    )
    if consultation_section:
        story.extend(consultation_section)
        story.append(Spacer(1, 4 * mm))

    story.extend(_build_assessment_section(assessment_results, styles))
    story.append(Spacer(1, 4 * mm))

    recommendation_section = _build_recommendation_section(risk_summary, styles)
    if recommendation_section:
        story.extend(recommendation_section)
        story.append(Spacer(1, 4 * mm))

    timeline_section = _build_timeline_section(timeline, styles)
    if timeline_section:
        story.extend(timeline_section)

    doc.build(story, onFirstPage=_draw_page_decorations, onLaterPages=_draw_page_decorations)
    return buffer.getvalue()
