import React, { useState, useRef, useCallback } from "react";
import { Play, ClipboardCheck, ClipboardCopy, Download, Trash2, CheckCircle2, AlertCircle } from "lucide-react";

/* ============================== native SheetJS replacement ============================== */

function csv(text: string): any[][] {
  const rows: any[][] = [];
  let cur = '', q = false, row: any[] = [];
  for (let i = 0; i < text.length; i++) {
    const c = text[i], nx = text[i + 1];
    if (q) {
      if (c === '"' && nx === '"') { cur += '"'; i++; }
      else if (c === '"') q = false;
      else cur += c;
    } else {
      if (c === '"') q = true;
      else if (c === ',') { row.push(cur); cur = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && nx === '\n') i++;
        if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
        cur = ''; row = [];
      } else cur += c;
    }
  }
  if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
  return rows;
}

function txt(u: Uint8Array): string {
  return new TextDecoder('utf-8').decode(u);
}

function u16(d: DataView, o: number): number {
  return d.getUint16(o, true);
}

function u32(d: DataView, o: number): number {
  return d.getUint32(o, true);
}

async function inflate(u: Uint8Array): Promise<Uint8Array> {
  if (typeof (window as any).DecompressionStream === 'undefined') {
    throw Error('Browser cannot decompress XLSX offline. Use recent Edge/Chrome or upload CSV.');
  }
  let ds = new (window as any).DecompressionStream('deflate-raw');
  return new Uint8Array(await new Response(new Blob([u.buffer as ArrayBuffer]).stream().pipeThrough(ds)).arrayBuffer());
}

async function unzip(ab: ArrayBuffer): Promise<Map<string, Uint8Array>> {
  let u = new Uint8Array(ab), d = new DataView(ab), e = -1;
  for (let i = u.length - 22; i >= 0 && i > u.length - 66000; i--) {
    if (u[i] === 80 && u[i + 1] === 75 && u[i + 2] === 5 && u[i + 3] === 6) { e = i; break; }
  }
  if (e < 0) throw Error('Invalid XLSX file.');
  let n = u16(d, e + 10), p = u32(d, e + 16), m = new Map<string, Uint8Array>();
  for (let k = 0; k < n; k++) {
    if (u32(d, p) !== 0x02014b50) break;
    let meth = u16(d, p + 10), cs = u32(d, p + 20), nl = u16(d, p + 28), el = u16(d, p + 30), cl = u16(d, p + 32), lo = u32(d, p + 42), name = txt(u.slice(p + 46, p + 46 + nl)), ln = u16(d, lo + 26), le = u16(d, lo + 28), st = lo + 30 + ln + le, dat = u.slice(st, st + cs);
    m.set(name, meth === 0 ? dat : await inflate(dat));
    p += 46 + nl + el + cl;
  }
  return m;
}

function xml(s: string): Document {
  return new DOMParser().parseFromString(String(s || '').replace(/^\uFEFF/, ''), 'application/xml');
}

function els(n: Node | null, name: string): Element[] {
  if (!n) return [];
  let a: Element[] = [];
  let element = n as any;
  if (element.getElementsByTagNameNS) a = Array.from(element.getElementsByTagNameNS('*', name));
  if (!a.length && element.getElementsByTagName) a = Array.from(element.getElementsByTagName(name));
  if (!a.length && element.getElementsByTagName) {
    a = Array.from(element.getElementsByTagName('*')).filter((x: any) => (x.localName || x.nodeName || '').split(':').pop() === name) as Element[];
  }
  return a;
}

function firstEl(n: Node | null, name: string): Element | null {
  return els(n, name)[0] || null;
}

function relId(n: Element): string {
  return n.getAttribute('r:id') || n.getAttribute('id') || n.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id') || '';
}

function allT(n: Node | null): string {
  return els(n, 't').map(x => x.textContent || '').join('');
}

function shared(doc: Document | null): string[] {
  return doc ? els(doc, 'si').map(allT) : [];
}

function rels(doc: Document | null): Map<string, string> {
  let m = new Map<string, string>();
  if (doc) els(doc, 'Relationship').forEach(r => m.set(r.getAttribute('Id') || r.getAttribute('id') || '', r.getAttribute('Target') || r.getAttribute('target') || ''));
  return m;
}

function targets(wb: Document, rd: Document | null): Map<string, string> {
  let rm = rels(rd), m = new Map<string, string>();
  els(wb, 'sheet').forEach(s => {
    let t = rm.get(relId(s)) || '';
    t = t.replace(/^\//, '');
    if (t && !t.startsWith('xl/')) t = 'xl/' + t;
    if (s.getAttribute('name') && t) m.set(s.getAttribute('name') || '', t);
  });
  return m;
}

function cellIndex(ref: string | null): number {
  let x = String(ref || '').match(/[A-Z]+/i);
  return x ? (colToIndex(x[0]) ?? 0) : 0;
}

function parseSheet(doc: Document, ss: string[]): any[][] {
  let rows: any[][] = [];
  els(doc, 'row').forEach(rr => {
    let a: any[] = [];
    els(rr, 'c').forEach(c => {
      let i = cellIndex(c.getAttribute('r')), t = c.getAttribute('t'), v = firstEl(c, 'v'), is = firstEl(c, 'is'), val = '';
      if (t === 's' && v) val = ss[+v.textContent!] || '';
      else if (t === 'inlineStr' && is) val = allT(is);
      else if (v) val = v.textContent || '';
      a[i] = val;
    });
    rows.push(a);
  });
  return rows;
}

/* ============================== pure helpers ============================== */

const clean = (v: any): string => String(v ?? "").replace(/\s+/g, " ").trim();
const norm = (v: any): string => clean(v).replace(/_/g, " ").toLowerCase();
const escHtml = (s: any): string => String(s ?? "").replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m] as string));
const pad2 = (n: any): string => String(Number(n || 0)).padStart(2, "0");
const num = (v: any): number => (v === null || v === undefined || v === "" ? NaN : Number.isFinite(Number(v)) ? Number(v) : NaN);
const unique = (a: any[]): string[] => [...new Set((a || []).map(clean).filter(Boolean))];

function colToIndex(c: any): number | null {
  c = String(c || "").trim().toUpperCase();
  let n = 0;
  for (let ch of c) {
    if (ch < "A" || ch > "Z") continue;
    n = n * 26 + ch.charCodeAt(0) - 64;
  }
  return n ? n - 1 : null;
}
function getCell(row: any[] | undefined, colLetter: string): string {
  const i = colToIndex(colLetter);
  return i == null || !row || row[i] == null ? "" : String(row[i]).trim();
}
function rowHasData(r: any[] | undefined): boolean {
  return Array.isArray(r) && r.some((x) => clean(x));
}
function rowNorms(r: any[] | undefined): string[] {
  return (r || []).map((x) => norm(x));
}
function findHeaderRowIndex(rows: any[][]): number {
  const keys = [
    "report id", "reportid", "worldwide unique case identification number",
    "pt name", "pt", "ccsi listedness", "listedness", "case seriousness",
    "event seriousness", "casenarrative", "case narrative", "source", "dme",
  ];
  for (let i = 0; i < (rows || []).length; i++) {
    const cells = rowNorms(rows[i]).filter(Boolean);
    if (!cells.length) continue;
    const hits = keys.filter((k) => cells.some((c) => c === k || c.includes(k))).length;
    if (hits >= 2) return i;
  }
  return -1;
}
function dataRows(rows: any[][]): any[][] {
  rows = rows || [];
  const h = findHeaderRowIndex(rows);
  return (h >= 0 ? rows.slice(h + 1) : rows.slice(11)).filter(rowHasData);
}
function hasHeaderOnlyOrZeroData(rows: any[][]): boolean {
  return (rows || []).length > 0 && findHeaderRowIndex(rows) >= 0 && dataRows(rows).length === 0;
}

/* -------- file reading using unzip/xml -------- */

async function readFile(file: File | null, cache: Map<string, any>): Promise<{ rows: any[][]; sheet: string; zero: boolean }> {
  if (!file) return { rows: [], sheet: "not uploaded", zero: false };
  const key = [file.name, file.size, file.lastModified].join("|");
  if (cache.has(key)) return cache.get(key);
  let result;
  if (file.name.toLowerCase().endsWith(".csv")) {
    const rows = csv(await file.text());
    result = { rows, sheet: "CSV", zero: hasHeaderOnlyOrZeroData(rows) };
    cache.set(key, result);
    return result;
  }
  let z = await unzip(await file.arrayBuffer()), wbXml = z.get('xl/workbook.xml');
  if (!wbXml) throw Error('Workbook structure not found in ' + file.name);
  let wb = xml(txt(wbXml)), rd = z.get('xl/_rels/workbook.xml.rels') ? xml(txt(z.get('xl/_rels/workbook.xml.rels')!)) : null, ss = shared(z.get('xl/sharedStrings.xml') ? xml(txt(z.get('xl/sharedStrings.xml')!)) : null), tg = targets(wb, rd), names = [...tg.keys()];
  if (!names.length) throw Error('No worksheet tab found in ' + file.name);
  let sel = names[0], target = tg.get(sel);
  if (!target || !z.get(target)) throw Error('Worksheet file part could not be read in ' + file.name);
  let rows = parseSheet(xml(txt(z.get(target)!)), ss);
  result = { rows, sheet: sel, zero: hasHeaderOnlyOrZeroData(rows) };
  cache.set(key, result);
  return result;
}

