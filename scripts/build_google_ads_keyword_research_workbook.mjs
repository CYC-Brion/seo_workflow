import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath = process.argv[2];
const outputPath = process.argv[3];
if (!sourcePath || !outputPath) {
  throw new Error("Usage: node build_google_ads_keyword_research_workbook.mjs <source-json> <output-xlsx>");
}

const payload = JSON.parse(await fs.readFile(sourcePath, "utf8"));
const ideas = payload.ideas || [];
const workbook = Workbook.create();
const summary = workbook.worksheets.add("Overview");
const research = workbook.worksheets.add("Keyword Research");

for (const sheet of [summary, research]) sheet.showGridLines = false;

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Google Ads Keyword Research — Review Workbook"]];
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["Source: Google Ads Keyword Planner | Language: " + payload.target_language + " | Location: " + payload.target_location + " | Generated: " + payload.generated_at_utc]];
summary.getRange("A4:B4").values = [["Metric", "Value"]];
summary.getRange("A5:B10").values = [
  ["Core pillar seeds queried", payload.seed_keywords.length],
  ["Unique candidate keywords", ideas.length],
  ["Keywords with monthly-volume data", null],
  ["Total reported monthly searches", null],
  ["Keywords marked Keep", null],
  ["Automatically excluded", null],
];
const lastResearchRow = Math.max(2, ideas.length + 1);
summary.getRange("B7").formulas = [[`=COUNT('Keyword Research'!D2:D${lastResearchRow})`]];
summary.getRange("B8").formulas = [[`=SUM('Keyword Research'!D2:D${lastResearchRow})`]];
summary.getRange("B9").formulas = [[`=COUNTIF('Keyword Research'!B2:B${lastResearchRow},"Keep")`]];
summary.getRange("B10").formulas = [[`=COUNTIF('Keyword Research'!B2:B${lastResearchRow},"Exclude")`]];
summary.getRange("D4:H4").merge();
summary.getRange("D4").values = [["How to review"]];
summary.getRange("D5:H9").merge();
summary.getRange("D5").values = [[
  "1. Review the keyword and its Google Ads demand data.\n" +
  "2. Set Review Status to Keep, Review, or Exclude.\n" +
  "3. Set Priority A/B/C only for keywords worth planning.\n" +
  "4. Do not generate articles from this file yet; this is the research and decision layer."
]];
summary.getRange("A11:H11").merge();
summary.getRange("A11").values = [["Seed Keywords Queried"]];
summary.getRange(`A12:H${Math.max(12, 11 + Math.ceil(payload.seed_keywords.length / 4))}`).clear({ applyTo: "all" });
const seedRows = [];
for (let index = 0; index < payload.seed_keywords.length; index += 4) {
  seedRows.push(payload.seed_keywords.slice(index, index + 4));
  while (seedRows.at(-1).length < 4) seedRows.at(-1).push("");
}
summary.getRangeByIndexes(11, 0, seedRows.length, 4).values = seedRows;

const headers = [
  "Priority", "Review Status", "Keyword", "Avg. Monthly Searches", "Competition",
  "Competition Index", "Low Top-of-Page Bid (USD)", "High Top-of-Page Bid (USD)",
  "Sources", "Seed Keywords", "Monthly Search History", "Notes", "Filter Stage", "Filter Reason",
];
research.getRangeByIndexes(0, 0, 1, headers.length).values = [headers];
const rows = ideas.map((idea) => [
  "", idea.review_status || "Review", idea.keyword, idea.avg_monthly_searches, idea.competition || "",
  idea.competition_index, idea.low_top_of_page_bid_micros == null ? null : idea.low_top_of_page_bid_micros / 1_000_000,
  idea.high_top_of_page_bid_micros == null ? null : idea.high_top_of_page_bid_micros / 1_000_000,
  (idea.sources || []).join(", "), (idea.seed_keywords || []).join("; "),
  (idea.monthly_search_volumes || []).map((item) => `${item.year || ""}-${item.month || ""}: ${item.monthly_searches ?? ""}`).join(" | "), "",
  idea.filter_stage || "", idea.filter_reason || "",
]);
if (rows.length) research.getRangeByIndexes(1, 0, rows.length, headers.length).values = rows;
research.tables.add(`A1:N${lastResearchRow}`, true, "KeywordResearchTable");
research.freezePanes.freezeRows(1);
research.freezePanes.freezeColumns(3);
research.getRange(`A2:A${lastResearchRow}`).dataValidation = { rule: { type: "list", values: ["", "A", "B", "C"] } };
research.getRange(`B2:B${lastResearchRow}`).dataValidation = { rule: { type: "list", values: ["Keep", "Review", "Exclude"] } };
research.getRange(`D2:D${lastResearchRow}`).format.numberFormat = "#,##0";
research.getRange(`F2:F${lastResearchRow}`).format.numberFormat = "#,##0";
research.getRange(`G2:H${lastResearchRow}`).format.numberFormat = '"$"#,##0.00';
research.getRange(`D2:D${lastResearchRow}`).conditionalFormats.add("dataBar", { color: "#2E75B6", gradient: true });

summary.getRange("A1:H1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center", verticalAlignment: "center" };
summary.getRange("A2:H2").format = { fill: "#D9EAF7", font: { color: "#1F1F1F", italic: true }, wrapText: true };
summary.getRange("A4:B4").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("D4:H4").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A11:H11").format = { fill: "#2E75B6", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A4:B10").format.borders = { preset: "all", style: "thin", color: "#C9D5E3" };
summary.getRange("D4:H9").format.borders = { preset: "outside", style: "thin", color: "#C9D5E3" };
summary.getRange("D5:H9").format = { fill: "#F4F8FC", wrapText: true, verticalAlignment: "top" };
summary.getRange("A11:D" + (11 + seedRows.length)).format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
research.getRange(`A1:N1`).format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true, verticalAlignment: "center" };
research.getRange(`A2:C${lastResearchRow}`).format.fill = "#FFFDF3";
research.getRange(`A2:B${lastResearchRow}`).format.font = { color: "#7F6000" };
research.getRange(`I2:K${lastResearchRow}`).format.wrapText = true;

summary.getRange("A1:H1").format.rowHeight = 28;
summary.getRange("A2:H2").format.rowHeight = 28;
summary.getRange("D5:H9").format.rowHeight = 24;
summary.getRange("A:A").format.columnWidth = 29;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:C").format.columnWidth = 42;
summary.getRange("D:D").format.columnWidth = 20;
summary.getRange("E:E").format.columnWidth = 16;
summary.getRange("F:F").format.columnWidth = 18;
summary.getRange("G:H").format.columnWidth = 22;
summary.getRange("I:I").format.columnWidth = 29;
summary.getRange("J:J").format.columnWidth = 36;
summary.getRange("K:K").format.columnWidth = 52;
research.getRange("L:L").format.columnWidth = 28;
research.getRange("M:M").format.columnWidth = 15;
research.getRange("N:N").format.columnWidth = 42;

const check = await workbook.inspect({ kind: "table", range: `Keyword Research!A1:N${Math.min(lastResearchRow, 12)}`, include: "values,formulas", tableMaxRows: 12, tableMaxCols: 14 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
console.log(errors.ndjson);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const preview = await workbook.render({ sheetName: "Overview", range: "A1:H16", scale: 1.5, format: "png" });
await fs.writeFile(outputPath.replace(/\.xlsx$/i, ".png"), new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
