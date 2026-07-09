const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const summary = JSON.parse(fs.readFileSync(path.join(__dirname, "portfolio_summary.json"), "utf8"));

// ---- Palette: "Midnight Executive" ----
const NAVY = "1E2761";
const NAVY_DARK = "141B4D";
const ICE = "CADCFC";
const WHITE = "FFFFFF";
const INK = "2B2E3A";
const MUTED = "6B7280";
const GREEN = "2E8B57";
const AMBER = "D9A441";
const RED = "C0392B";

const RAG_COLOR = { Green: GREEN, Amber: AMBER, Red: RED, Unknown: MUTED };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "Professional Services -- Project Health Agent";
pres.title = "Monthly Project Health Update";

const FONT_HEAD = "Cambria";
const FONT_BODY = "Calibri";

function addFooter(slide, label) {
  slide.addText(label, {
    x: 0.5, y: 7.08, w: 8, h: 0.3, fontFace: FONT_BODY, fontSize: 9, color: MUTED,
  });
  slide.addText(`As of ${summary.as_of}`, {
    x: 10.5, y: 7.08, w: 2.3, h: 0.3, fontFace: FONT_BODY, fontSize: 9, color: MUTED, align: "right",
  });
}

function statChip(slide, x, y, w, h, value, label, color) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08, fill: { color: WHITE },
    line: { color: "E5E7EB", width: 1 },
    shadow: { type: "outer", color: "1E2761", blur: 8, offset: 3, angle: 90, opacity: 0.12 },
  });
  slide.addText(String(value), {
    x, y: y + 0.12, w, h: h - 0.55, align: "center", valign: "middle",
    fontFace: FONT_HEAD, fontSize: 40, bold: true, color,
  });
  slide.addText(label, {
    x, y: y + h - 0.42, w, h: 0.4, align: "center", valign: "top",
    fontFace: FONT_BODY, fontSize: 12, color: INK,
  });
}

function ragDot(slide, x, y, rag) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: 0.16, h: 0.16, fill: { color: RAG_COLOR[rag] || MUTED }, line: { type: "none" },
  });
}

// ============================================================ SLIDE 1 -- TITLE
{
  const slide = pres.addSlide();
  slide.background = { color: NAVY };
  slide.addShape(pres.shapes.OVAL, { x: 10.6, y: -1.6, w: 5, h: 5, fill: { color: NAVY_DARK }, line: { type: "none" } });
  slide.addShape(pres.shapes.OVAL, { x: -1.4, y: 5.3, w: 4, h: 4, fill: { color: NAVY_DARK }, line: { type: "none" } });

  slide.addText("PROFESSIONAL SERVICES", {
    x: 0.7, y: 1.35, w: 8, h: 0.4, fontFace: FONT_BODY, fontSize: 14, color: ICE, charSpacing: 3,
  });
  slide.addText("Monthly Project Health Update", {
    x: 0.7, y: 1.75, w: 10.5, h: 1.3, fontFace: FONT_HEAD, fontSize: 40, bold: true, color: WHITE,
  });
  slide.addText("A portfolio-level view of schedule, milestone, and delivery risk across active engagements.", {
    x: 0.7, y: 2.95, w: 9.5, h: 0.6, fontFace: FONT_BODY, fontSize: 15, color: ICE,
  });

  slide.addText([
    { text: `${summary.portfolio_size} active projects reviewed`, options: { breakLine: true, bullet: false } },
    { text: `Snapshot as of ${summary.as_of}`, options: { breakLine: true, bullet: false } },
    { text: "Generated automatically by the Project Health Reporting Agent", options: { bullet: false } },
  ], { x: 0.7, y: 6.0, w: 9, h: 1, fontFace: FONT_BODY, fontSize: 12, color: ICE, lineSpacingMultiple: 1.4 });
}

