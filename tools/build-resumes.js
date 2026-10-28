// Builds every résumé variant from resume/resume-data.json:
//   resume/<file>.docx and resume/<id>.html (print-friendly). PDFs are printed from the HTML by tools/print-resumes.py.
// Run from the repo root: node tools/build-resumes.js && python3 tools/print-resumes.py
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, BorderStyle, TabStopType, ExternalHyperlink, HeadingLevel } = require("docx");

const root = path.join(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(root, "resume/resume-data.json"), "utf8"));
const fileBase = (r) => r.id === "master" ? "Alvin-Diaz-Merasol-Resume" : "Alvin-Diaz-Merasol-Resume-" + r.label.replace(/[^A-Za-z0-9]+/g, "-").replace(/-+$/, "");
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- DOCX ---------- */
const FONT = "Arial";
const SZ = 20; // 10pt
function heading(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 80 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "141B2B", space: 2 } },
    children: [new TextRun({ text: text.toUpperCase(), bold: true, font: FONT, size: 21, characterSpacing: 20 })] });
}
function jobHead(left, right) {
  return new Paragraph({ spacing: { before: 140, after: 0 }, tabStops: [{ type: TabStopType.RIGHT, position: 9638 }],
    children: [new TextRun({ text: left, bold: true, font: FONT, size: SZ }), new TextRun({ text: "\t" + right, font: FONT, size: SZ, color: "3D485C" })] });
}
function bullet(text) {
  return new Paragraph({ numbering: { reference: "dots", level: 0 }, spacing: { after: 30 }, children: [new TextRun({ text, font: FONT, size: SZ })] });
}
function para(runs, opts = {}) { return new Paragraph({ spacing: { after: 40 }, ...opts, children: runs }); }
function docxFor(role) {
  const C = [];
  C.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 40 }, children: [new TextRun({ text: D.name + ", " + D.credentials, bold: true, font: FONT, size: 36, color: "141B2B" })] }));
  C.push(para([new TextRun({ text: role.headline, font: FONT, size: 22, color: "8F5400" })]));
  C.push(para([new TextRun({ text: D.location + "  |  " + D.email, font: FONT, size: 18, color: "3D485C" })], { spacing: { after: 0 } }));
  const linkRuns = [];
  D.links.forEach((l, i) => {
    if (i) linkRuns.push(new TextRun({ text: "  |  ", font: FONT, size: 18, color: "3D485C" }));
    linkRuns.push(new ExternalHyperlink({ link: l.url, children: [new TextRun({ text: l.text, font: FONT, size: 18, color: "3D485C" })] }));
  });
  C.push(para(linkRuns));
  C.push(heading("Summary"));
  C.push(para([new TextRun({ text: role.summary, font: FONT, size: SZ })]));
  C.push(heading("Core Skills"));
  role.skills.forEach((k) => { const s = D.skills[k]; C.push(para([new TextRun({ text: s.label + ": ", bold: true, font: FONT, size: SZ }), new TextRun({ text: s.text, font: FONT, size: SZ })], { spacing: { after: 30 } })); });
  C.push(heading("Experience"));
  D.experience.forEach((e) => {
    C.push(jobHead(e.title, e.dates));
    if (e.org) C.push(para([new TextRun({ text: e.org, italics: true, font: FONT, size: SZ, color: "3D485C" })], { spacing: { after: 30 } }));
    e.bullets.forEach((b) => C.push(bullet(b)));
  });
  C.push(heading("Education and Licenses"));
  D.education.forEach((e) => C.push(jobHead(e.title, e.where)));
  return new Document({
    creator: D.name, title: D.name + " — Résumé", description: role.label,
    styles: { default: { document: { run: { font: FONT, size: SZ } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 36, bold: true, color: "141B2B" }, paragraph: { spacing: { after: 40 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 21, bold: true, color: "141B2B" }, paragraph: { spacing: { before: 220, after: 80 }, outlineLevel: 1 } },
      ] },
    numbering: { config: [{ reference: "dots", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
    sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1134, right: 1134 } } }, children: C }],
  });
}