/* -------- Section 01/02 logic -------- */

function classifySource(s: any): "Regulatory" | "Literature" | "Company" {
  s = norm(s);
  if (s.includes("regulatory")) return "Regulatory";
  if (s.includes("literature")) return "Literature";
  return "Company";
}
function sourceCounts(psurRows: any[][], map: any) {
  const by = { Regulatory: new Set<string>(), Literature: new Set<string>(), Company: new Set<string>() };
  psurRows.forEach((r) => {
    const id = getCell(r, map.psurId);
    const src = classifySource(getCell(r, map.psurSource));
    if (id) by[src].add(id);
  });
  return {
    Regulatory: by.Regulatory.size,
    Literature: by.Literature.size,
    Company: by.Company.size,
    total: by.Regulatory.size + by.Literature.size + by.Company.size,
  };
}
function isSerious(r: any[], map: any): boolean {
  const s = norm(getCell(r, map.esEventSer) || getCell(r, map.esCaseSer));
  if (/^non[- ]?serious$/.test(s)) return false;
  return s.includes("serious");
}
function isUnlistedES(r: any[], map: any): boolean {
  const l = norm(getCell(r, map.esListed));
  return l.includes("unlisted") || l.includes("unexpected");
}
function isOffLabelUseRow(r: any[], map: any): boolean {
  const pt = norm(getCell(r, map.esPt));
  return pt === "off label use" || pt === "off-label use" || pt === "product use in unapproved indication";
}
function eventCounts(esRows: any[][], map: any) {
  const out = { seriousUnlisted: 0, seriousListed: 0, nonSeriousUnlisted: 0, nonSeriousListed: 0, offLabel: 0, total: 0 };
  esRows.forEach((r) => {
    const pt = getCell(r, map.esPt);
    if (!pt) return;
    out.total++;
    if (isOffLabelUseRow(r, map)) { out.offLabel++; return; }
    const ser = isSerious(r, map), un = isUnlistedES(r, map);
    if (ser && un) out.seriousUnlisted++;
    else if (ser && !un) out.seriousListed++;
    else if (!ser && un) out.nonSeriousUnlisted++;
    else out.nonSeriousListed++;
  });
  return out;
}
function makeCurrentTable(src: any, ev: any, period: string): string {
  return `<h3><u>Data for Current period ${period ? "(" + period + ")" : ""}</u></h3><table><tr><th colspan="2">Total Valid ICSR</th><th colspan="2">Adverse events</th></tr><tr><td>Regulatory</td><td>${pad2(src.Regulatory)}</td><td>Serious unlisted</td><td>${pad2(ev.seriousUnlisted)}</td></tr><tr><td>Literature</td><td>${pad2(src.Literature)}</td><td>Serious listed</td><td>${pad2(ev.seriousListed)}</td></tr><tr><td>Company</td><td>${pad2(src.Company)}</td><td>Non-serious unlisted</td><td>${pad2(ev.nonSeriousUnlisted)}</td></tr><tr><td></td><td></td><td>Non-serious listed</td><td>${pad2(ev.nonSeriousListed)}</td></tr><tr><td></td><td></td><td>Off label use</td><td>${pad2(ev.offLabel)}</td></tr><tr><th>Total</th><th>${pad2(src.total)}</th><th>Total</th><th>${pad2(ev.total)}</th></tr></table>`;
}
function makeCumTable(src: any, period: string): string {
  return `<h3><u>Data for cumulative period ${period ? "(" + period + ")" : ""}</u></h3><table><tr><th>Total Valid ICSR</th><th>Regulatory</th><th>Literature</th><th>Company</th><th>Total</th></tr><tr><td>PvEdge</td><td>${pad2(src.Regulatory)}</td><td>${pad2(src.Literature)}</td><td>${pad2(src.Company)}</td><td>${pad2(src.total)}</td></tr></table>`;
}

interface GenerateSectionParams {
  files: {
    psurCurrent: File | null;
    psurCum: File | null;
    esCurrent: File | null;
    esCum: File | null;
    qFile: File | null;
    smqFile: File | null;
  };
  common: any;
  mapping: any;
  cache: Map<string, any>;
}

async function generateSection({ files, common, mapping, cache }: GenerateSectionParams) {
  const pc = files.psurCurrent, ec = files.esCurrent;
  if (!pc || !ec) throw new Error("Upload PSUR Current and Event Summary Current.");
  const [pcr, pcur, ecur, ecum] = await Promise.all([
    readFile(pc, cache), readFile(files.psurCum, cache), readFile(ec, cache), readFile(files.esCum, cache),
  ]);
  const map = mapping;
  const psurCurrent = dataRows(pcr.rows), psurCum = dataRows(pcur.rows), esCurrent = dataRows(ecur.rows);
  const drug = escHtml(common.drug || "the product");
  const client = escHtml(common.client || "the MAH");
  const period = [common.from, common.to].map(escHtml).filter(Boolean).join(" to ");
  const cumPeriod = [common.cumFrom, common.cumTo || common.to].map(escHtml).filter(Boolean).join(" to ");
  const currentCaseCount = unique(esCurrent.map((r) => getCell(r, map.esId))).length || sourceCounts(psurCurrent, map).total;
  const method = currentCaseCount > 100 ? "qualitative and quantitative" : "qualitative";
  const quantLine = currentCaseCount > 100 ? "<p>Additionally, a quantitative signal detection report was generated.</p>" : "";
  const srcCur = sourceCounts(psurCurrent, map), srcCum = sourceCounts(psurCum, map), evCur = eventCounts(esCurrent, map);
  const intro = `<h2>1. Introduction</h2><p>The ${method} signal detection for ${drug} covers period from ${period}. The signal detection activity is based on the completeness of the available information, relatedness of the event with the drug, and the strength of the causal relationship of the adverse reactions with ${drug}.</p>`;
  const evalPara = "<p>An evaluation based on the increase in frequency/severity of listed ADRs was carried out. Event frequency listings of current period were reviewed against cumulative period and evaluated for drug-event pairs. Based on the evaluation and comparison of both periods, no medically significant increase in frequency or severity of events was identified.</p>";
  const conclusion = (srcCur.total === 0 && evCur.total === 0)
    ? "<p>Based on the available data in the current and cumulative period, no new signal could be identified for further validation.</p>"
    : "<p>Based on the available data in the current and cumulative period, no new signal could be identified for further validation, unless further assessment identifies otherwise.</p>";
  const section2 = `<h2>2. Detection of signals from MAH database</h2><p>Review of the ${client} global safety data, included in the PvEdge database, was done for ${drug}. Event frequency and event summary listings for current period are generated from the PvEdge database.</p>${quantLine}${makeCurrentTable(srcCur, evCur, period)}${makeCumTable(srcCum, cumPeriod)}${evalPara}${conclusion}`;
  return {
    html: intro + section2,
    source: `PSUR Current: ${pcr.sheet} • ES Current: ${ecur.sheet} • PSUR Cumulative: ${pcur.sheet} • ES Cumulative: ${ecum.sheet}`,
    method, cases: pad2(currentCaseCount), events: pad2(evCur.total), icsr: pad2(srcCur.total),
  };
}

/* -------- DME logic -------- */