// ============================================================ SLIDE 2 -- PORTFOLIO SNAPSHOT
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  slide.addText("Portfolio Snapshot", { x: 0.6, y: 0.4, w: 9, h: 0.6, fontFace: FONT_HEAD, fontSize: 30, bold: true, color: NAVY });
  slide.addText("Where the portfolio stands today, at a glance.", { x: 0.6, y: 0.98, w: 9, h: 0.4, fontFace: FONT_BODY, fontSize: 13, color: MUTED });

  const counts = summary.rag_counts;
  const chipW = 3.6, chipH = 1.9, gap = 0.35, startX = 0.6, y = 1.7;
  const order = [["Red", RED], ["Amber", AMBER], ["Green", GREEN]];
  order.forEach(([rag, color], i) => {
    statChip(slide, startX + i * (chipW + gap), y, chipW, chipH, counts[rag] || 0, `${rag} projects`, color);
  });

  // Headline callout below chips
  const redCount = counts.Red || 0;
  const total = summary.portfolio_size;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.6, y: 4.0, w: 12.1, h: 1.55, rectRadius: 0.08, fill: { color: "F5F7FB" }, line: { type: "none" },
  });
  slide.addText([
    { text: `${redCount} of ${total} projects are Red`, options: { bold: true, color: NAVY, breakLine: true, fontSize: 18 } },
    { text: summary.top_risk_dimension
        ? `Schedule and milestone slippage are the most common drivers across the flagged projects -- not isolated, one-off issues.`
        : `No dominant risk driver identified this cycle.`, options: { color: INK, fontSize: 13 } },
  ], { x: 0.9, y: 4.18, w: 11.5, h: 1.2, fontFace: FONT_BODY, valign: "top", lineSpacingMultiple: 1.3 });

  slide.addText("Per-project detail", { x: 0.6, y: 5.75, w: 5, h: 0.35, fontFace: FONT_HEAD, fontSize: 14, bold: true, color: NAVY });
  let ty = 6.15;
  summary.projects.forEach((p) => {
    ragDot(slide, 0.65, ty + 0.08, p.latest_rag);
    slide.addText(p.name, { x: 0.9, y: ty, w: 7.3, h: 0.3, fontFace: FONT_BODY, fontSize: 12, color: INK });
    slide.addText(p.latest_rag, { x: 8.3, y: ty, w: 1.3, h: 0.3, fontFace: FONT_BODY, fontSize: 12, bold: true, color: RAG_COLOR[p.latest_rag] });
    slide.addText(p.pm || "", { x: 9.7, y: ty, w: 3.0, h: 0.3, fontFace: FONT_BODY, fontSize: 11, color: MUTED, align: "right" });
    ty += 0.34;
  });

  addFooter(slide, "Source: weekly automated health scans across all active project plans.");
}

// ============================================================ SLIDE 3 -- TREND ACROSS PROJECTS
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  slide.addText("Trend Across Projects", { x: 0.6, y: 0.4, w: 9, h: 0.6, fontFace: FONT_HEAD, fontSize: 30, bold: true, color: NAVY });
  slide.addText("Movement over the last three weekly scans -- direction matters as much as current color.", {
    x: 0.6, y: 0.98, w: 11.5, h: 0.4, fontFace: FONT_BODY, fontSize: 13, color: MUTED,
  });

  let ty = 1.75;
  summary.projects.forEach((p) => {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.6, y: ty, w: 12.1, h: 1.35, rectRadius: 0.08, fill: { color: "F9FAFB" }, line: { type: "none" },
    });
    slide.addText(p.name, { x: 0.85, y: ty + 0.12, w: 5.2, h: 0.4, fontFace: FONT_BODY, fontSize: 14, bold: true, color: INK });
    const trendLabel = { worsening: "Worsening", improving: "Improving", flat: "Steady" }[p.trend];
    const trendColor = { worsening: RED, improving: GREEN, flat: MUTED }[p.trend];
    slide.addText(trendLabel, { x: 0.85, y: ty + 0.55, w: 2.2, h: 0.35, fontFace: FONT_BODY, fontSize: 12, bold: true, color: trendColor });

    // History dots + labels
    let hx = 3.3;
    p.history.forEach((h, i) => {
      ragDot(slide, hx, ty + 0.62, h.rag);
      slide.addText(h.as_of.slice(5), { x: hx - 0.25, y: ty + 0.85, w: 0.7, h: 0.25, fontFace: FONT_BODY, fontSize: 8, color: MUTED, align: "center" });
      if (i < p.history.length - 1) {
        slide.addShape(pres.shapes.LINE, { x: hx + 0.16, y: ty + 0.70, w: 1.0, h: 0, line: { color: "D1D5DB", width: 1.5 } });
      }
      hx += 1.16;
    });

    slide.addText(p.narrative.split(".")[0] + ".", {
      x: 6.4, y: ty + 0.12, w: 6.1, h: 1.1, fontFace: FONT_BODY, fontSize: 11, color: INK, valign: "top", lineSpacingMultiple: 1.2,
    });
    ty += 1.55;
  });

  addFooter(slide, "Dots read left-to-right, oldest to most recent weekly scan.");
}

