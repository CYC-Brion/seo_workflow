from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# 归档的一次性脚本（生成 Google Ads Basic Access 申请用的 PDF），路径锚定到项目根
OUTPUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "output" / "pdf" / "yusheng_google_ads_api_tool_documentation.pdf"
)


def build_document() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Yusheng SEO Keyword Planner - Tool Documentation",
        author="Yusheng",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocumentTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#17365D"),
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#52616B"),
        alignment=TA_CENTER,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=9,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.3,
        leading=12.2,
        textColor=colors.HexColor("#1F2933"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BulletCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.3,
        leading=12.2,
        leftIndent=13,
        firstLineIndent=-9,
        textColor=colors.HexColor("#1F2933"),
        spaceAfter=2,
    ))

    body = styles["BodyTextCustom"]
    heading = styles["SectionHeading"]
    bullet = styles["BulletCustom"]
    story = [
        Paragraph("Yusheng SEO Keyword Planner", styles["DocumentTitle"]),
        Paragraph("Google Ads API Tool Documentation for Basic Access Application", styles["SubTitle"]),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2F75B5")),
        Spacer(1, 6),
        Paragraph("Company and Tool Overview", heading),
        Paragraph(
            "Yusheng is a B2B manufacturer of lighting hardware and related metal components. "
            "The Yusheng SEO Keyword Planner is a private, internal Python-based workflow used "
            "to support search engine optimization and content planning for https://yushengco.com/.",
            body,
        ),
        Paragraph("Purpose and Intended Use", heading),
        Paragraph(
            "The tool uses the Google Ads API Keyword Planner to retrieve keyword ideas and "
            "planning metrics for English-language B2B searches related to lighting hardware, "
            "lamp parts, machining, sourcing, quality control, and manufacturing.",
            body,
        ),
        Paragraph("- Keyword ideas and planning metrics are used to identify relevant search topics.", bullet),
        Paragraph("- The workflow ranks and filters terms for editorial planning and website content prioritization.", bullet),
        Paragraph("- The tool does not create, edit, pause, or manage Google Ads campaigns, ad groups, ads, budgets, or bids.", bullet),
        Paragraph("API Use and Data Handling", heading),
        Paragraph(
            "The workflow is designed to use the KeywordPlanIdeaService GenerateKeywordIdeas "
            "operation for keyword research. It may use read-only account access checks during "
            "connection validation. API results are retained only in Yusheng's private local SEO "
            "workflow files for internal planning. The data is not sold, redistributed, or made "
            "available through a public application.",
            body,
        ),
        Paragraph("Access Control", heading),
        Paragraph(
            "Access is limited to Yusheng internal staff who operate the SEO workflow. The tool "
            "is not offered to the public, clients, or other third parties. OAuth credentials and "
            "API configuration are stored locally in an environment configuration file that is "
            "excluded from source control.",
            body,
        ),
        Paragraph("Architecture Summary", heading),
    ]

    data = [
        [Paragraph("Component", styles["BulletCustom"]), Paragraph("Function", styles["BulletCustom"])],
        [Paragraph("Internal Python workflow", body), Paragraph("Runs keyword expansion and SEO content planning locally.", body)],
        [Paragraph("Google OAuth", body), Paragraph("Authorizes Yusheng's own Google Ads account access.", body)],
        [Paragraph("Google Ads API", body), Paragraph("Provides Keyword Planner ideas and planning metrics.", body)],
        [Paragraph("Local SEO files", body), Paragraph("Store internal planning outputs for yushengco.com only.", body)],
    ]
    table = Table(data, colWidths=[46 * mm, 124 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7FAFC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        KeepTogether(table),
        Paragraph("Compliance Statement", heading),
        Paragraph(
            "Yusheng will use the Google Ads API only for the internal purposes described in this "
            "document and will comply with the Google Ads API Terms and Policies. This tool is not "
            "used for app conversion tracking, remarketing, or third-party campaign management.",
            body,
        ),
    ])
    document.build(story)


if __name__ == "__main__":
    build_document()
