from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "keyword_library"
SOURCE_FILE = OUTPUT_DIR / "seo_keyword_library_full.xlsx"


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_sheet_rows(workbook_path: Path, sheet_name: str) -> Tuple[List[str], List[Tuple]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    worksheet = workbook[sheet_name]
    rows = list(worksheet.iter_rows(values_only=True))
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    return headers, rows[1:]


def build_lookup(rows: List[Tuple], headers: List[str]) -> Dict[str, Dict]:
    lookup = {}
    for row in rows:
        data = {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
        keyword = str(data.get("keywords") or data.get("keyword") or "").strip()
        if keyword:
            lookup[keyword.lower()] = data
    return lookup


def make_workbook(title: str) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)
    return wb


def style_sheet(worksheet) -> None:
    header_fill = PatternFill("solid", fgColor="E36D2D")
    header_font = Font(color="FFFFFF", bold=True)
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for column_cells in worksheet.columns:
        max_len = 0
        column = column_cells[0].column_letter
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        worksheet.column_dimensions[column].width = min(max_len + 4, 56)


def cluster_direction(cluster: str) -> str:
    return {
        "core": "factory overview and conversion intent",
        "floor": "product selection and fit for floor lamp projects",
        "wall": "product selection and fit for wall lamp projects",
        "table": "product selection and fit for table lamp projects",
        "components": "structure, specs, and component applications",
        "process": "process explanation and quality control",
        "procurement": "supplier comparison and buying guide",
        "application": "use cases, project fit, and buyer scenarios",
        "trust": "proof, capability, and sourcing confidence",
    }.get(cluster, "buyer-oriented technical explainer")


def cluster_targets(cluster: str) -> str:
    return {
        "core": "Home; About Us; Services; Contact",
        "floor": "Floor Lamp Sets; Services; Contact",
        "wall": "Wall Lamp Sets; Services; Contact",
        "table": "Table Lamp Sets; Services; Contact",
        "components": "Tubes; Panels; Universal Joints; Machined Parts",
        "process": "Services; About Us; Contact",
        "procurement": "Services; RFQ; About Us; Contact",
        "application": "Home; Services; Contact",
        "trust": "About Us; Services; Contact",
    }.get(cluster, "Home; Services; Contact")


def main() -> None:
    ensure_output_dir()

    keyword_headers, keyword_rows = read_sheet_rows(SOURCE_FILE, "keywords")
    plan_headers, plan_rows = read_sheet_rows(SOURCE_FILE, "plan")

    keyword_index = {name: index for index, name in enumerate(keyword_headers)}
    plan_index = {name: index for index, name in enumerate(plan_headers)}

    keyword_lookup = build_lookup(keyword_rows, keyword_headers)

    # Split keywords into ordinary and pillar groups based on the source workbook.
    ordinary_keywords = [row for row in keyword_rows if str(row[keyword_headers.index("lane")]).strip().lower() == "ordinary"]
    pillar_keywords = [row for row in keyword_rows if str(row[keyword_headers.index("lane")]).strip().lower() == "pillar"]

    # Split plan rows by lane.
    ordinary_plan = [row for row in plan_rows if str(row[plan_headers.index("lane")]).strip().lower() == "ordinary"]
    pillar_plan = [row for row in plan_rows if str(row[plan_headers.index("lane")]).strip().lower() == "pillar"]

    # Build a longer phase-3 plan by extending the source plan with fuller direction coverage.
    phase3_plan = []
    week = 1
    phase3_order = [
        ("pillar", "lighting hardware manufacturer", "Technical Guides", [
            "manufacturing capability overview",
            "factory strength and customization scope",
            "OEM/ODM decision guide",
            "supplier comparison and sourcing fit",
        ]),
        ("pillar", "lighting hardware supplier comparison", "Industry Insights", [
            "supplier audit checklist",
            "how to compare factories on quality and lead time",
            "pricing, MOQ, and collaboration model",
        ]),
        ("pillar", "lighting hardware sourcing guide", "Industry Insights", [
            "buyer checklist for first-time sourcing",
            "how to reduce sourcing risk",
            "sample, lead time, and order process",
        ]),
        ("pillar", "OEM vs ODM lighting hardware", "Industry Insights", [
            "decision guide for product development",
            "cost, lead time, and customization comparison",
            "which model fits different buyers",
        ]),
        ("pillar", "custom lighting hardware", "Technical Guides", [
            "customization workflow from idea to sample",
            "design support and engineering collaboration",
            "prototype, approval, and production transition",
        ]),
        ("pillar", "lighting manufacturing process", "Technical Guides", [
            "step-by-step manufacturing flow",
            "process control and quality checkpoints",
        ]),
        ("pillar", "lighting parts quality control", "Technical Guides", [
            "incoming inspection, in-process checks, and final QC",
            "inspection checklist for buyers",
        ]),
        ("pillar", "surface treatment for lighting hardware", "Technical Guides", [
            "corrosion resistance and finish selection",
            "plating, coating, and wear resistance",
        ]),
        ("pillar", "floor lamp parts supplier", "Technical Guides", [
            "supplier comparison and selection guide",
            "replacement parts and project sourcing",
            "quality checklist for floor lamp projects",
        ]),
        ("pillar", "wall lamp parts supplier", "Technical Guides", [
            "supplier comparison and selection guide",
            "project fit and customization options",
            "quality checklist for wall lamp projects",
        ]),
        ("pillar", "table lamp parts supplier", "Technical Guides", [
            "supplier comparison and selection guide",
            "replacement parts and spare parts planning",
            "quality checklist for table lamp projects",
        ]),
    ]

    for lane, keyword, category, directions in phase3_order:
        base = keyword_lookup.get(keyword.lower(), {})
        cluster = str(base.get("cluster") or "core")
        targets = str(base.get("internal_link_targets") or cluster_targets(cluster))
        for direction in directions:
            phase3_plan.append({
                "week": week,
                "lane": lane,
                "keyword": keyword,
                "category": category,
                "direction": direction,
                "title_angle": direction,
                "internal_link_targets": targets,
            })
            week += 1

    # Add ordinary keywords as a long-tail queue after the pillar program.
    for row in ordinary_keywords:
        keyword = str(row[keyword_headers.index("keywords")]).strip()
        category = str(row[keyword_headers.index("category")]).strip()
        cluster = str(row[keyword_headers.index("cluster")]).strip()
        targets = str(row[keyword_headers.index("internal_link_targets")]).strip()
        phase3_plan.append({
            "week": week,
            "lane": "ordinary",
            "keyword": keyword,
            "category": category,
            "direction": cluster_direction(cluster),
            "title_angle": cluster_direction(cluster),
            "internal_link_targets": targets,
        })
        week += 1

    def write_workbook(path: Path, keywords_subset, plan_subset):
        wb = make_workbook(path.stem)

        ws = wb.create_sheet("keywords")
        keyword_headers_out = ["keywords", "category", "lane", "priority", "cluster", "internal_link_targets", "notes"]
        ws.append(keyword_headers_out)
        for row in keywords_subset:
            if isinstance(row, dict):
                data = row
            else:
                data = {name: row[index] if index < len(row) else None for name, index in keyword_index.items()}
            ws.append([data.get(header) for header in keyword_headers_out])
        style_sheet(ws)

        ws = wb.create_sheet("plan")
        plan_headers_out = ["week", "lane", "keyword", "category", "direction", "title_angle", "internal_link_targets"]
        ws.append(plan_headers_out)
        for row in plan_subset:
            if isinstance(row, dict):
                data = row
            else:
                data = {name: row[index] if index < len(row) else None for name, index in plan_index.items()}
            ws.append([data.get(header) for header in plan_headers_out])
        style_sheet(ws)

        ws = wb.create_sheet("title_templates")
        ws.append(["template", "angle_type"])
        title_templates = [
            ("What Is {keyword}? A Practical Guide for Buyers and Engineers", "Educational"),
            ("How {keyword} Works: Materials, Structure, and Manufacturing Basics", "Technical"),
            ("{keyword}: 7 Things to Check Before You Order", "Buyer Checklist"),
            ("How to Choose the Right {keyword} for Your Project", "Selection Guide"),
            ("{keyword} Explained: Specs, Quality, and Common Mistakes", "Explainer"),
            ("{keyword} Comparison: What Buyers Should Evaluate First", "Comparison"),
            ("{keyword} Supplier Guide: Quality, Lead Time, and Customization", "Supplier Guide"),
            ("{keyword} for Hotel and Project Use: What to Know", "Application"),
        ]
        for template, angle in title_templates:
            ws.append([template, angle])
        style_sheet(ws)

        ws = wb.create_sheet("article_angles")
        ws.append(["angle", "recommended_category", "use_case"])
        article_angles = [
            ("Material selection and durability", "Technical Guides", "Compare metals, finishes, and load-bearing needs."),
            ("Structure and load-bearing design", "Technical Guides", "Explain geometry, stability, and mechanical performance."),
            ("Surface treatment and corrosion resistance", "Technical Guides", "Focus on coating, plating, and wear resistance."),
            ("Assembly precision and tolerance control", "Technical Guides", "Show how fit, alignment, and tolerance affect quality."),
            ("QC and inspection process", "Technical Guides", "Cover incoming inspection, in-process checks, and final QC."),
            ("Supplier comparison and sourcing fit", "Industry Insights", "Help buyers compare factories and shortlist vendors."),
            ("OEM vs ODM decision guide", "Industry Insights", "Clarify which cooperation model fits the buyer."),
            ("Lead time, MOQ, and pricing", "Industry Insights", "Support procurement decisions with practical constraints."),
        ]
        for angle, category, use_case in article_angles:
            ws.append([angle, category, use_case])
        style_sheet(ws)

        ws = wb.create_sheet("README")
        ws.append(["item", "detail"])
        ws.append(["Purpose", "Workspace-scoped keyword library for phase-3 long-cycle publishing."])
        ws.append(["Keywords source", f"{len(keywords_subset)} keywords copied from seo_keyword_library_full.xlsx."])
        ws.append(["Plan rows", f"{len(plan_subset)} rows in the chosen run plan."])
        ws.append(["Usage", "Import keywords into the workflow; use plan for ordered execution."])
        style_sheet(ws)

        wb.save(path)

    # Ordinary file: all ordinary keywords and ordinary plan rows.
    ordinary_path = OUTPUT_DIR / "seo_phase3_ordinary.xlsx"
    write_workbook(ordinary_path, ordinary_keywords, ordinary_plan)

    # Pillar file: pillar keywords plus the full pillar direction plan.
    pillar_path = OUTPUT_DIR / "seo_phase3_pillar.xlsx"
    write_workbook(pillar_path, pillar_keywords, pillar_plan)

    # Long-cycle phase-3 workbook: all keywords with a long queue that prioritizes pillar then ordinary.
    phase3_path = OUTPUT_DIR / "seo_phase3_long_cycle.xlsx"
    write_workbook(phase3_path, keyword_rows, phase3_plan)

    print(f"Saved: {ordinary_path}")
    print(f"Saved: {pillar_path}")
    print(f"Saved: {phase3_path}")


if __name__ == "__main__":
    main()