// ============================================================ SLIDE 4 -- TOP RISK DRIVERS
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  slide.addText("Emerging Risk: What's Actually Driving It", { x: 0.6, y: 0.4, w: 11.5, h: 0.6, fontFace: FONT_HEAD, fontSize: 28, bold: true, color: NAVY });
  slide.addText("How many projects are flagged Amber/Red on each dimension -- the pattern, not just the count.", {
    x: 0.6, y: 1.0, w: 11.5, h: 0.4, fontFace: FONT_BODY, fontSize: 13, color: MUTED,
  });

  const dims = summary.dimension_red_amber_counts;
  const labels = Object.keys(dims).map((d) => d[0].toUpperCase() + d.slice(1));
  const values = Object.values(dims);

  slide.addChart(pres.charts.BAR, [{ name: "Projects flagged", labels, values }], {
    x: 0.6, y: 1.6, w: 7.0, h: 4.5, barDir: "bar",
    chartColors: [NAVY],
    showValue: true, dataLabelColor: WHITE, dataLabelFontSize: 12,
    valAxisMaxVal: summary.portfolio_size, valAxisMinVal: 0,
    catAxisLabelFontSize: 12, showLegend: false, showTitle: false,
  });

  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 7.9, y: 1.6, w: 4.8, h: 4.5, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" },
  });
  slide.addText("Read on the pattern", { x: 8.2, y: 1.85, w: 4.2, h: 0.4, fontFace: FONT_HEAD, fontSize: 16, bold: true, color: WHITE });
  const topDim = summary.top_risk_dimension ? summary.top_risk_dimension[0].toUpperCase() + summary.top_risk_dimension.slice(1) : "N/A";
  slide.addText([
    { text: `${topDim} is the most common flag across the flagged projects.`, options: { breakLine: true, bullet: true } },
    { text: "It's showing up in more than one project, which points to a portfolio-level cause (resourcing, client dependency, or estimation) rather than one team's execution.", options: { breakLine: true, bullet: true } },
    { text: "Sentiment and budget are excluded from this cycle's scoring where source data didn't include cost actuals or PM commentary -- flagged, not guessed.", options: { bullet: true } },
  ], { x: 8.2, y: 2.35, w: 4.3, h: 3.5, fontFace: FONT_BODY, fontSize: 12, color: ICE, valign: "top", lineSpacingMultiple: 1.35 });

  addFooter(slide, "Counts reflect the most recent scan per project.");
}