/* ---------- print-friendly HTML ---------- */
function htmlFor(role) {
  const others = D.roles.map((r) => `<option value="${r.id}.html"${r.id === role.id ? " selected" : ""}>${esc(r.label)}</option>`).join("");
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(D.name)} — Résumé${role.id === "master" ? "" : " (" + esc(role.label) + ")"}</title>
<meta name="description" content="${esc(role.headline)}">
<meta name="robots" content="noindex">
<style>
@font-face{font-family:"Plex";src:url(../assets/fonts/plex-sans-400.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"Plex";src:url(../assets/fonts/plex-sans-400i.woff2) format("woff2");font-weight:400;font-style:italic;font-display:swap}
@font-face{font-family:"Plex";src:url(../assets/fonts/plex-sans-500.woff2) format("woff2");font-weight:500;font-display:swap}
@font-face{font-family:"Plex";src:url(../assets/fonts/plex-sans-600.woff2) format("woff2");font-weight:600;font-display:swap}
@page{size:A4;margin:14mm 16mm}
*{box-sizing:border-box}
html{background:#E9ECF2}
body{margin:0;font:400 9.6pt/1.42 "Plex",Arial,sans-serif;color:#141B2B}
.sheet{max-width:210mm;margin:0 auto;background:#fff;padding:14mm 16mm}
.bar{max-width:210mm;margin:16px auto;padding:0 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;font:500 14px/1.3 system-ui,sans-serif}
.bar a,.bar select{display:inline-flex;align-items:center;min-height:42px;padding:0 14px;border:1px solid #9AA6BA;border-radius:4px;background:#fff;color:#141B2B;text-decoration:none;font:inherit}
.bar a.primary{background:#F2A516;border-color:#F2A516;color:#1B1203;font-weight:600}
h1{margin:0;font:600 20pt/1.1 "Plex",Arial,sans-serif}
.headline{margin-top:3px;font:500 10.6pt/1.3 "Plex",Arial,sans-serif;color:#8F5400}
.contact{margin-top:5px;color:#3D485C;font-size:9pt}
.contact a{color:inherit;text-decoration:none}
.contact span+span::before{content:"  |  ";color:#9AA6BA}
h2{margin:13px 0 5px;padding-bottom:3px;border-bottom:1.2px solid #141B2B;font:600 10.2pt/1.2 "Plex",Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase}
p{margin:0}
ul{margin:3px 0 0;padding-left:15px}
li{margin:1.5px 0}
.job{margin-top:8px;break-inside:avoid}
.jh{display:flex;justify-content:space-between;gap:12px}
.jh b{font-weight:600}
.jh span{color:#3D485C;text-align:right}
.org{color:#3D485C;font-style:italic}
.skills p{margin:2px 0}
.skills b{font-weight:600}
@media print{html{background:#fff}.bar{display:none}.sheet{padding:0;max-width:none}}
@media (max-width:600px){.sheet{padding:20px 16px}.jh{flex-direction:column;gap:0}.jh span{text-align:left}}
</style></head><body>
<nav class="bar" aria-label="Résumé downloads">
  <a href="../index.html#resume">Back to portfolio</a>
  <label for="role" style="position:absolute;left:-9999px">Résumé version</label>
  <select id="role" onchange="location.href=this.value">${others}</select>
  <a class="primary" href="${fileBase(role)}.pdf" download>Download PDF</a>
  <a href="${fileBase(role)}.docx" download>Download Word</a>
</nav>
<main class="sheet">
<h1>${esc(D.name)}, ${esc(D.credentials)}</h1>
<p class="headline">${esc(role.headline)}</p>
<p class="contact"><span>${esc(D.location)}</span><span><a href="mailto:${esc(D.email)}">${esc(D.email)}</a></span></p>
<p class="contact">${D.links.map((l) => `<span><a href="${esc(l.url)}">${l.label === "Portfolio" ? "Portfolio: " : ""}${esc(l.text)}</a></span>`).join("")}</p>
<h2>Summary</h2>
<p>${esc(role.summary)}</p>
<h2>Core Skills</h2>
<div class="skills">${role.skills.map((k) => `<p><b>${esc(D.skills[k].label)}:</b> ${esc(D.skills[k].text)}</p>`).join("")}</div>
<h2>Experience</h2>
${D.experience.map((e) => `<div class="job"><div class="jh"><b>${esc(e.title)}</b><span>${esc(e.dates)}</span></div>${e.org ? `<div class="org">${esc(e.org)}</div>` : ""}<ul>${e.bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul></div>`).join("\n")}
<h2>Education and Licenses</h2>
${D.education.map((e) => `<div class="jh"><b>${esc(e.title)}</b><span>${esc(e.where)}</span></div>`).join("\n")}
</main>
</body></html>`;
}

(async () => {
  const manifest = [];
  for (const r of D.roles) {
    const base = fileBase(r);
    fs.writeFileSync(path.join(root, "resume", r.id + ".html"), htmlFor(r));
    fs.writeFileSync(path.join(root, "resume", base + ".docx"), await Packer.toBuffer(docxFor(r)));
    manifest.push({ id: r.id, label: r.label, headline: r.headline, summary: r.summary, projects: r.projects, html: "resume/" + r.id + ".html", pdf: "resume/" + base + ".pdf", docx: "resume/" + base + ".docx" });
  }
  fs.copyFileSync(path.join(root, "resume/master.html"), path.join(root, "resume/index.html"));
  fs.writeFileSync(path.join(root, "resume/manifest.json"), JSON.stringify(manifest, null, 1));
  console.log("built", manifest.length, "variants");
})();