function headerScore(row: any[], type: "es" | "ps"): number {
  const cells = (row || []).map(norm);
  const keys = type === "es"
    ? ["pt name", "dme", "listedness", "report id", "case seriousness", "event seriousness"]
    : ["reportid", "report id", "casenarrative", "case narrative", "pt", "medical history", "suspect drugs"];
  return keys.filter((k) => cells.some((c) => c === k || c.includes(k))).length;
}
function findHeader(rows: any[][], type: "es" | "ps"): number {
  let best = -1, score = 0;
  for (let i = 0; i < (rows || []).length; i++) {
    const s = headerScore(rows[i], type);
    if (s > score) { score = s; best = i; }
  }
  return score >= 2 ? best : -1;
}
function objectsFromRows(rows: any[][], type: "es" | "ps") {
  const h = findHeader(rows, type);
  if (h < 0) return { headers: [] as string[], data: [] as any[], headerIndex: -1 };
  const headers = (rows[h] || []).map(clean);
  const data = [];
  for (let i = h + 1; i < rows.length; i++) {
    const r = rows[i];
    if (!rowHasData(r)) continue;
    const o: Record<string, string> = {};
    headers.forEach((head, idx) => { if (head) o[head] = clean(r[idx]); });
    data.push(o);
  }
  return { headers, data, headerIndex: h };
}
function pickHeader(headers: string[], manual: string, candidates: string[]): string {
  if (clean(manual)) {
    const m = headers.find((h) => norm(h) === norm(manual)) || headers.find((h) => norm(h).includes(norm(manual)));
    if (m) return m;
  }
  for (const c of candidates) {
    const exact = headers.find((h) => norm(h) === norm(c));
    if (exact) return exact;
  }
  for (const c of candidates) {
    const inc = headers.find((h) => norm(h).includes(norm(c)));
    if (inc) return inc;
  }
  return "";
}
function isDme(v: any): boolean { return ["y", "yes", "true", "1"].includes(norm(v)); }
function isUnlistedVal(v: any): boolean { const x = norm(v); return x.includes("unlisted") || x.includes("unexpected"); }
function buildPsurMap(psurObjs: any[], headers: string[]): Map<string, any[]> {
  const idH = pickHeader(headers, "", ["ReportId", "Report Id", "Report ID"]);
  const narrH = pickHeader(headers, "", ["CaseNarrative", "Case Narrative"]);
  const medH = pickHeader(headers, "", ["Medical History"]);
  const suspH = pickHeader(headers, "", ["Suspect Drugs"]);
  const conH = pickHeader(headers, "", ["Concomitant drugs", "Concomitant Drugs"]);
  const ptH = pickHeader(headers, "", ["PT", "PT Name"]);
  const m = new Map<string, any[]>();
  psurObjs.forEach((o) => {
    const id = clean(o[idH]);
    if (!id) return;
    if (!m.has(id)) m.set(id, []);
    m.get(id)!.push({ pt: o[ptH] || "", narr: o[narrH] || "", med: o[medH] || "", sus: o[suspH] || "", con: o[conH] || "" });
  });
  return m;
}
function truncate(s: string, n = 220): string { s = clean(s); return s.length > n ? s.slice(0, n - 1) + "..." : s; }

interface AnalyseDmeSettings {
  ptCol: string;
  dmeCol: string;
  listedCol: string;
  idCol: string;
  mode: string;
}

function analyseDme(esObj: any, psurObj: any, dmeSettings: AnalyseDmeSettings) {
  const h = esObj.headers;
  const ptH = pickHeader(h, dmeSettings.ptCol, ["PT Name", "PT"]);
  const dmeH = pickHeader(h, dmeSettings.dmeCol, ["DME"]);
  const listedH = pickHeader(h, dmeSettings.listedCol, ["CCSI Listedness", "Listedness", "Other Listedness", "Other_Listedness"]);
  const idH = pickHeader(h, dmeSettings.idCol, ["Report Id", "ReportId", "Report ID", "WorldWide Unique Case Identification Number"]);
  if (!ptH || !dmeH || !listedH) throw new Error("Required Event Summary headers not detected. Need PT Name/PT, DME, and Listedness/CCSI Listedness.");
  const groups = new Map<string, any>();
  let allDmeCount = 0, unlistedCount = 0;
  const caseSet = new Set<string>(), allDmeCaseSet = new Set<string>();
  esObj.data.forEach((o: any, idx: number) => {
    if (!isDme(o[dmeH])) return;
    allDmeCount++;
    const pt = clean(o[ptH]) || "Blank PT";
    const id = clean(o[idH]) || "row " + (idx + 1);
    allDmeCaseSet.add(id);
    if (isUnlistedVal(o[listedH])) {
      unlistedCount++;
      caseSet.add(id);
      if (!groups.has(pt)) groups.set(pt, { pt, events: 0, cases: new Set<string>(), rows: [] as any[] });
      const g = groups.get(pt);
      g.events++; g.cases.add(id); g.rows.push(o);
    }
  });
  const psurMap = buildPsurMap(psurObj.data || [], psurObj.headers || []);
  return { ptH, dmeH, listedH, idH, groups, total: unlistedCount, allDmeCount, cases: caseSet.size, allDmeCases: allDmeCaseSet.size, psurMap };
}
function dmeGroupTable(a: any): string {
  if (!a.groups.size) return "";
  const rows = [...a.groups.values()].sort((x, y) => y.events - x.events || x.pt.localeCompare(y.pt))
    .map((g) => `<tr><td>${escHtml(g.pt)}</td><td>${pad2(g.events)}</td><td>${pad2(g.cases.size)}</td><td>${escHtml([...g.cases].join(", "))}</td></tr>`).join("");
  return `<table><tr><th>PT Name</th><th>DME event count</th><th>Unique case count</th><th>Report ID(s)</th></tr>${rows}</table>`;
}
function dmeReviewListing(a: any): string {
  if (!a.groups.size) return "";
  let html = "<h3>Review listing</h3>";
  [...a.groups.values()].forEach((g) => {
    html += `<p><b>${escHtml(g.pt)}</b> (${pad2(g.events)} event(s); ${pad2(g.cases.size)} case(s))</p><ul>`;
    [...g.cases].forEach((id) => {
      const arr = a.psurMap.get(id) || [];
      if (arr.length) {
        arr.slice(0, 2).forEach((x: any) => {
          html += `<li><b>${escHtml(id)}</b>: ${x.med ? "<br>Medical history: " + escHtml(truncate(x.med)) : ""}${x.sus ? "<br>Suspect drugs: " + escHtml(truncate(x.sus)) : ""}${x.con ? "<br>Concomitant drugs: " + escHtml(truncate(x.con)) : ""}${x.narr ? "<br>Narrative: " + escHtml(truncate(x.narr)) : ""}</li>`;
        });
      } else html += `<li><b>${escHtml(id)}</b>: No matching PSUR narrative row detected.</li>`;
    });
    html += "</ul>";
  });
  return html;
}
function makeDmeOutput(a: any, drug: string, period: string, mode: string): string {
  let html = "<h2>Qualitative Method (For Designated Medical Events (DMEs))</h2>";
  if (a.total === 0) {
    html += `<p>No unlisted Designated Medical Events (DME) were received for ${drug} during ${period}.</p>`;
  } else {
    const pts = [...a.groups.values()].sort((x, y) => y.events - x.events || x.pt.localeCompare(y.pt)).map((g) => `${escHtml(g.pt)} (n=${g.events})`).join(", ");
    html += `<p>A total of ${pad2(a.total)} unlisted designated medical event(s) (DMEs) (PTs: ${pts}) were reported in ${period}.</p>`;
    html += dmeGroupTable(a);
    html += `<p>The above event(s) should be medically reviewed using available case narrative, medical history, co-suspect/concomitant medication, temporal association, dechallenge/rechallenge information, and RSI/label context before deciding whether further signal evaluation is required.</p>`;
  }
  if (mode === "review") html += dmeReviewListing(a);
  return html;
}

interface GenerateDmeParams {
  files: {
    psurCurrent: File | null;
    psurCum: File | null;
    esCurrent: File | null;
    esCum: File | null;
    qFile: File | null;
    smqFile: File | null;
  };
  common: any;
  dmeSettings: AnalyseDmeSettings;
  cache: Map<string, any>;
}

async function generateDme({ files, common, dmeSettings, cache }: GenerateDmeParams) {
  const esf = files.esCurrent;
  if (!esf) throw new Error("Upload common Event Summary Current file.");
  const [esRows, psRows] = await Promise.all([readFile(esf, cache), readFile(files.psurCurrent, cache)]);
  const esObj = objectsFromRows(esRows.rows, "es");
  const psObj = objectsFromRows(psRows.rows, "ps");
  if (esObj.headerIndex < 0) throw new Error("Event Summary header row not detected.");
  const a = analyseDme(esObj, psObj, dmeSettings);
  const drug = escHtml(common.drug || "the product");
  const period = escHtml([common.from, common.to].map(escHtml).filter(Boolean).join(" to ") || "the current period");
  const html = makeDmeOutput(a, drug, period, dmeSettings.mode);
  const source = `ES: ${esRows.sheet} • ES header row: ${esObj.headerIndex + 1} • PT: ${a.ptH} • DME: ${a.dmeH} • Listedness: ${a.listedH} • ID: ${a.idH || "not detected"}${files.psurCurrent ? ` • PSUR: ${psRows.sheet}` : ""}`;
  return { html, source, all: pad2(a.allDmeCount), unlisted: pad2(a.total), zero: a.total === 0 };
}

/* -------- Non-DME quantitative logic -------- */

function qVal(row: any[], colLetter: string): any {
  const i = colToIndex(colLetter);
  return i == null ? "" : row[i] ?? "";
}
function passNonDme(row: any[], q: any) {
  const dme = clean(qVal(row, q.dmeCol)).toUpperCase();
  const label = clean(qVal(row, q.labelCol)).toLowerCase();
  const current = num(qVal(row, q.currentCol));
  const cum = num(qVal(row, q.cumCol));
  const prr = num(qVal(row, q.prrCol));
  const chi = num(qVal(row, q.chiCol));
  return dme === "N" && (label === "unexpected" || label === "unlisted") &&
    !Number.isNaN(cum) && cum >= num(q.cumThreshold) &&
    !Number.isNaN(prr) && prr >= num(q.prrThreshold) &&
    !Number.isNaN(chi) && chi >= num(q.chiThreshold)
    ? { current } : null;
}