// ============================================================ SLIDE 5 -- SPOTLIGHT ON AT-RISK PROJECTS
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  slide.addText("Spotlight: Projects Needing Attention", { x: 0.6, y: 0.4, w: 11, h: 0.6, fontFace: FONT_HEAD, fontSize: 28, bold: true, color: NAVY });

  const atRisk = summary.projects.filter((p) => p.latest_rag !== "Green").slice(0, 2);
  const colW = 5.85, gap = 0.4, startX = 0.6, y = 1.25, h = 5.6;

  atRisk.forEach((p, i) => {
    const x = startX + i * (colW + gap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: colW, h, rectRadius: 0.08, fill: { color: "F9FAFB" }, line: { type: "none" } });
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.3, y: y + 0.3, w: 1.3, h: 0.42, rectRadius: 0.21, fill: { color: RAG_COLOR[p.latest_rag] }, line: { type: "none" } });
    slide.addText(p.latest_rag, { x: x + 0.3, y: y + 0.3, w: 1.3, h: 0.42, align: "center", valign: "middle", fontFace: FONT_BODY, fontSize: 12, bold: true, color: WHITE });
    slide.addText(p.name, { x: x + 0.3, y: y + 0.85, w: colW - 0.6, h: 0.7, fontFace: FONT_HEAD, fontSize: 16, bold: true, color: NAVY });
    slide.addText(`PM: ${p.pm || "Unassigned"}`, { x: x + 0.3, y: y + 1.5, w: colW - 0.6, h: 0.3, fontFace: FONT_BODY, fontSize: 11, color: MUTED });

    const dimLines = Object.entries(p.dimensions)
      .filter(([, d]) => d.score !== null && d.score > 0)
      .map(([k, d]) => ({ text: `${k[0].toUpperCase()}${k.slice(1)}: ${d.label}`, options: { bullet: true, breakLine: true, color: RAG_COLOR[d.label] || INK } }));
    slide.addText(dimLines.length ? dimLines : [{ text: "No dimension currently flagged.", options: {} }], {
      x: x + 0.3, y: y + 1.95, w: colW - 0.6, h: 1.3, fontFace: FONT_BODY, fontSize: 12, valign: "top", lineSpacingMultiple: 1.3,
    });

    slide.addText(p.narrative, {
      x: x + 0.3, y: y + 3.35, w: colW - 0.6, h: h - 3.6, fontFace: FONT_BODY, fontSize: 10.5, color: INK, valign: "top", lineSpacingMultiple: 1.25,
    });
  });

  if (atRisk.length === 0) {
    slide.addText("No projects are currently Amber or Red.", { x: 0.6, y: 3, w: 11, h: 1, fontFace: FONT_BODY, fontSize: 16, color: MUTED });
  }

  addFooter(slide, "Full evidence trail available in the weekly JSON/Markdown reports per project.");
}

// ============================================================ SLIDE 6 -- RECOMMENDATIONS
{
  const slide = pres.addSlide();
  slide.background = { color: NAVY };
  slide.addText("Recommendations & Next Steps", { x: 0.6, y: 0.5, w: 11, h: 0.6, fontFace: FONT_HEAD, fontSize: 30, bold: true, color: WHITE });

  const recs = [
    ["Address the shared bottleneck, not just the symptom", "Schedule slippage is showing up across multiple projects at once -- treat it as a resourcing/estimation review, not a project-by-project fire drill."],
    ["Escalate stalled dependencies this week", "Tasks stuck behind unmet predecessors or client-side blockers are a leading indicator of Red status; a targeted unblock call is cheaper now than a re-baseline later."],
    ["Close the budget and sentiment data gap", "Two of five health signals could not be scored this cycle because cost actuals and PM commentary weren't captured consistently -- wiring these in sharpens every future report."],
  ];

  let ty = 1.5;
  recs.forEach(([title, body], i) => {
    slide.addShape(pres.shapes.OVAL, { x: 0.7, y: ty, w: 0.5, h: 0.5, fill: { color: ICE }, line: { type: "none" } });
    slide.addText(String(i + 1), { x: 0.7, y: ty, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: FONT_HEAD, fontSize: 16, bold: true, color: NAVY });
    slide.addText(title, { x: 1.4, y: ty - 0.05, w: 10.8, h: 0.4, fontFace: FONT_HEAD, fontSize: 16, bold: true, color: WHITE });
    slide.addText(body, { x: 1.4, y: ty + 0.38, w: 10.8, h: 0.7, fontFace: FONT_BODY, fontSize: 12.5, color: ICE, lineSpacingMultiple: 1.3 });
    ty += 1.35;
  });

  slide.addText("Prepared by the Professional Services Project Health Reporting Agent -- refreshed weekly.", {
    x: 0.6, y: 6.9, w: 11, h: 0.4, fontFace: FONT_BODY, fontSize: 10, color: ICE,
  });
}

const outPath = path.join(__dirname, "Monthly_Executive_Update.pptx");
pres.writeFile({ fileName: outPath }).then(() => console.log("done:", outPath));
