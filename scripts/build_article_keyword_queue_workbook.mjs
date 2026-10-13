import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath = process.argv[2];
const outputPath = process.argv[3];
if (!sourcePath || !outputPath) {
  throw new Error("Usage: node build_article_keyword_queue_workbook.mjs <queue-json> <output-xlsx>");
}

const payload = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const queue = payload.queue || [];
const workbook = Workbook.create();
const overview = workbook.worksheets.add("Overview");
const keywords = workbook.worksheets.add("keywords");
const plan = workbook.worksheets.add("plan");
for (const sheet of [overview, keywords, plan]) sheet.showGridLines = false;

overview.getRange("A1:H1").merge();
overview.getRange("A1").values = [["SEO Article Keyword Queue — Google Ads Prioritized"]];
overview.getRange("A2:H2").merge();
overview.getRange("A2").values = [[`Market: ${payload.market || "United States"} | Source: Google Ads Keyword Planner + industry/AI review | Queue is ready for preselected workflow mode`]];
overview.getRange("A4:B4").values = [["Metric", "Value"]];
overview.getRange("A5:B9").values = [
  ["Google Ads candidates", payload.statistics?.source_ideas ?? 0],
  ["Industry/AI-approved candidates", payload.statistics?.review_approved ?? 0],
  ["Candidates after editorial rules", payload.statistics?.after_rules ?? 0],
  ["Distinct topic clusters", payload.statistics?.unique_topic_clusters ?? 0],
  ["Ready-to-run articles", queue.length],
];
overview.getRange("D4:H4").merge();
overview.getRange("D4").values = [["Execution rule"]];
overview.getRange("D5:H9").merge();
overview.getRange("D5").values = [["This workbook is the content queue, not a research dump. Each row has passed rule and AI screening, has measurable US Google Ads demand, avoids exact historical workflow keywords, and is deduplicated to one primary article per topic cluster. Run it with --use-preselected-keywords so the article workflow does not expand or re-filter the approved queue."]];
overview.getRange("A11:H11").merge();
overview.getRange("A11").values = [["Run command (review the 12 rows first; this command creates drafts with the current workflow defaults if schedule-hours is 0)"]];
overview.getRange("A12:H13").merge();
overview.getRange("A12").values = [[`D:\\Python\\python.exe -m src.cli.main workflow run ${outputPath} --use-preselected-keywords --schedule-hours 0`]];

const keywordHeaders = ["keywords", "category", "lane", "priority", "cluster", "internal_link_targets", "notes", "sequence", "avg_monthly_searches", "competition", "high_top_of_page_bid_usd", "priority_score", "selection_reason", "workflow_status"];
keywords.getRangeByIndexes(0, 0, 1, keywordHeaders.length).values = [keywordHeaders];
const keywordRows = queue.map((row) => [
  row.keyword, row.category, row.lane, row.priority, row.cluster, row.internal_link_targets,
  row.direction, row.sequence, row.avg_monthly_searches, row.competition || "",
  row.high_top_of_page_bid_micros == null ? null : row.high_top_of_page_bid_micros / 1_000_000,
  row.priority_score, row.selection_reason, row.workflow_status,
]);
if (keywordRows.length) keywords.getRangeByIndexes(1, 0, keywordRows.length, keywordHeaders.length).values = keywordRows;
const lastRow = Math.max(2, queue.length + 1);
keywords.tables.add(`A1:N${lastRow}`, true, "ArticleKeywordQueue");
keywords.freezePanes.freezeRows(1);
keywords.freezePanes.freezeColumns(2);
keywords.getRange(`D2:D${lastRow}`).dataValidation = { rule: { type: "list", values: ["A", "B", "C"] } };
keywords.getRange(`H2:H${lastRow}`).format.numberFormat = "0";
keywords.getRange(`I2:I${lastRow}`).format.numberFormat = "#,##0";
keywords.getRange(`K2:K${lastRow}`).format.numberFormat = '"$"#,##0.00';
keywords.getRange(`L2:L${lastRow}`).format.numberFormat = "0";
keywords.getRange(`I2:I${lastRow}`).conditionalFormats.add("dataBar", { color: "#2E75B6", gradient: true });

const planHeaders = ["week", "lane", "keyword", "category", "priority", "cluster", "direction", "title_angle", "internal_link_targets"];
plan.getRangeByIndexes(0, 0, 1, planHeaders.length).values = [planHeaders];
const planRows = queue.map((row) => ["", row.lane, row.keyword, row.category, row.priority, row.cluster, row.direction, row.direction, row.internal_link_targets]);
if (planRows.length) plan.getRangeByIndexes(1, 0, planRows.length, planHeaders.length).values = planRows;
plan.tables.add(`A1:I${lastRow}`, true, "ArticlePlan");
plan.freezePanes.freezeRows(1);

overview.getRange("A1:H1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center", verticalAlignment: "center" };
overview.getRange("A2:H2").format = { fill: "#D9EAF7", font: { italic: true }, wrapText: true };
overview.getRange("A4:B4").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" } };
overview.getRange("D4:H4").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A11:H11").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
overview.getRange("A4:B9").format.borders = { preset: "all", style: "thin", color: "#C9D5E3" };
overview.getRange("D4:H9").format.borders = { preset: "outside", style: "thin", color: "#C9D5E3" };
overview.getRange("D5:H9").format = { fill: "#F4F8FC", wrapText: true, verticalAlignment: "top" };
overview.getRange("A12:H13").format = { fill: "#FFF2CC", font: { color: "#7F6000" }, wrapText: true };
overview.getRange("A1:H1").format.rowHeight = 28;
overview.getRange("A2:H2").format.rowHeight = 28;
overview.getRange("D5:H9").format.rowHeight = 26;
overview.getRange("A:A").format.columnWidth = 31;
overview.getRange("B:B").format.columnWidth = 18;
overview.getRange("C:C").format.columnWidth = 34;
overview.getRange("D:H").format.columnWidth = 18;

keywords.getRange(`A1:N1`).format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true, verticalAlignment: "center" };
keywords.getRange(`A2:G${lastRow}`).format.fill = "#FFFDF3";
keywords.getRange(`H2:L${lastRow}`).format.fill = "#F4F8FC";
keywords.getRange(`M2:N${lastRow}`).format.wrapText = true;
keywords.getRange("A:A").format.columnWidth = 34;
keywords.getRange("B:D").format.columnWidth = 18;
keywords.getRange("E:E").format.columnWidth = 25;
keywords.getRange("F:F").format.columnWidth = 28;
keywords.getRange("G:G").format.columnWidth = 54;
keywords.getRange("H:L").format.columnWidth = 17;
keywords.getRange("M:M").format.columnWidth = 60;
keywords.getRange("N:N").format.columnWidth = 24;
plan.getRange("A1:I1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
plan.getRange("A:A").format.columnWidth = 12;
plan.getRange("B:B").format.columnWidth = 16;
plan.getRange("C:C").format.columnWidth = 34;
plan.getRange("D:F").format.columnWidth = 18;
plan.getRange("G:H").format.columnWidth = 54;
plan.getRange("I:I").format.columnWidth = 28;

const check = await workbook.inspect({ kind: "table", range: `keywords!A1:N${lastRow}`, include: "values,formulas", tableMaxRows: 15, tableMaxCols: 14 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
console.log(errors.ndjson);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const preview = await workbook.render({ sheetName: "Overview", range: "A1:H13", scale: 1.5, format: "png" });
await fs.writeFile(outputPath.replace(/\.xlsx$/i, ".png"), new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