interface GenerateNonDmeParams {
  file: File | null;
  qSettings: any;
  cache: Map<string, any>;
}

async function generateNonDme({ file, qSettings, cache }: GenerateNonDmeParams) {
  if (!file) throw new Error("Choose quantitative sheet.");
  const r = await readFile(file, cache);
  const start = Math.max(0, parseInt(qSettings.startRow || "14", 10));
  const totalSet = new Set<string>(), currentList = [];
  for (const row of r.rows.slice(start)) {
    const pt = clean(qVal(row, qSettings.ptCol));
    if (!pt) continue;
    const pass = passNonDme(row, qSettings);
    if (pass) {
      totalSet.add(pt);
      if (!Number.isNaN(pass.current) && pass.current > 0) currentList.push(pt);
    }
  }
  const finalCurrent: string[] = [], seen = new Set<string>();
  for (const pt of currentList) if (!seen.has(pt)) { seen.add(pt); finalCurrent.push(pt); }
  const totalCount = totalSet.size, currentCount = finalCurrent.length;
  const cumTh = clean(qSettings.cumThreshold) || "5", prrTh = clean(qSettings.prrThreshold) || "2", chiTh = clean(qSettings.chiThreshold) || "4";
  const para = `A total of ${totalCount} unlisted events were received with Proportional reporting ratio (PRR) of ${prrTh} or more and CHI square value of ${chiTh} or more and reported at least ${cumTh} times in cumulative period. Out of which ${currentCount} events were reported in current period as SDRs (Signals of Disproportionate Reporting).`;
  const ptText = finalCurrent.map((x, i) => `${i + 1}. ${x}`).join("\n");
  return { para, ptText, total: totalCount, current: currentCount, source: `Quantitative sheet: ${r.sheet} • Data starts after row ${start}`, finalCurrent };
}

/* -------- Special circumstances logic -------- */

function parseAge(text: any): number | null {
  const t = String(text || "").toLowerCase();
  const m = t.match(/(\d{1,3})\s*(-?year|-?yr|years|yrs)\b|aged\s*(\d{1,3})|age\s*[:=-]?\s*(\d{1,3})/);
  return m ? Number(m[1] || m[3] || m[4]) : null;
}
function isElderlyPSUR(r: any[], m: any): boolean {
  const ag = norm(getCell(r, m.psurAge));
  const age = parseAge(getCell(r, m.psurPatient));
  return ag.includes("elderly") || (age !== null && age >= 65);
}
function isPediatricPSUR(r: any[], m: any): boolean {
  const ag = norm(getCell(r, m.psurAge));
  const age = parseAge(getCell(r, m.psurPatient));
  return /(paediatric|pediatric|child|adolescent|infant|newborn|neonate|paed)/.test(ag) || (age !== null && age < 18);
}
function isElderlyES(r: any[], m: any): boolean { return norm(getCell(r, m.esAge)).includes("elderly"); }
function isPediatricES(r: any[], m: any): boolean { return /(paediatric|pediatric|child|children|adolescent|infant|newborn|neonate|paed)/.test(norm(getCell(r, m.esAge))); }
function countPT(rows: any[][], m: any): Map<string, number> {
  const f = new Map<string, number>();
  rows.forEach((r) => { const pt = getCell(r, m.esPt); if (pt) f.set(pt, (f.get(pt) || 0) + 1); });
  return f;
}
function repeated(freq: Map<string, number>, th = 5): string {
  return [...freq.entries()].filter(([_, n]) => n >= th).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([pt, n]) => `${pt} (n=${n})`).join(", ");
}
function buildIndex(rows: any[][], m: any): Map<string, any[][]> {
  const idx = new Map<string, any[][]>();
  rows.forEach((r) => { const id = getCell(r, m.psurId); if (id) { if (!idx.has(id)) idx.set(id, []); idx.get(id)!.push(r); } });
  return idx;
}
function caseInfo(id: string, idx: Map<string, any[][]>, m: any) {
  const r = (idx.get(id) || [])[0] || [];
  return { caseId: id, source: getCell(r, m.psurSource), narr: getCell(r, m.psurNarr), med: getCell(r, m.psurMed), sus: getCell(r, m.psurSus), con: getCell(r, m.psurCon), ind: getCell(r, m.psurInd), pt: getCell(r, m.psurPt), listed: getCell(r, m.psurListed) };
}
function simpleReason(infos: any[]): string {
  if (!infos.length) return "The reviewed cases did not reveal any clinically meaningful pattern suggestive of new significant safety information.";
  const ids = infos.map((x) => x.caseId).join(", ");
  const limited = infos.every((x) => (!x.narr || x.narr.length < 40) && (!x.med || x.med.length < 5));
  if (limited) return `The case(s) (${ids}) had limited information regarding medical history, course of event and contributory factors, hence precluded meaningful further evaluation.`;
  return `The case(s) (${ids}) were reviewed based on available narrative, medical history, therapy details and concomitant medications; however, no clinically meaningful safety pattern was identified.`;
}
function buildElderly(psur: any[][], es: any[][], m: any) {
  const pf = psur.filter((r) => isElderlyPSUR(r, m)), ids = unique(pf.map((r) => getCell(r, m.psurId)));
  const ef = es.filter((r) => isElderlyES(r, m)), un = ef.filter((r) => isUnlistedES(r, m));
  const rep = repeated(countPT(un, m));
  const idx = buildIndex(psur, m);
  const infos = unique(un.map((r) => getCell(r, m.esId))).map((id) => caseInfo(id, idx, m)).filter((x) => x.caseId);
  const freq = rep ? `Among the unlisted events, the following PTs were reported with frequency >=5 during current period: ${rep}.` : "All these unlisted events were reported with the frequency of <5 during current period.";
  return {
    title: "Elderly population",
    meta: { total_cases: ids.length, total_events: ef.length, unlisted_events: un.length },
    paragraph: `A total of ${pad2(ids.length)} cases of drug use in the elderly population were received in the current period with ${ef.length} adverse events. Out of which ${pad2(un.length)} events were reported as unlisted. ${freq} ${simpleReason(infos.slice(0, 2))} Hence, no new significant safety information is identified from review of the cases related to elderly population.`,
  };
}
function buildPediatric(psur: any[][], es: any[][], m: any) {
  const pf = psur.filter((r) => isPediatricPSUR(r, m)), ids = unique(pf.map((r) => getCell(r, m.psurId)));
  const ef = es.filter((r) => isPediatricES(r, m)), un = ef.filter((r) => isUnlistedES(r, m));
  const rep = repeated(countPT(un, m));
  const freq = rep ? `Among the unlisted events, the following PTs were reported with frequency >=5 during current period: ${rep}.` : (un.length ? "All these unlisted events were reported with the frequency of <5 during current period." : "");
  const para = ids.length || ef.length
    ? `A total of ${pad2(ids.length)} cases were received for drug use among paediatric patients in the current period with ${ef.length} adverse events. Out of which, ${pad2(un.length)} events were unlisted. ${freq} Hence, no new significant safety information is identified from review of the cases related to paediatric population.`
    : "No case of drug use among paediatric population was received in the current period.";
  return { title: "Paediatric population", meta: { total_cases: ids.length, total_events: ef.length, unlisted_events: un.length }, paragraph: para };
}
function buildFatal(_psur: any[][], es: any[][], m: any) {
  const rows = es.filter((r) => norm(getCell(r, m.esOutcome)).includes("fatal")), ids = unique(rows.map((r) => getCell(r, m.esId)));
  const para = ids.length
    ? `Fatal outcome: A total of ${pad2(ids.length)} ${ids.length === 1 ? "case" : "cases"} for fatal outcome with ${pad2(rows.length)} fatal adverse ${rows.length === 1 ? "event was" : "events were"} received in the current period. No new significant safety information was received from review of the ${ids.length === 1 ? "case" : "cases"} reported with fatal outcome.`
    : "Fatal outcome: No cases were received for fatal outcome during the current period.";
  return { title: "Fatal outcome", meta: { total_cases: ids.length, total_events: rows.length, unlisted_events: rows.filter((r) => isUnlistedES(r, m)).length }, paragraph: para };
}
function buildOffLabel(_psur: any[][], es: any[][], m: any) {
  const rows = es.filter((r) => isOffLabelUseRow(r, m)), ids = unique(rows.map((r) => getCell(r, m.esId)));
  const pts = [...countPT(rows, m).entries()].map(([pt, n]) => `${pt} (n=${n})`).join(", ");
  const para = ids.length
    ? `Off label use: A total of ${pad2(ids.length)} cases were received for off label use${pts ? " (" + pts + ")" : ""} during current period. Reported indications and case narratives should be reviewed against the approved RSI/label. Hence, no new significant safety information was identified upon review of these cases.`
    : "No case of off label use was received in the current period.";
  return { title: "Off label use", meta: { total_cases: ids.length, total_events: rows.length, unlisted_events: rows.filter((r) => isUnlistedES(r, m)).length }, paragraph: para };
}
function smqTerms(rows: any[][], needle: string): Set<string> {
  const set = new Set<string>();
  (rows || []).forEach((r) => r.forEach((c) => {
    const t = norm(c);
    if (t && t !== needle && !t.includes("smq") && !["pt name", "llt name", "term"].includes(t)) set.add(t);
  }));
  return set;
}
function rowsByTerms(es: any[][], m: any, set: Set<string>, extra: string[] = []): any[][] {
  const ex = new Set(extra.map(norm));
  return es.filter((r) => { const pt = norm(getCell(r, m.esPt)); return pt && (set.has(pt) || ex.has(pt)); });
}
function buildSmqBased(name: string, smqNeedle: string, defaultNo: string, _psur: any[][], es: any[][], smq: any[][], m: any, extra: string[] = []) {
  const set = smqTerms(smq, smqNeedle);
  const rows = rowsByTerms(es, m, set, extra);
  const ids = unique(rows.map((r) => getCell(r, m.esId)));
  const pt = [...countPT(rows, m).entries()].map(([p, n]) => `${p} (n=${n})`).join(", ");
  let para;
  if (!smq.length && !extra.length) para = `Upload SMQ Terms file to generate ${name} section.`;
  else if (!ids.length) para = defaultNo;
  else para = `Cases related to ${name.toLowerCase()} were searched using applicable MedDRA SMQ/direct terms. A total of ${pad2(ids.length)} ${ids.length === 1 ? "case was" : "cases were"} received for ${name.toLowerCase()}${pt ? " (PTs: " + pt + ")" : ""} during the current period. The available case information did not indicate new significant safety information. Hence, no new significant safety information was received from review of ${ids.length === 1 ? "this case" : "these cases"}.`;
  return { title: name, meta: { total_cases: ids.length, total_events: rows.length, unlisted_events: rows.filter((r) => isUnlistedES(r, m)).length }, paragraph: para };
}

interface GenerateSpecialParams {
  files: {
    psurCurrent: File | null;
    psurCum: File | null;
    esCurrent: File | null;
    esCum: File | null;
    qFile: File | null;
    smqFile: File | null;
  };
  mapping: any;
  cache: Map<string, any>;
}

async function generateSpecial({ files, mapping, cache }: GenerateSpecialParams) {
  const pf = files.psurCurrent, ef = files.esCurrent;
  if (!pf || !ef) throw new Error("Upload PSUR Current and Event Summary Current.");
  const [pr, er, sr] = await Promise.all([readFile(pf, cache), readFile(ef, cache), readFile(files.smqFile, cache)]);
  const psur = dataRows(pr.rows), es = dataRows(er.rows), smq = sr.rows.filter(rowHasData), m = mapping;
  const store: Record<string, any> = {
    elderly: buildElderly(psur, es, m),
    pediatric: buildPediatric(psur, es, m),
    fatal: buildFatal(psur, es, m),
    offlabel: buildOffLabel(psur, es, m),
    overdose: buildSmqBased("Overdose", "overdose", "No case of overdose was received in the current period.", psur, es, [], m, ["overdose", "intentional overdose", "accidental overdose", "prescribed overdose", "chronic overdose", "overmedication"]),
    medication: buildSmqBased("Medication error", "medication error", "No case related to medication error was received in the current period.", psur, es, smq, m, ["medication error", "incorrect route of product administration"]),
    pregnancy: buildSmqBased("Pregnancy and lactation", "pregnancy", "No case of drug exposure during pregnancy/lactation was received in the current period.", psur, es, smq, m, ["exposure during pregnancy", "maternal exposure during pregnancy", "exposure during lactation"]),
    abuse: buildSmqBased("Abuse/misuse", "drug abuse", "No case of drug abuse/misuse was received in the current period.", psur, es, smq, m, ["drug abuse", "drug misuse", "substance abuse"]),
    lack: buildSmqBased("Lack of efficacy", "lack of efficacy", "No case related to lack of efficacy was received in the current period.", psur, es, smq, m, ["drug ineffective", "lack of efficacy"]),
  };
  const source = `PSUR: ${pr.sheet} • ES: ${er.sheet} • SMQ: ${sr.sheet}`;
  Object.values(store).forEach((x) => (x.source = source));
  return store;
}

/* -------- Audit -------- */

function auditLine(label: string, r: any, type: "es" | "psur" | null) {
  if (!r || !r.rows) return `${label}: not uploaded`;
  const h = type ? findHeader(r.rows, type === "es" ? "es" : "ps") : findHeaderRowIndex(r.rows);
  const rows = h >= 0 ? r.rows.slice(h + 1).filter(rowHasData).length : Math.max(0, (r.rows || []).length - 11);
  const names = h >= 0 ? (r.rows[h] || []).map(clean).filter(Boolean).slice(0, 12) : [];
  return `${label}: sheet=${r.sheet}; header row=${h >= 0 ? h + 1 : "not detected"}; data rows=${rows}; columns=${names.join(", ") || "not detected"}`;
}

/* ============================== default state ============================== */

const DEFAULT_MAPPING = {
  psurId: "C", psurReaction: "D", psurLlt: "E", psurPt: "F", psurListed: "G", psurSerious: "H",
  psurNarr: "J", psurSource: "K", psurSus: "O", psurMed: "P", psurPatient: "W", psurAge: "X",
  psurInd: "AC", psurAction: "AD", psurStart: "AF", psurEnd: "AG", psurDur: "AH",
  psurEventStart: "AI", psurEventEnd: "AJ", psurCon: "AK",
  esId: "A", esPt: "K", esOutcome: "L", esListed: "M", esCaseSer: "N", esEventSer: "O", esAge: "AB",
};
const MAPPING_FIELDS = [
  ["psurId", "PSUR Report ID"], ["psurReaction", "PSUR Reaction Desc"], ["psurLlt", "PSUR LLT"],
  ["psurPt", "PSUR PT"], ["psurListed", "PSUR Listedness"], ["psurSerious", "PSUR Seriousness"],
  ["psurNarr", "PSUR Narrative"], ["psurSource", "PSUR Source"], ["psurSus", "PSUR Suspect Drugs"],
  ["psurMed", "PSUR Medical History"], ["psurPatient", "PSUR Patient Details"], ["psurAge", "PSUR Age Group"],
  ["psurInd", "PSUR Indication"], ["psurAction", "PSUR Action Taken"], ["psurStart", "PSUR Start Date"],
  ["psurEnd", "PSUR End Date"], ["psurDur", "PSUR Therapy Duration"], ["psurEventStart", "PSUR Event Start"],
  ["psurEventEnd", "PSUR Event End"], ["psurCon", "PSUR Concomitant"], ["esId", "ES Report ID"],
  ["esPt", "ES PT"], ["esOutcome", "ES Outcome"], ["esListed", "ES Listedness"],
  ["esCaseSer", "ES Case Seriousness"], ["esEventSer", "ES Event Seriousness"], ["esAge", "ES Age Group"],
];
const DEFAULT_COMMON = { drug: "", client: "Accord", prepared: "", from: "01-Jan-2026", to: "31-Mar-2026", cumFrom: "", cumTo: "31-Mar-2026" };
const DEFAULT_DME: AnalyseDmeSettings = { mode: "report", ptCol: "", dmeCol: "", listedCol: "", idCol: "" };
const DEFAULT_Q = { cumThreshold: "5", prrThreshold: "2", chiThreshold: "4", ptCol: "A", dmeCol: "B", labelCol: "C", currentCol: "D", cumCol: "E", prrCol: "O", chiCol: "S", startRow: "14" };

const SP_TABS = [
  ["elderly", "Elderly"], ["pediatric", "Paediatric"], ["medication", "Medication Error"], ["fatal", "Fatal"],
  ["offlabel", "Off-label"], ["pregnancy", "Pregnancy/Lactation"], ["abuse", "Abuse/Misuse"],
  ["overdose", "Overdose"], ["lack", "Lack of Efficacy"],
];

/* ============================== small UI atoms ============================== */

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function Field({ label, hint, children }: FieldProps) {
  return (
    <div className="mb-3">
      <label className="block text-[11px] font-extrabold uppercase tracking-wide text-slate-500 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-400 leading-snug mt-1">{hint}</p>}
    </div>
  );
}
const inputCls = "w-full border border-slate-300 rounded-[11px] px-3 py-2 bg-white text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500";

interface TextInputProps {
  value: any;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}

function TextInput({ value, onChange, placeholder, type = "text" }: TextInputProps) {
  return <input type={type} className={inputCls} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />;
}

interface FileInputProps {
  onChange: (f: File | null) => void;
  current: File | null;
}

function FileInput({ onChange, current }: FileInputProps) {
  return (
    <div>
      <input type="file" accept=".xlsx,.xlsm,.csv" className="w-full text-sm border border-slate-300 rounded-[11px] px-3 py-2 bg-white file:mr-3 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:bg-slate-900 file:text-white file:text-xs file:font-semibold"
        onChange={(e) => onChange(e.target.files?.[0] || null)} />
      {current && <p className="text-xs text-emerald-700 mt-1 truncate">✓ {current.name}</p>}
    </div>
  );
}

interface BtnProps {
  children: React.ReactNode;
  onClick: () => void;
  variant?: "default" | "primary" | "blue";
  disabled?: boolean;
  icon?: React.ComponentType<any>;
}

function Btn({ children, onClick, variant = "default", disabled, icon: Icon }: BtnProps) {
  const base = "inline-flex items-center gap-1.5 border rounded-[11px] px-3.5 py-2.5 font-extrabold text-sm cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed";
  const variants = {
    default: "border-slate-300 bg-white text-slate-800 hover:bg-slate-50",
    primary: "border-[#0b1f44] bg-[#0b1f44] text-white hover:bg-[#0f2a5c]",
    blue: "border-blue-600 bg-blue-600 text-white hover:bg-blue-700",
  };
  return <button className={`${base} ${variants[variant]}`} onClick={onClick} disabled={disabled}>{Icon && <Icon size={15} />}{children}</button>;
}

interface MetricProps {
  k: string;
  v: any;
}

function Metric({ k, v }: MetricProps) {
  return (
    <div className="border border-slate-200 rounded-2xl p-3 bg-white">
      <div className="text-[11px] uppercase text-slate-400 font-extrabold">{k}</div>
      <div className="text-[22px] font-black mt-1.5 text-slate-900">{v}</div>
    </div>
  );
}

interface StatusLineProps {
  status: { text: string; cls?: string };
}

function StatusLine({ status }: StatusLineProps) {
  if (!status || !status.text) return null;
  const cls = status.cls === "ok" ? "text-emerald-700" : status.cls === "err" ? "text-red-700" : "text-slate-500";
  const Icon = status.cls === "ok" ? CheckCircle2 : status.cls === "err" ? AlertCircle : null;
  return (
    <div className={`text-sm mt-3 whitespace-pre-wrap flex items-start gap-1.5 ${cls}`}>
      {Icon && <Icon size={15} className="mt-0.5 shrink-0" />}
      <span>{status.text}</span>
    </div>
  );
}

interface TabProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function Tab({ active, onClick, children }: TabProps) {
  return (
    <button onClick={onClick} className={`border rounded-[13px] px-4 py-2.5 font-black text-sm cursor-pointer transition ${active ? "bg-[#0b1f44] text-white border-[#0b1f44]" : "bg-white text-[#10203f] border-slate-300 hover:bg-slate-50"}`}>
      {children}
    </button>
  );
}

/* ============================== main component ============================== */

export const GeneratorPage: React.FC = () => {
  const cache = useRef(new Map()).current;
  const sectionRef = useRef<HTMLDivElement>(null);
  const dmeRef = useRef<HTMLDivElement>(null);

  const [common, setCommon] = useState(DEFAULT_COMMON);
  const [mapping, setMapping] = useState<Record<string, string>>(DEFAULT_MAPPING);
  const [files, setFiles] = useState<{
    psurCurrent: File | null;
    psurCum: File | null;
    esCurrent: File | null;
    esCum: File | null;
    qFile: File | null;
    smqFile: File | null;
  }>({ psurCurrent: null, psurCum: null, esCurrent: null, esCum: null, qFile: null, smqFile: null });
  const [dmeSettings, setDmeSettings] = useState<AnalyseDmeSettings>(DEFAULT_DME);
  const [qSettings, setQSettings] = useState(DEFAULT_Q);

  const [activePanel, setActivePanel] = useState("sec");
  const [activeSp, setActiveSp] = useState("elderly");

  const [sectionOut, setSectionOut] = useState<any>(null);
  const [dmeOut, setDmeOut] = useState<any>(null);
  const [qOut, setQOut] = useState({ para: "", ptText: "" });
  const [qMeta, setQMeta] = useState<any>(null);
  const [specialStore, setSpecialStore] = useState<Record<string, any>>({});

  const [statuses, setStatuses] = useState<Record<string, { text: string; cls: string }>>({
    all: { text: "Ready.", cls: "" },
    s: { text: "Ready.", cls: "" },
    dme: { text: "Ready.", cls: "" },
    q: { text: "Ready.", cls: "" },
    sp: { text: "Ready.", cls: "" }
  });
  const [auditText, setAuditText] = useState("No validation performed.");

  const setStatus = (k: string, text: string, cls = "") => setStatuses((p) => ({ ...p, [k]: { text, cls } }));
  const setFile = (k: string, f: File | null) => setFiles((p) => ({ ...p, [k]: f }));
  const setMapField = (k: string, v: string) => setMapping((p) => ({ ...p, [k]: v }));

  const runSection = useCallback(async () => {
    try {
      setStatus("s", "Reading uploaded files...");
      const r = await generateSection({ files, common, mapping, cache });
      setSectionOut(r);
      setStatus("s", "Section 01/02 draft generated.", "ok");
      return r;
    } catch (e: any) { setStatus("s", e.message || String(e), "err"); throw e; }
  }, [files, common, mapping, cache]);

  const runDme = useCallback(async () => {
    try {
      setStatus("dme", "Reading file(s)...");
      const r = await generateDme({ files, common, dmeSettings, cache });
      setDmeOut(r);
      setStatus("dme", r.zero ? "No unlisted DME detected." : "Unlisted DME detected and grouped by PT Name.", "ok");
      return r;
    } catch (e: any) { setStatus("dme", e.message || String(e), "err"); throw e; }
  }, [files, common, dmeSettings, cache]);

  const runNonDme = useCallback(async () => {
    try {
      setStatus("q", "Reading quantitative sheet...");
      const r = await generateNonDme({ file: files.qFile, qSettings, cache });
      setQOut({ para: r.para, ptText: r.ptText });
      setQMeta(r);
      setStatus("q", `Done | Total: ${r.total} | Current SDRs: ${r.current}`, "ok");
      return r;
    } catch (e: any) { setStatus("q", e.message || String(e), "err"); throw e; }
  }, [files.qFile, qSettings, cache]);

  const runSpecial = useCallback(async () => {
    try {
      setStatus("sp", "Reading files...");
      const store = await generateSpecial({ files, mapping, cache });
      setSpecialStore(store);
      setStatus("sp", "Special Circumstances drafts generated.", "ok");
      return store;
    } catch (e: any) { setStatus("sp", e.message || String(e), "err"); throw e; }
  }, [files, mapping, cache]);

  const validateFiles = useCallback(async (showOk = true) => {
    const lines = [];
    lines.push("PV Integrated Signal Drafting Studio - Validation & Audit Summary");
    lines.push("Generated: " + new Date().toLocaleString());
    lines.push("Product: " + (clean(common.drug) || "not entered"));
    lines.push("Period: " + [common.from, common.to].map(clean).filter(Boolean).join(" to "));
    const list: Array<[string, File | null, "psur" | "es" | null]> = [
      ["PSUR Current", files.psurCurrent, "psur"], ["PSUR Cumulative", files.psurCum, "psur"],
      ["ES Current", files.esCurrent, "es"], ["ES Cumulative", files.esCum, "es"],
      ["Quantitative", files.qFile, null], ["SMQ", files.smqFile, null],
    ];
    for (const [label, file, type] of list) {
      if (!file) { lines.push(label + ": not uploaded"); continue; }
      try {
        const r = await readFile(file, cache);
        lines.push(auditLine(label, r, type));
        if (r.zero) lines.push("  warning: header detected but zero data rows.");
      } catch (e: any) { lines.push(label + ": ERROR - " + (e.message || e)); }
    }
    lines.push("Logic: Common uploads are reused by Section 01/02, DME, Non-DME, and Special Circumstances.");
    const text = lines.join("\n");
    setAuditText(text);
    if (showOk) setStatus("all", "Validation completed. Review audit summary before final use.", "ok");
    return text;
  }, [files, common, cache]);

  const runAll = useCallback(async () => {
    const notes = [];
    setStatus("all", "Generating available sections...");
    try { await validateFiles(false); notes.push("Validation completed."); } catch (e: any) { notes.push("Validation warning: " + (e.message || e)); }
    if (files.psurCurrent && files.esCurrent) {
      try { await runSection(); notes.push("Section 01/02 generated."); } catch (e: any) { notes.push("Section 01/02 error: " + (e.message || e)); }
      try { await runDme(); notes.push("DME generated."); } catch (e: any) { notes.push("DME error: " + (e.message || e)); }
      try { await runSpecial(); notes.push("Special Circumstances generated."); } catch (e: any) { notes.push("Special Circumstances error: " + (e.message || e)); }
    } else notes.push("Section/DME/Special skipped: PSUR Current and ES Current required.");
    if (files.qFile) {
      try { await runNonDme(); notes.push("Non-DME generated."); } catch (e: any) { notes.push("Non-DME error: " + (e.message || e)); }
    } else notes.push("Non-DME skipped: quantitative sheet not uploaded.");
    setStatus("all", notes.join("\n"), "ok");
  }, [files, validateFiles, runSection, runDme, runSpecial, runNonDme]);

  const clearAll = () => {
    setCommon((p) => ({ ...p, drug: "", prepared: "", cumFrom: "" }));
    setFiles({ psurCurrent: null, psurCum: null, esCurrent: null, esCum: null, qFile: null, smqFile: null });
    setSectionOut(null); setDmeOut(null); setQOut({ para: "", ptText: "" }); setQMeta(null); setSpecialStore({});
    setAuditText("No validation performed.");
    setStatuses({ all: { text: "Ready.", cls: "" }, s: { text: "Ready.", cls: "" }, dme: { text: "Ready.", cls: "" }, q: { text: "Ready.", cls: "" }, sp: { text: "Ready.", cls: "" } });
    cache.clear();
  };

  /* clipboard helpers */
  const copyText = async (text: string) => {
    if (!clean(text)) { alert("No output"); return; }
    try { await navigator.clipboard.writeText(text); } catch (e) {
      const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove();
    }
  };
  const copyRich = async (ref: React.RefObject<HTMLDivElement | null>) => {
    const el = ref.current;
    if (!el || !clean(el.innerText)) { alert("No output"); return; }
    const html = `<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Segoe UI,Arial,sans-serif;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border:1px solid #777;padding:8px}th{background:#edf2fb}</style></head><body>${el.innerHTML}</body></html>`;
    const plain = el.innerText;
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([new window.ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([plain], { type: "text/plain" }) })]);
      } else throw new Error("fallback");
    } catch (e) {
      const range = document.createRange(); range.selectNodeContents(el);
      const sel = window.getSelection(); sel!.removeAllRanges(); sel!.addRange(range);
      document.execCommand("copy"); sel!.removeAllRanges();
    }
  };

  const downloadAll = () => {
    const parts = [];
    if (sectionOut) parts.push("SECTION 01/02\n" + (sectionRef.current ? sectionRef.current.innerText : ""));
    if (dmeOut) parts.push("DME\n" + (dmeRef.current ? dmeRef.current.innerText : ""));
    if (qOut.para || qOut.ptText) parts.push("NON-DME\n" + qOut.para + "\n\n" + qOut.ptText);
    Object.keys(specialStore).forEach((k) => parts.push(String(specialStore[k].title || k).toUpperCase() + "\n" + (specialStore[k].paragraph || "")));
    const blob = new Blob([parts.join("\n\n---\n\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "PV_Integrated_Drafts_Common_Upload_v1_0.txt";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const activeSpDraft = specialStore[activeSp];

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(180deg,#f8fbff 0%,#f5f7fb 100%)" }}>
      <div className="max-w-[1460px] mx-auto p-6 font-sans text-[#10203f]">

        {/* Hero */}
        <div className="rounded-[22px] p-6 mb-5 text-white shadow-lg" style={{ background: "linear-gradient(135deg,#0b1f44,#163168)" }}>
          <h1 className="text-3xl font-black m-0">PV Integrated Signal Drafting Studio</h1>
          <p className="mt-2 text-blue-100 text-sm">One upload area for Section 01/02, DME, Quantitative Non-DME, and all Special Circumstances outputs.</p>
        </div>

        {/* Common upload card */}
        <section className="bg-white border border-slate-200 rounded-[18px] shadow-lg p-5 mb-5">
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2.5 mb-4 text-xs text-amber-800">
            <b>Common upload:</b> Upload source files once. All modules below will reuse the same files and column mappings.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Field label="Drug name"><TextInput value={common.drug} onChange={(v) => setCommon((p) => ({ ...p, drug: v }))} placeholder="e.g. trastuzumab" /></Field>
            <Field label="Client / MAH"><TextInput value={common.client} onChange={(v) => setCommon((p) => ({ ...p, client: v }))} /></Field>
            <Field label="Prepared by / note optional"><TextInput value={common.prepared} onChange={(v) => setCommon((p) => ({ ...p, prepared: v }))} placeholder="optional" /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Current period from"><TextInput value={common.from} onChange={(v) => setCommon((p) => ({ ...p, from: v }))} /></Field>
            <Field label="Current period to"><TextInput value={common.to} onChange={(v) => setCommon((p) => ({ ...p, to: v }))} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Cumulative period from"><TextInput value={common.cumFrom} onChange={(v) => setCommon((p) => ({ ...p, cumFrom: v }))} placeholder="e.g. 28-May-2020" /></Field>
            <Field label="Cumulative period to"><TextInput value={common.cumTo} onChange={(v) => setCommon((p) => ({ ...p, cumTo: v }))} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="PSUR Current" hint="Used for source counts, narratives, and special cases.">
              <FileInput current={files.psurCurrent} onChange={(f) => setFile("psurCurrent", f)} />
            </Field>
            <Field label="PSUR Cumulative optional"><FileInput current={files.psurCum} onChange={(f) => setFile("psurCum", f)} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Event Summary Current" hint="Used for Section 02 table, DME, and special circumstances.">
              <FileInput current={files.esCurrent} onChange={(f) => setFile("esCurrent", f)} />
            </Field>
            <Field label="Event Summary Cumulative optional"><FileInput current={files.esCum} onChange={(f) => setFile("esCum", f)} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Quantitative Non-DME Sheet optional"><FileInput current={files.qFile} onChange={(f) => setFile("qFile", f)} /></Field>
            <Field label="SMQ Terms Sheet optional" hint="Required for Medication error, Pregnancy/lactation, Abuse/misuse, and Lack of efficacy.">
              <FileInput current={files.smqFile} onChange={(f) => setFile("smqFile", f)} />
            </Field>
          </div>

          <details className="border border-slate-200 rounded-[13px] p-3 mb-3 bg-[#fbfdff]">
            <summary className="font-extrabold cursor-pointer text-sm">Column mapping</summary>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
              {MAPPING_FIELDS.map(([key, label]) => (
                <Field key={key} label={label}><TextInput value={mapping[key]} onChange={(v) => setMapField(key, v)} /></Field>
              ))}
            </div>
          </details>

          <div className="flex gap-2 flex-wrap mt-3">
            <Btn variant="primary" icon={Play} onClick={runAll}>Generate All</Btn>
            <Btn icon={ClipboardCheck} onClick={() => validateFiles(true)}>Validate Files</Btn>
            <Btn icon={ClipboardCopy} disabled={auditText === "No validation performed."} onClick={() => copyText(auditText)}>Copy Audit</Btn>
            <Btn icon={Download} disabled={!sectionOut && !dmeOut && !qOut.para && Object.keys(specialStore).length === 0} onClick={downloadAll}>Download All TXT</Btn>
            <Btn icon={Trash2} onClick={clearAll}>Clear All</Btn>
          </div>
          <StatusLine status={statuses.all} />
          <div className="text-sm mt-3 border border-slate-200 rounded-xl p-3 bg-[#fbfdff] max-h-56 overflow-auto whitespace-pre-wrap text-slate-600">{auditText}</div>
        </section>

        {/* Tabs */}
        <div className="flex gap-2.5 flex-wrap my-4">
          <Tab active={activePanel === "sec"} onClick={() => setActivePanel("sec")}>Section 01/02</Tab>
          <Tab active={activePanel === "dme"} onClick={() => setActivePanel("dme")}>DME</Tab>
          <Tab active={activePanel === "nondme"} onClick={() => setActivePanel("nondme")}>Non-DME</Tab>
          <Tab active={activePanel === "special"} onClick={() => setActivePanel("special")}>Special Circumstances</Tab>
        </div>

        {/* Section 01/02 panel */}
        {activePanel === "sec" && (
          <div className="bg-white border border-slate-200 rounded-[18px] shadow-lg p-5">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Section 01 / 02 - Introduction & MAH Database</h2>
              <div className="flex gap-2">
                <Btn variant="primary" icon={Play} onClick={runSection}>Generate Section</Btn>
                <Btn icon={ClipboardCheck} onClick={() => copyRich(sectionRef)} disabled={!sectionOut}>Copy Rich Table</Btn>
                <Btn icon={ClipboardCopy} onClick={() => copyText(sectionOut?.html)} disabled={!sectionOut}>Copy HTML</Btn>
              </div>
            </div>
            <StatusLine status={statuses.s} />
            {sectionOut && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 my-4">
                <Metric k="Method" v={sectionOut.method} />
                <Metric k="Cases" v={sectionOut.cases} />
                <Metric k="Events" v={sectionOut.events} />
                <Metric k="ICSR" v={sectionOut.icsr} />
              </div>
            )}
            <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 max-h-[600px] overflow-auto prose max-w-none pv-report-preview">
              {sectionOut ? (
                <div ref={sectionRef} dangerouslySetInnerHTML={{ __html: sectionOut.html }} />
              ) : (
                <p className="text-slate-400 text-sm text-center py-10">Upload PSUR and Event Summary sheets, then click Generate.</p>
              )}
            </div>
          </div>
        )}

        {/* DME Panel */}
        {activePanel === "dme" && (
          <div className="bg-white border border-slate-200 rounded-[18px] shadow-lg p-5">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Designated Medical Events (DME)</h2>
              <div className="flex gap-2">
                <Btn variant="primary" icon={Play} onClick={runDme}>Generate DME</Btn>
                <Btn icon={ClipboardCheck} onClick={() => copyRich(dmeRef)} disabled={!dmeOut}>Copy Rich Table</Btn>
                <Btn icon={ClipboardCopy} onClick={() => copyText(dmeOut?.html)} disabled={!dmeOut}>Copy HTML</Btn>
              </div>
            </div>
            
            <div className="bg-slate-50/50 border border-slate-200 rounded-xl p-4 mb-4">
              <h4 className="font-extrabold text-xs uppercase text-slate-500 mb-3">DME Configuration & Mappings</h4>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <Field label="PT Name ColumnOverride"><TextInput value={dmeSettings.ptCol} onChange={(v) => setDmeSettings((p) => ({ ...p, ptCol: v }))} placeholder="e.g. PT Name" /></Field>
                <Field label="DME ColumnOverride"><TextInput value={dmeSettings.dmeCol} onChange={(v) => setDmeSettings((p) => ({ ...p, dmeCol: v }))} placeholder="e.g. DME" /></Field>
                <Field label="Listedness ColumnOverride"><TextInput value={dmeSettings.listedCol} onChange={(v) => setDmeSettings((p) => ({ ...p, listedCol: v }))} placeholder="e.g. Listedness" /></Field>
                <Field label="ID ColumnOverride"><TextInput value={dmeSettings.idCol} onChange={(v) => setDmeSettings((p) => ({ ...p, idCol: v }))} placeholder="e.g. Report ID" /></Field>
                <Field label="Mode">
                  <select className={inputCls} value={dmeSettings.mode} onChange={(e) => setDmeSettings((p) => ({ ...p, mode: e.target.value }))}>
                    <option value="report">Report Mode</option>
                    <option value="review">Review Mode (Show Narratives)</option>
                  </select>
                </Field>
              </div>
            </div>

            <StatusLine status={statuses.dme} />
            
            {dmeOut && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
                <Metric k="All DMEs" v={dmeOut.all} />
                <Metric k="Unlisted DMEs" v={dmeOut.unlisted} />
                <Metric k="Zero Unlisted" v={dmeOut.zero ? "Yes" : "No"} />
              </div>
            )}
            
            <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 max-h-[600px] overflow-auto prose max-w-none pv-report-preview">
              {dmeOut ? (
                <div ref={dmeRef} dangerouslySetInnerHTML={{ __html: dmeOut.html }} />
              ) : (
                <p className="text-slate-400 text-sm text-center py-10">Upload Event Summary and PSUR Current, then click Generate.</p>
              )}
            </div>
          </div>
        )}

        {/* Non-DME Panel */}
        {activePanel === "nondme" && (
          <div className="bg-white border border-slate-200 rounded-[18px] shadow-lg p-5">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Quantitative Non-DME</h2>
              <div className="flex gap-2">
                <Btn variant="primary" icon={Play} onClick={runNonDme}>Generate Non-DME</Btn>
                <Btn icon={ClipboardCopy} onClick={() => copyText(`${qOut.para}\n\n${qOut.ptText}`)} disabled={!qOut.para}>Copy Draft</Btn>
              </div>
            </div>
            
            <div className="bg-slate-50/50 border border-slate-200 rounded-xl p-4 mb-4">
              <h4 className="font-extrabold text-xs uppercase text-slate-500 mb-3">Quantitative Rules & Thresholds</h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-3">
                <Field label="Cum Count Threshold"><TextInput value={qSettings.cumThreshold} onChange={(v) => setQSettings((p) => ({ ...p, cumThreshold: v }))} /></Field>
                <Field label="PRR Threshold"><TextInput value={qSettings.prrThreshold} onChange={(v) => setQSettings((p) => ({ ...p, prrThreshold: v }))} /></Field>
                <Field label="Chi Square Threshold"><TextInput value={qSettings.chiThreshold} onChange={(v) => setQSettings((p) => ({ ...p, chiThreshold: v }))} /></Field>
                <Field label="PT Column Letter"><TextInput value={qSettings.ptCol} onChange={(v) => setQSettings((p) => ({ ...p, ptCol: v }))} /></Field>
                <Field label="DME Column Letter"><TextInput value={qSettings.dmeCol} onChange={(v) => setQSettings((p) => ({ ...p, dmeCol: v }))} /></Field>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                <Field label="Label Column Letter"><TextInput value={qSettings.labelCol} onChange={(v) => setQSettings((p) => ({ ...p, labelCol: v }))} /></Field>
                <Field label="Current Col Letter"><TextInput value={qSettings.currentCol} onChange={(v) => setQSettings((p) => ({ ...p, currentCol: v }))} /></Field>
                <Field label="Cumulative Col Letter"><TextInput value={qSettings.cumCol} onChange={(v) => setQSettings((p) => ({ ...p, cumCol: v }))} /></Field>
                <Field label="PRR Column Letter"><TextInput value={qSettings.prrCol} onChange={(v) => setQSettings((p) => ({ ...p, prrCol: v }))} /></Field>
                <Field label="Chi Column Letter"><TextInput value={qSettings.chiCol} onChange={(v) => setQSettings((p) => ({ ...p, chiCol: v }))} /></Field>
                <Field label="Start Row Index"><TextInput value={qSettings.startRow} onChange={(v) => setQSettings((p) => ({ ...p, startRow: v }))} /></Field>
              </div>
            </div>

            <StatusLine status={statuses.q} />
            
            {qMeta && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
                <Metric k="Total Passed" v={qMeta.total} />
                <Metric k="Current SDRs" v={qMeta.current} />
                <Metric k="Source" v={qMeta.source.split("•")[0]} />
              </div>
            )}

            <div className="space-y-4">
              {qOut.para ? (
                <>
                  <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 text-sm leading-relaxed text-slate-700">
                    <p className="font-bold mb-2">Generated Paragraph:</p>
                    <p>{qOut.para}</p>
                  </div>
                  {qOut.ptText && (
                    <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 font-mono text-xs text-slate-700 whitespace-pre-wrap">
                      <p className="font-bold mb-2 text-sm font-sans">Signals of Disproportionate Reporting (SDRs):</p>
                      {qOut.ptText}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-slate-400 text-sm text-center py-10">Upload Quantitative Non-DME Sheet, then click Generate.</p>
              )}
            </div>
          </div>
        )}

        {/* Special Circumstances Panel */}
        {activePanel === "special" && (
          <div className="bg-white border border-slate-200 rounded-[18px] shadow-lg p-5">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Special Circumstances</h2>
              <div className="flex gap-2">
                <Btn variant="primary" icon={Play} onClick={runSpecial}>Generate All Special</Btn>
                <Btn icon={ClipboardCopy} onClick={() => copyText(activeSpDraft?.paragraph)} disabled={!activeSpDraft?.paragraph}>Copy Active Tab Text</Btn>
              </div>
            </div>

            <StatusLine status={statuses.sp} />

            {/* Sub Tabs */}
            <div className="flex gap-1.5 flex-wrap my-4 border-b border-slate-200 pb-3">
              {SP_TABS.map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setActiveSp(key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                    activeSp === key
                      ? "bg-[#0b1f44] text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {label} {specialStore[key] ? "✓" : ""}
                </button>
              ))}
            </div>

            {activeSpDraft ? (
              <div className="space-y-4">
                {activeSpDraft.meta && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Metric k="Cases" v={activeSpDraft.meta.total_cases} />
                    <Metric k="Events" v={activeSpDraft.meta.total_events} />
                    <Metric k="Unlisted Events" v={activeSpDraft.meta.unlisted_events} />
                  </div>
                )}
                <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 text-sm leading-relaxed text-slate-700">
                  <p className="font-bold mb-2">{activeSpDraft.title}:</p>
                  <p>{activeSpDraft.paragraph}</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-400 text-sm text-center py-10">Upload PSUR and Event Summary sheets, then click Generate.</p>
            )}
          </div>
        )}

        {/* Style injection for report HTML tables */}
        <style>{`
          .pv-report-preview h2 { font-size: 1.25rem; font-weight: 850; color: #0b1f44; margin-top: 1.5rem; margin-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.25rem; }
          .pv-report-preview h3 { font-size: 1.1rem; font-weight: 750; color: #0f2a5c; margin-top: 1.25rem; margin-bottom: 0.5rem; }
          .pv-report-preview p { font-size: 0.875rem; line-height: 1.5rem; color: #334155; margin-bottom: 1rem; }
          .pv-report-preview table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.875rem; background: #fff; }
          .pv-report-preview th, .pv-report-preview td { border: 1px solid #cbd5e1; padding: 0.75rem; text-align: left; }
          .pv-report-preview th { background-color: #edf2fb; font-weight: 700; color: #10203f; }
          .pv-report-preview tr:nth-child(even) { background-color: #f8fafc; }
        `}</style>

      </div>
    </div>
  );
};

export default GeneratorPage;
