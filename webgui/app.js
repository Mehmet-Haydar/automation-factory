/* AUTOMATION_FACTORY — Workbench web GUI front-end.
   Dense Cockpit · Emerald IDE.
   Talks to the Python backend via window.pywebview.api.
   Falls back to sample data when opened in a plain browser. */

"use strict";

/* ─────────────────────────────────────────────────────────────────────
   ICONS  (Lucide-style inline SVG paths)
───────────────────────────────────────────────────────────────────── */
const ICONS = {
  factory:       '<path d="M2 20a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1V9l-6 4V9l-6 4V8L2 12Z"/><path d="M7 18h.01M12 18h.01M17 18h.01"/>',
  search:        '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  settings:      '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V15z"/>',
  moon:          '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  sun:           '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  "chevron-right":'<path d="m9 18 6-6-6-6"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  folder:        '<path d="M4 20a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2z"/>',
  "folder-open": '<path d="M6 14l1.45-2.9A2 2 0 0 1 9.24 10H21a2 2 0 0 1 1.94 2.5l-1.55 6A2 2 0 0 1 19.46 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/>',
  file:          '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  "file-code":   '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 13-2 2 2 2"/><path d="m15 13 2 2-2 2"/>',
  "file-text":   '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8M16 17H8M10 9H8"/>',
  "git-branch":  '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
  flow:          '<circle cx="12" cy="4" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M10.8 6.2 6.2 16.8"/><path d="M13.2 6.2l4.6 10.6"/><path d="M7.5 19h9"/>',
  sparkles:      '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/>',
  cpu:           '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>',
  chip:          '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>',
  package:       '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  layers:        '<path d="m12 2 9 5-9 5-9-5 9-5z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  plus:          '<path d="M12 5v14M5 12h14"/>',
  refresh:       '<path d="M3 12a9 9 0 0 1 9-9 9 9 0 0 1 6.36 2.64L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9 9 0 0 1-6.36-2.64L3 16"/><path d="M3 21v-5h5"/>',
  more:          '<circle cx="5" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="19" cy="12" r="1.4" fill="currentColor"/>',
  x:             '<path d="M18 6 6 18M6 6l12 12"/>',
  check:         '<path d="M20 6 9 17l-5-5"/>',
  play:          '<path d="m6 3 14 9-14 9V3z"/>',
  upload:        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
  table:         '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M12 3v18"/>',
  send:          '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  history:       '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
  alert:         '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><path d="M12 9v4M12 17h.01"/>',
  "panel-bottom":'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 15h18"/>',
  "panel-right": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M15 3v18"/>',
  filter:        '<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>',
  dot:           '<circle cx="12" cy="12" r="3" fill="currentColor"/>',
  shield:        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  save:          '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
  trash:         '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
  edit:          '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
  copy:          '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  "folder-plus": '<path d="M4 20a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/>',
  "git-commit":  '<circle cx="12" cy="12" r="3"/><line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/>',
  zap:           '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  "bar-chart":   '<rect x="3" y="12" width="4" height="9"/><rect x="10" y="7" width="4" height="14"/><rect x="17" y="3" width="4" height="18"/>',
  loader:        '<line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>',
};

function svg(name, size) {
  const inner = ICONS[name] || ICONS.file;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}
function injectIcons(root) {
  (root || document).querySelectorAll(".ic[data-i]").forEach((el) => {
    const s = parseInt(el.getAttribute("data-s") || "14", 10);
    el.innerHTML = svg(el.getAttribute("data-i"), s);
  });
}

/* ─────────────────────────────────────────────────────────────────────
   SCL SYNTAX HIGHLIGHT
───────────────────────────────────────────────────────────────────── */
const SCL_KW = /\b(FUNCTION_BLOCK|END_FUNCTION_BLOCK|FUNCTION|END_FUNCTION|VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|VAR_TEMP|VAR|END_VAR|BEGIN|END|IF|THEN|ELSIF|ELSE|END_IF|CASE|OF|END_CASE|FOR|TO|DO|END_FOR|WHILE|END_WHILE|REPEAT|UNTIL|END_REPEAT|RETURN|TRUE|FALSE|AND|OR|NOT|XOR|MOD|REGION|END_REGION|CONSTANT|TYPE|END_TYPE|STRUCT|END_STRUCT)\b/g;
const SCL_TY = /\b(BOOL|INT|DINT|SINT|USINT|UINT|UDINT|WORD|DWORD|BYTE|REAL|LREAL|TIME|STRING|CHAR|ARRAY|POINTER|ANY|VOID)\b/g;
const strStore = [];

function escapeHtml(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function highlightSCL(line) {
  const ci = line.indexOf("//");
  let code = line, comment = "";
  if (ci >= 0) { code = line.slice(0, ci); comment = line.slice(ci); }
  let h = escapeHtml(code);
  h = h.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g,(m)=>` STR${strStore.push(m)-1} `);
  h = h.replace(SCL_KW,'<span class="kw">$1</span>');
  h = h.replace(SCL_TY,'<span class="ty">$1</span>');
  h = h.replace(/\b(\d+\.?\d*)\b/g,'<span class="nu">$1</span>');
  h = h.replace(/ STR(\d+) /g,(m,i)=>`<span class="str">${escapeHtml(strStore[+i])}</span>`);
  strStore.length = 0;
  if (comment) h += `<span class="co">${escapeHtml(comment)}</span>`;
  return h || " ";
}
function highlightJSON(line) {
  const store = [];
  let h = escapeHtml(line);
  h = h.replace(/"((?:[^"\\]|\\.)*)"/g, (m) => { store.push(m); return `\x00J${store.length-1}\x00`; });
  h = h.replace(/\b(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b/g, '<span class="nu">$1</span>');
  h = h.replace(/\b(true|false|null)\b/g, '<span class="kw">$1</span>');
  h = h.replace(/\x00J(\d+)\x00(\s*:)/g, (_,i,after) => `<span class="ty">${store[+i]}</span>${after}`);
  h = h.replace(/\x00J(\d+)\x00/g, (_,i) => `<span class="str">${store[+i]}</span>`);
  return h || " ";
}
function buildCodeHtml(text, kind) {
  const isScl  = kind === "scl";
  const isJson = kind === "json";
  return (text || "").split("\n").map((ln, i) =>
    `<div class="ln"><div class="gutter">${i+1}</div><div class="src">${
      isScl ? highlightSCL(ln) : isJson ? highlightJSON(ln) : escapeHtml(ln)||" "
    }</div></div>`
  ).join("");
}

/* ─────────────────────────────────────────────────────────────────────
   MARKDOWN RENDERER  (basic — used for .md file preview mode)
───────────────────────────────────────────────────────────────────── */
function _mmConfig() {
  const dark = document.documentElement.getAttribute("data-theme") !== "light";
  const tv = dark ? {
    primaryColor:        "#1e3a5f",
    primaryTextColor:    "#e6e9ec",
    primaryBorderColor:  "#10b981",
    lineColor:           "#64748b",
    secondaryColor:      "#12263d",
    background:          "#0f1216",
    edgeLabelBackground: "#1a2535",
    fontFamily:          "inherit",
    fontSize:            "13px",
  } : {
    primaryColor:        "#dbeafe",
    primaryTextColor:    "#1e3a5f",
    primaryBorderColor:  "#059669",
    lineColor:           "#64748b",
    secondaryColor:      "#e0f2fe",
    background:          "#ffffff",
    edgeLabelBackground: "#eef1f4",
    fontFamily:          "inherit",
    fontSize:            "13px",
  };
  return { startOnLoad: false, securityLevel: "loose", theme: "base", themeVariables: tv };
}
function _mmApply() {
  if (typeof mermaid !== "undefined") mermaid.initialize(_mmConfig());
}
function _mdInline(s) {
  return s.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
          .replace(/\*(.+?)\*/g,"<em>$1</em>")
          .replace(/`([^`]+?)`/g,'<code class="md-ic">$1</code>');
}
function _mdTableRow(raw, tag) {
  const cells = raw.replace(/^\|/, "").replace(/\|$/, "").split("|");
  return "<tr>" + cells.map(c => `<${tag} class="md-td">${_mdInline(escapeHtml(c.trim()))}</${tag}>`).join("") + "</tr>";
}
function renderMarkdown(text) {
  const lines = (text||"").split("\n");
  let html="", inCode=false, codeAcc="", codeLang="";
  let inList=false, listTag="ul";
  let tableRows=[], tablePhase="";   // "head" | "body"
  const flushList  = ()=>{ if(inList){html+=`</${listTag}>`;inList=false;} };
  const flushTable = ()=>{
    if (!tableRows.length) return;
    let th="", tb="";
    tableRows.forEach(r=>{ if(r.isHead) th+=r.html; else tb+=r.html; });
    html += `<div class="md-table-wrap"><table class="md-table">` +
            (th?`<thead>${th}</thead>`:"") +
            (tb?`<tbody>${tb}</tbody>`:"") +
            `</table></div>`;
    tableRows=[]; tablePhase="";
  };
  for (const raw of lines) {
    if (raw.startsWith("```")) {
      if (inCode) {
        if (codeLang === "mermaid") {
          const safe = codeAcc.replace(/(?<!-)->(?!>)/g, "→");
          html += `<div class="mermaid-wrap"><div class="mermaid">${safe}</div></div>`;
        } else {
          html += `<pre class="md-pre"><code class="md-code">${escapeHtml(codeAcc)}</code></pre>`;
        }
        inCode=false; codeAcc="";
      } else { flushList(); flushTable(); inCode=true; codeLang=raw.slice(3).trim(); }
      continue;
    }
    if (inCode) { codeAcc+=(codeAcc?"\n":"")+raw; continue; }
    // ── Markdown table detection ──
    if (raw.trim().startsWith("|")) {
      flushList();
      // Separator row (|---|---|) → switches head→body
      if (/^\|[\s|:-]+\|[\s|:-]*$/.test(raw.trim())) {
        tablePhase = "body"; continue;
      }
      const isHead = tablePhase === "";
      tableRows.push({ isHead, html: _mdTableRow(raw, isHead ? "th" : "td") });
      if (isHead) tablePhase = "head";
      continue;
    }
    flushTable();
    const e = escapeHtml(raw);
    if (!raw.trim()) { flushList(); html+="<br>"; continue; }
    if (raw.startsWith("# "))    { flushList(); html+=`<h1 class="md-h1">${_mdInline(e.slice(2))}</h1>`; continue; }
    if (raw.startsWith("## "))   { flushList(); html+=`<h2 class="md-h2">${_mdInline(e.slice(3))}</h2>`; continue; }
    if (raw.startsWith("### "))  { flushList(); html+=`<h3 class="md-h3">${_mdInline(e.slice(4))}</h3>`; continue; }
    if (raw.startsWith("#### ")) { flushList(); html+=`<h4 class="md-h3">${_mdInline(e.slice(5))}</h4>`; continue; }
    if (raw.match(/^[-*] /)) {
      if (!inList||listTag!=="ul"){ flushList(); html+="<ul class='md-ul'>"; inList=true; listTag="ul"; }
      html+=`<li>${_mdInline(e.slice(2))}</li>`; continue;
    }
    if (raw.match(/^\d+\. /)) {
      if (!inList||listTag!=="ol"){ flushList(); html+="<ol class='md-ul'>"; inList=true; listTag="ol"; }
      html+=`<li>${_mdInline(e.replace(/^\d+\. /,""))}</li>`; continue;
    }
    if (raw.match(/^[-_*]{3,}$/)){ flushList(); html+="<hr class='md-hr'>"; continue; }
    flushList();
    html+=`<p class="md-p">${_mdInline(e)}</p>`;
  }
  flushList(); flushTable();
  if (inCode) {
    if (codeLang === "mermaid") { const safe=codeAcc.replace(/(?<!-)->(?!>)/g,"→"); html+=`<div class="mermaid-wrap"><div class="mermaid">${safe}</div></div>`; }
    else html += `<pre class="md-pre"><code class="md-code">${escapeHtml(codeAcc)}</code></pre>`;
  }
  return html;
}

/* ─────────────────────────────────────────────────────────────────────
   SAMPLE FALLBACK DATA  (shown when no pywebview)
───────────────────────────────────────────────────────────────────── */
const SAMPLE = {
  version:"", project_name:"demo_project", project_path:"D:\\customer_projects\\demo_project",
  project_type:"RETROFIT", gate:1, gate_max:7, gate_name:"Discovery", gate_pct:14,
  platform:"S7-1500", model:"claude-sonnet-4-6", git_changes:"3 changes",
  tree:[
    {name:"RD",kind:"folder",depth:0,open:false,path:"RD"},
    {name:"SCL",kind:"folder",depth:0,open:false,path:"SCL"},
    {name:"REPORTS",kind:"folder",depth:0,open:false,path:"REPORTS"},
    {name:"PROJECT_STATE.json",kind:"json",depth:0,status:"ok",path:"PROJECT_STATE.json"},
    {name:"FB_Motor_Standard.scl",kind:"scl",depth:0,status:"mod",path:"FB_Motor_Standard.scl"},
  ],
  actions:[
    {id:"analyze",      label:"Analyze Project", icon:"sparkles",  hint:"",primary:true},
    {id:"extract_io",   label:"Extract IO List", icon:"table",     hint:""},
    {id:"generate_scl", label:"Generate SCL",    icon:"play",      hint:""},
    {id:"validate",     label:"Validate",        icon:"check",     hint:""},
    {id:"show_standards",label:"Show Standards", icon:"file-text", hint:""},
    {id:"export_tia",   label:"Export TIA",      icon:"upload",    hint:""},
  ],
  prompts:[{title:"code_gen.motor_fb",gate:4},{title:"review.safety",gate:5}],
  library:[{name:"FB_Motor_Standard",category:"motor",ver:"1.0.0",platform:"S7-1500",
            desc:"Standard motor FB (DOL drive, run feedback, fault).",ports:[]}],
  diagnostics:[{sev:"dim",line:"Workbench ready — select a file or click an action."}],
};
const SAMPLE_REPORT = {
  title:"neue — Modernisation Quote", customer:"ACME GmbH", date:"2026-05-25",
  prepared_by:"Mehmet Haydar", version:"1.0", platform_from:"S5", platform_to:"S7-1500",
  summary:"This proposal outlines a full PLC migration from S5 to S7-1500, covering engineering, hardware supply, and commissioning services. The project targets zero production downtime using a parallel-run cutover strategy.",
  decision_matrix:[
    {aspect:"PLC Hardware",     keep:"S5-135U reuse",   retrofit:"ET200SP remote IO",  greenfield:"S7-1500 rack"},
    {aspect:"Safety",           keep:"Hardwired relays", retrofit:"F-CPU add-on",      greenfield:"SIL 2 PLC"},
    {aspect:"HMI",              keep:"OP7 panels",       retrofit:"KTP700 panels",     greenfield:"WinCC Unified"},
    {aspect:"Long-term support",keep:"None (EOL 2024)",  retrofit:"10 yr lifecycle",   greenfield:"15 yr lifecycle"},
  ],
  cost_items:[{label:"Engineering (120 h)",value:"€ 24.000"},{label:"Hardware supply",value:"€ 21.000"},{label:"Commissioning",value:"€ 15.000"}],
  cost_total:"€ 60.000", gate:1, gate_max:7,
};
const SAMPLE_ONB = {
  user:"Demo",recents:[{name:"demo_project",path:"D:\\customer_projects\\demo_project"}],
  templates:[{id:"conveyor",name:"Conveyor Retrofit",desc:"Belt / conveyor line"},{id:"blank",name:"Blank Project",desc:"Start from scratch"}],
};
const SAMPLE_DASH = {
  project:"neue",type:"RETROFIT",gate:1,gate_max:7,
  gate_names:["Discovery","Extraction","Human Review","Code Generation","Validation","PLCSIM / Field Verify","FAT / SAT"],
  kpis:[{label:"RD Documents",value:"0/14",icon:"file-text"},{label:"Gate",value:"1/7",icon:"chip"},{label:"Platform",value:"S7-1500",icon:"cpu"},{label:"Project Type",value:"RETROFIT",icon:"package"}],
  // Canonical 14-Point taxonomy (matches project_analyzer.RD_INPUT_NEEDS).
  rds:["IO List","DataDict","Logic Flow","Mode","Safety ⚠️","Motion","Timing","Alarm","Comms","FBSpec","HMI","UseCase","Annotation","Modernization"]
    .map((n,i)=>({code:`RD${String(i+1).padStart(2,"0")}`,name:n,status:"draft"})),
};
const SAMPLE_GATES = {
  current:1,max:7,overall_pct:0,
  gates:[
    {n:1,name:"Discovery",     status:"current",needs_approval:false,docs:[{rd:"RD01",status:"draft"},{rd:"RD02",status:"draft"},{rd:"RD03",status:"draft"},{rd:"RD13",status:"draft"}],actions:[],when:"",who:""},
    {n:2,name:"Extraction",    status:"pending",needs_approval:false,docs:[{rd:"RD04",status:"draft"},{rd:"RD05",status:"draft"},{rd:"RD06",status:"draft"},{rd:"RD07",status:"draft"},{rd:"RD08",status:"draft"},{rd:"RD09",status:"draft"},{rd:"RD10",status:"draft"},{rd:"RD11",status:"draft"},{rd:"RD12",status:"draft"},{rd:"RD14",status:"draft"}],actions:[],when:"",who:""},
    {n:3,name:"Human Review",  status:"pending",needs_approval:true, docs:[],actions:["validate","rd01_crosscheck"],when:"",who:""},
    {n:4,name:"Code Generation",status:"pending",needs_approval:true,docs:[],actions:["assemble_program","generate_scl","generate_sequence_fb"],when:"",who:""},
    {n:5,name:"Validation",    status:"pending",needs_approval:false,docs:[],actions:["validate"],when:"",who:""},
    {n:6,name:"PLCSIM / Field Verify",status:"pending",needs_approval:true, docs:[],actions:["generate_test_scenarios","export_tia","send_to_tia"],when:"",who:""},
    {n:7,name:"FAT / SAT",     status:"pending",needs_approval:true, docs:[],actions:["generate_report","generate_fat"],when:"",who:""},
  ],
};
const SAMPLE_SETTINGS = {
  theme:"dark",accent:"emerald",ai_mode:"api",ai_provider:"anthropic",ai_model:"claude-sonnet-4-6",api_keys_status:{},keyring_available:true,
  catalog:{
    anthropic:{display:"Anthropic",models:["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5-20251001"],default:"claude-sonnet-4-6"},
    openai:{display:"OpenAI",models:["gpt-4o","gpt-4o-mini"],default:"gpt-4o"},
  },
};
const SAMPLE_FILE = `FUNCTION_BLOCK "FB_Motor_Standard"\nVAR_INPUT\n  Start   : BOOL;   // start command\n  Stop    : BOOL;   // stop command\n  Fault_Rst : BOOL;\nEND_VAR\nVAR_OUTPUT\n  Running : BOOL;\n  Fault   : BOOL;\nEND_VAR\nBEGIN\n  IF Stop THEN\n    Running := FALSE;\n  ELSIF Start AND NOT Fault THEN\n    Running := TRUE;\n  END_IF;\nEND_FUNCTION_BLOCK`;
const SAMPLE_GIT = {branch:"main",remote:"",changes:["M FB_Motor_Standard.scl"," M PROJECT_STATE.json"],log:["a1b2c3d Add motor FB","b2c3d4e Init project"]};
const SAMPLE_GATE_MODEL = SAMPLE_GATES;

/* ─────────────────────────────────────────────────────────────────────
   API BRIDGE
───────────────────────────────────────────────────────────────────── */
const Backend = {
  ready() { return !!(window.pywebview && window.pywebview.api); },
  async _call(method, ...args) {
    if (this.ready()) {
      try {
        const resp = await window.pywebview.api[method](...args);
        this._consumeWarnings(resp);
        return resp;
      }
      catch(e) {
        // A crashed API call must never fail silently (UX audit 2026-06-10):
        // surface it in the diagnostics log + one toast, then return null so
        // callers fall into their explicit "no backend" branches.
        console.error(method, e);
        try {
          logLine(`[api] ${method} failed: ${e && e.message ? e.message : e}`, "error");
          toast(`Backend call failed: ${method}`, "error");
        } catch(_) { /* logging UI not ready yet */ }
      }
    }
    return null;
  },
  // The backend attaches a `_warnings` array (via _attach_warnings) to every
  // API response that can emit a runtime warning, and a `_pii_warnings`
  // string array (charter §11 soft PII warning) on direct-AI call sites.
  // Surface both in the diagnostics log instead of silently dropping them.
  _consumeWarnings(resp) {
    if (!resp || typeof resp !== "object") return;
    const w = resp._warnings;
    if (Array.isArray(w)) {
      for (const item of w) {
        const msg = (item && item.msg) ? item.msg : String(item);
        try { logLine(`[backend] ${msg}`, "warn"); } catch(_) { console.warn("[backend]", msg); }
      }
    }
    const pii = resp._pii_warnings;
    if (Array.isArray(pii)) {
      for (const msg of pii) {
        try { logLine(`[privacy] ${msg}`, "warn"); toast(String(msg)); } catch(_) { console.warn("[privacy]", msg); }
      }
    }
  },
  async get_state()                  { return (await this._call("get_state"))              || SAMPLE; },
  async read_file(p)                 { return (await this._call("read_file", p))           || {name:p, kind:p.endsWith(".scl")?"scl":p.endsWith(".json")?"json":p.endsWith(".md")?"md":"text", text:SAMPLE_FILE}; },
  async save_file(p, c)              { return (await this._call("save_file", p, c))        || {ok:false,msg:"No backend"}; },
  async run_pipeline(id, fp)         { return (await this._call("run_pipeline", id, fp||"")) || {ok:false,output:"No backend"}; },
  async list_dir(p)                  { return (await this._call("list_dir", p))            || []; },
  async get_settings()               { return (await this._call("get_settings"))           || SAMPLE_SETTINGS; },
  async save_settings(d)             { return (await this._call("save_settings_data", d))  || true; },
  async test_api(p, k)               { return (await this._call("test_api", p, k))         || {ok:false,msg:"No backend"}; },
  async get_gate_history()           { return (await this._call("get_gate_history"))        || SAMPLE_GATES; },
  async advance_gate(sig, acceptStructural, compileLogPath, manualTestConfirmed) { return (await this._call("advance_gate", sig||"", !!acceptStructural, compileLogPath||"", !!manualTestConfirmed)) || {ok:false}; },
  async review_rd(rd, sig)           { return (await this._call("review_rd", rd, sig||""))   || {ok:false,msg:"No backend"}; },
  async unreview_rd(rd)              { return (await this._call("unreview_rd", rd))          || {ok:false,msg:"No backend"}; },
  async mark_rd_na(rd, reason)       { return (await this._call("mark_rd_na", rd, reason||"")) || {ok:false,msg:"No backend"}; },
  async unmark_rd_na(rd)             { return (await this._call("unmark_rd_na", rd))         || {ok:false,msg:"No backend"}; },
  async get_io_reconciliation()      { return (await this._call("get_io_reconciliation"))     || {ok:false,exists:false}; },
  async get_regen_delta()            { return (await this._call("get_regen_delta"))            || {ok:false,msg:"No backend"}; },
  async run_delta_assembly()         { return (await this._call("run_delta_assembly"))         || {ok:false,output:"No backend"}; },
  async ack_io_reconciliation(note)  { return (await this._call("ack_io_reconciliation", note||"")) || {ok:false,msg:"No backend"}; },
  async get_gate3_consistency()      { return (await this._call("get_gate3_consistency"))     || {ok:false,msg:"No backend"}; },
  async waive_gate3_finding(id, reason, name) { return (await this._call("waive_gate3_finding", id, reason||"", name||"")) || {ok:false,msg:"No backend"}; },
  async copy_prompt(n)               { return (await this._call("copy_prompt", n))         || {ok:false,msg:"No backend"}; },
  async get_dashboard()              { return (await this._call("get_dashboard"))           || SAMPLE_DASH; },
  async get_report()                 { return (await this._call("get_report"))              || SAMPLE_REPORT; },
  async get_onboarding()             { return (await this._call("get_onboarding"))          || SAMPLE_ONB; },
  async open_project(p)              { return (await this._call("open_project", p))         || {ok:false,msg:"No backend"}; },
  async remove_from_recents(p)       { return (await this._call("remove_from_recents", p))  || {ok:false}; },
  async create_project(t, n, par, meta) { return (await this._call("create_project", t, n, par, meta))||{ok:false,msg:"No backend"}; },
  async search_project(q)            { return (await this._call("search_project", q))       || []; },
  async git_info()                   { return (await this._call("git_info"))                || SAMPLE_GIT; },
  async git_diff(p)                  { return (await this._call("git_diff", p))             || {diff:"(demo diff)"}; },
  async get_library_blocks()         { return (await this._call("get_library_blocks"))       || SAMPLE.library; },
  async import_block(n)              { return (await this._call("import_block", n))          || {ok:false,msg:"No backend"}; },
  async get_block_scl(n)             { return (await this._call("get_block_scl", n))         || {ok:false,text:""}; },
  async new_file(parent, name)       { return (await this._call("new_file", parent, name))   || {ok:false,msg:"No backend"}; },
  async new_folder(parent, name)     { return (await this._call("new_folder", parent, name)) || {ok:false,msg:"No backend"}; },
  async reveal_path(p)               { return  await this._call("reveal_path", p); },
  async delete_file(p)               { return (await this._call("delete_file", p))           || {ok:false,msg:"No backend"}; },
  async rename_file(p, n)            { return (await this._call("rename_file", p, n))        || {ok:false,msg:"No backend"}; },
  async browse_for_folder()          { return (await this._call("browse_for_folder"))         || {ok:false,path:""}; },
  async browse_for_file(kind)        { return (await this._call("browse_for_file", kind||"")) || {ok:false,path:""}; },
  async version_compare_scan(f)      { return (await this._call("version_compare_scan", f||[]))      || {ok:false,msg:"No backend"}; },
  async version_compare_diff(a,b,n)  { return (await this._call("version_compare_diff", a, b, n))    || {ok:false,msg:"No backend"}; },
  async version_compare_hypotheses(f,c){ return (await this._call("version_compare_hypotheses", f, c||{})) || {ok:false,msg:"No backend"}; },
  async get_ai_suggestion(ctx, ln)   { return (await this._call("get_ai_suggestion", ctx, ln))||{ok:false,suggestion:"",msg:""}; },
  async get_gate_model()             { return (await this._call("get_gate_model"))             || SAMPLE_GATE_MODEL; },
  async find_rd_file(rdId)          { return (await this._call("find_rd_file", rdId))          || {found:false, path:null}; },
  async get_file_context(p)          { return (await this._call("get_file_context", p))         || {actions:[], prompts:[]}; },
  async list_project_reports()       { return (await this._call("list_project_reports"))        || {ok:false, reports:[]}; },
  async export_handover_package()    { return (await this._call("export_handover_package"))     || {ok:false, msg:"No backend"}; },
  async project_qa(q)                { return (await this._call("project_qa", q))               || {ok:false, hits:[]}; },
  async set_theme(theme)             { return  await this._call("set_theme", theme); },
  async save_io_list(p, rows)        { return (await this._call("save_io_list", p, rows))       || {ok:false,msg:"No backend"}; },
  async validate_io_list(p)         { return (await this._call("validate_io_list", p))         || {ok:false,issues:[]}; },
  async export_io_xlsx(p)            { return (await this._call("export_io_xlsx", p))           || {ok:false,msg:"No backend"}; },
  async generate_fat(t, l, p)        { return (await this._call("generate_fat", t||"FAT", l||"de", !!p)) || {ok:false,msg:"No backend"}; },
  async get_sistema_status()         { return (await this._call("get_sistema_status"))           || {ok:false,msg:"No backend"}; },
  async add_sistema_record(fn,f,pl,e){ return (await this._call("add_sistema_record", fn, f||"", pl||"", e||"")) || {ok:false,msg:"No backend"}; },
  async delete_sistema_record(i)     { return (await this._call("delete_sistema_record", i))     || {ok:false,msg:"No backend"}; },
  async generate_sistema_prep(l)     { return (await this._call("generate_sistema_prep", l||"de")) || {ok:false,msg:"No backend"}; },
  async generate_ce_assessment(l, p) { return (await this._call("generate_ce_assessment", l||"de", !!p)) || {ok:false,msg:"No backend"}; },
  async generate_customer_report()   { return (await this._call("generate_customer_report"))     || {ok:false,msg:"No backend"}; },
  async size_hardware(pct)           { return (await this._call("size_hardware", pct||20))        || {ok:false,msg:"No backend"}; },
  async get_bom_library()            { return (await this._call("get_bom_library"))               || {ok:false,devices:[]}; },
  async get_hw_library()             { return (await this._call("get_hw_library"))                || {ok:false,devices:[],categories:[]}; },
  async get_device_text(p)           { return (await this._call("get_device_text", p))            || {ok:false,text:""}; },
  async save_device_text(p, text)    { return (await this._call("save_device_text", p, text))     || {ok:false,msg:"No backend"}; },
  async create_device(c, ven, mod)   { return (await this._call("create_device", c, ven, mod))    || {ok:false,msg:"No backend"}; },
  async generate_bom(selected)       { return (await this._call("generate_bom", selected||[]))    || {ok:false,msg:"No backend"}; },
  async generate_ob1(name, ow)       { return (await this._call("generate_ob1", name||"OB_Main", ow||false))|| {ok:false,msg:"No backend"}; },
  async generate_iec_tags()          { return (await this._call("generate_iec_tags"))            || {ok:false,msg:"No backend"}; },
  async validate_scl_file(p)        { return (await this._call("validate_scl_file", p))         || {ok:false,issues:[]}; },
  async run_analysis()               { return (await this._call("run_analysis"))                 || {ok:false,msg:"No backend"}; },
  async get_workflows()              { return (await this._call("get_workflows"))                || []; },
  async run_workflow(wf, fp)         { return (await this._call("run_workflow", wf, fp||""))     || {ok:false,output:"No backend"}; },
  async get_raw_folder_status()     { return (await this._call("get_raw_folder_status"))         || {ok:false,total:0,by_category:{}}; },
  async import_s5d(p)               { return (await this._call("import_s5d", p))                 || {ok:false,msg:"No backend"}; },
  async generate_hmi_draft()         { return (await this._call("generate_hmi_draft"))            || {ok:false,msg:"No backend"}; },
  async generate_hmi_interface()     { return (await this._call("generate_hmi_interface"))        || {ok:false,msg:"No backend"}; },
  async read_hmi_table(kind)         { return (await this._call("read_hmi_table", kind))          || {ok:false,msg:"No backend"}; },
  async get_hmi_wiring()             { return (await this._call("get_hmi_wiring"))                || {ok:false,msg:"No backend"}; },
  async set_hmi_wiring(tag, approved, by, note) { return (await this._call("set_hmi_wiring", tag, !!approved, by||"", note||"")) || {ok:false,msg:"No backend"}; },
  async generate_hmi_wiring_code()   { return (await this._call("generate_hmi_wiring_code"))      || {ok:false,msg:"No backend"}; },
  async generate_revision_log()      { return (await this._call("generate_revision_log"))         || {ok:false,msg:"No backend"}; },
  async save_hmi_table(kind, edits)  { return (await this._call("save_hmi_table", kind, edits))   || {ok:false,msg:"No backend"}; },
  async run_retrofit_preanalysis(c) { return (await this._call("run_retrofit_preanalysis", c))   || {ok:false,msg:"No backend"}; },
  async run_topic_extraction(c)     { return (await this._call("run_topic_extraction", c))       || {ok:false,msg:"No backend"}; },
  async run_discovery(c)            { return (await this._call("run_discovery", c))              || {ok:false,msg:"No backend"}; },
  async run_topic_generation(c)     { return (await this._call("run_topic_generation", c))       || {ok:false,msg:"No backend"}; },
  async get_output_language()        { return (await this._call("get_output_language"))           || {ok:false,language:"EN",supported:["TR","EN","DE"]}; },
  async set_output_language(l)       { return (await this._call("set_output_language", l))         || {ok:false,msg:"No backend"}; },
  async get_legacy_extraction_status(){ return (await this._call("get_legacy_extraction_status"))|| {ok:false,items:[]}; },
  async get_preanalysis_status()    { return (await this._call("get_preanalysis_status"))        || {ok:false,exists:false}; },
  async generate_sequence_fb(c)     { return (await this._call("generate_sequence_fb", c||{}))   || {ok:false,msg:"No backend"}; },
  async generate_machine_dossier()  { return (await this._call("generate_machine_dossier"))      || {ok:false,msg:"No backend"}; },
  async list_machine_dossier()      { return (await this._call("list_machine_dossier"))          || {ok:false,files:[]}; },
  async open_dossier_file(n)        { return (await this._call("open_dossier_file", n))          || {ok:false,msg:"No backend"}; },
  async get_dossier_svg(n)          { return (await this._call("get_dossier_svg", n))            || {ok:false,msg:"No backend"}; },
  async get_decision_table()        { return (await this._call("get_decision_table"))            || {ok:false,rows:[]}; },
  async save_decision_table(e)      { return (await this._call("save_decision_table", e||[]))    || {ok:false,msg:"No backend"}; },
  async get_decision_cascade()      { return (await this._call("get_decision_cascade"))          || {ok:false,msg:"No backend"}; },
  async get_workdesk()              { return (await this._call("get_workdesk"))                  || {ok:false,desk:[],reading:[]}; },
  async get_gate6_compile_status()  { return (await this._call("get_gate6_compile_status"))      || {ok:false,tia_auto:false}; },
  async generate_test_scenarios()   { return (await this._call("generate_test_scenarios"))        || {ok:false,msg:"No backend"}; },
  async get_tia_bridge_status()     { return (await this._call("get_tia_bridge_status"))         || {ok:false,bridges:[]}; },
  async set_tia_settings(d)         { return (await this._call("set_tia_settings", d||{}))       || {ok:false,msg:"No backend"}; },
  async set_project_target(d)       { return (await this._call("set_project_target", d||{}))     || {ok:false,msg:"No backend"}; },
  async send_to_tia(o)              { return (await this._call("send_to_tia", o||{}))            || {ok:false,msg:"No backend"}; },
  async get_tia_send_status()       { return (await this._call("get_tia_send_status"))           || {ok:false,exists:false}; },
  async tia_fix_propose(o)          { return (await this._call("tia_fix_propose", o||{}))        || {ok:false,msg:"No backend"}; },
  async tia_fix_apply(a)            { return (await this._call("tia_fix_apply", a||{}))          || {ok:false,msg:"No backend"}; },
  async tia_fix_discard()           { return (await this._call("tia_fix_discard"))               || {ok:false,msg:"No backend"}; },
  async extract_legacy_pdfs(o)      { return (await this._call("extract_legacy_pdfs", o||{}))    || {ok:false,msg:"No backend"}; },
  async confirm_extracted_text(n,t) { return (await this._call("confirm_extracted_text", n, t))  || {ok:false,msg:"No backend"}; },
  async get_provider_for_task(t)    { return (await this._call("get_provider_for_task", t))      || {provider:"anthropic",model:"",max_tokens:4096}; },
  async list_prompts_by_category(cat){ return (await this._call("list_prompts_by_category",cat))|| []; },
  async get_prompt_text(path)        { return (await this._call("get_prompt_text", path))        || {ok:false,text:""}; },
  async save_user_prompt(cat,ti,bo,g){ return (await this._call("save_user_prompt",cat,ti,bo,g))|| {ok:false,msg:"No backend"}; },
  async normalize_prompt(text,cat)   { return (await this._call("normalize_prompt",text,cat))    || {ok:false,normalized:"",msg:"no_api_key",mode:"api"}; },
  async adapt_prompt(text)           { return (await this._call("adapt_prompt", text))           || {ok:false,warnings:[],suggestions:[],enhanced:text}; },
  async git_commit(msg)              { return (await this._call("git_commit", msg))               || {ok:false,msg:"No backend"}; },
  async git_push(forceClassified)    { return (await this._call("git_push", !!forceClassified))   || {ok:false,msg:"No backend"}; },
  async git_pull()                   { return (await this._call("git_pull"))                       || {ok:false,msg:"No backend"}; },
  async git_init_project()           { return (await this._call("git_init_project"))               || {ok:false,msg:"No backend"}; },
  async rd03_get()                   { return (await this._call("rd03_get"))                       || {ok:false,msg:"No backend"}; },
  async rd03_regen_mermaid()         { return (await this._call("rd03_regen_mermaid"))             || {ok:false,msg:"No backend"}; },
  async rd03_chat_propose(msgs)      { return (await this._call("rd03_chat_propose", msgs||[]))    || {ok:false,msg:"No backend"}; },
  async rd03_chat_apply(tbl)         { return (await this._call("rd03_chat_apply", tbl||""))       || {ok:false,msg:"No backend"}; },
};

/* ─────────────────────────────────────────────────────────────────────
   STATE
───────────────────────────────────────────────────────────────────── */
let STATE         = null;
let OPEN_TABS     = [];      // [{path, name, kind, dirty, text}]
let ACTIVE_TAB    = null;    // path string
let CURRENT_FILE  = null;    // {name, kind, lines, _path, _text}
let currentBottomTab = "diagnostics";
let editMode      = false;   // true = textarea editing, false = highlighted view
const LOG = [];
let LAST_PREVIEW  = "";
let AI_GHOST_TEXT = "";      // inline AI suggestion
let splitMode     = false;
const $ = (id) => document.getElementById(id);

/* ─────────────────────────────────────────────────────────────────────
   RENDER — main state → DOM
───────────────────────────────────────────────────────────────────── */
function render() {
  if (!STATE) return;   // bootstrap may fire a render before get_state() resolves
  const s = STATE;
  $("app-version").textContent  = s.version || "";
  $("bc-project").textContent   = s.project_name || "—";
  $("proj-name").textContent    = (s.project_name || "—").toUpperCase();
  $("proj-badge").textContent   = s.project_type || "PROJECT";
  $("git-changes").textContent  = s.git_changes || "";
  if ($("status-branch")) $("status-branch").textContent = s.git_branch || "main";
  if ($("sidebar-branch")) $("sidebar-branch").textContent = s.git_branch || "main";
  const gitBadge = $("act-git-badge");
  if (gitBadge) { const n = s.git_change_count || 0; gitBadge.textContent = n || ""; gitBadge.style.display = n ? "" : "none"; }
  $("gate-caps").textContent    = `Gate ${s.gate}/${s.gate_max}`;
  $("gate-pct").textContent     = s.gate_pct != null ? s.gate_pct + "%" : "";
  $("gate-title").textContent   = s.gate_name || "";
  $("gate-platform").textContent= s.platform || "—";
  $("status-platform").textContent = s.platform || "—";
  $("status-model").textContent = s.model || "—";
  $("status-gate-num").textContent = `${s.gate}/${s.gate_max}`;
  updateThemeLabel();
  { const _lc = $("lib-count"); if (_lc) _lc.textContent = `${(s.library||[]).length} blocks`; }  // panel may be absent (removed from rail)
  $("gate-bar").innerHTML = Array.from({length:s.gate_max},(_,i)=>`<div class="gate-seg ${i<s.gate?"on":""}"></div>`).join("");
  $("gate-dots").innerHTML = Array.from({length:s.gate_max},(_,i)=>{
    const n=i+1, cls=n===s.gate?"gdot cur":(n<s.gate?"gdot on":"gdot");
    return `<span class="${cls}"></span>`;
  }).join("");
  renderTree(); renderActions(); renderPrompts(); renderLibrary(); renderDiagnostics();
  renderReportsPanel();
  renderGateNavBar();
  injectIcons();
  // Right rail gate section → open gate view (NOT the first .rr-sec —
  // the "Next step" card sits above it since the UX overhaul)
  const rrGate = document.getElementById("rr-gate-sec");
  if (rrGate && !rrGate._gateWired) {
    rrGate._gateWired = true;
    rrGate.style.cursor = "pointer";
    rrGate.addEventListener("click", ()=>setActivePage("gate"));
  }
  // Prompt Library header → collapse / expand
  const plHead = document.getElementById("prompt-lib-head");
  if (plHead && !plHead._wired) {
    plHead._wired = true;
    plHead.addEventListener("click", ()=>{
      document.getElementById("rr-prompts")?.classList.toggle("collapsed");
    });
  }
}

/* ─────────────────────────────────────────────────────────────────────
   GATE NAV BAR  (always-on stepper below topbar)
───────────────────────────────────────────────────────────────────── */
function renderGateNavBar() {
  const model = _gateModel;
  const stepsEl = $("gnb-steps");
  const labelEl = $("gnb-gate-label");
  const nameEl  = $("gnb-gate-name");
  const pctEl   = $("gnb-pct");
  if (!stepsEl) return;
  if (!model || !model.gates) {
    stepsEl.innerHTML = `<span style="font-size:11px;color:var(--fg-dim);padding:0 12px">Open a project to see gate progress</span>`;
    if (labelEl) labelEl.textContent = "GATE —/7";
    if (nameEl)  nameEl.textContent  = "—";
    if (pctEl)   pctEl.textContent   = "—%";
    return;
  }
  const gates   = model.gates || [];
  const current = model.current || 1;
  const pct     = model.gate_pct ?? (model.overall_pct != null ? Math.round(model.overall_pct) : Math.round((current - 1) / 7 * 100));
  const curGate = gates.find((g) => g.n === current) || gates[0];
  stepsEl.innerHTML = gates.map((g) => {
    const isDone    = g.status === "done";
    const isCurrent = g.status === "current";
    const isWarn    = isCurrent && g.needs_approval;
    const isNext    = !isDone && !isCurrent && g.n === current + 1;
    let cls = "gnb-step";
    if (isDone)        cls += " done";
    else if (isWarn)   cls += " warn";
    else if (isCurrent) cls += " current";
    else if (isNext)   cls += " next";
    else               cls += " pending";
    let iconHtml;
    if (isDone)         iconHtml = `<span class="gnb-badge done">✓</span>`;
    else if (isWarn)    iconHtml = `<span class="gnb-badge warn">⚠</span>`;
    else if (isCurrent) iconHtml = `<span class="gnb-badge current">${g.n}</span>`;
    else if (isNext)    iconHtml = `<span class="gnb-badge next">${g.n}</span>`;
    else                iconHtml = `<span class="gnb-num">${g.n}</span>`;
    return `<div class="${cls}" data-n="${g.n}" title="Gate ${g.n}: ${escapeHtml(g.name)}">
      ${iconHtml}
      <div class="gnb-info">
        <div class="gnb-name">${escapeHtml(g.name)}</div>
        <div class="gnb-sub">${GATE_SUBTITLES[g.n] || ""}</div>
      </div>
    </div>`;
  }).join("");
  if (labelEl) labelEl.textContent = `GATE ${current}/7`;
  if (nameEl)  nameEl.textContent  = curGate ? curGate.name : "—";
  if (pctEl)   pctEl.textContent   = pct + "%";
  injectIcons(stepsEl);
  // Step click → open gate view for that gate
  stepsEl.querySelectorAll(".gnb-step").forEach((el) => {
    el.addEventListener("click", () => {
      const n = parseInt(el.getAttribute("data-n"));
      if (!n) return;
      document.querySelectorAll(".activitybar .act-btn").forEach((x)=>x.classList.remove("active"));
      const ab = document.querySelector(`.activitybar .act-btn[data-view="gate"]`);
      if (ab) ab.classList.add("active");
      const resizer = $("sidebar-resizer");
      if (resizer) resizer.style.display = "none";
      showGateView(n);
    });
  });
  // Timeline button
  const tlBtn = $("gnb-timeline-btn");
  if (tlBtn && !tlBtn._wired) {
    tlBtn._wired = true;
    tlBtn.addEventListener("click", () => setActivePage("gate"));
  }
}

/* ─────────────────────────────────────────────────────────────────────
   FILE TREE
───────────────────────────────────────────────────────────────────── */
const FILE_ICON = {folder:"folder",scl:"file-code",md:"file-text",json:"file",text:"file-text",table:"table"};
function treeHtml(nodes, depth) {
  let html = "";
  for (const n of (nodes||[])) {
    const isFile = n.kind !== "folder";
    const indent = 8 + depth * 14;
    const ic = FILE_ICON[n.kind] || "file";
    const icClass = n.kind==="scl"?"ficon-scl":(n.kind==="folder"?("ficon-folder"+(n.open?" open":"")):"");
    const chev = !isFile
      ? `<span class="chev ic" data-i="${n.open?"chevron-down":"chevron-right"}" data-s="11"></span>`
      : `<span class="chev"></span>`;
    let badge = "";
    if      (n.status==="ok")    badge='<span class="badge ok">OK</span>';
    else if (n.status==="mod")   badge='<span class="badge mod">MOD</span>';
    else if (n.status==="warn")  badge='<span class="badge warn">!</span>';
    else if (n.status==="draft") badge='<span class="badge draft">DRAFT</span>';
    const dirty = OPEN_TABS.find(t=>t.path===n.path&&t.dirty) ? '<span class="dot" style="margin-left:auto;margin-right:4px"></span>' : "";
    // I-A5: escape every attribute that comes from filesystem-derived data.
    // On non-Windows hosts a filename can contain ", <, >, and a path may
    // contain quote chars — interpolating raw values into HTML attributes
    // allows DOM-injection through a crafted filename.
    html += `<div class="tree-row ${isFile?"":"folder"} ${ACTIVE_TAB===n.path?"active":""}" data-path="${escapeHtml(n.path||"")}" data-file="${isFile?1:0}" data-name="${escapeHtml(n.name)}" style="padding-left:${indent}px">
      ${chev}<span class="ic ${icClass}" data-i="${ic}" data-s="13"></span>
      <span class="fname">${escapeHtml(n.name)}</span>${dirty}${badge}</div>`;
    if (!isFile && n.open && n.children) html += treeHtml(n.children, depth+1);
  }
  return html;
}
function findNode(nodes, path) {
  for (const n of (nodes||[])) {
    if ((n.path||"")===path) return n;
    if (n.children) { const f=findNode(n.children,path); if (f) return f; }
  }
  return null;
}
async function onTreeClick(row) {
  const path = row.getAttribute("data-path");
  const isFile = row.getAttribute("data-file")==="1";
  if (isFile) {
    if (path) {
      if (splitMode && $("split-right")) { openFileInSplitRight(path); return; }
      openFile(path, row);
    }
    return;
  }
  const node = findNode(STATE.tree, path);
  if (!node) return;
  if (node.open) { node.open=false; }
  else { if (!node.children) node.children = await Backend.list_dir(path); node.open=true; }
  renderTree();
}
function renderTree() {
  const tree = $("tree");
  tree.innerHTML = treeHtml(STATE.tree, 0);
  injectIcons(tree);
  tree.querySelectorAll(".tree-row").forEach((row)=>{
    row.addEventListener("click", ()=>onTreeClick(row));
    row.addEventListener("contextmenu", (e)=>{ e.preventDefault(); showContextMenu(e, row); });
  });
}

/* ─────────────────────────────────────────────────────────────────────
   CONTEXT MENU
───────────────────────────────────────────────────────────────────── */
function showContextMenu(e, row) {
  closeContextMenu();
  const path   = row.getAttribute("data-path");
  const isFile = row.getAttribute("data-file")==="1";
  const name   = row.getAttribute("data-name") || path;
  const menu   = document.createElement("div");
  menu.className = "ctx-menu"; menu.id = "ctx-menu";
  const items = isFile ? [
    {icon:"edit",        label:"Open",              action:()=>openFile(path)},
    {icon:"copy",        label:"Copy path",          action:()=>{ navigator.clipboard.writeText(path); toast("Path copied"); }},
    {icon:"save",        label:"Save",               action:()=>saveCurrentFile()},
    {icon:"folder-open", label:"Reveal in Explorer", action:()=>Backend.reveal_path(path)},
    null,
    {icon:"trash",  label:"Delete",       action:()=>confirmDelete(path, name)},
    {icon:"edit",   label:"Rename…",      action:()=>promptRename(path, name)},
  ] : [
    {icon:"folder-plus", label:"New file…",          action:()=>promptNewFile(path)},
    {icon:"folder",      label:"New folder…",         action:()=>promptNewFolder(path)},
    {icon:"folder-open", label:"Reveal in Explorer",  action:()=>Backend.reveal_path(path)},
    {icon:"refresh",     label:"Refresh",             action:()=>{ renderTree(); }},
  ];
  menu.innerHTML = items.map((it,i)=>it
    ? `<div class="ctx-item" data-idx="${i}">${svg(it.icon,13)}<span>${it.label}</span></div>`
    : `<div class="ctx-sep"></div>`
  ).join("");
  const validItems = items.filter(Boolean);
  menu.querySelectorAll(".ctx-item").forEach((el)=>{
    const idx = parseInt(el.getAttribute("data-idx"));
    const it  = items[idx];
    if (it) el.addEventListener("click",()=>{ closeContextMenu(); it.action(); });
  });
  const x = Math.min(e.clientX, window.innerWidth  - 180);
  const y = Math.min(e.clientY, window.innerHeight - validItems.length * 30 - 16);
  menu.style.cssText = `left:${x}px;top:${y}px`;
  document.body.appendChild(menu);
  setTimeout(()=>document.addEventListener("click", closeContextMenu, {once:true}), 50);
}
function closeContextMenu() {
  const m = $("ctx-menu"); if (m) m.remove();
}
async function confirmDelete(path, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  const r = await Backend.delete_file(path);
  if (r && r.ok) {
    closeTab(path);
    STATE = await Backend.get_state();
    render(); toast(`Deleted ${name}`);
    logLine(`[fs] Deleted ${name}`, "warn");
  } else {
    toast((r && r.msg) || "Delete failed");
  }
}
async function promptRename(path, oldName) {
  const newName = prompt("New name:", oldName);
  if (!newName || newName === oldName) return;
  const r = await Backend.rename_file(path, newName);
  if (r && r.ok) {
    const newPath = r.path || path.replace(oldName, newName);
    OPEN_TABS = OPEN_TABS.map(t => t.path === path ? {...t, path: newPath, name: newName} : t);
    if (ACTIVE_TAB === path) ACTIVE_TAB = newPath;
    if (CURRENT_FILE && CURRENT_FILE._path === path) { CURRENT_FILE._path = newPath; CURRENT_FILE.name = newName; }
    STATE = await Backend.get_state(); render(); toast(`Renamed to ${newName}`);
    logLine(`[fs] Renamed ${oldName} → ${newName}`, "info");
  } else {
    toast((r && r.msg) || "Rename failed");
  }
}
async function promptNewFile(parentPath) {
  const name = prompt("New file name (e.g. FB_Valve.scl):");
  if (!name) return;
  const r = await Backend.new_file(parentPath, name);
  if (r && r.ok) {
    STATE = await Backend.get_state(); render(); toast(`Created ${name}`);
    openFile(r.path);
  } else {
    toast((r && r.msg) || "Create failed");
  }
}
async function promptNewFolder(parentPath) {
  const name = prompt("New folder name:");
  if (!name) return;
  const r = await Backend.new_folder(parentPath, name);
  if (r && r.ok) { STATE = await Backend.get_state(); render(); toast(`Folder "${name}" created`); }
  else toast((r && r.msg) || "Create failed");
}

/* ─────────────────────────────────────────────────────────────────────
   ACTIONS & PROMPTS & LIBRARY
───────────────────────────────────────────────────────────────────── */
function renderActions() {
  $("actions").innerHTML = (STATE.actions||[]).map((a)=>
    `<div class="action ${a.primary?"primary":""}" data-id="${a.id}" title="${escapeHtml(ACTION_HINTS[a.id]||"")}">
      <span class="ic" data-i="${a.icon||"play"}" data-s="13"></span>
      <span>${a.label}</span><div class="fill"></div>
      <span class="hint">${a.hint||""}</span>
    </div>`).join("");
  $("actions").querySelectorAll(".action").forEach((el)=>
    el.addEventListener("click",()=>runAction(el.getAttribute("data-id"))));
}
function renderPrompts() {
  // Prompt Library panel was removed from the workspace right rail (2026-06-29);
  // guard so the render call is a safe no-op when the container is absent.
  const box = $("prompts");
  if (!box) return;
  box.innerHTML = (STATE.prompts||[]).map((p)=>
    `<div class="prompt-row" data-title="${p.title}"><span class="ic" data-i="dot" data-s="10"></span>${p.title}<span class="g">G${p.gate}</span></div>`).join("");
  box.querySelectorAll(".prompt-row").forEach((el)=>
    el.addEventListener("click",()=>selectPrompt(el.getAttribute("data-title"))));
}
async function selectPrompt(title) {
  $("prompt-sel-name").textContent = title;
  const r = await Backend.copy_prompt(title);
  if (r.ok && r.text) {
    try {
      await navigator.clipboard.writeText(r.text);
    } catch (e) {
      // pywebview/WebView2 may block the async clipboard API — fall back
      const ta = document.createElement("textarea");
      ta.value = r.text; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); ta.remove();
    }
  }
  toast(r.ok ? (r.msg||"Copied") : (r.msg||"Prompt not found"), r.ok ? undefined : "error");
  logLine("[prompt] " + (r.msg||title), r.ok ? "success" : "warn");
  LAST_PREVIEW = r.preview||"";
  if (currentBottomTab==="ai") renderBottom();
}
function renderLibrary() {
  // Block Library panel was removed from the workspace right rail (2026-06-29);
  // FB blocks remain on the dedicated Block Library page. Safe no-op here.
  const box = $("library");
  if (!box) return;
  const blocks = STATE.library||[];
  box.innerHTML = blocks.map((b)=>
    `<div class="lib-card" data-name="${escapeHtml(b.name)}">
      <div class="top">
        <span class="ic" data-i="cpu" data-s="12" style="color:var(--accent)"></span>
        <span class="name">${escapeHtml(b.name)}</span>
        <span class="ver">v${b.ver}</span>
      </div>
      <div class="desc">${escapeHtml(b.desc||"")}</div>
      <div class="lib-actions">
        <span class="lib-btn" data-action="preview" data-name="${escapeHtml(b.name)}" title="Preview SCL">${svg("file-code",11)} Preview</span>
        <span class="lib-btn accent" data-action="import" data-name="${escapeHtml(b.name)}" title="Import to project">${svg("arrow-right",11)} Import</span>
      </div>
    </div>`).join("");
  $("library").querySelectorAll(".lib-btn").forEach((el)=>{
    el.addEventListener("click",()=>{
      const action = el.getAttribute("data-action");
      const name   = el.getAttribute("data-name");
      if (action==="import") importLibraryBlock(name);
      else previewLibraryBlock(name);
    });
  });
}
async function importLibraryBlock(name) {
  const r = await Backend.import_block(name);
  if (r && r.ok) {
    toast(`Imported ${name} → SCL/`);
    logLine(`[library] ${name} imported to SCL/`, "success");
    STATE = await Backend.get_state(); render();
  } else {
    toast((r&&r.msg)||"Import failed"); logLine(`[library] import failed: ${r&&r.msg}`, "warn");
  }
}
async function previewLibraryBlock(name) {
  const r = await Backend.get_block_scl(name);
  if (r && r.ok && r.text) {
    LAST_PREVIEW = r.text;
    switchBottomTab("ai");
    toast(`Library preview: ${name}`);
  } else {
    toast("Preview unavailable");
  }
}

/* ─────────────────────────────────────────────────────────────────────
   BOTTOM PANEL
───────────────────────────────────────────────────────────────────── */
function switchBottomTab(name) {
  currentBottomTab = name;
  document.querySelectorAll(".btab").forEach((x) => x.classList.remove("active"));
  const btn = document.querySelector(`.btab[data-tab="${name}"]`);
  if (btn) btn.classList.add("active");
  if (name === "terminal") { const d = $("term-dot"); if (d) d.classList.remove("show"); }
  renderBottom();
}
function logLine(text, sev) {
  LOG.push({sev:sev||"info", line:text, ts:new Date().toLocaleTimeString()});
  if (currentBottomTab==="terminal") renderBottom();
  // Errors logged while the terminal tab is hidden get an unread dot so
  // they never pass silently (UX audit 3.5).
  else if (sev === "error") { const d = $("term-dot"); if (d) d.classList.add("show"); }
}
function logSep(label) {
  LOG.push({sev:"sep", line:label, ts:new Date().toLocaleTimeString()});
  if (currentBottomTab==="terminal") renderBottom();
}
function setPos(ln, col) {
  const total = CURRENT_FILE ? CURRENT_FILE.lines : 0;
  const text  = total > 0 ? `Ln ${ln}/${total}, Col ${col}` : `Ln ${ln}, Col ${col}`;
  const sp = $("status-pos"); if (sp) sp.textContent = text;
  const ep = $("ed-pos");     if (ep) ep.textContent = text;
}
function renderDiagnostics() {
  const d = STATE.diagnostics||[];
  const errors = d.filter((x)=>x.sev==="error").length;
  const warns  = d.filter((x)=>x.sev==="warn").length;
  const badge  = $("diag-count");
  badge.textContent = errors + warns;
  if (errors) {
    badge.style.background = "var(--error)";
    badge.style.color = "#fff";
  } else {
    badge.style.background = "";
    badge.style.color = "";
  }
  renderBottom();
}
function _renderDiff(text) {
  return text.split("\n").map((ln) => {
    if (ln.startsWith("+++") || ln.startsWith("---") || ln.startsWith("diff ") || ln.startsWith("index ") || ln.startsWith("new file"))
      return `<div class="ln"><div class="src" style="color:var(--fg-dim)">${escapeHtml(ln)||" "}</div></div>`;
    if (ln.startsWith("@@"))
      return `<div class="ln"><div class="src" style="color:var(--accent)">${escapeHtml(ln)||" "}</div></div>`;
    if (ln.startsWith("+"))
      return `<div class="ln"><div class="src" style="color:var(--success);background:rgba(52,211,153,.07)">${escapeHtml(ln)||" "}</div></div>`;
    if (ln.startsWith("-"))
      return `<div class="ln"><div class="src" style="color:var(--error);background:rgba(248,113,113,.07)">${escapeHtml(ln)||" "}</div></div>`;
    return `<div class="ln"><div class="src">${escapeHtml(ln)||" "}</div></div>`;
  }).join("");
}
function renderBottom() {
  const body = $("diag"); if (!body) return;
  if (currentBottomTab==="diagnostics") {
    const d = STATE.diagnostics||[];
    body.className = "bottom-body diag";
    body.innerHTML = d.map((x,i)=>{
      const m = x.line.match(/^([^:\n]+):(\d+) — /);
      const dataAttrs = m ? ` data-file="${escapeHtml(m[1])}" data-line="${m[2]}" style="cursor:pointer" title="Open ${escapeHtml(m[1])} at line ${m[2]}"` : "";
      return `<div class="diag-row"><span class="ts">#${i+1}</span><span class="${x.sev}"${dataAttrs}>${escapeHtml(x.line)}</span></div>`;
    }).join("") || `<div style="padding:6px 8px;color:var(--fg-dim);font-size:11px">No diagnostics.</div>`;
    body.querySelectorAll("[data-file]").forEach((el)=>{
      el.addEventListener("click", async ()=>{
        const f = el.getAttribute("data-file");
        const lineNum = parseInt(el.getAttribute("data-line")||"1");
        await openFile(f);
        const codeEl = $("main-code");
        if (codeEl && lineNum) {
          const lns = codeEl.querySelectorAll(".ln");
          const target = lns[lineNum-1];
          if (target) {
            target.scrollIntoView({block:"center"});
            target.classList.add("hl");
            setTimeout(()=>target.classList.remove("hl"), 2000);
          }
        }
      });
    });
  } else if (currentBottomTab==="terminal") {
    body.className = "bottom-body diag";
    const MAX_ROWS = 400;
    const overflow = LOG.length > MAX_ROWS;
    const rows = LOG.length ? LOG.slice(-MAX_ROWS) : [{sev:"dim",line:"(empty) — run an action or prompt",ts:""}];
    const overflowMsg = overflow ? `<div style="padding:3px 8px;font-size:10px;color:var(--fg-dim)">… ${LOG.length - MAX_ROWS} earlier lines hidden — use ✕ Clear</div>` : "";
    body.innerHTML = `<div style="display:flex;justify-content:flex-end;padding:2px 6px">${LOG.length?`<span class="ts" style="cursor:pointer;color:var(--fg-dim);font-size:10px" id="term-clear">✕ Clear</span>`:""}</div>${overflowMsg}`
      + rows.map((x)=>x.sev==="sep"
          ? `<div style="display:flex;align-items:center;gap:6px;padding:3px 0;margin:2px 0"><span class="ts">${x.ts}</span><span style="flex:1;height:1px;background:var(--border)"></span><span class="dim" style="font-size:10px;white-space:nowrap">${escapeHtml(x.line)}</span><span style="flex:1;height:1px;background:var(--border)"></span></div>`
          : `<div><span class="ts">${x.ts||""}</span><span class="${x.sev}">${escapeHtml(x.line)}</span></div>`
      ).join("");
    body.scrollTop = body.scrollHeight;
    const clr = body.querySelector("#term-clear");
    if (clr) clr.addEventListener("click",()=>{ LOG.length=0; renderBottom(); });
  } else if (currentBottomTab==="ai") {
    body.className = "bottom-body";
    if (!LAST_PREVIEW) {
      body.innerHTML = `<div style="color:var(--fg-dim);padding:8px">Select a prompt or run an action — preview appears here.</div>`;
    } else {
      const isDiff = LAST_PREVIEW.startsWith("diff ") || LAST_PREVIEW.includes("\n--- a/") || LAST_PREVIEW.includes("\n+++ b/");
      const isScl  = /\b(FUNCTION_BLOCK|FUNCTION|VAR_INPUT|VAR_OUTPUT|END_VAR|END_FUNCTION)\b/.test(LAST_PREVIEW);
      const isJson = !isDiff && !isScl && /^\s*[\[{]/.test(LAST_PREVIEW.trimStart());
      if (isDiff) {
        body.innerHTML = `<div class="code" style="font-size:11px;line-height:17px;padding:4px 0">${_renderDiff(LAST_PREVIEW)}</div>`;
      } else if (isScl) {
        body.innerHTML = `<div class="code" style="font-size:11px;line-height:17px;padding:4px 0">${buildCodeHtml(LAST_PREVIEW,"scl")}</div>`;
      } else if (isJson) {
        body.innerHTML = `<div class="code" style="font-size:11px;line-height:17px;padding:4px 0">${buildCodeHtml(LAST_PREVIEW,"json")}</div>`;
      } else {
        body.innerHTML = `<pre style="white-space:pre-wrap;font-family:var(--mono);font-size:11px;color:var(--fg-muted);line-height:18px;margin:0;padding:6px 8px">${escapeHtml(LAST_PREVIEW)}</pre>`;
      }
    }
  } else {
    body.className = "bottom-body";
    const f = CURRENT_FILE;
    if (f) {
      const tab = OPEN_TABS.find((t)=>t.path===f._path);
      const text = tab ? (tab.text||f._text||"") : (f._text||"");
      const chars = text.length;
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      const isDirty = tab && tab.dirty;
      const statusLabel = isDirty ? `<span style="color:var(--warning)">● Unsaved</span>` : `<span style="color:var(--success)">✓ Saved</span>`;
      const ext = (f.name||"").split(".").pop().toLowerCase();
      const langLabel = {scl:"IEC 61131-3 SCL",st:"Structured Text",md:"Markdown",json:"JSON",xlsx:"Excel",xls:"Excel"}[ext]||ext.toUpperCase()||"Text";
      body.innerHTML = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 20px;font-size:11.5px;line-height:1.9;padding:4px 6px">
        <div style="color:var(--fg-dim)">File</div><div style="color:var(--fg);font-weight:600;font-family:var(--mono)">${escapeHtml(f.name)}</div>
        <div style="color:var(--fg-dim)">Language</div><div style="color:var(--fg)">${langLabel}</div>
        <div style="color:var(--fg-dim)">Size</div><div style="color:var(--fg)">${f.lines} lines · ${chars.toLocaleString()} chars · ${words.toLocaleString()} words</div>
        <div style="color:var(--fg-dim)">Status</div><div>${statusLabel}</div>
        <div style="color:var(--fg-dim)">Gate</div><div style="color:var(--fg)">Gate ${STATE.gate}/${STATE.gate_max} — ${STATE.gate_name||""}</div>
        <div style="color:var(--fg-dim)">Platform</div><div style="color:var(--fg)">${escapeHtml(STATE.platform||"—")}</div>
        <div style="color:var(--fg-dim)">Path</div><div style="color:var(--fg-dim);font-family:var(--mono);font-size:10px;word-break:break-all">${escapeHtml(f._path||"")}</div>
      </div>`;
    } else {
      body.innerHTML = `<div style="color:var(--fg-dim);padding:8px">Select a file — details appear here.</div>`;
    }
  }
}

/* ─────────────────────────────────────────────────────────────────────
   FILE OPEN  (multi-tab)
───────────────────────────────────────────────────────────────────── */
function _isIOListPath(path) {
  const up = (path||"").toUpperCase();
  return up.includes("RD01") && up.includes("IO") && (up.endsWith(".MD")||up.endsWith(".XLSX")||up.endsWith(".XLS"));
}

// RD11/RD08 worksheets open in their grid editors (V2, 2026-07-07)
function _hmiTableKind(path) {
  const up = (path||"").toUpperCase();
  if (up.endsWith("RD11_HMI.MD")) return "rd11";
  if (up.endsWith("RD08_ALARM.MD")) return "rd08";
  return null;
}

// Grid editor for the RD11/RD08 worksheets — same discipline as the dossier
// decision grid: grey deterministic columns are locked, amber ✎ columns are
// the engineer's; saves persist to hmi_decisions.json (regeneration-proof).
function renderHmiTableGrid(cw, t) {
  const ht = t.hmi;
  const editable = new Set(ht.editable || []);
  const key = ht.key;
  const editCount = () => Object.values(t.hmiEdits||{})
    .reduce((n, c) => n + Object.keys(c).length, 0);
  const th = ht.columns.map((c) =>
    `<th style="${editable.has(c)?"color:var(--warning)":""}">${escapeHtml(c)}${editable.has(c)?" ✎":""}</th>`).join("");
  const body = ht.rows.map((r) => {
    const k = r[key];
    return `<tr>${ht.columns.map((c) => {
      const v = r[c] || "";
      if (!editable.has(c)) {
        return `<td style="color:${c===key?"var(--fg)":"var(--fg-dim)"};white-space:nowrap">${escapeHtml(v)}</td>`;
      }
      return `<td style="padding:0"><input class="hmi-cell" data-key="${escapeHtml(k)}" data-col="${escapeHtml(c)}" value="${escapeHtml(v)}"
        style="width:100%;min-width:90px;background:rgba(217,164,65,.07);border:1px dashed rgba(217,164,65,.45);border-radius:3px;color:var(--fg);font:inherit;padding:3px 6px" /></td>`;
    }).join("")}</tr>`;
  }).join("");
  cw.innerHTML = `<div style="display:flex;flex-direction:column;height:100%">
    <div style="display:flex;gap:10px;align-items:center;padding:7px 12px;border-bottom:1px solid var(--border);flex-wrap:wrap">
      <b style="font-size:12.5px">${escapeHtml(ht.file)}</b>
      <span class="sm-hint">${ht.rows.length} rows · grey = deterministic (locked) · <span style="color:var(--warning)">amber ✎ = engineer</span> — edits persist in hmi_decisions.json, regeneration keeps them</span>
      <span style="flex:1"></span>
      <span id="hmi-grid-status" class="sm-hint"></span>
      <button class="btn primary" id="hmi-grid-save">Save (<span id="hmi-grid-n">0</span>)</button>
    </div>
    <div style="overflow:auto;flex:1;padding:6px 10px">
      <table class="md-table" style="font-size:11.5px;font-variant-numeric:tabular-nums">
        <thead><tr>${th}</tr></thead><tbody>${body}</tbody>
      </table>
    </div>
  </div>`;
  const nEl = cw.querySelector("#hmi-grid-n");
  cw.querySelectorAll(".hmi-cell").forEach((inp) => inp.addEventListener("input", () => {
    const k = inp.getAttribute("data-key"), c = inp.getAttribute("data-col");
    t.hmiEdits[k] = t.hmiEdits[k] || {};
    t.hmiEdits[k][c] = inp.value;
    t.dirty = true;
    nEl.textContent = String(editCount());
    renderTabBar();
  }));
  cw.querySelector("#hmi-grid-save").addEventListener("click", async () => {
    if (!editCount()) { toast("No changes"); return; }
    const r = await Backend.save_hmi_table(ht.kind, t.hmiEdits);
    const st = cw.querySelector("#hmi-grid-status");
    if (r && r.ok) {
      toast(r.msg || "Saved");
      if ((r.problems||[]).length) {
        st.innerHTML = `<span style="color:var(--warning)">⚠ ${r.problems.length} refused</span>`;
        alert("Refused edits (locked columns / validation):\n\n" + r.problems.join("\n"));
      }
      t.hmiEdits = {}; t.dirty = false;
      const fresh = await Backend.read_hmi_table(ht.kind);
      if (fresh && fresh.ok) { t.hmi = fresh; }
      renderActiveTab();
    } else {
      toast((r && r.msg) || "Save failed");
    }
  });
}

async function openFile(path, _row) {
  if (!path) return;
  exitSplit();  // exit split mode when opening a fresh file

  // switch to existing tab if already open
  const existing = OPEN_TABS.find((t)=>t.path===path);
  if (existing) { ACTIVE_TAB = path; renderTabBar(); renderActiveTab(); _updateContextRail(path); return; }

  const f = await Backend.read_file(path);
  const isIOList = f.kind === "io_list" || _isIOListPath(path);
  const isScl = (f.kind==="scl")||path.endsWith(".scl");
  let kind  = isIOList?"io_list":(isScl?"scl":(f.kind||"text"));
  let hmiTable = null;
  const hmiKind = _hmiTableKind(path);
  if (hmiKind && !isIOList) {
    const ht = await Backend.read_hmi_table(hmiKind);
    if (ht && ht.ok) { kind = "hmi_table"; hmiTable = ht; }
  }
  // The wiring proposal opens as the APPROVAL grid (dilim ⑤): every
  // HMI→PLC line needs a named engineer decision before code generation.
  let hmiWiring = null;
  if ((path||"").toUpperCase().endsWith("HMI_WIRING_PROPOSAL.MD")) {
    const hw = await Backend.get_hmi_wiring();
    if (hw && hw.ok) { kind = "hmi_wiring"; hmiWiring = hw; }
  }
  const tabEntry = {path, name:f.name||path, kind, dirty:false, text:f.text||"", ioRows: isIOList?(f.rows||[]):null, ioFm: isIOList?(f.frontmatter||{}):null,
    xlsxRows: kind==="xlsx"?(f.rows||[]):null, xlsxSheet: f.sheet||"", xlsxTruncated: !!f.truncated,
    hmi: hmiTable, hmiEdits: {}, wiring: hmiWiring};
  OPEN_TABS.push(tabEntry);
  ACTIVE_TAB = path;
  CURRENT_FILE = {name:f.name||path, kind, lines:isIOList?(f.rows||[]).length:(f.text||"").split("\n").length, _path:path, _text:f.text||""};
  renderTabBar(); renderActiveTab();
  if (currentBottomTab==="inspector") renderBottom();
  logLine(`[file] Opened ${f.name||path}`, "dim");
  _updateContextRail(path);
}

async function _updateContextRail(path) {
  const ctx = await Backend.get_file_context(path);
  if (!ctx) return;
  if (ctx.actions && ctx.actions.length) { STATE.actions = ctx.actions; renderActions(); injectIcons($("actions")); }
  if (ctx.prompts && ctx.prompts.length) { STATE.prompts = ctx.prompts; renderPrompts(); }
  // Honest scope label: FILE actions act on the selected file, PROJECT
  // actions on the whole project (2026-07-06 audit).
  const caps = $("actions-caps");
  if (caps) caps.textContent =
    ctx.scope === "file" ? t("rr.actions_file") : t("rr.actions_project");
}

/* ─────────────────────────────────────────────────────────────────────
   REPORTS PANEL — companion reports quick access + project QA + handover
───────────────────────────────────────────────────────────────────── */
/* ── Machine Dossier in-app renderers (used by the dossier view) ───────── */

function renderDossierSvg(cw, tab) {
  // Own generated SVG — trusted content, rendered on a paper background so
  // the theme.json page colours read exactly as they will in the delivery.
  cw.innerHTML =
    `<div style="display:flex;flex-direction:column;height:100%">
      <div style="display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border)">
        <span class="sm-hint">${escapeHtml(tab.name)} — ${t("dossier.view_hint")}</span>
        <span class="fill" style="flex:1"></span>
        <button class="btn-sm" id="dsvg-ext">${t("dossier.open_external")}</button>
      </div>
      <div style="flex:1;overflow:auto;background:#e8eaec;padding:18px">
        <div style="background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.25);max-width:1020px;margin:0 auto">${tab.svgText}</div>
      </div>
    </div>`;
  const ext = cw.querySelector("#dsvg-ext");
  if (ext) ext.addEventListener("click", async ()=>{
    const res = await Backend.open_dossier_file(tab.name);
    if (!(res && res.ok)) toast(res && res.msg ? res.msg : t("gen.could_not_open"));
  });
}

function renderDecisionGrid(cw, tab) {
  const H = tab.headers || [];
  const lockN = H.length - 2;   // last two columns = engineer's
  const head = H.map((h, i) =>
    `<th style="${i>=lockN?"color:var(--accent)":""}">${escapeHtml(h)}</th>`).join("");
  const body = (tab.rows||[]).map((r, ri)=>{
    const cells = r.map((c, ci)=>{
      if (ci < lockN) return `<td class="dg-lock">${escapeHtml(String(c||""))}</td>`;
      const field = ci === lockN ? "decision" : "impact";
      return `<td><input class="dg-in" data-row="${ri}" data-field="${field}" value="${escapeHtml(String(c||""))}"/></td>`;
    }).join("");
    return `<tr data-addr="${escapeHtml(String(r[0]||""))}">${cells}</tr>`;
  }).join("");
  cw.innerHTML =
    `<div style="display:flex;flex-direction:column;height:100%">
      <div style="display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border)">
        <span class="sm-hint">${t("dossier.grid_hint")}</span>
        <span class="fill" style="flex:1"></span>
        <button class="btn-sm" id="dg-delta" title="Structured KEEP/REPLACE/DROP reading of the decisions + their cascade (read-only byproduct of the delta engine)">⇄ Old→Target</button>
        <button class="btn-sm" id="dg-excel">${t("dossier.open_external")}</button>
        <button class="btn primary" id="dg-save" style="padding:3px 14px">${t("dossier.save_decisions")}</button>
      </div>
      <div style="flex:1;overflow:auto">
        <table class="dg-table" style="border-collapse:collapse;font-size:11.5px;width:100%">
          <thead><tr>${head}</tr></thead><tbody>${body}</tbody>
        </table>
      </div>
    </div>`;
  cw.querySelectorAll(".dg-table th").forEach((th)=>{
    th.style.cssText += "position:sticky;top:0;background:var(--bg-alt,#1c2226);text-align:left;padding:4px 8px;border-bottom:1px solid var(--border);z-index:1";
  });
  cw.querySelectorAll(".dg-table td").forEach((td)=>{
    td.style.cssText += "padding:2px 8px;border-bottom:1px solid var(--border);white-space:nowrap";
  });
  cw.querySelectorAll(".dg-in").forEach((inp)=>{
    inp.style.cssText = "width:180px;background:var(--bg,#14181b);color:var(--fg,#e6eaec);border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:11.5px";
    inp.addEventListener("input", ()=>{ tab.dirty = true; });
  });
  const save = cw.querySelector("#dg-save");
  if (save) save.addEventListener("click", async ()=>{
    const byRow = {};
    cw.querySelectorAll(".dg-in").forEach((inp)=>{
      const tr = inp.closest("tr");
      const addr = tr ? tr.getAttribute("data-addr") : "";
      if (!addr) return;
      byRow[addr] = byRow[addr] || {address: addr, decision: "", impact: ""};
      byRow[addr][inp.getAttribute("data-field")] = inp.value;
    });
    const res = await Backend.save_decision_table(Object.values(byRow));
    if (res && res.ok) {
      tab.dirty = false;
      toast(res.msg || t("dossier.saved"));
      logLine(`[dossier] ${res.msg}`, "success");
    } else {
      toast(res && res.msg ? res.msg : "Save failed");
    }
  });
  const excel = cw.querySelector("#dg-excel");
  if (excel) excel.addEventListener("click", async ()=>{
    const res = await Backend.open_dossier_file("04_decision_table.xlsx");
    if (!(res && res.ok)) toast(res && res.msg ? res.msg : t("gen.could_not_open"));
  });
  const delta = cw.querySelector("#dg-delta");
  if (delta) delta.addEventListener("click", ()=>renderDecisionDelta(cw, tab));
}

/* Old⇄Target — the dossier's comparison view (locked design 2026-07-07:
   a toggle inside the dossier, NOT a permanent split). Byproduct of the
   decision-cascade engine: verb chips (KEEP/REPLACE/DROP/UNCLASSIFIED),
   per-device old vs target, and the propagation cascade with its status —
   the same evidence the Gate-3 reconciliation enforces. Read-only. */
async function renderDecisionDelta(cw, tab) {
  const r = await Backend.get_decision_cascade();
  if (!r || !r.ok) { toast((r && r.msg) || "Cascade failed"); return; }
  const s = r.summary || {};
  const V_CLS = { KEEP: "ok", REPLACE: "mod", DROP: "err", UNCLASSIFIED: "warn" };
  const vChip = (v) => `<span class="badge ${V_CLS[v]||"warn"}">${escapeHtml(v)}</span>`;
  const ST_COLOR = { pending: "var(--warning)", review: "var(--accent)", propagated: "var(--success)" };
  const rows = (r.devices||[]).map((d)=>`
    <tr>
      <td style="white-space:nowrap">${vChip(d.verb)}${d.safety?' <span title="safety device — red class rules apply">⚠️</span>':''}</td>
      <td><b>${escapeHtml(d.addr)}</b>${d.equipment?` <span class="fg-dim">${escapeHtml(d.equipment)}</span>`:""}<br><span class="fg-dim">${escapeHtml(d.name||"")}</span></td>
      <td>${escapeHtml(d.function||"—")}${d.old?`<br><span class="fg-dim">${escapeHtml(d.old)}</span>`:""}</td>
      <td>${escapeHtml(d.target||"—")}${d.impact?`<br><span class="fg-dim">impact: ${escapeHtml(d.impact)}</span>`:""}</td>
      <td>${(d.affected||[]).map((a)=>
        `<div style="color:${ST_COLOR[a.status]||"var(--fg-dim)"}">• ${escapeHtml(a.artifact)} ${escapeHtml(a.key)} — ${escapeHtml(a.action)} <b>[${escapeHtml(a.status)}]</b></div>`
      ).join("")||'<span class="fg-dim">—</span>'}</td>
    </tr>`).join("");
  const chip = (label, n, cls) => `<span class="badge ${cls}">${label}: ${n||0}</span>`;
  cw.innerHTML =
    `<div style="display:flex;flex-direction:column;height:100%">
      <div style="display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border);flex-wrap:wrap">
        <span class="caps">⇄ Old → Target</span>
        ${chip("KEEP", s.KEEP, "ok")} ${chip("REPLACE", s.REPLACE, "mod")}
        ${chip("DROP", s.DROP, "err")} ${chip("unclassified", s.UNCLASSIFIED, "warn")}
        ${chip("pending propagation", s.pending, s.pending?"warn":"ok")}
        <span class="fill" style="flex:1"></span>
        <button class="btn-sm" id="dd-grid">← Decision grid</button>
      </div>
      <div style="flex:1;overflow:auto">
        ${(r.devices||[]).length ? `
        <table class="dg-table" style="border-collapse:collapse;font-size:11.5px;width:100%">
          <thead><tr><th>Verb</th><th>Device (old)</th><th>Function / current</th><th>Target (decision)</th><th>Cascade</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>` : `<div class="editor-empty" style="margin:auto;padding:40px;text-align:center;color:var(--fg-dim)">No decisions yet — fill the DECISION column in the grid; this view derives KEEP/REPLACE/DROP and the cascade from it.</div>`}
      </div>
    </div>`;
  cw.querySelectorAll(".dg-table th").forEach((th)=>{
    th.style.cssText += "position:sticky;top:0;background:var(--bg-alt,#1c2226);text-align:left;padding:4px 8px;border-bottom:1px solid var(--border);z-index:1";
  });
  cw.querySelectorAll(".dg-table td").forEach((td)=>{
    td.style.cssText += "padding:4px 8px;border-bottom:1px solid var(--border);vertical-align:top";
  });
  const back = cw.querySelector("#dd-grid");
  if (back) back.addEventListener("click", async ()=>{
    const g = await Backend.get_decision_table();
    if (g && g.ok) renderDecisionGrid(cw, {name: tab.name, headers: g.headers, rows: g.rows});
    else toast((g && g.msg) || "Grid reload failed");
  });
}

/* HMI wiring approval (dilim ⑤) — the proposal file opens as THIS grid.
   Binding an HMI command into the program changes machine semantics, so
   each HMI→PLC line needs a NAMED approval (or an explicit rejection);
   Sts lines are display-only and generated from proven equations without
   approval. "Generate wiring code" emits FC_HMI_Wiring.scl from the
   approved lines; gaps become honest TODOs inside the file. */
async function renderHmiWiringView(cw, t) {
  const w = t.wiring;
  if (!w || !w.ok) {
    cw.innerHTML = `<div class="editor-empty" style="margin:auto">${escapeHtml((w&&w.msg)||"Wiring rows not available")}</div>`;
    return;
  }
  const stateChip = (r) => {
    if (r.area === "Sts") return `<span class="badge ok" title="Display only — generated from the proven legacy equation, no approval needed">auto (display)</span>`;
    if (r.approved === true)  return `<span class="badge ok" title="${escapeHtml(r.note||"")}">✓ approved · ${escapeHtml(r.by||"")} ${escapeHtml(r.at||"")}</span>`;
    if (r.approved === false) return `<span class="badge err" title="${escapeHtml(r.note||"")}">✗ rejected${r.by?" · "+escapeHtml(r.by):""}</span>`;
    return `<span class="badge warn">undecided</span>`;
  };
  const ctl = (r) => r.area === "Sts" ? "" : `
      <button class="btn-sm hw-approve" data-tag="${escapeHtml(r.tag)}" title="Named approval — generates the merge/binding">✓ Approve</button>
      <button class="btn-sm hw-reject" data-tag="${escapeHtml(r.tag)}" title="Keep it off the PLC side">✗ Reject</button>`;
  const rows = (w.rows||[]).map((r)=>`
    <tr>
      <td class="mono" style="white-space:nowrap">${escapeHtml(r.tag)}</td>
      <td>${escapeHtml(r.label||"")}</td>
      <td class="mono">${escapeHtml(r.legacy||"—")}</td>
      <td style="white-space:nowrap">${escapeHtml(r.direction)}</td>
      <td style="white-space:nowrap">${stateChip(r)}</td>
      <td style="white-space:nowrap">${ctl(r)}</td>
    </tr>`).join("");
  cw.innerHTML =
    `<div style="display:flex;flex-direction:column;height:100%">
      <div style="display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border);flex-wrap:wrap">
        <span class="caps">HMI wiring — engineer approval</span>
        <span class="badge ok">approved: ${w.approved||0}</span>
        <span class="badge err">rejected: ${w.rejected||0}</span>
        <span class="badge ${w.open?"warn":"ok"}">open: ${w.open||0}</span>
        ${w.dropped?`<span class="badge err" title="RD11 rows whose PLC_Tag breaks the DB_HMI contract — they are NOT in this grid and will never be wired until RD11 is fixed">dropped: ${w.dropped}</span>`:""}
        <span class="fill" style="flex:1"></span>
        <button class="btn primary" id="hw-gen" style="padding:3px 14px" title="FC_HMI_Wiring.scl from APPROVED lines + proven lamp/alarm equations (gaps become TODOs, never guesses)">⚡ Generate wiring code</button>
      </div>
      <div class="sm-hint" style="padding:4px 10px;border-bottom:1px solid var(--border)">Nothing is auto-applied: HMI→PLC lines need a named approval (they change program semantics); Sts lines are display-only and derive from the proven legacy equations.</div>
      ${(w.problems&&w.problems.length)?`<div style="font-size:11.5px;background:var(--bg-tertiary,rgba(255,80,0,.08));border-bottom:1px solid var(--err,#c33);padding:6px 10px">
        ⚠ <b>${w.problems.length} RD11 row(s) could not enter the proposal</b> (audit S-5 — they used to vanish silently):
        <ul style="margin:4px 0 0 18px">${w.problems.slice(0,10).map((p)=>`<li>${escapeHtml(p)}</li>`).join("")}</ul>
        ${w.problems.length>10?`<div>… +${w.problems.length-10} more</div>`:""}
      </div>`:""}
      <div style="flex:1;overflow:auto">
        <table class="dg-table" style="border-collapse:collapse;font-size:11.5px;width:100%">
          <thead><tr><th>Interface tag</th><th>Label</th><th>Legacy</th><th>Direction</th><th>State</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
  cw.querySelectorAll(".dg-table th").forEach((th)=>{
    th.style.cssText += "position:sticky;top:0;background:var(--bg-alt,#1c2226);text-align:left;padding:4px 8px;border-bottom:1px solid var(--border);z-index:1";
  });
  cw.querySelectorAll(".dg-table td").forEach((td)=>{
    td.style.cssText += "padding:3px 8px;border-bottom:1px solid var(--border)";
  });
  const _refresh = async () => {
    const hw = await Backend.get_hmi_wiring();
    if (hw && hw.ok) { t.wiring = hw; renderHmiWiringView(cw, t); }
  };
  cw.querySelectorAll(".hw-approve").forEach((b)=>b.addEventListener("click", async ()=>{
    const tag = b.getAttribute("data-tag");
    const by = (window.prompt(`Approve wiring of ${tag} — this changes program semantics.\nEngineer name / role (e.g. 'H. Becker, IBN'):`)||"").trim();
    if (!by) { toast("Approval cancelled — name required"); return; }
    const note = (window.prompt("Optional note (binding detail):")||"").trim();
    const r = await Backend.set_hmi_wiring(tag, true, by, note);
    if (r && r.ok) { toast(`${tag} approved`); _refresh(); }
    else toast((r&&r.msg)||"Approval failed");
  }));
  cw.querySelectorAll(".hw-reject").forEach((b)=>b.addEventListener("click", async ()=>{
    const tag = b.getAttribute("data-tag");
    const note = (window.prompt(`Reject wiring of ${tag} — optional reason:`)||"").trim();
    const r = await Backend.set_hmi_wiring(tag, false, "", note);
    if (r && r.ok) { toast(`${tag} rejected`); _refresh(); }
    else toast((r&&r.msg)||"Rejection failed");
  }));
  const gen = cw.querySelector("#hw-gen");
  if (gen) gen.addEventListener("click", async ()=>{
    gen.disabled = true; gen.textContent = "Generating…";
    const r = await Backend.generate_hmi_wiring_code();
    gen.disabled = false; gen.textContent = "⚡ Generate wiring code";
    if (r && r.ok) {
      toast(r.msg || "FC_HMI_Wiring.scl written");
      logLine(`[hmi-wiring] ${r.msg}`, "success");
      (r.todo||[]).slice(0, 20).forEach((x)=>logLine(`[hmi-wiring] TODO ${x}`, "warn"));
      if ((r.todo||[]).length) switchBottomTab("terminal");
    } else toast((r&&r.msg)||"Wiring codegen failed");
  });
}

/* 3-part sidebar (2026-07-07 user decision): ① Explorer tree ② Workdesk
   — every surface the engineer EDITS or SIGNS, with honest status chips
   ③ Review — read-only material (reference RDs in reading mode +
   deterministic reports). The old passive Reports list is retired. */
const _DESK_STATE_CHIP = {
  missing:  ["—", "var(--fg-dim)", "not produced yet"],
  draft:    ["🟡", "var(--warning)", "draft — engineer work pending"],
  reviewed: ["🟢", "var(--success)", "reviewed"],
  locked:   ["🔒", "var(--success)", "locked at Gate 3"],
  na:       ["⊘", "var(--fg-dim)", "Not Applicable"],
  grid:     ["✎", "var(--accent)", "editable grid"],
  open:     ["✍", "var(--warning)", "decisions pending"],
  done:     ["✓", "var(--success)", "all decided"],
};

async function renderReportsPanel() {   // name kept: single sidebar refresh hook
  const deskPanel = $("workdesk-panel"), deskList = $("workdesk-list");
  const readPanel = $("reading-panel"), readList = $("reading-list");
  if (!deskPanel || !readPanel) return;
  const r = await Backend.get_workdesk();
  if (!r || !r.ok) { deskPanel.style.display = "none"; readPanel.style.display = "none"; return; }

  const desk = r.desk || [];
  deskPanel.style.display = "";
  deskList.innerHTML = desk.map((d)=>{
    const [chip, color, hint] = _DESK_STATE_CHIP[d.state] || _DESK_STATE_CHIP.missing;
    const count = (d.count !== undefined && d.count > 0) ? ` <span class="mono" style="font-size:10px;color:var(--warning)">(${d.count})</span>` : "";
    const dim = d.state === "missing" ? "opacity:.45;" : "";
    return `<div class="tree-row desk-row" data-kind="${escapeHtml(d.kind)}" data-path="${escapeHtml(d.path||"")}" title="${escapeHtml(d.by ? hint+" · "+d.by : hint)}" style="padding-left:10px;${dim}">
      <span class="ic" data-i="${escapeHtml(d.icon||"file")}" data-s="13"></span>
      <span class="tree-label">${escapeHtml(d.label)}</span>${count}
      <span style="margin-left:auto;color:${color};font-size:11px">${chip}</span>
    </div>`;
  }).join("");
  injectIcons(deskList);
  deskList.querySelectorAll(".desk-row").forEach((row)=>{
    row.addEventListener("click", async ()=>{
      const kind = row.getAttribute("data-kind") || "";
      const path = row.getAttribute("data-path") || "";
      if (kind === "decisions") {           // dossier decision grid (Old→Target inside)
        _dossierSel = "04_decision_table.xlsx";
        showFlowchartView();
      } else if (kind === "wiring") {       // approval grid (kind hmi_wiring)
        setActivePage("explorer"); openFile(path);
      } else if (path) {                    // RD grids / RD05 file
        setActivePage("explorer"); openFile(path);
      } else {
        toast("Not produced yet — run the generating step first");
      }
    });
  });

  const reading = r.reading || [];
  readPanel.style.display = reading.length ? "" : "none";
  readList.innerHTML = reading.map((it)=>`
    <div class="tree-row read-row" data-kind="${escapeHtml(it.kind)}" data-rd="${escapeHtml(it.rd||"")}" data-path="${escapeHtml(it.path)}" title="${escapeHtml(it.hint||it.label)}" style="padding-left:10px">
      <span class="ic" data-i="${it.kind==="report"?"bar-chart":"file-text"}" data-s="13"></span>
      <span class="tree-label">${escapeHtml(it.label)}</span>
    </div>`).join("");
  injectIcons(readList);
  readList.querySelectorAll(".read-row").forEach((row)=>{
    row.addEventListener("click", ()=>{
      const kind = row.getAttribute("data-kind") || "";
      const path = row.getAttribute("data-path");
      if (kind.startsWith("rdread:")) {
        openRdReadingView(row.getAttribute("data-rd"), path);  // rendered MD, no editor
      } else {
        openFile(path);
      }
    });
  });

  const ho = $("btn-handover");
  if (ho && !ho._wired) {
    ho._wired = true;
    ho.addEventListener("click", async ()=>{
      logLine("[handover] Building handover package…", "info");
      const res = await Backend.export_handover_package();
      if (res && res.ok) { logLine(`[handover] ${res.msg}`, "success"); toast(res.msg); }
      else { logLine(`[handover] ${res && res.msg || "failed"}`, "error"); }
    });
  }
}

function renderTabBar() {
  const tb = $("tabbar");
  tb.querySelectorAll(".tab").forEach((x)=>x.remove());
  OPEN_TABS.forEach((t)=>{
    const tabIcon = FILE_ICON[t.kind] || "file";
    const tabIc   = t.kind==="scl"?"ti-scl":t.kind==="json"?"ti-json":t.kind==="md"?"ti-md":"";
    const tab   = document.createElement("div");
    tab.className = `tab ${t.path===ACTIVE_TAB?"active":""}`;
    tab.setAttribute("data-path", t.path);
    tab.innerHTML = `<span class="ic ${tabIc}" data-i="${tabIcon}" data-s="12"></span><span>${escapeHtml(t.name)}</span>${t.dirty?'<span class="dot" style="width:6px;height:6px;border-radius:3px;background:var(--accent)"></span>':''}<span class="ic x tab-close" data-i="x" data-s="11" title="Close"></span>`;
    tab.addEventListener("click",(e)=>{
      if (e.target.closest(".tab-close")) { closeTab(t.path); return; }
      ACTIVE_TAB = t.path; renderTabBar(); renderActiveTab();
    });
    const fill = tb.querySelector(".tab-fill");
    if (fill) tb.insertBefore(tab, fill); else tb.appendChild(tab);
  });
  injectIcons(tb);
}

function renderActiveTab() {
  closeFindBar();
  const t = OPEN_TABS.find((x)=>x.path===ACTIVE_TAB);
  if (!t) {
    $("codewrap").innerHTML = `<div class="editor-empty" id="editor-empty">Select a file from the Explorer — or press ⌘K</div>`;
    $("ed-breadcrumb").style.display = "none";
    CURRENT_FILE = null; editMode = false; renderBottom();
    document.querySelectorAll(".tree-row").forEach((r)=>r.classList.remove("active"));
    return;
  }
  CURRENT_FILE = {name:t.name, kind:t.kind, lines:t.kind==="io_list"?(t.ioRows||[]).length:(t.text||"").split("\n").length, _path:t.path, _text:t.text||""};
  $("editor-empty") && ($("editor-empty").style.display="none");
  const cw = $("codewrap");
  if (!splitMode) {
    if (t.kind === "io_list") {
      renderIOGrid(cw, t);
    } else if (t.kind === "hmi_table") {
      renderHmiTableGrid(cw, t);
    } else if (t.kind === "hmi_wiring") {
      renderHmiWiringView(cw, t);
    } else if (t.kind === "xlsx") {
      // read-only spreadsheet preview (2026-07-07) — engineer never has to
      // leave the app to see what a generated xlsx contains
      const rows = t.xlsxRows || [];
      const head = rows.length ? rows[0] : [];
      const body = rows.slice(1);
      cw.innerHTML = `<div style="padding:8px 10px;overflow:auto;height:100%">
        <div class="sm-hint" style="margin-bottom:6px">${escapeHtml(t.name)} — sheet “${escapeHtml(t.xlsxSheet||"")}” · read-only preview${t.xlsxTruncated?" · first 300 rows":""}</div>
        <table class="md-table" style="font-size:11.5px;font-variant-numeric:tabular-nums">
          <thead><tr>${head.map((c)=>`<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
          <tbody>${body.map((r)=>`<tr>${r.map((c)=>`<td>${escapeHtml(c)}</td>`).join("")}</tr>`).join("")}</tbody>
        </table></div>`;
    } else if (editMode) {
      renderEditMode(cw, t);
    } else if (t.kind === "md" || t.path.endsWith(".md")) {
      cw.innerHTML = `<div class="md-view">${renderMarkdown(t.text)}</div>`;
      if (cw.querySelector(".mermaid") && typeof mermaid !== "undefined") {
        _mmApply();
        mermaid.run({ nodes: cw.querySelectorAll(".mermaid") });
      }
    } else {
      const code = buildCodeHtml(t.text, t.kind);
      cw.innerHTML = `<div class="code" id="main-code">${code}</div>`;
      setupEditorEvents(cw.querySelector(".code"), t);
    }
  }
  $("ed-breadcrumb").style.display = "flex";
  $("ed-bc-path").textContent = t.name;
  $("ed-saved").textContent   = t.dirty ? "● Unsaved" : "● Saved";
  $("ed-saved").style.color   = t.dirty ? "var(--warning)" : "var(--success)";
  const modeBtn = $("ed-mode-btn");
  if (modeBtn) {
    const noToggle = t.kind === "io_list" || t.kind === "table";
    modeBtn.style.display = noToggle ? "none" : "";
    if (!noToggle) { modeBtn.textContent = editMode ? "Preview" : "Edit"; modeBtn.classList.toggle("editing", editMode); }
  }
  setPos(1,1);
  document.querySelectorAll(".tree-row").forEach((r)=>r.classList.remove("active"));
  const row = document.querySelector(`.tree-row[data-path="${CSS.escape(t.path)}"]`);
  if (row) row.classList.add("active");
  if (currentBottomTab==="inspector") renderBottom();
}

/* ─────────────────────────────────────────────────────────────────────
   IO LIST GRID EDITOR  (M3)
───────────────────────────────────────────────────────────────────── */
const IO_COLS = ["tag","address","dtype","direction","equipment","description","normal_state","eng_unit","range_min","range_max","safety_related","source_module","old_tag","notes","status"];
const IO_HEADERS = ["Tag","Address","Type","Dir","Equipment","Description","NormalState","EngUnit","RangeMin","RangeMax","Safety","SrcModule","OldTag","Notes","Status"];
let _ioSortCol = null, _ioSortAsc = true, _ioIssues = [];

function renderIOGrid(cw, t) {
  const rows = t.ioRows || [];
  const issueMap = {};
  for (const iss of _ioIssues) {
    const key = `${iss.row}-${iss.column}`;
    issueMap[key] = iss;
  }
  const rowsHtml = rows.map((r, ri) => {
    const hasErr = _ioIssues.some((i)=>i.row===ri&&i.severity==="error");
    const hasWarn = _ioIssues.some((i)=>i.row===ri&&i.severity==="warning");
    const rowCls = hasErr?"io-row-err":(hasWarn?"io-row-warn":"");
    const cells = IO_COLS.map((col, ci) => {
      const issue = issueMap[`${ri}-${col}`];
      const cellCls = issue?(issue.severity==="error"?"io-cell-err":"io-cell-warn"):"";
      const tip = issue?`title="${escapeHtml(issue.message)}"` :"";
      return `<td class="io-cell ${cellCls}" contenteditable="true" data-row="${ri}" data-col="${col}" ${tip}>${escapeHtml(r[col]||"")}</td>`;
    }).join("");
    return `<tr class="${rowCls}" data-row="${ri}">
      <td class="io-rn">${ri+1}</td>${cells}
      <td class="io-act">
        <span class="io-btn" data-action="dup" data-row="${ri}" title="Duplicate row">+</span>
        <span class="io-btn del" data-action="del" data-row="${ri}" title="Delete row">×</span>
      </td></tr>`;
  }).join("");
  const headCols = IO_HEADERS.map((h, ci) => {
    const col = IO_COLS[ci];
    const sorted = _ioSortCol===col;
    return `<th class="io-th ${sorted?"sorted":""}" data-col="${col}">${h}${sorted?(_ioSortAsc?"▲":"▼"):""}</th>`;
  }).join("");
  cw.innerHTML = `<div class="io-wrap"><div class="io-toolbar">
    <span class="io-info">${rows.length} rows</span>
    <button class="btn" id="io-add">+ Row</button>
    <button class="btn" id="io-validate">Validate</button>
    <button class="btn" id="io-save">Save MD</button>
    <button class="btn" id="io-xlsx">Export XLSX</button>
    <button class="btn ghost" id="io-raw">Raw text</button>
  </div>
  <div class="io-grid-wrap">
    <table class="io-table" id="io-table">
      <thead><tr><th class="io-rn">#</th>${headCols}<th class="io-act"></th></tr></thead>
      <tbody id="io-tbody">${rowsHtml}</tbody>
    </table>
  </div></div>`;

  // Cell inline edit
  cw.querySelector("#io-table").addEventListener("input", (e) => {
    const td = e.target.closest("[data-row][data-col]");
    if (!td) return;
    const ri = parseInt(td.getAttribute("data-row"));
    const col = td.getAttribute("data-col");
    t.ioRows[ri][col] = td.textContent;
    t.dirty = true;
    renderTabBar();
  });
  // Sort on header click
  cw.querySelectorAll(".io-th").forEach((th) => th.addEventListener("click", () => {
    const col = th.getAttribute("data-col");
    if (_ioSortCol === col) _ioSortAsc = !_ioSortAsc; else { _ioSortCol = col; _ioSortAsc = true; }
    t.ioRows.sort((a, b) => ((a[col]||"") < (b[col]||"") ? -1 : 1) * (_ioSortAsc ? 1 : -1));
    renderIOGrid(cw, t);
  }));
  // Row actions
  cw.querySelectorAll(".io-btn").forEach((btn) => btn.addEventListener("click", () => {
    const action = btn.getAttribute("data-action");
    const ri = parseInt(btn.getAttribute("data-row"));
    if (action === "del") {
      if (t.ioRows.length > 0) { t.ioRows.splice(ri, 1); t.dirty = true; _ioIssues = _ioIssues.filter((i)=>i.row!==ri); }
    } else if (action === "dup") {
      t.ioRows.splice(ri + 1, 0, {...t.ioRows[ri]});
      t.dirty = true;
    }
    renderIOGrid(cw, t); renderTabBar();
  }));
  // Add row
  cw.querySelector("#io-add").addEventListener("click", () => {
    const empty = {}; IO_COLS.forEach((c) => empty[c] = ""); empty.status = "Active";
    t.ioRows.push(empty); t.dirty = true;
    renderIOGrid(cw, t); renderTabBar();
  });
  // Save
  cw.querySelector("#io-save").addEventListener("click", async () => {
    const r = await Backend.save_io_list(t.path, t.ioRows);
    if (r && r.ok) { t.dirty = false; renderTabBar(); toast(r.msg||"Saved"); logLine(`[io] ${r.msg}`, "success"); }
    else { toast((r&&r.msg)||"Save failed"); }
  });
  // Validate
  cw.querySelector("#io-validate").addEventListener("click", async () => {
    // Save latest cell edits first
    const r = await Backend.save_io_list(t.path, t.ioRows);
    const vr = await Backend.validate_io_list(t.path);
    _ioIssues = (vr && vr.issues) || [];
    renderIOGrid(cw, t);
    const errs = _ioIssues.filter((i)=>i.severity==="error").length;
    const warns = _ioIssues.filter((i)=>i.severity==="warning").length;
    toast(`Validate: ${errs} errors, ${warns} warnings`);
    const lines = _ioIssues.map((i)=>`[io/${i.severity}] row ${i.row+1} ${i.column}: ${i.message}`);
    lines.forEach((ln,idx)=>logLine(ln, _ioIssues[idx].severity==="error"?"error":"warn"));
    switchBottomTab("terminal");
  });
  // Export XLSX
  cw.querySelector("#io-xlsx").addEventListener("click", async () => {
    const r = await Backend.export_io_xlsx(t.path);
    if (r && r.ok) { toast(r.msg||"Exported"); logLine(`[io] ${r.msg}`, "success"); }
    else { toast((r&&r.msg)||"Export failed"); }
  });
  // Raw text fallback
  cw.querySelector("#io-raw").addEventListener("click", () => {
    t.kind = "text"; t.ioRows = null;
    Backend.read_file(t.path).then((f) => { t.text = f.text||""; renderActiveTab(); });
  });
}

function renderEditMode(cw, t) {
  cw.innerHTML = `<textarea class="code-textarea" id="code-textarea" spellcheck="false">${escapeHtml(t.text||"")}</textarea>`;
  const ta = $("code-textarea");
  ta.addEventListener("input", ()=>{
    t.text = ta.value;
    t.dirty = true;
    CURRENT_FILE._text = t.text;
    CURRENT_FILE.lines = t.text.split("\n").length;
    $("ed-saved").textContent = "● Unsaved";
    $("ed-saved").style.color = "var(--warning)";
    renderTabBar();
  });
  ta.addEventListener("keydown",(e)=>{
    if (e.key==="Tab") {
      e.preventDefault();
      const s=ta.selectionStart, end=ta.selectionEnd;
      ta.value = ta.value.slice(0,s)+"  "+ta.value.slice(end);
      ta.selectionStart = ta.selectionEnd = s+2;
      t.text = ta.value; t.dirty=true;
    }
    if ((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s") { e.preventDefault(); saveCurrentFile(); }
    // track position
    const pos = ta.value.slice(0,ta.selectionStart).split("\n");
    setPos(pos.length, pos[pos.length-1].length+1);
  });
  ta.addEventListener("click",()=>{
    const pos = ta.value.slice(0,ta.selectionStart).split("\n");
    setPos(pos.length, pos[pos.length-1].length+1);
  });
  ta.focus();
}

function toggleEditMode() {
  const t = OPEN_TABS.find((x)=>x.path===ACTIVE_TAB);
  if (!t) return;
  // if in edit mode, sync textarea content before switching
  if (editMode) {
    const ta = $("code-textarea");
    if (ta) { t.text = ta.value; CURRENT_FILE._text = t.text; }
  }
  editMode = !editMode;
  renderActiveTab();
}

function setupEditorEvents(codeEl, tab) {
  if (!codeEl) return;
  codeEl.addEventListener("click",(e)=>{
    const ln = e.target.closest(".ln");
    if (!ln) return;
    const lines = codeEl.querySelectorAll(".ln");
    let lineNum = 1;
    for (let i=0;i<lines.length;i++) { if (lines[i]===ln) { lineNum=i+1; break; } }
    setPos(lineNum, 1);
    // highlight clicked line
    codeEl.querySelectorAll(".ln.hl").forEach((x)=>x.classList.remove("hl"));
    ln.classList.add("hl");
    // request inline AI suggestion if key set
    requestInlineAI(tab, lineNum);
  });
}

function closeTab(path) {
  const t = OPEN_TABS.find((x)=>x.path===path);
  // sync textarea before checking dirty state
  if (t && path===ACTIVE_TAB && editMode) {
    const ta = $("code-textarea"); if (ta) t.text = ta.value;
  }
  if (t && t.dirty && !confirm(`"${t.name}" has unsaved changes. Close anyway?`)) return;
  OPEN_TABS = OPEN_TABS.filter((x)=>x.path!==path);
  if (ACTIVE_TAB===path) {
    ACTIVE_TAB = OPEN_TABS.length ? OPEN_TABS[OPEN_TABS.length-1].path : null;
    if (!ACTIVE_TAB) editMode = false;
  }
  renderTabBar(); renderActiveTab();
}

/* ─────────────────────────────────────────────────────────────────────
   IN-EDITOR FIND BAR  (Ctrl+F)
───────────────────────────────────────────────────────────────────── */
let _find = {open:false, q:"", lines:[], idx:0};

function openFindBar() {
  if (!ACTIVE_TAB) return;
  _find.open = true;
  _find.lines = []; _find.idx = 0;
  _renderFindBar();
  if (_find.q) _doFind();
}

function closeFindBar() {
  const bar = $("find-bar"); if (bar) bar.remove();
  _find.open = false;
  _applyFindHL([], -1);
}

function _renderFindBar() {
  let bar = $("find-bar");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "find-bar"; bar.className = "find-bar";
    const cw = $("codewrap"); if (!cw) return;
    cw.appendChild(bar);
  }
  const total = _find.lines.length;
  const pos   = total ? `${_find.idx+1}/${total}` : (_find.q ? "0/0" : "");
  bar.innerHTML = `<input id="find-input" class="find-input" value="${escapeHtml(_find.q)}" placeholder="Find in file…" />`
    + `<span class="find-count">${pos}</span>`
    + `<button class="find-btn" id="find-prev" title="Previous (Shift+Enter)">↑</button>`
    + `<button class="find-btn" id="find-next" title="Next (Enter / F3)">↓</button>`
    + `<button class="find-btn find-close" id="find-close" title="Close (Esc)">✕</button>`;
  const inp = bar.querySelector("#find-input");
  inp.focus(); inp.select();
  inp.addEventListener("input", ()=>{ _find.q = inp.value; _doFind(); });
  inp.addEventListener("keydown", (e)=>{
    if (e.key==="Escape")  { e.preventDefault(); e.stopPropagation(); closeFindBar(); }
    else if (e.key==="Enter" && e.shiftKey) { e.preventDefault(); _findStep(-1); }
    else if (e.key==="Enter")               { e.preventDefault(); _findStep(1); }
    else if (e.key==="F3"  && e.shiftKey)   { e.preventDefault(); _findStep(-1); }
    else if (e.key==="F3")                  { e.preventDefault(); _findStep(1); }
  });
  bar.querySelector("#find-prev").addEventListener("click", ()=>_findStep(-1));
  bar.querySelector("#find-next").addEventListener("click", ()=>_findStep(1));
  bar.querySelector("#find-close").addEventListener("click", closeFindBar);
}

function _doFind() {
  const t = OPEN_TABS.find((x)=>x.path===ACTIVE_TAB);
  if (!t || !_find.q) { _find.lines=[]; _find.idx=0; _applyFindHL([],0); _renderFindBar(); return; }
  const q = _find.q.toLowerCase();
  _find.lines = (t.text||"").split("\n").reduce((acc,ln,i)=>{ if(ln.toLowerCase().includes(q)) acc.push(i); return acc; },[]);
  _find.idx = 0;
  _applyFindHL(_find.lines, _find.idx);
  _scrollToFindLine();
  _renderFindBar();
}

function _findStep(dir) {
  if (!_find.lines.length) return;
  _find.idx = (_find.idx + dir + _find.lines.length) % _find.lines.length;
  _applyFindHL(_find.lines, _find.idx);
  _scrollToFindLine();
  _renderFindBar();
}

function _applyFindHL(matchLines, curIdx) {
  const codeEl = $("main-code"); if (!codeEl) return;
  codeEl.querySelectorAll(".ln").forEach((el, i) => {
    el.classList.remove("hl-find", "hl-find-cur");
    if (matchLines.includes(i)) {
      el.classList.add("hl-find");
      if (matchLines[curIdx]===i) el.classList.add("hl-find-cur");
    }
  });
}

function _scrollToFindLine() {
  const codeEl = $("main-code"); if (!codeEl || !_find.lines.length) return;
  const lns = codeEl.querySelectorAll(".ln");
  const target = lns[_find.lines[_find.idx]];
  if (target) target.scrollIntoView({block:"center"});
}

/* ─────────────────────────────────────────────────────────────────────
   SAVE FILE
───────────────────────────────────────────────────────────────────── */
async function saveCurrentFile() {
  const t = OPEN_TABS.find((x)=>x.path===ACTIVE_TAB);
  if (!t) { toast("No file open"); return; }
  // sync textarea if in edit mode
  const ta = $("code-textarea");
  if (ta && editMode) { t.text = ta.value; CURRENT_FILE._text = t.text; }
  const r = await Backend.save_file(t.path, t.text||"");
  if (r && r.ok) {
    t.dirty = false; renderTabBar(); toast(`Saved ${t.name}`);
    logLine(`[fs] Saved ${t.name}`, "success");
  } else {
    toast((r&&r.msg)||"Save failed"); logLine(`[fs] Save failed: ${r&&r.msg}`, "error");
  }
}

/* ─────────────────────────────────────────────────────────────────────
   ACTIONS  (run pipeline + clipboard)
───────────────────────────────────────────────────────────────────── */
// Denetim G-04 fix (2026-07-10): the Actions panel (.action rows, right
// rail AND the Gate view's quick actions) wired straight to runAction()
// with no busy-guard. A fast double-click (or click-while-still-running)
// fired two concurrent Backend.run_pipeline()/AI calls for the SAME action
// — double AI billing for costly steps (analyze, generate_report, hmi
// draft…) and a real race on actions that WRITE files (assemble_program,
// generate_scl) where two overlapping writes can interleave. Single guard
// here protects every current and future call site of runAction().
let _actionRunning = false;
async function runAction(id) {
  if (_actionRunning) {
    toast("An action is already running — please wait for it to finish");
    return;
  }
  _actionRunning = true;
  try {
  const filePath = CURRENT_FILE ? CURRENT_FILE._path : "";
  logSep(id);
  logLine(`[action] Running ${id}…`, "dim");
  // Real execution
  let result;
  if (id === "analyze") {
    result = await Backend.run_analysis();
    if (result && result.ok) _showAnalysisInDiag(result);
  } else if (id === "generate_fat") {
    // SAT v2 (Faz 6): options modal — type (FAT/SAT/BOTH), language, PDF
    _openProtocolModal();
    result = null;
  } else if (id === "sistema_records") {
    // SAT v2 (Faz 6): engineer SISTEMA declarations + prep list
    _openSistemaModal();
    result = null;
  } else if (id === "generate_ce") {
    // SAT v2 (Faz 6.3): CE wesentliche-Veränderung — language/PDF options modal
    _openCeModal();
    result = null;
  } else if (id === "generate_report") {
    result = await Backend.generate_customer_report();
    if (result) {
      if (!result.ok && result.precondition_error) {
        // Gate 7 not approved / RD05 still unverified — surface the structured
        // reasons rather than a one-line "Done".
        const reasons = Array.isArray(result.reasons) ? result.reasons : [];
        logLine(`[report] Report blocked — preconditions not met`, "error");
        for (const r of reasons) logLine(`  • ${r}`, "warn");
        toast("Report blocked — preconditions not met");
      } else {
        logLine(`[report] ${result.msg||"Done"}`, result.ok?"success":"warn");
        if (result.ok) {
          // B-02: safety chain for customer report (same as FAT modal)
          if (result.rag_warnings && result.rag_warnings.length > 0) {
            for (const w of result.rag_warnings) {
              logLine(`  ⚠️ SAFETY KB [${w.entry_id||"?"}]${w.not_verified?" [NOT_VERIFIED]":""}: ${escapeHtml((w.chunk_text||"").split("\n")[0].substring(0,120))}`, "warn");
            }
          }
          await showReport();
          // Inject safety banner into the report view after render
          if (result.rag_warnings && result.rag_warnings.length > 0) {
            const rv = $("report-view");
            const warnHtml = result.rag_warnings.map(w =>
              `<div style="margin:4px 0">⚠️ <b>[${escapeHtml(w.entry_id||"?")}]</b>${w.not_verified?" <i>(NOT_VERIFIED)</i>":""} ${escapeHtml((w.chunk_text||"").split("\n")[0].replace(/^#+\s*/,"").substring(0,100))}</div>`
            ).join("");
            const banner = document.createElement("div");
            banner.id = "rr-rag-banner";
            banner.style.cssText = "border:2px solid #dc2626;background:#fef2f2;padding:12px;margin-bottom:16px;border-radius:6px;position:sticky;top:0;z-index:10";
            banner.innerHTML = `<b style="color:#dc2626">⚠️ ${t("dlg.safety_kb_warn")}</b> — ${result.rag_warnings.length} ${t("dlg.safety_kb_body")}<br>${warnHtml}<br><button class="btn primary" id="rr-rag-ok" style="margin-top:6px">${t("dlg.acknowledge")}</button>`;
            const pi = rv && rv.querySelector(".page-inner");
            if (pi) pi.insertBefore(banner, pi.firstChild);
            const ok = rv && rv.querySelector("#rr-rag-ok");
            if (ok) ok.addEventListener("click", () => { rv.querySelector("#rr-rag-banner")?.remove(); });
          }
        }
      }
    }
  } else if (id === "size_hardware") {
    result = await Backend.size_hardware(20);
    if (result && result.ok) { showHardwareView(result); }
    else logLine(`[hw] ${result&&result.msg||"Sizing failed"}`, "warn");
  } else if (id === "hmi_draft") {
    result = await Backend.generate_hmi_draft();
    logLine(`[hmi] ${(result&&result.msg)||"HMI draft failed"}`, result&&result.ok?"success":"error");
    if (result && result.ok) await refreshProjectState();
  } else if (id === "generate_hmi_interface") {
    result = await Backend.generate_hmi_interface();
    logLine(`[hmi] ${(result&&result.msg)||"HMI interface failed"}`, result&&result.ok?"success":"error");
    if (result && result.ok) await refreshProjectState();
  } else if (id === "validate" && filePath && (filePath.endsWith(".scl")||filePath.endsWith(".st"))) {
    // Validate the currently open SCL file first
    const vr = await Backend.validate_scl_file(filePath);
    if (vr && vr.ok) {
      const sev = vr.errors > 0 ? "error" : (vr.warnings > 0 ? "warn" : "success");
      logLine(`[validate] ${vr.file}: ${vr.errors} errors, ${vr.warnings} warnings`, sev);
      (vr.issues||[]).forEach((i)=>logLine(`  Ln ${i.line}: [${i.severity}] ${i.message}`, i.severity==="error"?"error":"warn"));
      if (STATE) STATE.diagnostics = (vr.issues||[]).map((i)=>({sev:i.severity==="error"?"error":"warn", line:`${vr.file}:${i.line} — ${i.message}`}));
      renderDiagnostics();
    }
    result = await Backend.run_pipeline(id, filePath);
  } else if (id === "generate_test_scenarios") {
    result = await Backend.run_pipeline(id, filePath);
    if (result && result.ok) {
      await refreshProjectState();
      setActivePage("explorer");
      await openFile("REPORTS/TEST_SCENARIOS.md");
    }
  } else if (id === "send_to_tia") {
    _openSendToTiaModal();
    result = null;
  } else {
    result = await Backend.run_pipeline(id, filePath);
    // Guard: a stale/renamed button id would otherwise die as one dim log
    // line — make the mismatch loud so it gets reported, not shrugged at.
    if (result && !result.ok && /^Unknown action/.test(result.output || "")) {
      toast(`Unknown action "${id}" — stale button? Please report this.`);
      logLine(`[action] Backend has no handler for "${id}" (stale UI element)`, "error");
    }
  }
  if (result && result.output) {
    const lines = String(result.output).split("\n");
    for (const ln of lines.slice(0, 120)) logLine(ln, result.ok?"info":"warn");
    LAST_PREVIEW = result.output;
    if (currentBottomTab==="ai") renderBottom();
  }
  switchBottomTab("terminal");
  // Refresh state + gate model after any state-changing action (pipelines
  // create RD/output files, so the tree and the gates both move)
  await refreshProjectState();
  } finally {
    _actionRunning = false;
  }
}

async function runWorkflow(name) {
  const filePath = CURRENT_FILE ? CURRENT_FILE._path : "";
  toast(`Workflow "${name}" started…`);
  logSep(`workflow: ${name}`);
  logLine(`[workflow] "${name}" — running (this may take a while)…`, "dim");
  switchBottomTab("terminal");
  const r = await Backend.run_workflow(name, filePath);
  if (r && r.output) {
    String(r.output).split("\n").slice(0, 120).forEach((ln)=>logLine(ln, r.ok?"info":"warn"));
    LAST_PREVIEW = r.output;
    renderBottom();
  }
  toast(r && r.ok ? `Workflow "${name}" complete` : (r && r.msg) || "Workflow failed");
  if (r && r.ok) await _refreshGateModel();
}

function _showAnalysisInDiag(result) {
  // Push analysis as structured diagnostics
  const lines = [`Project completion: ${result.overall_pct?.toFixed(0)||"?"}%`];
  if (result.recommended_next && result.recommended_next.length) {
    lines.push("Recommended next: " + result.recommended_next.join("; "));
  }
  const errs = (result.rd_list||[]).filter((r)=>r.status==="empty"||r.status==="template");
  const ok   = (result.rd_list||[]).filter((r)=>r.status==="done"||r.status==="ok");
  lines.push(`RD done: ${ok.length}, needs work: ${errs.length}`);
  (result.rd_list||[]).forEach((r)=>{
    const sev = (r.status==="done"||r.status==="ok")?"success":(r.status==="empty"?"warn":"info");
    logLine(`  ${r.rd_id} [${r.status}] ${r.title}${r.missing_inputs&&r.missing_inputs.length?" — missing: "+r.missing_inputs.join(", "):""}`, sev);
  });
  // Update STATE diagnostics
  if (STATE) {
    STATE.diagnostics = lines.map((l)=>({sev:"info", line:l}));
    renderDiagnostics();
  }
}

async function _refreshGateModel() {
  _gateModel = await Backend.get_gate_model();
  // If gate view is currently visible, re-render it
  const gv = $("gate-view");
  if (gv && gv.classList.contains("show") && _gateModel) {
    _renderGateView(_gateModel, _gateModel.current);
  }
  // Update right rail gate display
  if (STATE && _gateModel) {
    STATE.gate = _gateModel.current;
    STATE.gate_name = (_gateModel.gates||[]).find((g)=>g.n===_gateModel.current)?.name||"";
    STATE.gate_pct = _gateModel.gate_pct ?? (_gateModel.overall_pct != null ? Math.round(_gateModel.overall_pct) : Math.round((_gateModel.current - 1) / 7 * 100));
    STATE.doc_pct  = _gateModel.doc_pct ?? null;
    $("gate-caps").textContent = `Gate ${_gateModel.current}/7`;
    $("gate-title").textContent = STATE.gate_name;
    $("gate-pct").textContent = STATE.gate_pct + "%";
    $("status-gate-num").textContent = `${_gateModel.current}/7`;
    $("gate-bar").innerHTML = Array.from({length:7},(_,i)=>`<div class="gate-seg ${i<_gateModel.current?"on":""}"></div>`).join("");
    $("gate-dots").innerHTML = Array.from({length:7},(_,i)=>{
      const n=i+1, cls=n===_gateModel.current?"gdot cur":(n<_gateModel.current?"gdot on":"gdot");
      return `<span class="${cls}"></span>`;
    }).join("");
  }
  renderGateNavBar();
  updateNextStepCard();
}

// "Next step" card (right rail top) — ONE obvious suggested action at any
// moment, derived from the same _gateModel every other gate display uses.
function updateNextStepCard() {
  const sec = $("rr-next"), btn = $("rr-next-btn"), hint = $("rr-next-hint");
  if (!sec || !btn) return;
  let label, hintText, go;
  const model = _gateModel;
  if (!model || !model.gates || !model.gates.length) {
    label = "Create or open a project";
    hintText = "Nothing is open yet — start from a template or a recent project.";
    go = () => showOnboarding();
  } else {
    const cur = model.gates.find((g) => g.n === model.current) || model.gates[0];
    const isRetrofit = ((STATE && STATE.project_type) || "").toUpperCase() === "RETROFIT";
    if (cur.n === 1 && isRetrofit) {
      label = "Start Retrofit Pre-Analysis";
      hintText = "Gate 1 — scans _raw/legacy_code and drafts the RD pack for engineer review.";
    } else if (cur.needs_approval) {
      label = `Review & approve Gate ${cur.n}`;
      hintText = `${cur.name} — engineer sign-off required before advancing.`;
    } else {
      const first = (cur.actions || [])[0];
      label = first ? `Gate ${cur.n}: ${ACTION_LABELS[first] || first}`
                    : `Open Gate ${cur.n} — ${cur.name}`;
      hintText = GATE_SUBTITLES[cur.n] || "";
    }
    go = () => showGateView(cur.n);
  }
  btn.textContent = label;
  if (hint) hint.textContent = hintText;
  if (!btn._wired) { btn._wired = true; btn.addEventListener("click", () => btn._go && btn._go()); }
  btn._go = go;
  sec.style.display = "";
}

// One refresh to rule them all: STATE + gate model together, then every
// gate display (right rail, status bar, nav bar, open gate view) re-renders
// from the same fetch. Call this after ANY state-changing operation so the
// pages can never drift apart (UX audit 2026-06-10).
async function refreshProjectState() {
  STATE = await Backend.get_state();
  render();
  await _refreshGateModel();
}

/* ─────────────────────────────────────────────────────────────────────
   INLINE AI  (screen 08)
───────────────────────────────────────────────────────────────────── */
let _aiTimer = null;
async function requestInlineAI(tab, lineNum) {
  clearTimeout(_aiTimer);
  _aiTimer = setTimeout(async ()=>{
    hideGhostText();
    if (!tab) return;
    const lines = (tab.text||"").split("\n");
    const context = lines.slice(Math.max(0,lineNum-6), lineNum).join("\n");
    const r = await Backend.get_ai_suggestion(context, lineNum);
    if (r && r.ok && r.suggestion) {
      showGhostText(r.suggestion, lineNum);
    }
  }, 800);
}
function showGhostText(suggestion, lineNum) {
  hideGhostText();
  AI_GHOST_TEXT = suggestion;
  const codeEl = $("main-code")||document.querySelector("#codewrap .code");
  if (!codeEl) return;
  const lns = codeEl.querySelectorAll(".ln");
  const targetLn = lns[lineNum-1];
  if (!targetLn) return;
  const ghost = document.createElement("div");
  ghost.id = "ai-ghost";
  ghost.className = "ai-ghost-wrap";
  const lines = suggestion.split("\n");
  ghost.innerHTML = `<div class="ai-ghost-hint">AI suggestion — Tab to accept, Esc to dismiss</div>` +
    lines.map((ln)=>`<div class="ai-ghost-line"><div class="gutter" style="width:44px;flex:0 0 44px;text-align:right;padding-right:14px;color:var(--fg-dim)"></div><div class="src ai-ghost-text">${escapeHtml(ln)||" "}</div></div>`).join("");
  targetLn.after(ghost);
}
function hideGhostText() {
  const g = $("ai-ghost"); if (g) g.remove();
  AI_GHOST_TEXT = "";
}
function acceptGhostText() {
  if (!AI_GHOST_TEXT || !ACTIVE_TAB) return;
  const t = OPEN_TABS.find((x)=>x.path===ACTIVE_TAB);
  if (!t) return;
  const codeEl = $("main-code")||document.querySelector("#codewrap .code");
  const hlLn   = codeEl && codeEl.querySelector(".ln.hl");
  let insertAt = t.text.length; // default: append
  if (hlLn) {
    const lns = codeEl.querySelectorAll(".ln");
    let lineIdx = 0;
    for (let i=0;i<lns.length;i++) { if (lns[i]===hlLn) { lineIdx=i; break; } }
    const textLines = t.text.split("\n");
    const before = textLines.slice(0,lineIdx+1).join("\n");
    const after  = textLines.slice(lineIdx+1).join("\n");
    t.text = before + "\n" + AI_GHOST_TEXT + (after?"\n"+after:"");
  } else {
    t.text = t.text + "\n" + AI_GHOST_TEXT;
  }
  t.dirty = true;
  hideGhostText();
  renderTabBar(); renderActiveTab();
  toast("AI suggestion accepted");
  logLine("[AI] Suggestion accepted", "success");
}

/* ─────────────────────────────────────────────────────────────────────
   SPLIT EDITOR  (screen 09)
───────────────────────────────────────────────────────────────────── */
function enterSplit() {
  if (splitMode) { exitSplit(); return; }
  splitMode = true;
  const btn = $("split-toggle");
  if (btn) btn.classList.add("split-on");
  const cw = $("codewrap");
  const existingCode = cw.querySelector(".code");
  const leftName  = CURRENT_FILE ? CURRENT_FILE.name : null;
  const leftKind  = CURRENT_FILE ? CURRENT_FILE.kind : "file";
  const leftIcon  = FILE_ICON[leftKind] || "file";
  const leftBody  = existingCode ? existingCode.outerHTML : `<div class="editor-empty">No file open on left</div>`;
  cw.classList.add("split");
  cw.innerHTML = `
    <div class="split-pane" id="split-left">
      <div class="split-pane-hd">
        <span class="ic" data-i="${leftIcon}" data-s="11"></span>
        <span class="sp-name">${leftName?escapeHtml(leftName):"— select file —"}</span>
      </div>
      <div class="split-pane-body">${leftBody}</div>
    </div>
    <div class="split-pane" id="split-right">
      <div class="split-pane-hd">
        <span class="ic" data-i="file-text" data-s="11"></span>
        <span class="sp-name" id="split-r-name">— select spec file —</span>
        <span class="sp-close" id="split-close" title="Close split">✕</span>
      </div>
      <div class="split-pane-empty" id="split-r-body">Select a spec or RD file from the Explorer</div>
    </div>`;
  injectIcons(cw);
  $("split-close").addEventListener("click", exitSplit);
  toast("Split editor open — select a second file from the Explorer");
}
function exitSplit() {
  if (!splitMode) return;
  splitMode = false;
  const btn = $("split-toggle");
  if (btn) btn.classList.remove("split-on");
  const cw = $("codewrap");
  cw.classList.remove("split");
  if (CURRENT_FILE && CURRENT_FILE._path) {
    const t = OPEN_TABS.find((x)=>x.path===CURRENT_FILE._path);
    if (t) {
      cw.innerHTML = `<div class="code" id="main-code">${buildCodeHtml(t.text,t.kind)}</div>`;
      setupEditorEvents(cw.querySelector(".code"), t);
    } else {
      cw.innerHTML = `<div class="editor-empty" id="editor-empty">Select a file from the Explorer — or press ⌘K</div>`;
    }
  } else {
    cw.innerHTML = `<div class="editor-empty" id="editor-empty">Select a file from the Explorer — or press ⌘K</div>`;
  }
}
async function openFileInSplitRight(path) {
  const f = await Backend.read_file(path);
  const isScl = (f.kind==="scl")||path.endsWith(".scl");
  const isJson = (f.kind==="json")||path.endsWith(".json");
  const kind  = isScl?"scl":(isJson?"json":(f.kind||"text"));
  const icon  = FILE_ICON[kind] || "file";
  const bodyEl = $("split-r-body");
  if (!bodyEl) return;
  bodyEl.className = "split-pane-body";
  bodyEl.removeAttribute("style");
  bodyEl.innerHTML = `<div class="code">${buildCodeHtml(f.text, kind)}</div>`;
  const nameEl = $("split-r-name"); if (nameEl) nameEl.textContent = f.name||path;
  const hd = document.querySelector("#split-right .split-pane-hd .ic");
  if (hd) { hd.setAttribute("data-i", icon); injectIcons(document.getElementById("split-right")); }
  toast(`${f.name||path} — opened in right pane`);
}

/* ─────────────────────────────────────────────────────────────────────
   THEME / ACCENT
───────────────────────────────────────────────────────────────────── */
const ACCENT_LABELS = {emerald:"Emerald",amber:"Amber",cool:"Cool Steel",daylight:"Daylight"};
function accentLabel() { return ACCENT_LABELS[document.documentElement.dataset.accent||"emerald"]||"Emerald"; }
function updateThemeLabel() {
  const theme = document.documentElement.dataset.theme==="light"?"Light":"Dark";
  const el = $("status-theme"); if (el) el.textContent=`${accentLabel()} · ${theme}`;
}
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("btn-theme").innerHTML = svg(theme==="light"?"sun":"moon", 15);
  updateThemeLabel();
}
function applyAccent(accent) {
  document.documentElement.dataset.accent = accent;
  updateThemeLabel();
}
function toggleTheme() {
  const next = document.documentElement.dataset.theme==="light"?"dark":"light";
  applyTheme(next);
  // G-02 fix: route set_theme through the Backend bridge so it uses the same
  // ready-check + error-logging path as every other API call. The direct
  // window.pywebview.api.set_theme() call bypassed Backend._call and swallowed
  // all exceptions silently, so theme preference was never persisted on disk.
  Backend.set_theme(next);
}

/* ─────────────────────────────────────────────────────────────────────
   SETTINGS MODAL
───────────────────────────────────────────────────────────────────── */
/* Task labels + recommendations shown in Settings task-routing section. */
const _TASK_LABELS = {
  default:        "Default AI",
  scl_generation: "SCL Generation",
  preanalysis:    "PDF / Image Analysis",
  translation:    "Technical Translation",
};
const _TASK_RECS = { preanalysis:"google", scl_generation:"anthropic", translation:"google" };

async function openSettings() {
  if ($("settings-overlay")) return;
  const s = await Backend.get_settings();
  const accents   = [["emerald","#10b981","Emerald"],["amber","#f59e0b","Amber"],["cool","#06b6d4","Cool Steel"],["daylight","#e8a020","Daylight"]];
  const providers = Object.keys(s.catalog||{});
  const keyStatus = s.api_keys_status || {};
  const keyringOk = (s.keyring_available !== false);
  const ps0       = s.provider_settings || {};
  const routing0  = s.task_routing || {};

  /* Build one provider card per provider */
  function providerCard(prov) {
    const info  = s.catalog[prov] || {};
    const psCfg = ps0[prov]  || {};
    const st    = keyStatus[prov] || "unset";
    const curModel   = psCfg.model    || info.default || "";
    const curMaxTok  = psCfg.max_tokens || info.default_max_tokens || 4096;
    const keyHint    = st==="set"    ? "••••••••• (stored in OS keystore — type to replace)"
                     : st==="unsafe" ? "⚠ plaintext on disk — install keyring to secure"
                     : !keyringOk    ? "⚠ keyring unavailable — key stored as PLAINTEXT"
                     :                 "Enter API key…";
    const noKey = (st==="unset");
    return `<div class="prov-card" data-prov="${prov}">
      <div class="prov-head">
        <span class="prov-name">${escapeHtml(info.display||prov)}</span>
        ${info.badge ? `<span class="prov-badge">${escapeHtml(info.badge)}</span>` : ""}
      </div>
      <div class="sm-field">
        <label>API Key</label>
        <input class="prov-key" data-prov="${prov}" type="password" placeholder="${escapeHtml(keyHint)}" />
        <button class="btn prov-test" data-prov="${prov}" style="white-space:nowrap">Test</button>
        <span class="prov-hint sm-hint" data-prov="${prov}"></span>
      </div>
      <div class="sm-field">
        <label>Model</label>
        <select class="prov-model" data-prov="${prov}">
          ${(info.models||[]).map(m=>`<option value="${m}"${m===curModel?" selected":""}>${m}</option>`).join("")||`<option value="${curModel}">${curModel||"(default)"}</option>`}
        </select>
      </div>
      <div class="sm-field">
        <label>Max Tokens</label>
        <input class="prov-maxtok" data-prov="${prov}" type="number" min="256" max="65536" step="512" value="${curMaxTok}" style="width:90px;flex:none" />
        <span class="sm-hint">recommended: ${info.default_max_tokens||4096}</span>
      </div>
      ${noKey && info.badge ? `<div class="prov-warn">⚠ No key — tasks will fall back to default provider</div>` : ""}
    </div>`;
  }

  /* Task routing rows */
  function taskRoutingRows() {
    return Object.entries(_TASK_LABELS).map(([task, label])=>{
      const cur = routing0[task] || (task==="default"?"anthropic":"");
      const rec = _TASK_RECS[task];
      const recLabel = rec ? (s.catalog[rec]||{}).display || rec : "";
      return `<div class="sm-field">
        <label style="width:130px;flex:0 0 130px">${escapeHtml(label)}</label>
        <select class="task-route" data-task="${task}">
          ${providers.map(p=>`<option value="${p}"${p===cur?" selected":""}>${(s.catalog[p]||{}).display||p}</option>`).join("")}
        </select>
        ${recLabel ? `<span class="sm-hint task-rec">${escapeHtml(recLabel)} recommended</span>` : ""}
      </div>`;
    }).join("");
  }

  const ov = document.createElement("div");
  ov.className="overlay show"; ov.id="settings-overlay";
  ov.innerHTML=`<div class="settings-modal">
    <div class="sm-head"><span class="ic" data-i="settings" data-s="16"></span>Settings<div class="fill"></div><span class="icon-btn" id="sm-close-hd" style="cursor:pointer">${svg("x",14)}</span></div>
    <div class="sm-body">
      <div class="sm-sec"><div class="lbl">${t("set.appearance")}</div><div class="seg-row" id="sm-theme">
        <div class="seg2 ${s.theme!=="light"?"on":""}" data-v="dark">${t("set.dark")}</div>
        <div class="seg2 ${s.theme==="light"?"on":""}" data-v="light">${t("set.light")}</div></div></div>
      <div class="sm-sec"><div class="lbl">${t("set.language")}</div>
        <div class="seg-row" id="sm-uilang">
          ${I18N_LANGS.map(([c,label])=>`<div class="seg2 ${UI_LANG===c?"on":""}" data-v="${c}">${label}</div>`).join("")}
        </div>
        <div class="sm-hint" style="margin-top:6px">${t("set.language_hint")}</div>
      </div>
      <div class="sm-sec"><div class="lbl">Accent colour</div><div class="accent-row" id="sm-accent">
        ${accents.map((a)=>`<div class="swatch ${s.accent===a[0]?"on":""}" data-v="${a[0]}"><span class="dotc" style="background:${a[1]}"></span>${a[2]}</div>`).join("")}
      </div></div>
      <div class="sm-sec"><div class="lbl">${t("set.profile")}</div>
        <div class="sm-field"><label>${t("set.your_name")}</label><input id="sm-username" type="text" placeholder="${t("set.name_ph")}" value="${escapeHtml(s.username||"")}" /></div>
      </div>
      <div class="sm-sec"><div class="lbl">AI / API — Providers</div>
        ${providers.map(providerCard).join("")}
      </div>
      <div class="sm-sec"><div class="lbl">Task Routing</div>
        <div class="sm-hint" style="margin-bottom:10px">If a provider has no key, tasks fall back to the Default AI.</div>
        ${taskRoutingRows()}
      </div>
      <div class="sm-sec"><div class="lbl">TIA Portal (Openness — direct path)</div>
        <div id="sm-tia" class="sm-hint">Detecting TIA installations…</div>
      </div>
    </div>
    <div class="sm-foot"><button class="btn primary" id="sm-save">${t("gen.save")}</button><button class="btn ghost" id="sm-close">${t("gen.close")}</button><span class="sm-hint" id="sm-save-hint"></span></div>
  </div>`;
  document.body.appendChild(ov); injectIcons(ov);
  const q = (sel)=>ov.querySelector(sel);
  _renderTiaSettingsCard(ov);

  // C-A2: editedKeys tracks only values freshly typed in this dialog.
  const editedKeys = {};

  ov.querySelectorAll(".prov-key").forEach(inp=>{
    inp.addEventListener("input", e=>{ editedKeys[inp.dataset.prov]=e.target.value; });
  });
  ov.querySelectorAll(".prov-test").forEach(btn=>{
    btn.addEventListener("click", async()=>{
      const prov = btn.dataset.prov;
      const key  = (ov.querySelector(`.prov-key[data-prov="${prov}"]`)||{}).value||"";
      const hint = ov.querySelector(`.prov-hint[data-prov="${prov}"]`);
      hint.textContent="testing…";
      const r = await Backend.test_api(prov, key);
      hint.textContent=(r.ok?"✓ ":"✗ ")+(r.msg||"");
    });
  });
  ov.querySelectorAll("#sm-theme .seg2").forEach(el=>el.addEventListener("click",()=>{
    ov.querySelectorAll("#sm-theme .seg2").forEach(x=>x.classList.remove("on"));
    el.classList.add("on"); applyTheme(el.getAttribute("data-v"));
  }));
  ov.querySelectorAll("#sm-accent .swatch").forEach(el=>el.addEventListener("click",()=>{
    ov.querySelectorAll("#sm-accent .swatch").forEach(x=>x.classList.remove("on"));
    el.classList.add("on"); applyAccent(el.getAttribute("data-v"));
  }));
  ov.querySelectorAll("#sm-uilang .seg2").forEach(el=>el.addEventListener("click",()=>{
    ov.querySelectorAll("#sm-uilang .seg2").forEach(x=>x.classList.remove("on"));
    el.classList.add("on"); setUiLang(el.getAttribute("data-v"));
  }));

  const close=()=>ov.remove();
  q("#sm-close").addEventListener("click",close);
  q("#sm-close-hd").addEventListener("click",close);
  ov.addEventListener("click",e=>{ if(e.target===ov) close(); });

  q("#sm-save").addEventListener("click", async()=>{
    // Collect per-provider settings
    const provider_settings = {};
    ov.querySelectorAll(".prov-card").forEach(card=>{
      const p = card.dataset.prov;
      const model    = (card.querySelector(".prov-model")||{}).value||"";
      const maxTokRaw= (card.querySelector(".prov-maxtok")||{}).value||"4096";
      const max_tokens = Math.max(256, Math.min(65536, parseInt(maxTokRaw)||4096));
      provider_settings[p] = {model, max_tokens};
      const key = (card.querySelector(".prov-key")||{}).value||"";
      if (key) editedKeys[p] = key;
    });
    // C-A2: only send keys the user actually typed.
    const api_keys = {};
    for (const p in editedKeys) { if (editedKeys[p]) api_keys[p]=editedKeys[p]; }
    // Collect task routing
    const task_routing = {};
    ov.querySelectorAll(".task-route").forEach(sel=>{ task_routing[sel.dataset.task]=sel.value; });
    const defaultProv = task_routing.default || "anthropic";
    const defaultModel = (provider_settings[defaultProv]||{}).model || "";

    await Backend.save_settings({
      theme:   document.documentElement.dataset.theme,
      accent:  document.documentElement.dataset.accent||"emerald",
      username: q("#sm-username").value.trim(),
      ai_provider: defaultProv,
      ai_model: defaultModel,
      api_keys, provider_settings, task_routing,
    });
    q("#sm-save-hint").textContent="Saved ✓";
    if (STATE) { STATE.model=defaultModel||STATE.model; const el=$("status-model"); if(el) el.textContent=STATE.model; }
  });
}

/* ─────────────────────────────────────────────────────────────────────
   PAGE HEADER HELPER  (shared chrome for all full-page views)
───────────────────────────────────────────────────────────────────── */
function pageHeader({backId="page-back", icon="layers", title="", subtitle="", actionsHtml=""} = {}) {
  const sub = subtitle ? `<div class="ph-sub">${escapeHtml(subtitle)}</div>` : "";
  return `<div class="page-head">
    <div class="ph-back" id="${escapeHtml(backId)}"><span class="ic" data-i="chevron-right" data-s="13" style="transform:rotate(180deg)"></span>Workbench</div>
    <div class="ph-logo"><span class="ic" data-i="${escapeHtml(icon)}" data-s="18"></span></div>
    <div class="ph-info"><div class="ph-title">${escapeHtml(title)}</div>${sub}</div>
    <div class="ph-actions">${actionsHtml}</div>
  </div>`;
}

/* ─────────────────────────────────────────────────────────────────────
   FULL VIEWS  (Dashboard / Report / Onboarding / Git)
───────────────────────────────────────────────────────────────────── */
function hideViews() {
  document.querySelectorAll(".dash-view").forEach((v)=>v.classList.remove("show"));
}
function hideDashboard() { setActivePage("explorer"); }

function setActivePage(view) {
  document.querySelectorAll(".activitybar .act-btn").forEach((x)=>x.classList.remove("active"));
  const btn = document.querySelector(`.activitybar .act-btn[data-view="${view || "explorer"}"]`);
  if (btn) btn.classList.add("active");
  // Hide resizer when any full-page view is active (it has z-index:10 and would poke through)
  const resizer = $("sidebar-resizer");
  if (resizer) resizer.style.display = view !== "explorer" ? "none" : "";
  switch (view) {
    case "explorer":
      hideViews();
      break;
    case "dashboard": showDashboard(); break;
    case "gate":      showGateView(null); break;
    case "flowchart": showFlowchartView(); break;
    case "prompt":    showPromptView(); break;
    case "hardware":  showHardwareView(null); break;
    case "report":    showReport(); break;
    case "git":       showGitPanel(); break;
    case "library": showLibraryView(); break;
    case "vcompare": showVersionCompareView(); break;
    default:
      hideViews();
  }
}

/* ─────────────────────────────────────────────────────────────────────
   LIBRARY VIEW  (full page — block browser)
───────────────────────────────────────────────────────────────────── */
let _libBlocks   = [];
let _libSelected = null;
let _libCat      = "all";
let _libSearch   = "";

async function showLibraryView() {
  _libBlocks = await Backend.get_library_blocks();
  // No empty right pane on open (2026-07-06 audit): preselect the first
  // block so the page never greets the user with a blank detail area.
  if (!_libSelected && _libBlocks.length) _libSelected = _libBlocks[0];
  const v = $("library-view");
  _renderLibraryView(v);
  hideViews(); v.classList.add("show"); injectIcons(v);
}

function _renderLibraryView(v) {
  const cats = ["all", ...new Set(_libBlocks.map((b)=>b.category).filter(Boolean).sort())];
  const filtered = _libBlocks.filter((b)=>
    (_libCat==="all" || b.category===_libCat) &&
    (!_libSearch || b.name.toLowerCase().includes(_libSearch.toLowerCase()) ||
     (b.desc||"").toLowerCase().includes(_libSearch.toLowerCase()))
  );

  const catIcon = (c)=>({motor:"zap",valve:"git-branch",io:"table",code_gen:"file-code",system:"settings"}[c]||"cpu");
  const catTabs = cats.map((c)=>
    `<div class="pv-cat ${_libCat===c?"active":""}" data-cat="${c}">${c==="all"?"All":c}</div>`
  ).join("");

  // Duplicate detection: collect all block names for alternative lookup
  const allBlockNames = new Set(_libBlocks.map((b)=>b.name));
  const blockCards = filtered.map((b)=>{
    const isSel = _libSelected && _libSelected.name===b.name;
    // Lifecycle badge (requires backend to populate; defaults to DRAFT)
    const lc = b.lifecycle || "DRAFT";
    const lcClass = lc==="FROZEN"?"lc-frozen":lc.startsWith("AUTO_VERIFIED")?"lc-verified":"lc-draft";
    const lcLabel = lc==="FROZEN"?"FROZEN":lc.startsWith("AUTO_VERIFIED")?"VERIFIED":"DRAFT";
    // Duplicate/alternative warning: if block.alternatives list provided by backend
    const alts = (b.alternatives||[]).filter((a)=>allBlockNames.has(a));
    const dupWarn = alts.length
      ? `<div class="lfc-dup-warn">${svg("alert",11)} Alternative: ${alts.map((a)=>escapeHtml(a)).join(", ")}</div>`
      : "";
    return `<div class="lib-full-card ${isSel?"active":""}" data-name="${escapeHtml(b.name)}">
      <div class="lfc-top">
        <span class="ic" data-i="${catIcon(b.category)}" data-s="13" style="color:var(--accent);flex:0 0 16px"></span>
        <span class="lfc-name">${escapeHtml(b.name)}</span>
        <span class="lfc-ver">v${escapeHtml(b.ver||"1.0")}</span>
        <span class="lfc-lc ${lcClass}">${lcLabel}</span>
      </div>
      <div class="lfc-desc">${escapeHtml(b.desc||"")}</div>
      ${dupWarn}
      <div class="lfc-meta">
        ${b.platform?`<span class="lfc-platform">${escapeHtml(b.platform)}</span>`:""}
        ${(b.ports||[]).length?`<span class="lfc-ports">${b.ports.length} ports</span>`:""}
        ${b.source&&b.source!=="Factory"?`<span class="lfc-source">${escapeHtml(b.source)}</span>`:""}
      </div>
      <div class="lfc-actions">
        <span class="lib-btn" data-action="preview" data-name="${escapeHtml(b.name)}">${svg("file-code",11)} Preview</span>
        <span class="lib-btn" data-action="gate-status" data-name="${escapeHtml(b.name)}" title="View gate status">${svg("shield",11)} Gate</span>
        <span class="lib-btn accent" data-action="import" data-name="${escapeHtml(b.name)}" title="Import this frozen library FB into the current project (also available in Gate view)">${svg("arrow-right",11)} Import</span>
      </div>
    </div>`;
  }).join("") || `<div style="color:var(--fg-dim);font-size:12px;padding:16px">No blocks found</div>`;

  const previewPanel = _libSelected
    ? `<div class="lib-preview">
        <div class="lib-preview-hd">
          <span class="ic" data-i="file-code" data-s="13" style="color:var(--accent)"></span>
          <span>${escapeHtml(_libSelected.name)}</span>
          <span class="fill"></span>
          <button class="btn primary" id="lib-import-sel">${svg("arrow-right",12)} Import to project</button>
        </div>
        <div class="lib-ports" id="lib-ports">
          ${(_libSelected.ports||[]).map((p)=>`<div class="lib-port-row">
            <span class="lib-port-dir ${(p.direction||"").toLowerCase()}">${p.direction||"?"}</span>
            <span class="mono" style="font-size:11px;flex:1">${escapeHtml(p.name)}</span>
            <span style="font-size:10px;color:var(--fg-dim)">${escapeHtml(p.type||"")}</span>
          </div>`).join("") || `<div style="color:var(--fg-dim);font-size:11px;padding:8px">No port definitions</div>`}
        </div>
        <div class="lib-scl-wrap" id="lib-scl-wrap">
          <div style="color:var(--fg-dim);font-size:11px;padding:12px">Loading SCL…</div>
        </div>
      </div>`
    : `<div class="lib-preview-empty">Select a block from the list to preview</div>`;

  const libActionsHtml = `
    <span class="ws-badge ws-library" title="Library workspace — author, freeze and version reference FBs (project-independent)">LIBRARY WORKSPACE</span>
    <button class="btn" id="lib-new-fb-btn" title="Author a new reference FB (contract + prompt + SCL + gate)">${svg("plus",12)} New FB</button>
    <button class="btn" id="lib-new-variant-btn" title="Create a brand variant (copy-on-write fork of a Factory block)">${svg("git-branch",12)} New Variant</button>
    <button class="btn" id="lib-freeze-btn" disabled title="Manual step — freeze/version happens via fb_acceptance_check.py (CLI) after a gate PASS; not available from the GUI yet">${svg("shield",12)} Freeze/Version</button>
    <input id="lib-search" class="pv-input" placeholder="Search blocks…" value="${escapeHtml(_libSearch)}" style="width:140px"/>`;
  v.innerHTML = `<div class="pv-wrap">
    ${pageHeader({backId:"lib-back", icon:"package", title:"Block Library",
        subtitle:`${_libBlocks.length} reference FBs — frozen blocks are imported into projects unchanged`, actionsHtml: libActionsHtml})}
    <div class="pv-cats">${catTabs}</div>
    <div class="lib-body">
      <div class="lib-grid" id="lib-grid">${blockCards}</div>
      ${previewPanel}
    </div>
  </div>`;

  injectIcons(v);
  v.querySelector("#lib-back").addEventListener("click",()=>{ _libSelected=null; setActivePage("explorer"); });

  // Library workspace: New FB — direct engineer to the contract + gate workflow
  const newFbBtn = v.querySelector("#lib-new-fb-btn");
  if (newFbBtn) newFbBtn.addEventListener("click", ()=>{
    toast("New FB: create a .contract.json in 06_KNOWLEDGE_BASE/contracts/, write the SCL, then run fb_acceptance_check.py.");
    logLine("[library-build] New FB workflow: contract → SCL → gate → freeze", "info");
  });
  // Library workspace: New Variant — copy-on-write fork
  const newVarBtn = v.querySelector("#lib-new-variant-btn");
  if (newVarBtn) newVarBtn.addEventListener("click", ()=>{
    const sel = _libSelected ? _libSelected.name : "(select a block first)";
    toast(`New Variant of ${sel}: copy to User library, tag source:"user", re-run gate.`);
    logLine(`[library-build] New Variant: ${sel} → user fork (copy-on-write, source:"user")`, "info");
  });
  // Freeze/Version is a manual CLI step (fb_acceptance_check.py) — the GUI
  // button is intentionally disabled with an honest tooltip; no fake action.

  const searchEl = v.querySelector("#lib-search");
  if (searchEl) searchEl.addEventListener("input",(e)=>{ _libSearch=e.target.value; _renderLibraryView(v); injectIcons(v); });

  v.querySelectorAll(".pv-cat").forEach((el)=>el.addEventListener("click",()=>{
    _libCat=el.getAttribute("data-cat"); _libSearch=""; _renderLibraryView(v); injectIcons(v);
  }));

  v.querySelectorAll(".lib-full-card").forEach((el)=>el.addEventListener("click",(e)=>{
    if (e.target.closest(".lib-btn")) return;
    const name=el.getAttribute("data-name");
    _libSelected=_libBlocks.find((b)=>b.name===name)||null;
    _renderLibraryView(v); injectIcons(v);
    if (_libSelected) _loadLibraryScl(v, _libSelected.name);
  }));

  v.querySelectorAll(".lib-btn").forEach((el)=>el.addEventListener("click",()=>{
    const action=el.getAttribute("data-action"), name=el.getAttribute("data-name");
    if (action==="import") { importLibraryBlock(name); return; }
    if (action==="gate-status") {
      const blk = _libBlocks.find((b)=>b.name===name);
      const lc = (blk&&blk.lifecycle)||"DRAFT";
      toast(`Gate status: ${name} — ${lc}. Run fb_acceptance_check.py for full gate report.`);
      logLine(`[gate] ${name}: lifecycle=${lc}`, "info");
      return;
    }
    _libSelected=_libBlocks.find((b)=>b.name===name)||null;
    _renderLibraryView(v); injectIcons(v);
    if (_libSelected) _loadLibraryScl(v, name);
  }));

  const importSel = v.querySelector("#lib-import-sel");
  if (importSel) importSel.addEventListener("click",()=>{ if (_libSelected) importLibraryBlock(_libSelected.name); });

  if (_libSelected) _loadLibraryScl(v, _libSelected.name);
}

/* ─────────────────────────────────────────────────────────────────────
   VERSION COMPARE VIEW  (full page — diff legacy project version folders)
───────────────────────────────────────────────────────────────────── */
let _vcFolders = [];      // selection order = version order (oldest first is the engineer's job)
let _vcResult  = null;    // last version_compare_scan result
let _vcPairA   = 0;       // A/B pair for content diffs (indices into versions)
let _vcPairB   = 1;
let _vcSelFile = null;    // selected file key (casefold)
let _vcSelName = null;    // selected file display name (passed to the diff API)
let _vcDiff    = null;    // last diff result for the selected file
let _vcHypo    = null;    // last AI-hypotheses result
let _vcHypoBusy= false;
let _vcConsent = false;   // CONFIDENTIAL consent checkbox (not persisted — per session)

async function showVersionCompareView() {
  const v = $("vcompare-view");
  _renderVcView(v);
  hideViews(); v.classList.add("show"); injectIcons(v);
}

function _vcStatusBadge(status) {
  return `<span class="vc-badge ${escapeHtml(status)}">${escapeHtml(status)}</span>`;
}

function _renderVcView(v) {
  const chips = _vcFolders.map((p, i) => `
    <span class="vc-chip" title="${escapeHtml(p)}">
      <span class="vc-chip-n">${i + 1}</span>${escapeHtml(p.split(/[\\/]/).pop() || p)}
      <span class="vc-chip-x" data-idx="${i}" title="Remove">×</span>
    </span>`).join("");

  const needMore = _vcFolders.length < 2;
  const hint = needMore
    ? `<span class="vc-hint">Add at least ${2 - _vcFolders.length} more folder${_vcFolders.length === 1 ? "" : "s"} — e.g. _Versionen/2018-08-18 and _aktiv</span>`
    : "";

  let resultHtml = "";
  if (_vcResult && _vcResult.ok) {
    const r = _vcResult;
    const pairSel = r.versions.length > 2 ? `
      <div class="vc-pair">
        Diff pair:
        <select id="vc-pair-a">${r.versions.map((x, i) =>
          `<option value="${i}" ${i === _vcPairA ? "selected" : ""}>${escapeHtml(x.name)}</option>`).join("")}</select>
        →
        <select id="vc-pair-b">${r.versions.map((x, i) =>
          `<option value="${i}" ${i === _vcPairB ? "selected" : ""}>${escapeHtml(x.name)}</option>`).join("")}</select>
      </div>` : "";
    const truncWarn = r.versions.some((x) => x.truncated)
      ? `<div class="vc-trunc">⚠ One or more folders hit the 500-file scan limit — the listing is incomplete.</div>` : "";

    const rows = r.files.map((f) => {
      const cells = f.per_version.map((p) =>
        p ? `<td class="mono vc-cell" title="${escapeHtml(p.mtime)} · ${escapeHtml(p.sha256.slice(0, 12))}…">${p.size} B</td>`
          : `<td class="vc-cell vc-absent">—</td>`).join("");
      return `<tr class="vc-row ${_vcSelFile === f.key ? "active" : ""}" data-key="${escapeHtml(f.key)}" data-name="${escapeHtml(f.name)}">
        <td>${_vcStatusBadge(f.status)}</td>
        <td class="mono">${escapeHtml(f.name)}${f.binary ? ' <span class="vc-bin">bin</span>' : ""}</td>
        ${cells}</tr>`;
    }).join("");

    const s = r.summary;
    resultHtml = `
      ${truncWarn}
      <div class="vc-summary">
        ${s.modified} modified · ${s.added} added · ${s.removed} removed · ${s.unchanged} unchanged${s.mixed ? ` · ${s.mixed} mixed` : ""} — ${s.total} files
      </div>
      ${pairSel}
      <div class="vc-body">
        <div class="vc-table-wrap">
          <table class="vc-table">
            <thead><tr><th>Status</th><th>File</th>${r.versions.map((x) =>
              `<th title="${escapeHtml(x.path)}">${escapeHtml(x.name)}</th>`).join("")}</tr></thead>
            <tbody>${rows || `<tr><td colspan="${2 + r.versions.length}" class="vc-empty">No files found in the selected folders.</td></tr>`}</tbody>
          </table>
        </div>
        <div class="vc-detail" id="vc-detail">${_vcDiff ? _vcDiffHtml(_vcDiff) : `<div class="vc-empty">Select a file row to see its content diff (${escapeHtml(r.versions[_vcPairA].name)} → ${escapeHtml(r.versions[_vcPairB].name)}).</div>`}</div>
      </div>`;
  } else if (_vcResult && !_vcResult.ok) {
    resultHtml = `<div class="vc-error">${escapeHtml(_vcResult.msg || "Scan failed.")}</div>`;
  } else {
    resultHtml = `<div class="vc-empty" style="padding:24px">No comparison yet. Add version folders (e.g. the dated subfolders of a legacy <span class="mono">_Versionen/</span> archive plus <span class="mono">_aktiv/</span>) and press Compare.</div>`;
  }

  // ── AI hypotheses panel (Faz C) — only meaningful after a comparison.
  let hypoHtml = "";
  if (_vcResult && _vcResult.ok) {
    const projectOpen = !!(STATE && STATE.project_path);
    const aiDisabledReason = !projectOpen
      ? "Open a project first — AI hypotheses use the open project's data classification and audit log."
      : "";
    let cards = "";
    if (_vcHypoBusy) {
      cards = `<div class="vc-empty">Asking the AI…</div>`;
    } else if (_vcHypo && !_vcHypo.ok) {
      cards = `<div class="vc-error">${escapeHtml(_vcHypo.msg || "AI call failed.")}</div>`;
    } else if (_vcHypo && _vcHypo.ok) {
      cards = (_vcHypo.hypotheses || []).map((h) => `
        <div class="vc-hypo-card">
          <div class="vc-hypo-top">
            ${h.confidence ? `<span class="vc-conf ${escapeHtml(h.confidence)}">${escapeHtml(h.confidence)}</span>` : ""}
            <span class="vc-draft">${escapeHtml(_vcHypo.label || "DRAFT_UNVERIFIED")}</span>
          </div>
          <div class="vc-hypo-text">${escapeHtml(h.text)}</div>
          ${h.evidence ? `<div class="vc-hypo-ev">Evidence: ${escapeHtml(h.evidence)}</div>` : ""}
        </div>`).join("")
        || `<div class="vc-empty">The AI returned no hypotheses.</div>`;
    }
    hypoHtml = `
      <div class="vc-hypo">
        <div class="vc-hypo-hd">
          <span class="caps">AI change hypotheses</span>
          <span class="vc-hint">— why might these changes have been made? Drafts only; an engineer must verify each one.</span>
        </div>
        <div class="vc-hypo-controls">
          <label class="vc-consent"><input type="checkbox" id="vc-consent" ${_vcConsent ? "checked" : ""}/>
            Customer consent confirmed for sending this diff summary to the AI provider (CONFIDENTIAL data needs consent)</label>
          <button class="btn" id="vc-hypo-btn" ${(!projectOpen || _vcHypoBusy) ? "disabled" : ""}
            title="${escapeHtml(aiDisabledReason || "Generate AI hypotheses from the diff summary")}">${svg("sparkles", 12)} Generate hypotheses</button>
          ${aiDisabledReason ? `<span class="vc-hint">${escapeHtml(aiDisabledReason)}</span>` : ""}
        </div>
        <div class="vc-hypo-cards">${cards}</div>
      </div>`;
  }

  v.innerHTML = `<div class="pv-wrap">
    ${pageHeader({backId: "vc-back", icon: "history", title: "Version Compare",
      subtitle: "What changed between legacy project versions — deterministic diff, no AI",
      actionsHtml: `<button class="btn" id="vc-add-folder">${svg("folder-open", 12)} Add folder</button>
        <button class="btn primary" id="vc-compare" ${needMore ? "disabled" : ""} title="${needMore ? "Select at least two folders" : "Scan and compare the selected folders"}">${svg("zap", 12)} Compare</button>`})}
    <div class="vc-chips">${chips || `<span class="vc-hint">No folders selected yet.</span>`}${hint}</div>
    ${resultHtml}
    ${hypoHtml}
  </div>`;

  injectIcons(v);
  v.querySelector("#vc-back").addEventListener("click", () => setActivePage("explorer"));

  v.querySelector("#vc-add-folder").addEventListener("click", async () => {
    const r = await Backend.browse_for_folder();
    if (!r || !r.ok || !r.path) return;             // dialog cancelled / no backend
    if (_vcFolders.includes(r.path)) { toast("Folder already in the list."); return; }
    _vcFolders.push(r.path);
    _renderVcView(v);
  });

  v.querySelectorAll(".vc-chip-x").forEach((el) => el.addEventListener("click", () => {
    _vcFolders.splice(parseInt(el.getAttribute("data-idx"), 10), 1);
    _vcResult = null; _vcSelFile = null; _vcDiff = null; _vcHypo = null;
    _renderVcView(v);
  }));

  const cmpBtn = v.querySelector("#vc-compare");
  if (cmpBtn) cmpBtn.addEventListener("click", async () => {
    cmpBtn.disabled = true;
    const r = await Backend.version_compare_scan(_vcFolders);
    _vcResult = r; _vcSelFile = null; _vcDiff = null; _vcHypo = null;
    _vcPairA = 0; _vcPairB = (r && r.ok ? r.versions.length : 2) - 1;
    _renderVcView(v);
  });

  const pairA = v.querySelector("#vc-pair-a"), pairB = v.querySelector("#vc-pair-b");
  const onPair = async () => {
    _vcPairA = parseInt(pairA.value, 10); _vcPairB = parseInt(pairB.value, 10);
    if (_vcSelFile) await _vcLoadDiff(v); else _renderVcView(v);
  };
  if (pairA) pairA.addEventListener("change", onPair);
  if (pairB) pairB.addEventListener("change", onPair);

  v.querySelectorAll(".vc-row").forEach((el) => el.addEventListener("click", async () => {
    _vcSelFile = el.getAttribute("data-key");
    _vcSelName = el.getAttribute("data-name");
    await _vcLoadDiff(v);
  }));

  const consentEl = v.querySelector("#vc-consent");
  if (consentEl) consentEl.addEventListener("change", () => { _vcConsent = consentEl.checked; });

  const hypoBtn = v.querySelector("#vc-hypo-btn");
  if (hypoBtn) hypoBtn.addEventListener("click", async () => {
    _vcHypoBusy = true; _renderVcView(v);
    _vcHypo = await Backend.version_compare_hypotheses(_vcFolders, {confirmed: _vcConsent});
    _vcHypoBusy = false; _renderVcView(v);
  });
}

async function _vcLoadDiff(v) {
  if (_vcPairA === _vcPairB) {
    _vcDiff = {ok: false, msg: "Pick two different versions to diff."};
    _renderVcView(v); return;
  }
  _vcDiff = await Backend.version_compare_diff(_vcPairA, _vcPairB, _vcSelName || _vcSelFile);
  _renderVcView(v);
}

function _vcDiffHtml(d) {
  if (!d || !d.ok) return `<div class="vc-error">${escapeHtml((d && d.msg) || "Diff failed.")}</div>`;
  const head = `<div class="vc-detail-hd"><span class="mono">${escapeHtml(d.relname || "")}</span><span class="vc-mode">${escapeHtml(d.mode)}</span></div>`;
  if (d.mode === "seq") {
    const row = (cls, op, txt) => `<tr class="${cls}"><td class="mono">${escapeHtml(op)}</td><td>${txt}</td></tr>`;
    const rows = [
      ...(d.added   || []).map((e) => row("vc-add", e.operand, `+ ${escapeHtml(e.desc)}`)),
      ...(d.removed || []).map((e) => row("vc-del", e.operand, `− ${escapeHtml(e.desc)}`)),
      ...(d.changed || []).map((e) => row("vc-chg", e.operand,
        `<span class="vc-old">${escapeHtml(e.old_desc) || "<i>(empty)</i>"}</span> → <span class="vc-new">${escapeHtml(e.new_desc) || "<i>(empty)</i>"}</span>`)),
    ].join("");
    const errs = (d.parse_errors_old || d.parse_errors_new)
      ? `<div class="vc-hint">⚠ Unparsed records: ${d.parse_errors_old} (old) / ${d.parse_errors_new} (new)</div>` : "";
    return `${head}
      <div class="vc-summary">${(d.added || []).length} added · ${(d.removed || []).length} removed · ${(d.changed || []).length} changed · ${d.unchanged} unchanged symbols (${d.old_symbols} → ${d.new_symbols})</div>
      ${errs}
      ${rows ? `<table class="vc-seq-table"><thead><tr><th>Operand</th><th>Description</th></tr></thead><tbody>${rows}</tbody></table>`
             : `<div class="vc-empty">Symbol tables are identical.</div>`}`;
  }
  if (d.mode === "text") {
    const lines = (d.lines || []).map((ln) => {
      const cls = ln.startsWith("+") ? "vc-add" : ln.startsWith("-") ? "vc-del" : ln.startsWith("@@") ? "vc-hunk" : "";
      return `<span class="${cls}">${escapeHtml(ln)}</span>`;
    }).join("\n");
    return `${head}${d.truncated ? `<div class="vc-hint">⚠ Diff truncated.</div>` : ""}
      ${lines ? `<pre class="vc-pre">${lines}</pre>` : `<div class="vc-empty">Files are identical (no text differences).</div>`}`;
  }
  // binary / too_large / added_only / removed_only — honest note, no fake diff
  const ident = (d.mode === "binary" && typeof d.identical === "boolean")
    ? `<div class="vc-summary">Content is ${d.identical ? "byte-identical" : "DIFFERENT"} (sha256).</div>` : "";
  return `${head}${ident}<div class="vc-note">${escapeHtml(d.msg || "")}</div>`;
}

async function _loadLibraryScl(v, name) {
  const wrap = v.querySelector("#lib-scl-wrap");
  if (!wrap) return;
  const r = await Backend.get_block_scl(name);
  wrap.innerHTML = (r && r.ok && r.text)
    ? `<div class="code" style="font-size:11px">${buildCodeHtml(r.text,"scl")}</div>`
    : `<div style="color:var(--fg-dim);font-size:11px;padding:12px">SCL not available</div>`;
}

async function showDashboard() {
  const [d, gm] = await Promise.all([Backend.get_dashboard(), Backend.get_gate_model()]);
  if (gm) _gateModel = gm;
  const v = $("dashboard-view");
  const badgeClass = (s)=>RD_STATUS_CLASS[s]||"draft";
  const badgeText  = (s)=>RD_STATUS_LABEL[s]||"DRAFT";
  // Gate truth comes from the gate model (RD-derived), never from the
  // d.gate counter — the counter is only the fallback when the model is
  // unavailable (UX audit: pages showed different steps).
  const curN  = (gm && gm.current) || d.gate;
  const gates = (gm && gm.gates) || null;
  const pipe = (d.gate_names||[]).map((nm,i)=>{
    const n=i+1;
    const gst = gates ? ((gates.find((g)=>g.n===n)||{}).status||"")
                      : (n<curN?"done":(n===curN?"current":""));
    const st = gst==="done"?"done":(gst==="current"?"current":"");
    const line=i<(d.gate_names.length-1)?`<div class="dp-line ${st==="done"?"done":""}"></div>`:"";
    return `<div class="dp-node clickable" data-n="${n}" title="Open Gate ${n}: ${nm}" style="cursor:pointer"><div class="dp-dot ${st}">${st==="done"?"✓":n}</div><div class="dp-name">${nm}</div></div>${line}`;
  }).join("");

  // Progress bar + quick actions from current gate
  const pct    = gm ? (gm.gate_pct ?? gm.overall_pct ?? Math.round((curN - 1) / 7 * 100)) : Math.round((curN - 1) / 7 * 100);
  const docPct = gm && gm.doc_pct != null ? gm.doc_pct : null;
  const curGate = gates ? (gates.find((g)=>g.status==="current")||gates[curN-1]) : null;
  const quickActHtml = curGate && (curGate.actions||[]).length
    ? `<div class="dash-sec-title">Gate ${curN} — Quick Actions <span style="font-size:10px;color:var(--fg-dim);font-weight:400">(${GATE_SUBTITLES[curN]||""})</span></div>
       <div class="dash-quick-acts">${(curGate.actions||[]).map((aid)=>
         `<button class="btn dash-qbtn" data-action="${aid}"><span class="ic" data-i="${ACTION_ICONS[aid]||"play"}" data-s="13"></span>${ACTION_LABELS[aid]||aid}</button>`
       ).join("")}</div>` : "";

  // Progress mini-bar
  const progBar = Array.from({length:7},(_,i)=>`<div class="dash-prog-seg${i<curN?" on":""}"></div>`).join("");
  // Same staleness warning as the gate view — the dashboard is where most
  // users look first, it must not pretend everything is still approved.
  const staleRds = gm && Array.isArray(gm.stale_rds) ? gm.stale_rds : [];
  const staleHtml = staleRds.length
    ? `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:8px 0;padding:8px 12px;border:1px solid var(--warning);border-radius:6px;background:rgba(251,191,36,.08);font-size:12px">
        <span class="ic" data-i="alert" data-s="13" style="color:var(--warning)"></span>
        <strong style="color:var(--warning)">Changed after approval — re-validate:</strong>
        ${staleRds.map((s)=>`<span class="badge warn" title="${escapeHtml(s.change)} after Gate ${s.gate} (${escapeHtml(s.when||"")})">${escapeHtml(s.rd_file)}</span>`).join("")}
       </div>` : "";
  const dashTypeHtml = `<span class="dash-type">${escapeHtml(d.type)}</span>`;
  v.innerHTML=`<div class="page-inner">
    ${pageHeader({backId:"dash-back", icon:"zap", title:escapeHtml(d.project), subtitle:escapeHtml(d.type||""), actionsHtml:dashTypeHtml})}
    <div class="kpi-row">${(d.kpis||[]).map((k)=>`<div class="kpi"><div class="kl"><span class="ic" data-i="${k.icon||"dot"}" data-s="13"></span>${k.label}</div><div class="kv">${k.value}</div></div>`).join("")}
      <div class="kpi"><div class="kl"><span class="ic" data-i="bar-chart" data-s="13"></span>Gate %</div><div class="kv">${pct}%</div></div>
      ${docPct != null ? `<div class="kpi"><div class="kl"><span class="ic" data-i="file-text" data-s="13"></span>Docs %</div><div class="kv">${docPct}%</div></div>` : ""}
    </div>
    <div class="dash-prog-row">${progBar}<span class="dash-prog-pct">${pct}%</span></div>
    ${staleHtml}
    <div class="dash-sec-title">Gate Pipeline — click to open workspace</div>
    <div class="dash-pipe">${pipe}</div>
    ${quickActHtml}
    <div class="dash-sec-title">RD Documents (${(d.rds||[]).filter((r)=>r.status==="ok").length}/${(d.rds||[]).length})</div>
    <div class="rd-grid">${(d.rds||[]).map((r)=>`<div class="rd-card" data-code="${r.code}" style="cursor:pointer" title="Open / create ${r.code}"><div class="rc-top"><span class="rc-code">${r.code}</span><span class="badge ${badgeClass(r.status)}">${badgeText(r.status)}</span></div><div class="rc-name">${r.name}</div></div>`).join("")}</div>
  </div>`;
  hideViews(); v.classList.add("show"); injectIcons(v);
  v.querySelector("#dash-back").addEventListener("click", ()=>setActivePage("explorer"));
  // Quick action buttons
  v.querySelectorAll(".dash-qbtn").forEach((el)=>el.addEventListener("click",()=>{
    const aid = el.getAttribute("data-action");
    setActivePage("explorer"); runAction(aid);
  }));
  // Pipeline nodes → gate view
  v.querySelectorAll(".dp-node.clickable").forEach((el)=>el.addEventListener("click",()=>{
    const n=parseInt(el.getAttribute("data-n"));
    if (n) { setActivePage("gate"); if (_gateModel) setTimeout(()=>_renderGateView(_gateModel, n), 30); }
  }));
  v.querySelectorAll(".rd-card").forEach((el)=>el.addEventListener("click",()=>{
    toast(`${el.dataset.code} — open/create in project`); setActivePage("explorer");
  }));
}

async function showReport() {
  const d = await Backend.get_report();
  const v = $("report-view");

  // Normalize data — support both old and new field names
  const matrix = d.decision_matrix || (d.matrix||[]).map((m)=>({aspect:m.area,keep:m.old,retrofit:"—",greenfield:m.new}));
  const items   = d.cost_items || d.items || [];
  const total   = d.cost_total || d.total || "—";
  const summary = d.summary || `Modernization assessment for ${escapeHtml(d.title||d.customer||"this project")}.`;
  const pfrom   = d.platform_from || "S5";
  const prepBy  = d.prepared_by || "—";

  const matrixRows = matrix.map((m)=>
    `<tr><td>${escapeHtml(m.aspect||m.area||"")}</td><td>${escapeHtml(m.keep||m.old||"")}</td><td>${escapeHtml(m.retrofit||"—")}</td><td>${escapeHtml(m.greenfield||m.new||"")}</td></tr>`
  ).join("");
  const costRows = items.map((it)=>
    `<tr><td>${escapeHtml(it.label||it.desc||"")}</td><td class="rp-money">${escapeHtml(it.value||it.price||"")}</td></tr>`
  ).join("");

  const actHtml = `<button class="btn" id="rep-regenerate">Regenerate</button>
    <button class="btn primary" id="rep-print">Print / Save PDF</button>
    <button class="btn" id="rep-folder" title="Generate the report file and open its folder">${svg("folder-open",12)} Open output folder</button>`;

  v.innerHTML = `<div class="page-inner">
    ${pageHeader({backId:"rep-back", icon:"file-text", title:"customer_report.pdf",
        subtitle:`${escapeHtml(d.customer||"—")} · ${d.date||""}`, actionsHtml:actHtml})}
    <div class="report-page">
      <div class="rp-eyebrow">MODERNIZATION PROPOSAL</div>
      <h1 class="rp-project">${escapeHtml(d.title||d.customer||"Project")}</h1>
      <div class="rp-meta">
        <span>Prepared by: <strong>${escapeHtml(prepBy)}</strong></span>
        <span>Date: <strong>${escapeHtml(d.date||"—")}</strong></span>
        <span>Version: <strong>${escapeHtml(d.version||"1.0")}</strong></span>
        <span>Gate: <strong>${d.gate||"—"}/${d.gate_max||7}</strong></span>
      </div>
      <hr class="rp-hr"/>
      <div class="rp-section-title">01 · Executive Summary</div>
      <p class="rp-body">${summary}</p>
      <div class="rp-section-title">02 · Cost Breakdown</div>
      <table class="rp-table"><tbody>${costRows||"<tr><td colspan='2'>No cost items yet — click Regenerate</td></tr>"}</tbody></table>
      <div class="rp-total-row"><span>Total</span><span class="rp-total-val">${escapeHtml(total)}</span></div>
      <div class="rp-section-title">03 · Modernization Decision Matrix</div>
      <table class="rp-table rp-matrix">
        <thead><tr><th>Aspect</th><th>Keep ${escapeHtml(pfrom)}</th><th>Retrofit</th><th>Greenfield</th></tr></thead>
        <tbody>${matrixRows||"<tr><td colspan='4'>No matrix data yet</td></tr>"}</tbody>
      </table>
    </div>
  </div>`;

  hideViews(); v.classList.add("show"); injectIcons(v);
  v.querySelector("#rep-back").addEventListener("click", ()=>setActivePage("explorer"));
  v.querySelector("#rep-regenerate").addEventListener("click", async () => {
    const btn = v.querySelector("#rep-regenerate");
    btn.textContent = "Generating…"; btn.disabled = true;
    const r = await Backend.generate_customer_report();
    btn.textContent = "Regenerate"; btn.disabled = false;
    if (r && r.ok) { toast(r.msg||"Report generated"); setActivePage("report"); }
    else toast((r&&r.msg)||"Generation failed");
  });
  v.querySelector("#rep-print").addEventListener("click", ()=>window.print());
  // (the old send-to-client label was dishonest — nothing was ever sent;
  // it generated locally and opened the folder, so it is now labelled that way)
  v.querySelector("#rep-folder").addEventListener("click", async () => {
    const btn = v.querySelector("#rep-folder");
    btn.textContent = "Generating…"; btn.disabled = true;
    const r = await Backend.generate_customer_report();
    btn.textContent = "Open output folder"; btn.disabled = false;
    if (r && r.ok) { await Backend.reveal_path(r.path||""); toast("Report saved — folder opened"); }
    else toast((r&&r.msg)||"Generation failed");
  });
}

/* ─────────────────────────────────────────────────────────────────────
   HARDWARE VIEW  (M7)
───────────────────────────────────────────────────────────────────── */
// Hardware workbench (2026-07-06 rework): prompt-workspace layout — category
// tabs, device list with BOM checkboxes, right pane shows/edits the device MD.
// The old page hid the MD contents entirely; now the sheet IS the page.
let _hwCategory = "all";
let _hwDevices = [];
let _hwCategories = [];
let _hwSelected = null;         // {id, rel_path, model, vendor, verified, part_number, text}
let _hwMode = "view";           // "view" | "new"
let _hwBomSel = new Set();      // device ids ticked for BOM
let _hwSizer = null;

function _hwVerBadge(verified) {
  const nv = !verified || verified === "NOT_VERIFIED";
  const bg = nv ? "rgba(217,164,65,.16)" : "rgba(80,180,120,.16)";
  const fg = nv ? "#d9a441" : "#4fae74";
  const label = nv ? "NOT_VERIFIED" : escapeHtml(verified);
  const tip = nv ? "Draft entry — an engineer must verify part numbers against the datasheet before BOM use" : "Verified on " + escapeHtml(verified);
  return `<span title="${tip}" style="font-size:10px;font-weight:700;letter-spacing:.04em;padding:2px 7px;border-radius:9px;background:${bg};color:${fg};white-space:nowrap">${label}</span>`;
}

async function _hwSelectDevice(d) {
  const r = await Backend.get_device_text(d.rel_path);
  if (!(r && r.ok)) { toast((r && r.msg) || "Could not read device file"); return; }
  _hwSelected = {...d, text: r.text || ""};
  _hwMode = "view";
}

async function showHardwareView(sizerResult) {
  const v = $("hardware-view");
  const lib = await Backend.get_hw_library();
  _hwDevices = (lib && lib.devices) || [];
  _hwCategories = (lib && lib.categories) || [];
  if (sizerResult) _hwSizer = sizerResult;
  if (_hwCategory !== "all" && !_hwCategories.includes(_hwCategory)) _hwCategory = "all";
  // keep selection across refreshes; otherwise preselect the first device
  // (no empty editor on open — same rule as the Prompt workspace)
  const keep = _hwSelected && _hwDevices.find((d)=>d.rel_path===_hwSelected.rel_path);
  if (keep) { await _hwSelectDevice(keep); }
  else {
    _hwSelected = null;
    const visible = _hwDevices.filter((d)=>_hwCategory==="all"||d.category===_hwCategory);
    if (_hwMode !== "new" && visible.length) await _hwSelectDevice(visible[0]);
  }
  _renderHardwareView(v);
  hideViews(); v.classList.add("show"); injectIcons(v);
}

function _renderHardwareView(v) {
  const cats = [{id:"all",label:`All (${_hwDevices.length})`}]
    .concat(_hwCategories.map((c)=>({id:c,label:`${c} (${_hwDevices.filter((d)=>d.category===c).length})`})));
  const catTabs = cats.map((c)=>
    `<div class="pv-cat ${_hwCategory===c.id?"active":""}" data-cat="${escapeHtml(c.id)}">${escapeHtml(c.label)}</div>`).join("");

  const visible = _hwDevices.filter((d)=>_hwCategory==="all"||d.category===_hwCategory);
  const listHtml = visible.length
    ? visible.map((d)=>`<div class="pv-item ${_hwSelected&&_hwSelected.rel_path===d.rel_path?"active":""}" data-rel="${escapeHtml(d.rel_path)}" style="display:flex;align-items:center;gap:8px">
        <input type="checkbox" class="hw-bom-ck" data-id="${escapeHtml(d.id)}" ${_hwBomSel.has(d.id)?"checked":""} title="Include in BOM" style="margin:0;flex:none" />
        <span style="flex:1;min-width:0">
          <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(d.model||d.id)}</span>
          <span style="display:block;font-size:10px;color:var(--fg-dim)">${escapeHtml(d.vendor||"?")} · ${escapeHtml(d.category||"")}</span>
        </span>
        ${_hwVerBadge(d.verified)}
      </div>`).join("")
    : `<div style="color:var(--fg-dim);font-size:12px;padding:10px">No devices in this category</div>`;

  const sizerStrip = _hwSizer ? `
    <div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;padding:8px 12px;margin:8px 0 0;border:1px solid var(--border);border-radius:6px;font-size:12px">
      <span><b>IO</b> ${_hwSizer.io_count||0}</span><span><b>Reserve</b> ${_hwSizer.reserve_pct||20}%</span>
      <span><b>Platform</b> ${escapeHtml(_hwSizer.platform||"—")}</span><span><b>CPU</b> ${escapeHtml(_hwSizer.cpu||"—")}</span>
      <span><b>Modules</b> ${_hwSizer.total_modules||0}</span>
      ${(_hwSizer.warnings||[]).map((w)=>`<span style="color:#d9a441">! ${escapeHtml(w)}</span>`).join("")}
      ${(_hwSizer.errors||[]).map((w)=>`<span style="color:#c95555">✕ ${escapeHtml(w)}</span>`).join("")}
    </div>` : "";

  let bodyHtml;
  if (_hwMode === "new") {
    bodyHtml = `<div class="pv-editor-wrap">
      <div class="pv-editor-head"><span style="font-weight:600;color:var(--fg)">New Device</span></div>
      <div style="display:grid;grid-template-columns:180px 1fr;gap:10px;padding:14px;max-width:560px">
        <label style="align-self:center">Category</label>
        <select id="hw-new-cat" class="pv-select">
          ${["controllers","drives","io_modules","safety","sensors","hmi","network","accessories"]
            .concat(_hwCategories.filter((c)=>!["controllers","drives","io_modules","safety","sensors","hmi","network","accessories"].includes(c)))
            .map((c)=>`<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("")}
        </select>
        <label style="align-self:center">Vendor</label><input id="hw-new-vendor" class="pv-input" placeholder="e.g. Siemens / SEW / ifm" />
        <label style="align-self:center">Model</label><input id="hw-new-model" class="pv-input" placeholder="e.g. SINAMICS G120X" />
      </div>
      <div style="padding:0 14px;font-size:11px;color:var(--fg-dim)">Creates a NOT_VERIFIED skeleton sheet (same sections as the library) and opens it here for editing. For a datasheet PDF, use <b>Datasheet (AI)</b> instead — it fills the sheet automatically.</div>
      <div class="pv-action-row">
        <button class="btn primary" id="hw-create-btn">Create skeleton</button>
        <button class="btn ghost" id="hw-cancel-new">Cancel</button>
      </div>
    </div>`;
  } else if (_hwSelected) {
    const d = _hwSelected;
    bodyHtml = `<div class="pv-editor-wrap">
      <div class="pv-editor-head" style="gap:10px">
        <span style="font-weight:600;color:var(--fg)">${escapeHtml(d.model||d.id)}</span>
        <span style="font-size:11px;color:var(--fg-dim)">${escapeHtml(d.vendor||"")}${d.part_number?" · "+escapeHtml(d.part_number):""}</span>
        <div class="fill"></div>
        ${_hwVerBadge(d.verified)}
        <span style="font-size:10px;color:var(--fg-dim);font-family:var(--mono,monospace)">${escapeHtml(d.rel_path)}</span>
      </div>
      <textarea class="pv-textarea" id="hw-textarea" spellcheck="false">${escapeHtml(d.text||"")}</textarea>
      <div class="pv-action-row">
        <button class="btn primary" id="hw-save-btn">Save</button>
        <button class="btn" id="hw-reveal-btn">Show in folder</button>
        <span style="flex:1"></span>
        <span style="font-size:11px;color:var(--fg-dim)">Save also refreshes the offline RAG index</span>
      </div>
    </div>`;
  } else {
    bodyHtml = `<div style="display:grid;place-items:center;flex:1;color:var(--fg-dim);font-size:13px">Select a device from the list →</div>`;
  }

  const actHtml = `
    <button class="btn" id="hw-datasheet-btn" title="Select a device datasheet PDF → AI extracts the spec → saves to the library → updates the RAG index">${svg("upload",12)} Datasheet (AI)</button>
    <button class="btn" id="hw-new-btn">+ New Device</button>
    <button class="btn" id="hw-sizer-btn" title="Suggest CPU + IO modules from the project IO count (20% reserve)">Size from IO</button>
    <button class="btn primary" id="hw-bom-btn">Generate BOM (${_hwBomSel.size})</button>`;

  v.innerHTML = `<div class="pv-wrap">
    ${pageHeader({backId:"hw-back", icon:"cpu", title:"Hardware Workbench", subtitle:"Device library — view & edit the sheets, size from IO, tick devices for the BOM", actionsHtml:actHtml})}
    <div class="pv-cats">${catTabs}</div>
    ${sizerStrip}
    <div class="pv-body">
      <div class="pv-list" id="hw-list" style="width:260px;flex:0 0 260px">${listHtml}</div>
      <div class="pv-divider" id="hw-divider"></div>
      <div class="pv-panel">${bodyHtml}</div>
    </div>
  </div>`;
  injectIcons(v);

  v.querySelector("#hw-back").addEventListener("click", ()=>{ _hwSelected=null; _hwMode="view"; setActivePage("explorer"); });
  v.querySelectorAll(".pv-cat").forEach((el)=>el.addEventListener("click", async()=>{
    _hwCategory = el.getAttribute("data-cat");
    _hwSelected = null; _hwMode = "view";
    const visible2 = _hwDevices.filter((d)=>_hwCategory==="all"||d.category===_hwCategory);
    if (visible2.length) await _hwSelectDevice(visible2[0]);
    _renderHardwareView(v);
  }));
  v.querySelectorAll("#hw-list .pv-item").forEach((el)=>el.addEventListener("click", async(e)=>{
    if (e.target && e.target.classList.contains("hw-bom-ck")) return;
    const d = _hwDevices.find((x)=>x.rel_path===el.getAttribute("data-rel"));
    if (!d) return;
    if (_hwMode==="view" && _hwSelected && _hwSelected.rel_path!==d.rel_path) {
      const ta = v.querySelector("#hw-textarea");
      if (ta && ta.value !== _hwSelected.text && !confirm("Discard unsaved changes to " + _hwSelected.rel_path + "?")) return;
    }
    await _hwSelectDevice(d);
    _renderHardwareView(v);
  }));
  v.querySelectorAll(".hw-bom-ck").forEach((ck)=>ck.addEventListener("change", ()=>{
    const id = ck.getAttribute("data-id");
    if (ck.checked) _hwBomSel.add(id); else _hwBomSel.delete(id);
    const bomBtn = v.querySelector("#hw-bom-btn");
    if (bomBtn) bomBtn.textContent = `Generate BOM (${_hwBomSel.size})`;
  }));

  // drag-to-resize (same interaction as the Prompt workspace)
  const dv = v.querySelector("#hw-divider"), ls = v.querySelector("#hw-list");
  if (dv && ls) dv.addEventListener("mousedown", (e)=>{
    const rx = e.clientX, lw = ls.offsetWidth;
    dv.classList.add("dragging");
    const onMove = (ev)=>{ const w = Math.min(420, Math.max(150, lw+(ev.clientX-rx))); ls.style.width=w+"px"; ls.style.flex=`0 0 ${w}px`; };
    const onUp = ()=>{ dv.classList.remove("dragging"); document.removeEventListener("mousemove",onMove); document.removeEventListener("mouseup",onUp); };
    document.addEventListener("mousemove",onMove); document.addEventListener("mouseup",onUp); e.preventDefault();
  });

  v.querySelector("#hw-new-btn").addEventListener("click", ()=>{ _hwMode="new"; _renderHardwareView(v); });
  const cancelNew = v.querySelector("#hw-cancel-new");
  if (cancelNew) cancelNew.addEventListener("click", async()=>{ _hwMode="view"; await showHardwareView(); });
  const createBtn = v.querySelector("#hw-create-btn");
  if (createBtn) createBtn.addEventListener("click", async()=>{
    const cat = v.querySelector("#hw-new-cat").value;
    const ven = v.querySelector("#hw-new-vendor").value.trim();
    const mod = v.querySelector("#hw-new-model").value.trim();
    if (!ven || !mod) { toast("Vendor and model are required"); return; }
    const r = await Backend.create_device(cat, ven, mod);
    if (!(r && r.ok)) { toast((r&&r.msg)||"Create failed"); return; }
    toast(r.msg||"Created");
    _hwMode = "view"; _hwSelected = {rel_path:r.rel_path};
    await showHardwareView();
  });

  const saveBtn = v.querySelector("#hw-save-btn");
  if (saveBtn) saveBtn.addEventListener("click", async()=>{
    const text = v.querySelector("#hw-textarea").value;
    const r = await Backend.save_device_text(_hwSelected.rel_path, text);
    if (r && r.ok) {
      _hwSelected.text = text;
      toast(r.msg + (r.rag_warn ? " — " + r.rag_warn : ""));
      await showHardwareView();   // metadata (verified, part no) may have changed
    } else toast((r&&r.msg)||"Save failed");
  });
  const revealBtn = v.querySelector("#hw-reveal-btn");
  if (revealBtn) revealBtn.addEventListener("click", async()=>{
    const lib = await Backend.get_hw_library();
    if (lib && lib.root) Backend.reveal_path(lib.root + "/" + _hwSelected.rel_path);
  });

  const dsBtn = v.querySelector("#hw-datasheet-btn");
  dsBtn.addEventListener("click", async()=>{
    dsBtn.disabled = true; dsBtn.textContent = "Selecting…";
    try {
      const pick = await Backend.browse_for_file("pdf");
      if (pick && pick.ok && pick.path) {
        dsBtn.textContent = "Extracting…";
        const r = await Backend.ingest_device(pick.path);
        if (r && r.ok) {
          toast(`Device saved: ${r.device_id}${r.rag_warn ? " (RAG: " + r.rag_warn + ")" : ""}`);
          _hwSelected = r.file_path ? {rel_path: String(r.file_path).replace(/^09_HARDWARE_LIBRARY\/|^06_HARDWARE_LIB\//, "")} : null;
          await showHardwareView();
          return;
        }
        toast(`Datasheet error: ${(r && r.msg) || "unknown error"}`);
      }
    } catch(e) { toast(`Datasheet error: ${e.message||e}`); }
    dsBtn.disabled = false; dsBtn.innerHTML = `${svg("upload",12)} Datasheet (AI)`;
  });

  v.querySelector("#hw-sizer-btn").addEventListener("click", async()=>{
    const r = await Backend.size_hardware(20);
    if (r && (r.ok || r.io_count !== undefined)) { _hwSizer = r; _renderHardwareView(v); }
    if (r && !r.ok) toast((r&&r.msg)||"Sizing failed");
  });
  v.querySelector("#hw-bom-btn").addEventListener("click", async()=>{
    if (!_hwBomSel.size) { toast("Tick at least one device in the list"); return; }
    // bom_manager reads dev["device_id"] — the old page sent {id:…} and every
    // BOM row came out with an empty ID (latent bug, fixed 2026-07-06)
    const selected = _hwDevices.filter((d)=>_hwBomSel.has(d.id))
      .map((d)=>({device_id:d.id, quantity:1}));
    const r = await Backend.generate_bom(selected);
    toast((r&&r.msg)||"BOM done");
    if (r && r.ok && r.path) Backend.reveal_path(r.path);
  });
}

async function openProjectBrowse() {
  const r = await Backend.browse_for_folder();
  if (!(r && r.ok && r.path)) return;   // user cancelled
  const ok = await Backend.open_project(r.path);
  if (ok && ok.ok) { await refreshProjectState(); setActivePage("explorer"); toast("Project opened"); }
  else toast("Could not open: " + ((ok && ok.msg) || r.path));
}

let _onbTemplates = [];

async function showOnboarding() {
  const d = await Backend.get_onboarding();
  _onbTemplates = d.templates || [];
  const v = $("onboarding-view");
  // One obvious primary path (UX audit 3.1): big "New Project" opens the
  // creation form directly; opening an existing folder is secondary;
  // recents follow below.
  v.innerHTML=`<div class="page-inner" style="max-width:760px">
    ${pageHeader({backId:"onb-back", icon:"factory", title:`Hello, ${escapeHtml(d.user)}`, subtitle:"Continue a project or create a new one.", actionsHtml:""})}
    <div class="onb-hero">
      <button class="btn primary" id="onb-new-btn" style="font-size:14px;padding:10px 26px">${svg("folder-plus",14)} New Project</button>
      <button class="btn" id="onb-browse-btn">${svg("folder-open",12)} Open existing folder…</button>
    </div>
    <!-- B-12: first-run orientation — the RD/Gate vocabulary is opaque to a
         new engineer; three concrete steps beat a manual they won't open. -->
    <div class="onb-quickstart">
      <div class="caps" style="margin:0 0 8px">How this works — 3 steps</div>
      <div class="onb-qs-steps">
        <div class="onb-qs-step"><span class="onb-qs-n">1</span>
          <b>Create a project</b><span>Retrofit (you have legacy code) or greenfield (you have a spec).</span></div>
        <div class="onb-qs-step"><span class="onb-qs-n">2</span>
          <b>Drop your sources</b><span>AWL/SCL/PDF exports into <code>_raw/legacy_code/</code> — drawings &amp; photos into <code>_raw/drawings/</code>. (.s7p/.zap archives: export sources first — the app shows how.)</span></div>
        <div class="onb-qs-step"><span class="onb-qs-n">3</span>
          <b>Run the gates</b><span>Gates → <b>Start Pre-Analysis</b>. The AI drafts the 14 requirement docs (RD01–RD14); you review &amp; sign; then it generates the S7-1500 SCL code.</span></div>
      </div>
    </div>
    <div class="caps" style="margin:18px 0 10px">Recent Projects</div>
    <div class="onb-list">${(d.recents||[]).map((r)=>`<div class="item" data-path="${escapeHtml(r.path)}"><span class="ic" data-i="folder" data-s="14"></span><span class="nm">${escapeHtml(r.name)}</span><span class="pth">${escapeHtml(r.path)}</span><button class="onb-rm" title="Remove from list" data-path="${escapeHtml(r.path)}">×</button></div>`).join("")||'<div style="color:var(--fg-dim);font-size:12px;padding:8px 0">No recent projects</div>'}</div>
  </div>`;
  hideViews(); v.classList.add("show"); injectIcons(v);
  v.querySelectorAll(".onb-list .item").forEach((el)=>el.addEventListener("click",async()=>{
    const r=await Backend.open_project(el.getAttribute("data-path"));
    if (r&&r.ok) { await refreshProjectState(); setActivePage("explorer"); toast("Project opened"); }
    else toast("Could not open project" + (r&&r.msg ? ": " + r.msg : ""));
  }));
  v.querySelectorAll(".onb-list .onb-rm").forEach((btn)=>btn.addEventListener("click",async(e)=>{
    e.stopPropagation();
    await Backend.remove_from_recents(btn.getAttribute("data-path"));
    showOnboarding();
  }));
  v.querySelector("#onb-new-btn").addEventListener("click", ()=>showNewProjectDialog((_onbTemplates[0]||{}).id||""));
  v.querySelector("#onb-browse-btn").addEventListener("click", openProjectBrowse);
  v.querySelector("#onb-back").addEventListener("click", ()=>setActivePage("explorer"));
}

async function showNewProjectDialog(templateId) {
  if ($("npd-overlay")) return;
  const ov = document.createElement("div");
  ov.className="overlay show"; ov.id="npd-overlay";
  ov.innerHTML=`<div class="settings-modal" style="width:500px">
    <div class="sm-head"><span class="ic" data-i="folder-plus" data-s="16"></span>New Project<div class="fill"></div></div>
    <div class="sm-body">
      <div class="sm-sec">
        <div class="sm-field"><label>Template</label>
          <select id="npd-template" style="width:100%">
            ${(_onbTemplates.length?_onbTemplates:[{id:"blank",name:"Blank Project",desc:""}]).map((t)=>
              `<option value="${escapeHtml(t.id)}"${t.id===templateId?" selected":""}>${escapeHtml(t.name)}${t.desc?" — "+escapeHtml(t.desc):""}</option>`).join("")}
          </select>
        </div>
        <div class="sm-field"><label>Project Name</label><input id="npd-name" type="text" placeholder="e.g. Kunde_Mueller_Retrofit" /></div>
        <div class="sm-field"><label>Location</label><input id="npd-path" type="text" placeholder="D:\\customer_projects" /><button class="btn" id="npd-browse" style="margin-left:6px;white-space:nowrap">${svg("folder",12)} Browse</button></div>
        <div class="sm-field"><label>Customer</label><input id="npd-customer" type="text" placeholder="optional — shown on reports and FAT protocols" /></div>
      </div>
      <div class="sm-sec">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div class="sm-field"><label>Output language</label>
            <select id="npd-lang" style="width:100%" title="Language for AI-generated documents, comments and reports">
              <option value="EN">English</option>
              <option value="DE">Deutsch</option>
              <option value="TR">Türkçe</option>
            </select>
          </div>
          <div class="sm-field"><label>Data Classification</label>
            <select id="npd-class" style="width:100%">
              <option value="CONFIDENTIAL">CONFIDENTIAL (default)</option>
              <option value="INTERNAL">INTERNAL</option>
              <option value="PUBLIC">PUBLIC</option>
              <option value="RESTRICTED">RESTRICTED</option>
            </select>
          </div>
        </div>
        <div style="font-size:10px;color:var(--fg-dim);margin-top:4px;line-height:1.5">
          Data Classification controls which AI providers may see project data:
          PUBLIC/INTERNAL → AI calls allowed · CONFIDENTIAL → engineer consent per send ·
          RESTRICTED → all AI &amp; TIA egress blocked.
        </div>
      </div>
      <div class="sm-sec">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div class="sm-field"><label>Platform</label>
            <select id="npd-platform" style="width:100%">
              <option value="S7-1500">Siemens S7-1500</option>
              <option value="S7-1200">Siemens S7-1200</option>
              <option value="S7-300">Siemens S7-300</option>
              <option value="generic">Generic / Other</option>
            </select>
          </div>
          <div class="sm-field"><label>TIA Portal Version</label>
            <select id="npd-tia" style="width:100%">
              <option value="V19">V19</option>
              <option value="V18">V18</option>
              <option value="V17">V17</option>
              <option value="V16">V16</option>
            </select>
          </div>
          <div class="sm-field"><label>CPU Model</label>
            <input id="npd-cpu" type="text" placeholder="e.g. CPU 1516-3 PN/DP" />
          </div>
          <div class="sm-field"><label>Safety CPU</label>
            <select id="npd-safety" style="width:100%">
              <option value="no">No</option>
              <option value="yes">Yes (F-CPU)</option>
            </select>
          </div>
        </div>
        <div style="font-size:10px;color:var(--fg-dim);margin-top:4px;line-height:1.5">
          Generated SCL targets <b>S7-1200/1500 (TIA Portal)</b> — it uses REGION
          syntax and optimized block access. Legacy S5/S7-300 code is the
          <i>input</i> (analysis); it is not regenerated for classic hardware.
        </div>
        <div class="prov-warn" id="npd-platform-warn" style="display:none;margin-top:6px">
          ⚠ S7-300/400 as <b>target</b> is not supported: the generated blocks use
          S7-1500-only syntax (REGION, S7_Optimized_Access) and will not compile
          for classic CPUs. Choose this only if you migrate the hardware too.
        </div>
      </div>
      <div class="sm-sec" style="padding-top:0">
        <div style="font-size:11px;color:var(--fg-dim);margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Hardware modules</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px" id="npd-hw-checks">
          ${["ET 200SP","ET 200MP","PROFINET IO","PROFIBUS DP","ASi","IO-Link","Drives (G120)","Drives (S120)","HMI (KTP)","HMI (KP)"].map((d)=>
            `<label style="display:flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;background:var(--bg3);padding:4px 8px;border-radius:4px;border:1px solid var(--border)"><input type="checkbox" data-hw="${d}" style="accent-color:var(--accent)" />${d}</label>`
          ).join("")}
        </div>
      </div>
      <div class="sm-hint" id="npd-hint"></div>
    </div>
    <div class="sm-foot"><button class="btn primary" id="npd-create">Create</button><button class="btn ghost" id="npd-cancel">Cancel</button></div>
  </div>`;
  document.body.appendChild(ov); injectIcons(ov);
  const q=(s)=>ov.querySelector(s);
  q("#npd-browse").addEventListener("click",async()=>{
    const r=await Backend.browse_for_folder();
    if (r&&r.ok&&r.path) q("#npd-path").value=r.path;
  });
  const close=()=>ov.remove();
  q("#npd-cancel").addEventListener("click",close);
  ov.addEventListener("click",(e)=>{ if(e.target===ov) close(); });
  // B-08: honest scope — warn when the chosen TARGET can't run the output
  q("#npd-platform").addEventListener("change",()=>{
    const v=q("#npd-platform").value;
    q("#npd-platform-warn").style.display=(v==="S7-300")?"":"none";
  });
  q("#npd-create").addEventListener("click",async()=>{
    const name=q("#npd-name").value.trim(), path=q("#npd-path").value.trim();
    if (!name||!path) { q("#npd-hint").textContent="Name and location are required"; return; }
    q("#npd-hint").textContent="Creating…";
    const meta={
      platform: q("#npd-platform").value,
      tia_version: q("#npd-tia").value,
      cpu_model: q("#npd-cpu").value.trim(),
      safety: q("#npd-safety").value==="yes",
      hw_modules: [...ov.querySelectorAll("#npd-hw-checks input:checked")].map((cb)=>cb.getAttribute("data-hw")),
      customer: q("#npd-customer").value.trim(),
      output_language: q("#npd-lang").value,
      data_classification: q("#npd-class").value,
    };
    const chosenTpl = q("#npd-template").value || templateId;
    const r=await Backend.create_project(chosenTpl, name, path, meta);
    if (r&&r.ok) {
      close(); await refreshProjectState(); setActivePage("explorer");
      toast(`Project "${name}" created — next: drop legacy code into _raw/legacy_code, then open Gates → Gate 1`);
      logLine(`[project] "${name}" created. Next: drop legacy code into _raw/legacy_code, then open Gates → Gate 1.`, "info");
    }
    else q("#npd-hint").textContent=(r&&r.msg)||"Creation failed";
  });
}

/* ─────────────────────────────────────────────────────────────────────
   GIT PANEL
───────────────────────────────────────────────────────────────────── */
async function showGitPanel() {
  const v = $("git-view");
  if (!v) return;
  const g = await Backend.git_info();
  const gitActHtml = `<span class="mono" style="font-size:11px;background:var(--accent-soft);color:var(--accent);padding:3px 8px;border-radius:4px">${escapeHtml(g.branch||"main")}</span>`;
  v.innerHTML=`<div class="page-inner" style="max-width:900px">
    ${pageHeader({backId:"git-back", icon:"git-branch", title:"Git", subtitle:escapeHtml(g.remote||"local repository"), actionsHtml:gitActHtml})}

    <div class="dash-sec-title">Commit</div>
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:20px">
      <div style="display:flex;gap:8px;align-items:center">
        <input id="git-msg" type="text" placeholder="Commit message…" style="flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:6px;color:var(--fg);font-size:12px;padding:6px 10px;outline:none" />
        <button class="btn primary" id="git-commit-btn" style="white-space:nowrap">${svg("git-commit",12)} Commit</button>
        <button class="btn" id="git-push-btn" style="white-space:nowrap">${svg("upload",12)} Push</button>
        <button class="btn" id="git-pull-btn" style="white-space:nowrap">${svg("refresh",12)} Pull</button>
        <button class="btn ghost" id="git-init-btn" style="white-space:nowrap">${svg("git-branch",12)} Init Repo</button>
      </div>
      <div id="git-op-hint" style="margin-top:8px;font-size:11px;color:var(--fg-dim);min-height:16px"></div>
    </div>

    <div class="dash-sec-title">Changed files (${g.changes.length})</div>
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:4px 0;margin-bottom:20px">
      ${g.changes.length
        ? g.changes.map((c)=>`<div class="git-change-row" data-path="${escapeHtml(c.slice(3))}">
            <span class="git-status">${escapeHtml(c.slice(0,2))}</span>
            <span class="git-file">${escapeHtml(c.slice(3))}</span>
            <span class="git-diff-btn" data-path="${escapeHtml(c.slice(3))}" title="View diff">${svg("file-code",12)} diff</span>
           </div>`).join("")
        : '<div style="padding:14px 18px;color:var(--fg-dim);font-size:12px">Working tree clean</div>'}
    </div>
    <div class="dash-sec-title">Recent commits</div>
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:4px 0">
      ${g.log.length
        ? g.log.map((l)=>{const h=l.slice(0,7),msg=l.slice(8);return `<div class="git-log-row"><span class="ic" data-i="git-commit" data-s="12" style="color:var(--accent);flex:0 0 16px"></span><span class="mono" style="color:var(--fg-dim);font-size:10px;flex:0 0 56px">${escapeHtml(h)}</span><span style="font-size:12px;color:var(--fg)">${escapeHtml(msg)}</span></div>`;}).join("")
        : '<div style="padding:14px 18px;color:var(--fg-dim);font-size:12px">No commits yet</div>'}
    </div>
  </div>`;
  hideViews(); v.classList.add("show"); injectIcons(v);
  const hint = v.querySelector("#git-op-hint");
  v.querySelector("#git-back").addEventListener("click",()=>setActivePage("explorer"));
  // Click changed-file row → open in editor; click diff btn → load diff
  v.querySelectorAll(".git-change-row").forEach((row)=>{
    row.addEventListener("click",(e)=>{ if (!e.target.classList.contains("git-diff-btn")) { setActivePage("explorer"); openFile(row.getAttribute("data-path")); } });
  });
  // Enter in commit message box → commit
  v.querySelector("#git-msg").addEventListener("keydown",(e)=>{ if (e.key==="Enter") v.querySelector("#git-commit-btn").click(); });
  v.querySelectorAll(".git-diff-btn").forEach((el)=>el.addEventListener("click",async()=>{
    const fp=el.getAttribute("data-path");
    const r=await Backend.git_diff(fp);
    LAST_PREVIEW=r.diff||"(no diff)";
    switchBottomTab("ai");
    setActivePage("explorer"); toast("Diff loaded in AI Preview panel");
  }));
  v.querySelector("#git-commit-btn").addEventListener("click",async()=>{
    const msg=v.querySelector("#git-msg").value.trim();
    if (!msg) { hint.textContent="Enter a commit message first"; return; }
    hint.textContent="Committing…";
    const r=await Backend.git_commit(msg);
    hint.style.color=r.ok?"var(--success)":"var(--error)";
    hint.textContent=r.msg||"Done";
    if (r.ok) { v.querySelector("#git-msg").value=""; setTimeout(()=>showGitPanel(),800); }
  });
  v.querySelector("#git-push-btn").addEventListener("click",async()=>{
    hint.textContent="Pushing…"; hint.style.color="var(--fg-dim)";
    let r=await Backend.git_push(false);
    // G-03 fix: if backend blocks due to CONFIDENTIAL/RESTRICTED classification,
    // surface a confirm dialog so the user can explicitly acknowledge that the
    // remote is a private/enterprise host. Never silently bypass.
    if (!r.ok && r.msg && (r.msg.includes("CONFIDENTIAL") || r.msg.includes("RESTRICTED") || r.msg.includes("gizli") || r.msg.includes("sınıflandırılmış"))) {
      const accepted = window.confirm(
        t("dlg.push_conf_head") + "\n\n" + r.msg + "\n\n" +
        t("dlg.push_conf_tail")
      );
      if (accepted) {
        hint.textContent="Pushing (confirmed)…"; hint.style.color="var(--fg-dim)";
        r = await Backend.git_push(true);
      } else {
        hint.style.color="var(--fg-dim)";
        hint.textContent=t("dlg.push_cancelled");
        return;
      }
    }
    hint.style.color=r.ok?"var(--success)":"var(--error)";
    hint.textContent=r.msg||"Done";
  });
  v.querySelector("#git-pull-btn").addEventListener("click",async()=>{
    hint.textContent="Pulling…"; hint.style.color="var(--fg-dim)";
    const r=await Backend.git_pull();
    hint.style.color=r.ok?"var(--success)":"var(--error)";
    hint.textContent=r.msg||"Done";
    if (r.ok) setTimeout(()=>showGitPanel(),600);
  });
  v.querySelector("#git-init-btn").addEventListener("click",async()=>{
    hint.textContent="Initializing repo…"; hint.style.color="var(--fg-dim)";
    const r=await Backend.git_init_project();
    hint.style.color=r.ok?"var(--success)":"var(--error)";
    hint.textContent=r.msg||"Done";
    if (r.ok) setTimeout(()=>showGitPanel(),800);
  });
}

/* ─────────────────────────────────────────────────────────────────────
   GATE VIEW  (full view — auto-derived model, per-gate workspace)
───────────────────────────────────────────────────────────────────── */
let _gateModel = null;

// SINGLE source of truth for RD-status and action labels/icons — the UX
// audit (2026-06-10) found dashboard and gate view each carrying their own
// copies with diverging labels ("Analyze" vs "Analyze Project") and colors
// (empty = warn vs draft). Every view must use these.
const RD_STATUS_LABEL = {ok:"OK",done:"OK",in_progress:"WIP",draft:"DRAFT",empty:"EMPTY",template:"TMPL",draft_unverified:"DRAFT",mod:"MOD",warn:"!"};
const RD_STATUS_CLASS = {ok:"ok",done:"ok",in_progress:"mod",draft:"draft",empty:"warn",template:"draft",draft_unverified:"draft",mod:"mod",warn:"warn"};

// 3-state verification badge (draft 🟡 → reviewed 🟢 → locked 🔒). Green ONLY
// means engineer-verified, so unverified RDs stand out (amber).
const RD_REVIEW_BADGE = {
  draft:    {cls:"warn",  label:"DRAFT ⚠"},
  stale:    {cls:"warn",  label:"⚠ RE-REVIEW"},
  reviewed: {cls:"ok",    label:"✓ REVIEWED"},
  locked:   {cls:"locked",label:"🔒 LOCKED"},
  na:       {cls:"draft", label:"⊘ N/A"},
  empty:    {cls:"draft", label:"—"},
};

const ACTION_LABELS = {analyze:"Analyze",extract_io:"Extract IO",assemble_program:"Assemble Program",generate_scl:"Generate SCL",generate_sequence_fb:"Sequence FB (AI)",rd01_crosscheck:"RD01 Cross-Check",validate:"Validate",export_tia:"Export TIA",send_to_tia:"Send to TIA",show_standards:"Standards",generate_report:"Customer Report",generate_fat:"FAT Protocol",size_hardware:"Size Hardware",generate_test_scenarios:"Generate Test Scenarios",hmi_draft:"HMI Draft (RD11/RD08)",generate_hmi_interface:"HMI Interface (DB_HMI)"};
const ACTION_ICONS  = {analyze:"sparkles",extract_io:"table",assemble_program:"package",generate_scl:"play",generate_sequence_fb:"sparkles",rd01_crosscheck:"check",validate:"check",export_tia:"upload",send_to_tia:"upload",show_standards:"file-text",generate_report:"file-text",generate_fat:"check",size_hardware:"cpu",generate_test_scenarios:"chip",hmi_draft:"table",generate_hmi_interface:"chip"};
// Plain-language tooltips for the same actions (jargon help, UX audit 3.3).
const ACTION_HINTS  = {
  analyze:"Scan the project and derive its current state",
  extract_io:"Read IO signals from legacy code into the RD01 IO List",
  assemble_program:"Build OB1 + instance DBs from frozen library FBs (library-first, no AI)",
  generate_scl:"SCL = Structured Control Language (IEC 61131-3 ST) — generate the sequence FB",
  generate_sequence_fb:"The ONLY AI-generated code artifact: sequence FB drafted from the reviewed RD03 (classification-guarded, audited, schema-validated — output is DRAFT until engineer review)",
  rd01_crosscheck:"Deterministic RD01 vs legacy-source verification: covered / missing / hallucinated operands + direction sanity (no AI)",
  validate:"Run the offline SCL validator (syntax + vendor rules)",
  export_tia:"Write SCL export files for manual TIA import",
  send_to_tia:"Transfer blocks + tags into TIA Portal via Openness and compile",
  show_standards:"Open the coding-standard documents",
  generate_report:"Generate the customer-facing modernization report",
  generate_fat:"FAT = Factory Acceptance Test — generate the test protocol",
  size_hardware:"Suggest CPU + IO modules from the IO count (20% reserve)",
  generate_test_scenarios:"Generate test scenarios from RD01 signals + FB contract behaviors (no AI, fully deterministic)",
  hmi_draft:"Pre-fill RD11 (HMI) + RD08 (Alarms) from the wired pulpit — buttons, selector switches, BCD thumbwheels, indicator lamps (deterministic, verbatim symbols, no AI)",
  generate_hmi_interface:"Generate DB_HMI.scl + DB_Alarm.scl + hmi_tags.xlsx from RD11/RD08 — plus a wiring proposal the engineer approves (never auto-bound)",
};

const GATE_NAMES = ["Discovery","Extraction","Human Review","Code Generation","Validation","PLCSIM / Field Verify","FAT / SAT"];
const GATE_SUBTITLES = {
  1:"Brief + inventory", 2:"14-Point Pack",    3:"Engineer sign-off",
  4:"SCL output",        5:"Consistency check", 6:"PLCSIM or signed manual test", 7:"Acceptance",
};

async function _promptCompileLog() {
  const st = await Backend.get_gate6_compile_status();
  const tiaAuto = !!(st && st.tia_auto);
  return new Promise((resolve) => {
    if ($("g6-compile-overlay")) { resolve(null); return; }
    const ov = document.createElement("div");
    ov.className = "overlay show"; ov.id = "g6-compile-overlay";
    ov.innerHTML = `<div class="settings-modal" style="max-width:520px">
      <div class="sm-head">${svg("chip",14)} Gate 6 — Compile Evidence (B-P2)</div>
      <div class="sm-body">
        ${tiaAuto
          ? `<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--ok,#2a2);border-radius:6px;margin-bottom:10px;font-size:12px">
               ${svg("check",13)} <span>Compile evidence auto-detected — <b>tia_compile.json</b> found (TIA Openness run).</span>
             </div>`
          : `<div class="sm-hint" style="margin-bottom:10px">No TIA Openness compile record found. Provide the TIA Portal compile log file manually.</div>
             <div class="sm-field">
               <label style="width:110px;flex:0 0 110px">Compile log</label>
               <input id="g6-log-path" type="text" placeholder="C:\\TIA_Projects\\MyProject\\compile_log.txt" style="flex:1"/>
               <button class="btn ghost" id="g6-browse" style="font-size:12px;flex:none">Browse…</button>
             </div>`
        }
        <label style="display:flex;gap:8px;font-size:12px;cursor:pointer;margin-top:10px;align-items:flex-start">
          <input id="g6-confirm" type="checkbox" style="margin-top:2px"/>
          I confirm that I have manually tested this program on PLCSIM or a real controller and the results are satisfactory.
        </label>
      </div>
      <div class="sm-foot">
        <button class="btn primary" id="g6-ok">OK</button>
        <button class="btn ghost" id="g6-cancel">Cancel</button>
        <span class="sm-hint" id="g6-hint"></span>
      </div>
    </div>`;
    document.body.appendChild(ov); injectIcons(ov);
    const q = s => ov.querySelector(s);
    if (!tiaAuto) {
      q("#g6-browse")?.addEventListener("click", async () => {
        const r = await Backend.browse_for_file("compile_log");
        if (r && r.ok && r.path) q("#g6-log-path").value = r.path;
      });
    }
    q("#g6-cancel").addEventListener("click", () => { ov.remove(); resolve(null); });
    ov.addEventListener("click", e => { if (e.target === ov) { ov.remove(); resolve(null); } });
    q("#g6-ok").addEventListener("click", () => {
      const confirmed = q("#g6-confirm").checked;
      if (!confirmed) { q("#g6-hint").textContent = "Engineer declaration required."; return; }
      const path = tiaAuto ? "" : (q("#g6-log-path")?.value.trim() || "");
      if (!tiaAuto && !path) { q("#g6-hint").textContent = "Compile log path is required."; return; }
      ov.remove();
      resolve({ compileLogPath: path, manualTestConfirmed: true });
    });
  });
}

async function showGateView(gateN) {
  _gateModel = await Backend.get_gate_model();
  const model = _gateModel;
  if (!model || !model.gates) return;
  const targetN = gateN != null ? gateN : model.current;
  _renderGateView(model, targetN);
}

// Role-based RD layout (2026-07-07): the flat RDxx list mixed three natures
// and read as "shapeless". Same files, same approval machinery — the GUI
// groups by what the engineer DOES with each doc and shows human names
// (the RD number stays as a small chip for traceability).
const RD_HUMAN = {
  RD01:"IO List", RD02:"Data Dictionary", RD03:"Logic Flow (AI analysis)",
  RD04:"Operating Modes", RD05:"Safety", RD06:"Motion / Axes",
  RD07:"Timing", RD08:"Alarms", RD09:"Communications",
  RD10:"FB Spec (legacy)", RD11:"HMI Tags", RD12:"Use Cases",
  RD13:"Legacy Annotation", RD14:"Modernization Map",
};
// work = engineer edits a grid · sign = named sign-off · ref = read & approve
const RD_ROLE = { RD01:"work", RD08:"work", RD11:"work", RD05:"sign" };
const RD_ROLE_HEADERS = {
  work: "📝 Worksheets — edit here",
  sign: "🛡 Sign-off required",
  ref:  "📖 Analysis & reference — read, then approve (bulk-locked at Gate 3)",
};

// Reading overlay for analysis RDs — rendered MD, no editor chrome.
async function openRdReadingView(rdId, path) {
  const f = await Backend.read_file(path);
  if (!f || !f.text) { toast("Could not read " + rdId); return; }
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "rdread-overlay";
  ov.innerHTML = `<div class="settings-modal" style="width:760px;max-height:86vh;display:flex;flex-direction:column">
    <div class="sm-head"><span class="ic" data-i="file-text" data-s="14"></span>
      ${escapeHtml(RD_HUMAN[rdId]||rdId)}
      <span style="font-family:var(--mono,monospace);font-size:9px;color:var(--fg-dim);border:1px solid var(--border);border-radius:3px;padding:1px 4px;margin-left:6px">${escapeHtml(rdId)}</span>
      <div class="fill"></div>
      <button class="btn ghost" id="rdread-src" style="font-size:11px">Open source file</button>
      <button class="btn" id="rdread-close" style="font-size:11px">Close</button>
    </div>
    <div class="sm-body rd-reading" style="overflow-y:auto;padding:14px 22px;line-height:1.55;font-size:13px">
      ${renderMarkdown(f.text)}
    </div>
  </div>`;
  document.body.appendChild(ov); injectIcons(ov);
  ov.addEventListener("click", (e)=>{ if (e.target === ov) ov.remove(); });
  ov.querySelector("#rdread-close").addEventListener("click", ()=>ov.remove());
  ov.querySelector("#rdread-src").addEventListener("click", ()=>{
    ov.remove(); setActivePage("explorer"); openFile(path);
  });
}

function _renderGateView(model, activeN) {
  const v = $("gate-view");
  const g = (model.gates||[]).find((x)=>x.n===activeN) || model.gates[0];
  if (!g) return;

  // Horizontal stepper
  const gates = model.gates || [];
  const stepperHtml = gates.map((mg, i) => {
    const isDone = mg.status === "done";
    const isCurrent = mg.status === "current";
    const isWarn = isCurrent && mg.needs_approval;
    const isActive = mg.n === activeN;
    let cc = "gvs-circle";
    let ci = mg.n;
    if (isDone)        { cc += " done"; ci = "✓"; }
    else if (isWarn)   { cc += " warn"; ci = "⚠"; }
    else if (isCurrent){ cc += " current"; }
    if (isActive) cc += " active-ring";
    const line = i < gates.length - 1
      ? `<div class="gvs-line${isDone?" done":""}"></div>` : "";
    return `<div class="gvs-step${isActive?" active":""}" data-n="${mg.n}">
      <div class="${cc}">${ci}</div>
      <div class="gvs-label"><div class="gvs-name">${escapeHtml(mg.name)}</div><div class="gvs-sub">${GATE_SUBTITLES[mg.n]||""}</div></div>
    </div>${line}`;
  }).join("");

  // Progress block
  const current = model.current || 1;
  const pct     = model.gate_pct ?? (model.overall_pct != null ? Math.round(model.overall_pct) : Math.round((current - 1) / 7 * 100));
  const docPct  = model.doc_pct != null ? model.doc_pct : null;
  const segHtml = Array.from({length: 7}, (_, i) =>
    `<div class="gvs-seg${i < current ? " on" : ""}"></div>`).join("");

  const approvalBadge = g.needs_approval
    ? `<span class="gate-approval-badge pulse">${svg("alert",12)} Approval Required</span>` : "";

  // Docs — 3-state verification (draft 🟡 → reviewed 🟢 → locked 🔒),
  // grouped by role: worksheets / sign-off / reference (2026-07-07).
  const _docRow = (d) => {
    const ui = d.ui_state || "draft";
    const b  = RD_REVIEW_BADGE[ui] || RD_REVIEW_BADGE.draft;
    const who = d.reviewed_by
      ? `${escapeHtml(d.reviewed_by)}${d.reviewed_at? " · "+escapeHtml(d.reviewed_at):""}` : "";
    let ctrl = "";
    if (ui === "na") {
      const rsn = d.na_reason ? ` — ${escapeHtml(d.na_reason)}` : "";
      ctrl = `<span class="rd-rev-meta" title="Not Applicable${rsn}">⊘</span>`
           + `<button class="rd-unna" data-rd="${d.rd}" title="Clear N/A">↺</button>`;
    } else if (ui === "locked") {
      ctrl = d.auto_accepted
        ? `<span class="rd-rev-meta rd-auto" title="Auto-accepted at the Gate-3 lock — NOT human-reviewed. Unlock happens automatically if the file is edited.">🔒<small>auto</small></span>`
        : `<span class="rd-rev-meta" title="Locked at Gate 3${who?" — "+who:""}">🔒</span>`;
    } else if (ui === "reviewed") {
      ctrl = `<button class="rd-unreview" data-rd="${d.rd}" title="Reviewed by ${who} — click to re-open">↺</button>`;
    } else if (ui === "empty") { // nothing produced → can only mark N/A
      // B-06: platform-based suggestion — old machines often have no HMI
      // export / operator manual; say so instead of implying a missing input.
      ctrl = d.na_hint
        ? `<button class="rd-na rd-na-suggested" data-rd="${d.rd}" title="${escapeHtml(d.na_hint)}">⊘ N/A suggested</button>`
        : `<button class="rd-na" data-rd="${d.rd}" title="Mark Not Applicable">⊘ N/A</button>`;
    } else { // draft or stale → approve, or mark N/A
      ctrl = `<button class="rd-verify" data-rd="${d.rd}" title="Engineer pre-approval (turn green)">${svg("check",11)} Approve</button>`
           + `<button class="rd-na" data-rd="${d.rd}" title="${escapeHtml(d.na_hint||"Mark Not Applicable")}">⊘${d.na_hint?" N/A?":""}</button>`;
    }
    const tip = d.author ? `Generated by: ${escapeHtml(d.author)}` : `Open ${d.rd}`;
    const role = RD_ROLE[d.rd] || "ref";
    const icon = role === "work" ? "table" : role === "sign" ? "check" : "file-text";
    return `<div class="gv-doc-row" data-rd="${d.rd}" data-rd-role="${role}" data-rd-path="${escapeHtml(d.path||'')}" title="${escapeHtml(tip)}">
      <span class="ic" data-i="${icon}" data-s="12"></span>
      <span>${escapeHtml(RD_HUMAN[d.rd]||d.rd)}</span>
      <span style="font-family:var(--mono,monospace);font-size:9px;color:var(--fg-dim);border:1px solid var(--border);border-radius:3px;padding:0 4px">${d.rd}</span>
      <span class="badge ${b.cls}" style="margin-left:auto">${b.label}</span>${ctrl}</div>`;
  };
  const _byRole = { work: [], sign: [], ref: [] };
  (g.docs||[]).forEach((d) => _byRole[RD_ROLE[d.rd] || "ref"].push(d));
  const docsHtml = ["work", "sign", "ref"].map((role) => {
    const docs = _byRole[role];
    if (!docs.length) return "";
    return `<div class="gv-doc-role-head" style="font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--fg-dim);margin:10px 0 4px;display:flex;align-items:center;gap:8px">
        <span>${RD_ROLE_HEADERS[role]}</span><span style="flex:1;height:1px;background:var(--border)"></span></div>`
      + docs.map(_docRow).join("");
  }).join("");
  // Review summary (Gate 3 = the bulk lock). Vites-2 (risk-based): the lock
  // waits only for the CRITICAL RDs (RD01/RD03/RD05); the rest are stamped
  // auto-accepted by the lock — said out loud, never silently.
  const rs = model.review_summary || {};
  const _lockReady = rs.lock_ready !== undefined ? rs.lock_ready : rs.all_reviewed;
  const _autoList = rs.auto_accept_on_lock || [];
  const reviewBanner = (g.n === 3 && rs.produced)
    ? `<div class="gv-review-summary${_lockReady?" ready":""}">
        ${_lockReady
          ? `${svg("check",13)} <strong>${rs.reviewed}/${rs.produced} RDs approved</strong> — critical set (RD01/RD03/RD05) is green; Human Review can be locked and Code Generation unlocked.`
          : `${svg("alert",13)} <strong>${rs.reviewed}/${rs.produced} RDs approved</strong> — critical approvals pending: ${(rs.critical_pending||rs.unreviewed||[]).join(", ")}`}
        ${_autoList.length?`<br><span style="color:var(--fg-dim)">Locking will auto-accept the remaining drafts: ${_autoList.join(", ")} — review any of them first if you want a human check on record.</span>`:""}
        ${(rs.stale&&rs.stale.length)?`<br><span style="color:var(--warning)">⚠ Changed after approval, must be re-approved: ${rs.stale.join(", ")}</span>`:""}
       </div>` : "";
  const actionsHtml = (g.actions||[]).map((aid) =>
    `<div class="action" data-id="${aid}" title="${escapeHtml(ACTION_HINTS[aid]||"")}"><span class="ic" data-i="${ACTION_ICONS[aid]||"play"}" data-s="13"></span><span>${ACTION_LABELS[aid]||aid}</span></div>`
  ).join("");

  const isCurrent = g.status === "current";
  const nextName  = isCurrent && g.n < 7 ? GATE_NAMES[g.n] : "";
  const advanceLabel = g.n === 3
    ? `🔒 Lock all RDs &amp; proceed to Code Generation`
    : `${svg("arrow-right",14)} Complete &amp; advance to Gate ${g.n + 1} — ${escapeHtml(nextName)}`;
  const advanceRow = isCurrent && g.n < 7
    ? `<div class="gv-advance-row">
        <button class="btn primary" id="gv-advance-btn">
          ${advanceLabel}
        </button>
       </div>` : "";

  // Generation labels routed by project_type (retrofit extract / greenfield design)
  const _isGreenfield = (model.project_type || "retrofit") === "greenfield";
  const g1Label = _isGreenfield ? "Greenfield Discovery" : "Retrofit Pre-Analysis";
  const g2Label = _isGreenfield ? "Greenfield Topic Design" : "Topic Extraction";
  // Gate 1: Discovery panel (async, filled after render)
  const retrofitPanel = (g.n === 1)
    ? `<div class="raw-panel" id="raw-panel">
        <div class="caps" style="margin-bottom:8px">
          ${svg("package",13)} ${g1Label}
        </div>
        <div id="raw-status" class="raw-status-row">
          <span class="fg-dim" style="font-size:12px">Scanning _raw/ folder…</span>
        </div>
        <div id="raw-progress" class="raw-progress" style="display:none"></div>
      </div>` : "";

  // Gate 2: Topic Extraction panel — generates RD04-12,14 + RD05 from the
  // legacy code + the APPROVED Gate-1 analysis. Locked until Gate-1 is green.
  const _g1 = (model.gates || []).find((x) => x.n === 1);
  const _g1docs = _g1 ? (_g1.docs || []) : [];
  // Vites-2 (risk-based): topic generation waits only for the CRITICAL
  // Gate-1 outputs (RD01 IO list, RD03 flowchart); RD02/RD13 join as drafts.
  const _g1crit = _g1docs.filter((d) => d.critical && d.ui_state !== "na");
  const _g1ready = _g1crit.length > 0 &&
    _g1crit.every((d) => d.ui_state === "reviewed" || d.ui_state === "locked");
  const _g1pending = _g1crit
    .filter((d) => !(d.ui_state === "reviewed" || d.ui_state === "locked"))
    .map((d) => d.rd);
  const topicPanel = (g.n === 2)
    ? `<div class="raw-panel" id="topic-panel">
        <div class="caps" style="margin-bottom:8px">${svg("sparkles",13)} ${g2Label} (Gate 2)</div>
        <div style="font-size:12px;color:var(--fg-dim);margin-bottom:8px">
          ${_isGreenfield
            ? "Designs RD04–RD12 and RD05 (Safety) from the functional spec and the <b>approved</b> Gate-1 design (IO list, data dictionary, logic flow)."
            : "Generates RD04–RD12, RD14 and RD05 (Safety) from the legacy code and the <b>approved</b> Gate-1 analysis (IO list, data dictionary, logic flow, annotation)."}</div>
        ${_g1ready
          ? `<button class="btn primary" id="topic-start-btn">${svg("sparkles",13)} Start ${g2Label}</button>`
          : `<div class="sm-hint" style="color:var(--warning);font-size:12px">⚠ Approve the critical Gate-1 outputs first${_g1pending.length?` (pending: ${_g1pending.join(", ")})`:""}. Open Gate 1, approve RD01 (IO list) and RD03 (logic flow), then return here.</div>`}
        <div id="topic-progress" class="raw-progress" style="display:none;margin-top:8px"></div>
      </div>` : "";

  // B-10: Gate 5's validator is STRUCTURAL only (keyword/parenthesis
  // balance) — without this notice a clean result reads like "compiles",
  // and the engineer meets the real errors first inside TIA.
  const validationScopePanel = (g.n === 5)
    ? `<div class="raw-panel" id="val-scope-panel" style="border-color:var(--warning)">
        <div class="caps" style="margin-bottom:6px;color:var(--warning)">${svg("alert",13)} What this gate checks — and what it does NOT</div>
        <div style="font-size:12px;line-height:1.55;color:var(--fg-dim)">
          The built-in SCL validator is <b>structural only</b>: keyword balance, parentheses,
          empty bodies. It does <b>not</b> check types, UDTs, FB interfaces or semantics —
          a clean result here is <b>not</b> a TIA compile. The first real compile happens at
          Gate 6 (Openness bridge) or when you import the sources into TIA manually.
        </div>
      </div>` : "";

  // Staleness banner: RDs edited after the last gate approval (advisory —
  // the gate does not regress, but the engineer must re-validate).
  const staleRds = Array.isArray(model.stale_rds) ? model.stale_rds : [];
  const staleBanner = staleRds.length
    ? `<div class="gv-stale-banner" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0;padding:8px 12px;border:1px solid var(--warning);border-radius:6px;background:rgba(251,191,36,.08);font-size:12px">
        <span class="ic" data-i="alert" data-s="13" style="color:var(--warning)"></span>
        <strong style="color:var(--warning)">Changed after approval — re-validate:</strong>
        ${staleRds.map((s)=>`<span class="badge warn" title="${escapeHtml(s.change)} after Gate ${s.gate} (${escapeHtml(s.when||"")})">${escapeHtml(s.rd_file)}</span>`).join("")}
       </div>` : "";

  const gateActionsHtml = `
    <button class="btn" id="gv-from-library-btn" title="Import a frozen library FB into this project">${svg("package",12)} From Library</button>
    ${approvalBadge}`;
  v.innerHTML = `<div class="page-inner">
    ${pageHeader({backId:"gv-back", icon:"chip", title:`Gate ${g.n}/7 — ${escapeHtml(g.name)}`, subtitle:GATE_SUBTITLES[g.n]||"", actionsHtml: gateActionsHtml})}
    <div class="gv-stepper">
      <div class="gvs-steps">${stepperHtml}</div>
      <div class="gvs-progress">
        <div class="gvs-pnum">GATE ${g.n}/7</div>
        <div class="gvs-pname">${escapeHtml(g.name)}</div>
        <div class="gvs-bar">${segHtml}</div>
        <div class="gvs-pct">${pct}%${docPct != null ? `<span style="font-size:10px;color:var(--fg-dim);margin-left:8px">Docs: ${docPct}%</span>` : ""}</div>
      </div>
    </div>
    ${staleBanner}
    ${reviewBanner}
    <div class="gv-body">
      <div class="gv-col"><div class="caps" style="margin-bottom:8px" title="RD = Requirement Document — the 14-Point requirements pack (RD01–RD14) that drives code generation">RD Documents</div>
        <div class="gv-docs">${docsHtml||`<div style="color:var(--fg-dim);font-size:12px;line-height:1.5">This gate owns no RD documents — the 14-point pack lives in Gates 1–2.<br>It advances on ${g.needs_approval?"an engineer sign-off":"evidence"} (see Actions / the panels below).</div>`}</div></div>
      <div class="gv-col"><div class="caps" style="margin-bottom:8px">Actions</div>
        <div class="gv-actions">${actionsHtml||'<div style="color:var(--fg-dim);font-size:12px">No actions</div>'}</div></div>
    </div>
    ${retrofitPanel}
    ${topicPanel}
    ${validationScopePanel}
    ${g.n === 3 ? `<div class="raw-panel" id="recon3-panel"><span class="fg-dim" style="font-size:12px">Running consistency checks (RD01 ↔ HMI ↔ dossier decisions)…</span></div>` : ""}
    ${(g.n === 3 || g.n === 4) ? `<div class="raw-panel" id="io-recon-panel"><span class="fg-dim" style="font-size:12px">Loading IO reconciliation…</span></div>` : ""}
    ${g.n === 4 ? `<div class="raw-panel" id="delta-panel"><span class="fg-dim" style="font-size:12px">Scanning RD01 changes…</span></div>` : ""}
    ${advanceRow}
    ${g.when?`<div class="gv-meta">Completed: ${escapeHtml(g.when)}${g.who?" · "+escapeHtml(g.who):""}</div>`:""}
  </div>`;

  hideViews(); v.classList.add("show"); injectIcons(v);
  // Scroll the active step into view
  const activeStep = v.querySelector(".gvs-step.active");
  if (activeStep) activeStep.scrollIntoView({behavior:"smooth", block:"nearest", inline:"center"});
  v.querySelector("#gv-back").addEventListener("click", ()=>setActivePage("explorer"));
  // Select from Library — import a frozen block into the current project
  const fromLibBtn = v.querySelector("#gv-from-library-btn");
  if (fromLibBtn) fromLibBtn.addEventListener("click", ()=>{
    toast("Select from Library: go to Block Library, choose a FROZEN or VERIFIED block, click Import.");
    logLine("[project-production] Select from Library → Block Library → Import to project", "info");
    setActivePage("library");
  });
  v.querySelectorAll(".gvs-step").forEach((el) => el.addEventListener("click", () => {
    const n = parseInt(el.getAttribute("data-n")); if (n) _renderGateView(model, n);
  }));
  v.querySelectorAll(".gv-doc-row").forEach((el) => el.addEventListener("click", async () => {
    const rd     = el.getAttribute("data-rd");
    const rdRole = el.getAttribute("data-rd-role");
    const rdPath = el.getAttribute("data-rd-path");
    // Reference docs open in the reading view (rendered MD, no editor
    // chrome) — the raw editor stays one click away inside the overlay.
    if (rdRole === "ref" && rdPath) { openRdReadingView(rd, rdPath); return; }
    if (rdPath) {
      const ci = OPEN_TABS.findIndex(t => t.path === rdPath);
      if (ci !== -1) OPEN_TABS.splice(ci, 1);
      setActivePage("explorer");
      openFile(rdPath);
    } else {
      // Fallback: ask backend to locate the file on disk now
      const res = await Backend.find_rd_file(rd);
      if (res && res.found && res.path) {
        const ci = OPEN_TABS.findIndex(t => t.path === res.path);
        if (ci !== -1) OPEN_TABS.splice(ci, 1);
        setActivePage("explorer");
        openFile(res.path);
      } else {
        toast(`${rd} ${t("dlg.rd_no_metadata")}`);
      }
    }
  }));
  // Engineer pre-approval (🟡 → 🟢). RD05 (Safety) demands a named sign-off.
  async function _refreshGate() {
    _gateModel = await Backend.get_gate_model();
    renderGateNavBar();
    _renderGateView(_gateModel, activeN);
  }
  v.querySelectorAll(".rd-verify").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const rd = btn.getAttribute("data-rd");
    let sig = "";
    if (rd === "RD05") {
      sig = (window.prompt(
        "RD05 (Safety) approval requires a certified-engineer sign-off.\n" +
        "Enter name / role (e.g. 'H. Becker, TÜV'):"
      ) || "").trim();
      if (!sig) { toast("RD05 approval cancelled — signature required"); return; }
    }
    btn.disabled = true;
    const r = await Backend.review_rd(rd, sig);
    if (r && r.ok) {
      toast(`${rd} approved${r.reviewed_by? " · "+r.reviewed_by:""}`);
      await _refreshGate();
    } else {
      toast((r && r.msg) || `${rd} could not be approved`); btn.disabled = false;
    }
  }));
  v.querySelectorAll(".rd-unreview").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const rd = btn.getAttribute("data-rd");
    const r = await Backend.unreview_rd(rd);
    if (r && r.ok) { toast(`${rd} approval reverted`); await _refreshGate(); }
  }));
  v.querySelectorAll(".rd-na").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const rd = btn.getAttribute("data-rd");
    const isSafety = rd === "RD05";
    const reason = (window.prompt(isSafety
      ? "RD05 (Safety) N/A requires a NAMED safety-engineer justification\n(e.g. 'No safety functions in scope — H. Becker, TÜV'):"
      : `Mark ${rd} Not Applicable — short reason (e.g. 'no HMI on this machine'):`) || "").trim();
    if (!reason) { toast("N/A cancelled — reason required"); return; }
    const r = await Backend.mark_rd_na(rd, reason);
    if (r && r.ok) { toast(`${rd} marked N/A`); await _refreshGate(); }
    else toast((r && r.msg) || `${rd} N/A failed`);
  }));
  v.querySelectorAll(".rd-unna").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const rd = btn.getAttribute("data-rd");
    const r = await Backend.unmark_rd_na(rd);
    if (r && r.ok) { toast(`${rd} N/A cleared`); await _refreshGate(); }
  }));
  v.querySelectorAll(".gv-actions .action").forEach((el) => el.addEventListener("click", () => {
    setActivePage("explorer"); runAction(el.getAttribute("data-id"));
  }));
  const advBtn = v.querySelector("#gv-advance-btn");
  if (advBtn) {
    advBtn.addEventListener("click", async () => {
      // Approval gates (Human Review / Simulation / FAT-SAT) require a sign-off.
      let sig = "";
      if (g.needs_approval) {
        sig = (window.prompt(
          `Gate ${g.n} — ${g.name} requires human approval.\n` +
          `Enter approver name / signature:`
        ) || "").trim();
        if (!sig) { toast("Approval cancelled — signature required"); return; }
      }
      // B-P2: Gate 6 (Simulation) requires compile log path + manual-test declaration.
      let compileLogPath = "";
      let manualTestConfirmed = false;
      if (g.n === 6) {
        const g6 = await _promptCompileLog();
        if (!g6) { toast("Gate 6 advance cancelled"); return; }
        compileLogPath = g6.compileLogPath;
        manualTestConfirmed = g6.manualTestConfirmed;
      }
      advBtn.disabled = true; advBtn.textContent = "Advancing…";
      let r = await Backend.advance_gate(sig, false, compileLogPath, manualTestConfirmed);
      // W-A5: the only blocker the engineer may knowingly override from the UI
      // is "validation was structural-only". Re-prompt and retry with the
      // explicit acknowledgement; every other blocker stays hard.
      const structuralOnly = !!(r && !r.ok && Array.isArray(r.blockers)
        && r.blockers.some((b) => b && b.includes("accept_structural_only")));
      if (structuralOnly) {
        const ok = window.confirm(
          "Validation was structural-only (keyword/parenthesis balance) — no TIA compile " +
          "was run, semantic errors may be uncaught.\n\n" +
          "Accept this gap and advance anyway?"
        );
        if (ok) r = await Backend.advance_gate(sig, true, compileLogPath, manualTestConfirmed);
      }
      if (r && r.ok) {
        toast(`Gate ${r.gate - 1} completed → Gate ${r.gate}: ${r.name}`);
        await refreshProjectState();  // every gate display from one fetch
        await showGateView(r.gate);
      } else {
        const msg = (r && r.blockers && r.blockers.length)
          ? r.blockers.join(" • ")
          : ((r && r.msg) || "Could not advance gate");
        toast(msg);
        advBtn.disabled = false; advBtn.innerHTML = `${svg("arrow-right",14)} Complete &amp; advance`;
      }
    });
  }

  // Gate 1: load _raw/ status and wire the discovery generator button
  if (g.n === 1) {
    _loadRawFolderStatus(v, g1Label);
  }
  // Gate 2: wire Topic Extraction button (enabled only when Gate 1 is approved)
  if (g.n === 2) {
    const tb = v.querySelector("#topic-start-btn");
    if (tb) tb.addEventListener("click", async () => {
      const status = await Backend.get_raw_folder_status();
      const provInfo = await Backend.get_provider_for_task("preanalysis");
      const lang = (await Backend.get_output_language()).language || "EN";
      _openRetrofitConsentModal(
        status, provInfo.provider || "anthropic",
        v.querySelector("#topic-progress"), "topic", lang,
        provInfo.warning || "");
    });
  }
  // Gate 3: Reconciliation & Preview — cross-artifact deviations, each
  // resolved by "go back & fix" or a named conscious-choice waiver; RED
  // (safety baseline) findings gate the lock unconditionally.
  if (g.n === 3) { _loadGate3Recon(v); }
  // Gate 3/4: IO reconciliation report (provenance + missing/extra), validated
  // by the engineer before code generation.
  if (g.n === 3 || g.n === 4) { _loadIoReconciliation(v); }
  // Gate 4: change management — RD01 delta vs the last assembly manifest,
  // with a "Regenerate affected" that leaves untouched devices' files alone.
  if (g.n === 4) { _loadRegenDelta(v); }
}

async function _loadRegenDelta(container) {
  const host = container.querySelector("#delta-panel");
  if (!host) return;
  const d = await Backend.get_regen_delta();
  if (!d.ok) { host.innerHTML = `<span class="fg-dim" style="font-size:12px">${escapeHtml(d.msg||"Delta scan unavailable")}</span>`; return; }
  const chips = (list, cls, label) => list.length
    ? `<span class="badge ${cls}" title="${escapeHtml(list.join(", "))}">${label}: ${list.length}</span>` : "";
  const total = (d.added||[]).length + (d.changed||[]).length + (d.removed||[]).length;
  if (!d.manifest_exists) {
    host.innerHTML = `
      <div class="caps" style="margin-bottom:6px">${svg("refresh",13)} Change management</div>
      <div style="font-size:12px;color:var(--fg-dim)">No assembly baseline yet — run <b>Assemble Program</b> once; after that, RD01 edits (e.g. adding one motor) can be regenerated selectively here.</div>`;
    injectIcons(host);
    return;
  }
  host.innerHTML = `
    <div class="caps" style="margin-bottom:6px">${svg("refresh",13)} Change management — RD01 vs last assembly (${escapeHtml(d.generated_at||"")})</div>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:12px">
      ${total === 0
        ? `<span class="fg-dim">No device changes since the last assembly.</span>`
        : `${chips(d.added||[], "ok", "new")} ${chips(d.changed||[], "warn", "changed")} ${chips(d.removed||[], "err", "removed")}
           <button class="btn primary" id="delta-regen-btn" style="margin-left:auto;font-size:12px"
             title="Regenerates only the new/changed devices' instance DBs + rebuilds OB_Main. Untouched devices' files stay byte-for-byte the same; removed devices are reported, never deleted.">
             ${svg("refresh",12)} Regenerate affected (${(d.added||[]).length + (d.changed||[]).length})</button>`}
    </div>`;
  injectIcons(host);
  const btn = host.querySelector("#delta-regen-btn");
  if (btn) btn.addEventListener("click", async () => {
    btn.disabled = true; btn.textContent = "Regenerating…";
    const r = await Backend.run_delta_assembly();
    logSep("delta assembly");
    (String(r.output||"").split("\n")).slice(0,80).forEach(ln => logLine(ln, r.ok?"info":"warn"));
    switchBottomTab("terminal");
    toast(r.ok ? `Delta assembly done — ${(r.affected||[]).length} device(s) regenerated` : "Delta assembly failed — see terminal");
    await refreshProjectState();
    _loadRegenDelta(container);
  });
}

/* Gate-3 "Reconciliation & Preview" — management by exception: ONLY the
   deviations are listed; consistent facts collapse into a counter. Every
   deviation exits through "go back & fix" (jump to the owning grid) or a
   "conscious choice" waiver (reason + name, permanent, lands in the
   traceability matrix). RED = safety baseline (EN ISO 13850) — no waiver,
   no signature, the only exit is to fix it. The bulk-lock button stays
   disabled until the list is clean or fully waived (backend enforces too). */
const _G3_CHECK_LABELS = {
  orphan_hmi_ref:          "HMI tags reference live RD01 IO rows",
  pulpit_without_tag:      "every pulpit element has an HMI tag",
  decision_not_propagated: "dossier DROP decisions propagated to the tags",
  semantic_change:         "device classes stable (no Y-Δ→VFD drift)",
  safety_on_hmi:           "no E-stop function on the HMI (EN ISO 13850)",
};

async function _loadGate3Recon(container) {
  const host = container.querySelector("#recon3-panel");
  if (!host) return;
  const r = await Backend.get_gate3_consistency();
  const advBtn = container.querySelector("#gv-advance-btn");
  if (!r || !r.ok) {
    host.innerHTML = `<span class="fg-dim" style="font-size:12px">Reconciliation: ${escapeHtml((r&&r.msg)||"not available")}</span>`;
    return;
  }
  const open   = (r.findings||[]).filter((f)=>!f.waived);
  const waived = (r.findings||[]).filter((f)=>f.waived);
  const consistent = r.consistent || {};
  const consistentTotal = Object.values(consistent).reduce((a,b)=>a+(b||0),0);
  // The bulk-lock button obeys the reconciliation verdict (backend re-checks).
  if (advBtn) {
    advBtn.disabled = !r.lock_ready;
    advBtn.title = r.lock_ready ? ""
      : `${r.unresolved} unresolved finding(s) — fix them or record a conscious choice first`;
  }
  const sevChip = (f) =>
    f.severity === "red"     ? `<span class="badge err" title="Safety baseline — cannot be waived">⛔ RED</span>`
    : f.severity === "pending" ? `<span class="badge warn">✍ signature pending</span>`
    :                          `<span class="badge warn">deviation</span>`;
  const findingRow = (f) => `
    <div class="g3-finding" style="border:1px solid ${f.severity==="red"?"var(--error)":"var(--border)"};border-radius:6px;padding:8px 10px;margin-top:6px${f.severity==="red"?";background:rgba(239,68,68,.06)":""}">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        ${sevChip(f)}<strong style="font-size:12.5px">${escapeHtml(f.title||"")}</strong>
      </div>
      <div style="font-size:12px;color:var(--fg-dim);margin:4px 0 8px;line-height:1.5">${escapeHtml(f.detail||"")}</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button class="btn g3-fix" style="font-size:12px" data-target="${escapeHtml(f.fix_target||"")}">↩ Go back &amp; fix</button>
        ${f.severity === "red"
          ? `<span style="font-size:11px;color:var(--error)">EN ISO 13850 — the safety baseline bends for no signature; the only exit is to fix it.</span>`
          : (f.waivable ? `<button class="btn ghost g3-waive" style="font-size:12px" data-id="${escapeHtml(f.id)}" title="Reason + name required; permanent; recorded in the traceability matrix">✍ Conscious choice (waive)…</button>` : "")}
      </div>
    </div>`;
  const statusChip = r.lock_ready
    ? `<span class="badge ok">✓ clean — the lock is available</span>`
    : `<span class="badge ${r.red?"err":"warn"}">${r.unresolved} unresolved${r.red?` · ${r.red} RED`:""}</span>`;
  const consistentHtml = `
    <details style="margin-top:8px"><summary style="font-size:12px;color:var(--success);cursor:pointer">✓ ${consistentTotal} consistent fact(s) — collapsed (management by exception)</summary>
      <div style="font-size:11.5px;color:var(--fg-dim);padding:6px 0 0 14px;line-height:1.6">
        ${Object.entries(consistent).map(([k,n])=>`${n} × ${escapeHtml(_G3_CHECK_LABELS[k]||k)}`).join("<br>")||"—"}
        ${(r.skipped||[]).length?`<br><span style="color:var(--warning)">Skipped (source data absent): ${r.skipped.map(escapeHtml).join(" · ")}</span>`:""}
      </div>
    </details>`;
  const waivedHtml = waived.length ? `
    <details style="margin-top:4px"><summary style="font-size:12px;color:var(--fg-dim);cursor:pointer">✍ ${waived.length} conscious choice(s) on record — never asked again</summary>
      <div style="font-size:11.5px;color:var(--fg-dim);padding:6px 0 0 14px;line-height:1.6">
        ${waived.map((f)=>`<div>• ${escapeHtml(f.title||"")} — <em>${escapeHtml((f.waiver&&f.waiver.reason)||"")}</em> (${escapeHtml((f.waiver&&f.waiver.by)||"")}, ${escapeHtml((f.waiver&&f.waiver.at)||"")})</div>`).join("")}
      </div>
    </details>` : "";
  host.innerHTML = `
    <div class="caps" style="margin-bottom:8px;display:flex;gap:8px;align-items:center">${svg("shield",13)} Reconciliation &amp; Preview — Gate-3 lock ${statusChip}</div>
    ${open.length
      ? open.map(findingRow).join("")
      : `<div style="font-size:12px;color:var(--success)">No open deviations — every cross-artifact fact agrees${waived.length?` (${waived.length} waived)`:""}.</div>`}
    ${waivedHtml}
    ${consistentHtml}`;
  injectIcons(host);
  host.querySelectorAll(".g3-fix").forEach((b)=>b.addEventListener("click", async ()=>{
    const tgt = b.getAttribute("data-target") || "";
    if (tgt === "rd11")      { setActivePage("explorer"); openFile("metadata/RD11_HMI.md"); }
    else if (tgt === "rd08") { setActivePage("explorer"); openFile("metadata/RD08_Alarm.md"); }
    else if (tgt === "rd01") {
      const res = await Backend.find_rd_file("RD01");
      if (res && res.found && res.path) { setActivePage("explorer"); openFile(res.path); }
      else toast("RD01 file not found");
    }
    else if (tgt === "dossier") { _dossierSel = "04_decision_table.xlsx"; showFlowchartView(); }
    else if (tgt.startsWith("review:")) {
      const rd = tgt.split(":")[1];
      const row = container.querySelector(`.gv-doc-row[data-rd="${rd}"]`);
      if (row) {
        row.scrollIntoView({behavior:"smooth", block:"center"});
        row.style.outline = "2px solid var(--warning)";
        setTimeout(()=>{ row.style.outline = ""; }, 2200);
      }
      toast(`Approve ${rd} in the RD Documents list above`);
    }
  }));
  host.querySelectorAll(".g3-waive").forEach((b)=>b.addEventListener("click", async ()=>{
    const id = b.getAttribute("data-id");
    const reason = (window.prompt(
      "Conscious choice — record WHY this deviation is accepted.\n" +
      "The waiver is permanent (asked once) and lands in the traceability matrix.\n\nReason:")||"").trim();
    if (!reason) { toast("Waiver cancelled — reason required"); return; }
    const name = (window.prompt(
      "Name / role of the engineer taking this decision\n(e.g. 'H. Becker, Inbetriebnahme'):")||"").trim();
    if (!name) { toast("Waiver cancelled — name required"); return; }
    const wr = await Backend.waive_gate3_finding(id, reason, name);
    if (wr && wr.ok) { toast("Recorded as a conscious choice — it will not be asked again"); _loadGate3Recon(container); }
    else toast((wr&&wr.msg)||"Waiver refused");
  }));
}

async function _loadIoReconciliation(container) {
  const host = container.querySelector("#io-recon-panel");
  if (!host) return;
  const r = await Backend.get_io_reconciliation();
  if (!r || !r.ok) {
    host.innerHTML = `<span class="fg-dim" style="font-size:12px">IO reconciliation: ${escapeHtml((r&&r.msg)||"RD01 not available")}</span>`;
    return;
  }
  const rep = r.report || {};
  const bySrc = Object.entries(rep.by_source || {})
    .map(([s,n]) => `<span class="raw-cat-badge">${escapeHtml(s)}: ${n}</span>`).join("");
  const dupCount = Object.keys(rep.duplicate_addresses || {}).length;
  const chip = (label, n, cls) => `<span class="badge ${cls}" title="${label}">${label}: ${n}</span>`;
  const ackState = r.acknowledged
    ? `<span class="badge ok">✓ validated${r.ack&&r.ack.by?" · "+escapeHtml(r.ack.by):""}</span>`
    : (r.stale_ack ? `<span class="badge warn">⚠ RD01 changed — re-validate</span>` : `<span class="badge warn">not validated</span>`);
  const secHtml = Object.entries(r.sections || {})
    .map(([h,b]) => `<details style="margin-top:4px"><summary style="font-size:11px;color:var(--fg-dim)">${escapeHtml(h)}</summary><pre style="white-space:pre-wrap;font-size:11px;margin:4px 0">${escapeHtml(b).slice(0,1200)}</pre></details>`).join("");
  host.innerHTML = `
    <div class="caps" style="margin-bottom:8px">${svg("table",13)} IO Reconciliation (RD01) ${ackState}</div>
    <div class="raw-file-badges" style="margin-bottom:6px">${bySrc||'<span class="fg-dim" style="font-size:12px">no Source column</span>'}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
      ${chip("signals", rep.total||0, "mod")}
      ${chip("new (not in legacy)", (rep.new_signals||[]).length, "mod")}
      ${chip("orphan (legacy only)", (rep.orphan_signals||[]).length, "warn")}
      ${chip("ghost (no addr/legacy)", (rep.ghost_rows||[]).length, "warn")}
      ${chip("duplicate addresses", dupCount, dupCount? "warn":"ok")}
      ${chip("safety", rep.safety||0, "ok")}
    </div>
    ${secHtml}
    <button class="btn ${r.acknowledged?"":"primary"}" id="io-recon-ack" style="margin-top:8px">
      ${svg("check",12)} ${r.acknowledged?"Re-validate IO reconciliation":"Validate IO reconciliation"}
    </button>`;
  injectIcons(host);
  const ackBtn = host.querySelector("#io-recon-ack");
  if (ackBtn) ackBtn.addEventListener("click", async () => {
    const note = window.prompt("Validate the IO reconciliation (provenance, missing/extra, conflicts).\nOptional note:");
    if (note === null) return;  // cancelled
    const ar = await Backend.ack_io_reconciliation(note.trim());
    if (ar && ar.ok) { toast("IO reconciliation validated"); _loadIoReconciliation(container); }
    else toast((ar&&ar.msg)||"Validation failed");
  });
}

async function _loadRawFolderStatus(container, startLabel = "Retrofit Pre-Analysis") {
  const statusEl   = container.querySelector("#raw-status");
  const progressEl = container.querySelector("#raw-progress");
  if (!statusEl) return;
  const status = await Backend.get_raw_folder_status();
  if (!status.ok) { statusEl.innerHTML = `<span class="fg-dim" style="font-size:12px">_raw/ folder not found — create it to use pre-analysis</span>`; return; }

  const cats = status.by_category || {};
  const badges = Object.entries(cats)
    .filter(([,files]) => files.length > 0)
    .map(([cat, files]) => `<span class="raw-cat-badge">${cat}: ${files.length}</span>`)
    .join("");
  const provInfo = await Backend.get_provider_for_task("preanalysis");
  const provLabel = provInfo.provider || "anthropic";

  // Direct .s5d import (2026-07-06): converts the Step5 binary to AWL in
  // _raw/legacy_code — no S5-für-Windows export needed. Offered in BOTH
  // states; the empty-folder state is exactly when you want it.
  const s5dBtn = `<button class="btn" id="raw-s5d-btn" style="margin-top:8px"
      title="Convert a Step5 binary project directly to AWL (proven instruction-identical vs a manual S5W export; timer constants recovered)">
      ${svg("upload",12)} Import Step5 binary (.s5d)…</button>`;

  if (status.total === 0) {
    statusEl.innerHTML = `<span class="fg-dim" style="font-size:12px">
      No files in _raw/ — add docs, drawings or photos to enable pre-analysis.</span>
      <div>${s5dBtn}</div>`;
    _wireS5dImport(container, () => _loadRawFolderStatus(container, startLabel));
    return;
  }

  statusEl.innerHTML = `
    <div class="raw-file-badges">${badges}</div>
    <div class="raw-info">${status.total} file${status.total!==1?"s":""} ready
      <span class="raw-provider-hint">· ${provLabel} recommended</span>
    </div>
    <div id="legacy-extract" style="margin-top:8px"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn primary" id="raw-start-btn" style="margin-top:8px">
        ${svg("sparkles",13)} Start ${escapeHtml(startLabel)}
      </button>
      ${s5dBtn}
    </div>`;

  container.querySelector("#raw-start-btn")?.addEventListener("click", async () => {
    const lang = (await Backend.get_output_language()).language || "EN";
    _openRetrofitConsentModal(status, provLabel, progressEl, "preanalysis", lang,
      provInfo.warning || "");
  });
  _wireS5dImport(container, () => _loadRawFolderStatus(container, startLabel));

  _renderLegacyExtraction(container);
}

function _wireS5dImport(container, refresh) {
  const btn = container.querySelector("#raw-s5d-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const pick = await Backend.browse_for_file("s5d");
    if (!(pick && pick.ok && pick.path)) return;
    btn.disabled = true; btn.textContent = "Converting…";
    const r = await Backend.import_s5d(pick.path);
    btn.disabled = false; btn.innerHTML = `${svg("upload",12)} Import Step5 binary (.s5d)…`;
    if (r && r.ok) {
      toast(r.msg || "Imported");
      if ((r.warnings||[]).length) {
        // warnings are engineer-relevant (skipped BB/DB, bare KT) — show
        // them, don't bury them in a toast
        alert("S5D import warnings (also in _raw/legacy_code/_s5d_import_info.md):\n\n" +
              r.warnings.join("\n"));
      }
      refresh();
      refreshProjectState();
    } else {
      toast((r && r.msg) || "S5D import failed");
    }
  });
}

// M1 — legacy-code PDF extraction review (Gate 1 panel)
async function _renderLegacyExtraction(container) {
  const host = container.querySelector("#legacy-extract");
  if (!host) return;
  const st = await Backend.get_legacy_extraction_status();
  if (!st.ok || !(st.items||[]).length) { host.innerHTML = ""; return; }

  const rows = st.items.map(it => {
    const q = it.quality ? ` · quality ${it.quality.score}/100` : "";
    let state, action = "";
    if (it.confirmed) {
      state = `<span style="color:var(--ok,#3a3)">✓ confirmed</span> <span class="fg-dim">(${escapeHtml(it.method||"")}${q})</span>`;
    } else if (it.extracted) {
      state = `<span style="color:var(--warn,#c90)">needs review</span> <span class="fg-dim">(${escapeHtml(it.method||"")}${q})</span>`;
      action = `<button class="btn ghost" data-review="${escapeHtml(it.name)}" style="font-size:11px;padding:2px 8px">Review &amp; confirm</button>`;
    } else {
      state = `<span class="fg-dim">not extracted</span>`;
    }
    return `<div style="display:flex;gap:8px;align-items:center;font-size:12px;margin:2px 0">
      <span style="flex:1">${escapeHtml(it.name)}</span>${state}${action}</div>`;
  }).join("");

  const needExtract = st.items.some(it => !it.extracted);
  host.innerHTML = `
    <div style="border:1px solid var(--border,#444);border-radius:6px;padding:8px 10px">
      <div style="font-size:12px;font-weight:600;margin-bottom:4px">Legacy code PDFs — text extraction</div>
      ${rows}
      <div class="fg-dim" style="font-size:11px;margin-top:4px">
        ⚠ Review the transcription before confirming — print/OCR confusions
        (O↔0, I↔1, B↔8) silently corrupt addresses like E 1.0.
      </div>
      ${needExtract ? `<button class="btn" id="legacy-extract-btn" style="margin-top:6px;font-size:12px">${svg("file-text",13)} Extract PDF text</button>` : ""}
    </div>`;

  host.querySelector("#legacy-extract-btn")?.addEventListener("click", async () => {
    const btn = host.querySelector("#legacy-extract-btn");
    btn.disabled = true; btn.textContent = "Extracting…";
    const r = await Backend.extract_legacy_pdfs({});
    const needsConsent = (r.results||[]).filter(x => x.status === "needs_ocr_consent");
    if (needsConsent.length) {
      _openOcrConsentModal(needsConsent.map(x => x.name), container);
    } else if (!r.ok) {
      toast(r.msg || "Extraction failed", "error");
    }
    _renderLegacyExtraction(container);
  });

  host.querySelectorAll("[data-review]").forEach(b => {
    b.addEventListener("click", () => _openExtractionReviewModal(b.dataset.review, container));
  });
}

function _openOcrConsentModal(names, container) {
  if ($("ocr-consent-overlay")) return;
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "ocr-consent-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:440px">
    <div class="sm-head">${svg("alert",14)} Scanned PDF — OCR Consent</div>
    <div class="sm-body">
      <p style="font-size:13px;margin-bottom:10px">These PDFs have no usable text layer.
        OCR sends the <b>full document, unanonymized,</b> to Gemini Vision (Google):</p>
      <ul style="font-size:12px;color:var(--fg-muted);margin-bottom:12px;padding-left:18px">
        ${names.map(n => `<li>${escapeHtml(n)}</li>`).join("")}</ul>
      <div class="sm-field" style="margin-bottom:8px">
        <label style="width:100px">Engineer</label>
        <input id="ocr-engineer" type="text" placeholder="Your name (required)" style="flex:1" value="${escapeHtml(STATE&&STATE.username||"")}" />
      </div>
      <label style="display:flex;gap:8px;align-items:flex-start;font-size:12px;cursor:pointer">
        <input id="ocr-confirm" type="checkbox" style="margin-top:2px" />
        I confirm I am authorised to send these documents to Google for transcription.
      </label>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="ocr-ok">Run OCR</button>
      <button class="btn ghost" id="ocr-cancel">Cancel</button>
      <span class="sm-hint" id="ocr-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#ocr-cancel").addEventListener("click", () => ov.remove());
  ov.addEventListener("click", e => { if (e.target === ov) ov.remove(); });
  q("#ocr-ok").addEventListener("click", async () => {
    const engineer = q("#ocr-engineer").value.trim();
    if (!engineer) { q("#ocr-hint").textContent = "Engineer name is required"; return; }
    if (!q("#ocr-confirm").checked) { q("#ocr-hint").textContent = "Please confirm the checkbox"; return; }
    q("#ocr-ok").disabled = true; q("#ocr-ok").textContent = "Running OCR…";
    if (STATE) STATE.username = engineer;
    Backend.save_settings({username: engineer});
    const r = await Backend.extract_legacy_pdfs({engineer, ocr_consent: true});
    ov.remove();
    const errs = (r.results||[]).filter(x => x.status === "error" || x.status === "blocked");
    if (errs.length) toast(errs.map(x => `${x.name}: ${x.msg}`).join(" • "), "error");
    else toast("OCR complete — review the transcriptions before confirming");
    _renderLegacyExtraction(container);
  });
}

async function _openExtractionReviewModal(pdfName, container) {
  if ($("extract-review-overlay")) return;
  const stem = pdfName.replace(/\.pdf$/i, "");
  const relPath = `_raw/legacy_code/${stem}.extracted.txt`;
  const file = await Backend.read_file(relPath);
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "extract-review-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:760px;width:90vw">
    <div class="sm-head">${svg("file-text",14)} ${escapeHtml(pdfName)} — extracted text review</div>
    <div class="sm-body">
      <div class="fg-dim" style="font-size:11.5px;margin-bottom:6px">
        Check addresses carefully (O↔0, I↔1, B↔8). Edit below, then confirm.
        Unconfirmed PDFs block Retrofit Pre-Analysis.
      </div>
      <textarea id="extract-text" spellcheck="false"
        style="width:100%;height:55vh;font-family:var(--mono,monospace);font-size:12px;white-space:pre">${escapeHtml(file.text||"")}</textarea>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="extract-confirm">Save &amp; Confirm</button>
      <button class="btn ghost" id="extract-cancel">Cancel</button>
      <span class="sm-hint" id="extract-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#extract-cancel").addEventListener("click", () => ov.remove());
  q("#extract-confirm").addEventListener("click", async () => {
    q("#extract-confirm").disabled = true;
    const r = await Backend.confirm_extracted_text(pdfName, q("#extract-text").value);
    if (r.ok) {
      ov.remove();
      toast(`${pdfName} extraction confirmed`);
      _renderLegacyExtraction(container);
    } else {
      q("#extract-hint").textContent = r.msg || "Confirm failed";
      q("#extract-confirm").disabled = false;
    }
  });
}

function _openRetrofitConsentModal(status, providerLabel, progressEl, mode = "preanalysis", currentLang = "EN", provWarning = "") {
  if ($("retrofit-consent-overlay")) return;
  const isTopic = mode === "topic";
  const _LANGS = [["TR","Türkçe"],["EN","English"],["DE","Deutsch"]];
  const langOptions = _LANGS.map(([c,n]) =>
    `<option value="${c}"${(currentLang||"EN")===c?" selected":""}>${n}</option>`).join("");
  const title = isTopic
    ? "Topic Extraction (Gate 2) — Data Sharing Consent"
    : "Retrofit Pre-Analysis — Data Sharing Consent";
  const startLabel = isTopic ? "Start Topic Extraction" : "Start Analysis";
  const cats = status.by_category || {};
  const fileList = Object.entries(cats)
    .filter(([,f]) => f.length)
    .map(([cat, files]) => `<li><b>${cat}:</b> ${files.slice(0,3).map(escapeHtml).join(", ")}${files.length>3?` +${files.length-3} more`:""}</li>`)
    .join("");

  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "retrofit-consent-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:480px">
    <div class="sm-head">${svg("alert",14)} ${title}</div>
    <div class="sm-body">
      <p style="font-size:13px;margin-bottom:12px">${isTopic
        ? `The legacy code and your <b>approved Gate-1 analysis</b> (RD01/02/03/13) will be sent to <b>${escapeHtml(providerLabel)}</b> to draft the remaining RDs. Ensure you have authorisation to share these documents.`
        : `The following files will be sent to <b>${escapeHtml(providerLabel)}</b> for analysis. Ensure you have authorisation to share these documents.`}</p>
      <ul style="font-size:12px;color:var(--fg-muted);margin-bottom:14px;padding-left:18px">${fileList}</ul>
      ${provWarning ? `<div style="font-size:12px;background:var(--bg-tertiary,rgba(255,80,0,.08));border:1px solid var(--err,#c33);border-radius:6px;padding:8px 10px;margin-bottom:14px">
        ⚠ <b>Output-ceiling risk:</b> ${escapeHtml(provWarning)}
      </div>` : ""}
      ${isTopic ? "" : `<div style="font-size:12px;background:var(--bg-tertiary,rgba(255,180,0,.08));border:1px solid var(--warn,#c90);border-radius:6px;padding:8px 10px;margin-bottom:14px">
        ⚠ <b>Visual files are NOT anonymized.</b> Photos, drawings and PDFs are uploaded as-is —
        only legacy <i>code text</i> is anonymized. Remove customer logos, nameplates, title blocks
        and identifying information from images/PDFs <b>before</b> starting the analysis.
      </div>`}
      <div class="sm-field" style="margin-bottom:10px">
        <label style="width:100px">Engineer</label>
        <input id="rc-engineer" type="text" placeholder="Your name (required)" style="flex:1" value="${escapeHtml(STATE&&STATE.username||"")}" />
      </div>
      <div class="sm-field" style="margin-bottom:10px">
        <label style="width:100px" title="Generated prose (descriptions, comments, alarm/HMI texts) is written in this language. Tag names & SCL keywords stay English.">Output language</label>
        <select id="rc-lang" style="flex:1">${langOptions}</select>
      </div>
      ${isTopic ? "" : `<label style="display:flex;gap:8px;align-items:flex-start;font-size:12px;cursor:pointer;margin-bottom:10px" title="One run produces all 14 RD drafts: discovery, then topic generation on the fresh (unreviewed) Gate-1 drafts. Uncheck for the two-stage flow with a review pause in between.">
        <input id="rc-auto" type="checkbox" style="margin-top:2px" checked />
        <span><b>Continue with topic generation automatically</b> — one run, all 14 RD drafts. Topic RDs will be based on the <i>unreviewed</i> Gate-1 drafts; review everything before the Gate-3 lock.</span>
      </label>`}
      <label style="display:flex;gap:8px;align-items:flex-start;font-size:12px;cursor:pointer">
        <input id="rc-confirm" type="checkbox" style="margin-top:2px" />
        I confirm I have authorisation to share these documents with ${escapeHtml(providerLabel)}. I accept responsibility for this data transfer.
      </label>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="rc-ok">${startLabel}</button>
      <button class="btn ghost" id="rc-cancel">Cancel</button>
      <span class="sm-hint" id="rc-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  const close = () => ov.remove();
  q("#rc-cancel").addEventListener("click", close);
  ov.addEventListener("click", e => { if (e.target === ov) close(); });
  q("#rc-ok").addEventListener("click", async () => {
    const engineer = q("#rc-engineer").value.trim();
    const confirmed = q("#rc-confirm").checked;
    const hint = q("#rc-hint");
    if (!engineer) { hint.textContent = "Engineer name is required"; return; }
    if (!confirmed) { hint.textContent = "Please confirm the data sharing checkbox"; return; }
    q("#rc-ok").disabled = true; q("#rc-ok").textContent = "Running…";
    if (STATE) STATE.username = engineer;
    Backend.save_settings({username: engineer});
    // Persist the chosen analysis/output language before generation runs —
    // _lang_directive then steers all generated prose (RD drafts, comments…).
    const langSel = q("#rc-lang");
    if (langSel && langSel.value) await Backend.set_output_language(langSel.value);
    ov._autoContinue = !!(q("#rc-auto") && q("#rc-auto").checked);
    close();
    if (progressEl) {
      progressEl.style.display = "";
      progressEl.innerHTML = `
        <div id="pa-steps-row" class="pa-steps-row"></div>
        <div class="pa-progress-bar-wrap"><div id="pa-bar" class="pa-progress-bar" style="width:0%"></div></div>
        <div id="pa-status" class="pa-status-bar"><span class="pa-spinner">⟳</span> Starting…</div>
        <details class="pa-log-details">
          <summary>Raw log</summary>
          <div class="pa-log-inner"><div class="raw-progress-log" id="raw-progress-log"></div></div>
        </details>
        <div id="raw-progress-drafts" style="margin-top:8px"></div>`;
    }
    // Dispatchers route by project_type (retrofit extract / greenfield design).
    const autoCont = !isTopic && !!(ov._autoContinue);
    const result = isTopic
      ? await Backend.run_topic_generation({engineer, confirmed: true})
      : await Backend.run_discovery({engineer, confirmed: true, auto_continue: autoCont});
    if (!result.ok) {
      const statusEl = progressEl?.querySelector("#pa-status");
      if (statusEl) { statusEl.textContent = result.msg || "Failed to start"; statusEl.className = "pa-status-bar pa-status-err"; }
      toast((isTopic ? "Topic Extraction" : "Pre-analysis") + " failed: " + (result.msg||"error"), "error");
      return;
    }
    _pollPreanalysis(progressEl);
  });
}

// M2 — background pre-analysis: step-tracker UI + poll loop
async function _pollPreanalysis(progressEl) {
  const stepsRowEl = progressEl?.querySelector("#pa-steps-row");
  const barEl      = progressEl?.querySelector("#pa-bar");
  const statusEl   = progressEl?.querySelector("#pa-status");
  const logEl      = progressEl?.querySelector("#raw-progress-log");
  const draftsEl   = progressEl?.querySelector("#raw-progress-drafts");

  const st = await Backend.get_preanalysis_status();
  if (!st.exists) { setTimeout(() => _pollPreanalysis(progressEl), 1500); return; }

  const names  = st.step_names || [];
  const total  = st.step_total || names.length || 6;
  const idx    = (typeof st.step_index === "number") ? st.step_index : -1;

  // Build step bubbles once (when names arrive from first non-trivial status)
  if (stepsRowEl && names.length && !stepsRowEl.dataset.built) {
    stepsRowEl.dataset.built = "1";
    stepsRowEl.innerHTML = names.map((n, i) => {
      const connector = (i < names.length - 1)
        ? `<div class="pa-step-connector" id="pa-conn-${i}"></div>` : "";
      return `<div class="pa-step-pill pending" id="pa-pill-${i}">
        <div class="pa-step-bubble">${i + 1}</div>
        <div class="pa-step-label">${escapeHtml(n)}</div>
      </div>${connector}`;
    }).join("");
  }

  // Update each pill's state
  if (stepsRowEl && names.length) {
    const allDone = !st.running && st.succeeded;
    for (let i = 0; i < total; i++) {
      const pill = stepsRowEl.querySelector(`#pa-pill-${i}`);
      if (!pill) continue;
      let state = "pending";
      if (allDone || i < idx) state = "done";
      else if (i === idx && st.running) state = "current";
      pill.className = `pa-step-pill ${state}`;
      const bubble = pill.querySelector(".pa-step-bubble");
      if (bubble) bubble.textContent = (state === "done") ? "✓" : String(i + 1);
      const conn = stepsRowEl.querySelector(`#pa-conn-${i}`);
      if (conn) conn.className = `pa-step-connector${(allDone || i < idx) ? " done" : ""}`;
    }
  }

  // Progress bar
  if (barEl) {
    const pct = !st.running && st.succeeded ? 100
      : (idx >= 0 ? Math.round(((idx) / total) * 100) : 0);
    barEl.style.width = pct + "%";
  }

  // Status bar text
  if (statusEl) {
    // B-02: oversize input badge — a truncated analysis silently loses
    // blocks/IO, so the size must stay visible for the whole run.
    let sizeBadge = "";
    const estTok = st.input_est_tokens || 0;
    if (estTok > 150000) {
      sizeBadge = ` <span class="pa-size-warn" title="Input almost certainly exceeds the model context — analysis will be incomplete. Split the sources per CPU/section.">⚠ input ~${Math.round(estTok/1000)}k tokens — TOO LARGE</span>`;
    } else if (estTok > 60000) {
      sizeBadge = ` <span class="pa-size-warn" title="Large input — the tail may be cut by the provider. Cross-check RD01 against the symbol table.">⚠ input ~${Math.round(estTok/1000)}k tokens</span>`;
    }
    if (st.running) {
      statusEl.className = "pa-status-bar";
      statusEl.innerHTML = `<span class="pa-spinner">⟳</span> ${escapeHtml(st.current_step || "Running…")}${sizeBadge}`;
    } else if (st.succeeded) {
      statusEl.className = "pa-status-bar pa-status-ok";
      statusEl.innerHTML = `✓ Complete — review the RD drafts below`;
    } else {
      statusEl.className = "pa-status-bar pa-status-err";
      statusEl.innerHTML = `✗ Failed: ${escapeHtml(st.msg || "error")}`;
    }
  }

  // Raw log (in collapsible)
  if (logEl) {
    logEl.textContent = st.output_tail || "";
    if (st.running) logEl.scrollTop = logEl.scrollHeight;
  }

  // Draft buttons (appear as steps complete)
  if (draftsEl && (st.drafts||[]).length) {
    const rendered = draftsEl.querySelectorAll("[data-open-rd]").length;
    if (rendered !== st.drafts.length) {
      draftsEl.innerHTML =
        `<div style="font-size:12px;font-weight:600;margin-bottom:4px">RD drafts written (DRAFT_UNVERIFIED — review required):</div>`
        + st.drafts.map(d =>
          `<button class="btn ghost" data-open-rd="metadata/${escapeHtml(d.file)}"
             style="font-size:11.5px;padding:2px 8px;margin:2px 4px 2px 0">
             ${svg("file-text",12)} ${escapeHtml(d.rd)} — ${escapeHtml(d.file)}${d.action==="sidecar"?" (sidecar)":""}</button>`
        ).join("");
      draftsEl.querySelectorAll("[data-open-rd]").forEach(b =>
        b.addEventListener("click", () => {
          // Force fresh read — stale cached tab would show 0 rows if file was
          // opened before the analysis wrote it.
          const ci = OPEN_TABS.findIndex(t => t.path === b.dataset.openRd);
          if (ci !== -1) OPEN_TABS.splice(ci, 1);
          setActivePage("explorer");
          openFile(b.dataset.openRd);
        }));
    }
  }

  if (st.running) { setTimeout(() => _pollPreanalysis(progressEl), 1500); return; }

  if (st.succeeded) {
    toast("Pre-analysis complete — review the RD drafts in metadata/");
    logLine("[retrofit] Pre-analysis complete: " + (st.msg||""), "success");
    // Update gate model data silently — do NOT re-render the gate view here
    // because _renderGateView would destroy the progress area and draft buttons
    // that the user needs to click. The gate view will refresh on next navigation.
    Backend.get_gate_model().then(gm => {
      if (gm) { _gateModel = gm; renderGateNavBar(); updateNextStepCard(); }
    });
    Backend.get_state().then(s => { if (s) { STATE = s; render(); } });
  } else {
    toast("Pre-analysis failed: " + (st.msg||"error"), "error");
    logLine("[retrofit] Pre-analysis failed: " + (st.msg||""), "error");
  }
  (st.job_warnings||[]).forEach(w => logLine("[retrofit] ⚠ " + w, "warn"));
}

// ===========================================================================
// M4 — TIA Portal direct path (Openness)
// ===========================================================================

async function _renderTiaSettingsCard(ov) {
  const host = ov.querySelector("#sm-tia");
  if (!host) return;
  const st = await Backend.get_tia_bridge_status();
  if (!st.ok) { host.textContent = st.msg || "Bridge status unavailable"; return; }

  const badge = (s) => ({
    ready: `<span style="color:var(--ok,#3a3)">● ready</span>`,
    not_installed: `<span class="fg-dim">○ not installed</span>`,
    not_configured: `<span style="color:var(--warn,#c90)">◐ not configured</span>`,
  }[s] || `<span style="color:var(--err,#c33)">✗ ${escapeHtml(s)}</span>`);

  const rows = (st.bridges||[]).map(b => `
    <div class="sm-field">
      <label style="width:170px;flex:0 0 170px">${escapeHtml(b.name||b.id)}</label>
      ${badge(b.status)}
      <label style="display:flex;gap:5px;align-items:center;font-size:12px;cursor:pointer;margin-left:10px">
        <input type="checkbox" class="tia-enable" data-bid="${b.id}" ${b.enabled?"checked":""} ${b.status!=="ready"?"disabled":""}/> enabled
      </label>
      ${b.dll ? `<span class="sm-hint" title="${escapeHtml(b.dll)}">dll ✓</span>` : ""}
      ${b.last_error ? `<span class="sm-hint" style="color:var(--warn,#c90)">${escapeHtml(b.last_error)}</span>` : ""}
    </div>`).join("");

  const proj = st.project || {};
  host.innerHTML = `
    ${st.pythonnet ? "" : `<div class="prov-warn" style="margin-bottom:8px">⚠ pythonnet not installed — direct path disabled. <code>pip install pythonnet</code> (folder export still works).</div>`}
    ${rows || `<div class="sm-hint">No TIA bridges could be loaded.</div>`}
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">Default PLC name</label>
      <input id="tia-plc-name" type="text" value="${escapeHtml(proj.plc_name||"PLC_1")}" style="width:140px;flex:none"/></div>
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">TIA project (.ap19/.ap20/.ap21)</label>
      <input id="tia-proj-path" type="text" placeholder="D:\\...\\MyProject.ap21" value="${escapeHtml(proj.tia_project_path||"")}" style="flex:1"/>
      <button class="btn ghost" id="tia-proj-browse" style="font-size:12px;flex:none" title="Pick the .ap19/.ap20/.ap21 file with the file explorer">Browse…</button></div>
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">Target CPU / TIA</label>
      <select id="tia-cpu" style="width:110px;flex:none">
        ${["S7-1500","S7-1200"].map(v=>`<option${(proj.target_platform||"S7-1500")===v?" selected":""}>${v}</option>`).join("")}
      </select>
      <select id="tia-ver" style="width:80px;flex:none">
        ${["V21","V20","V19"].map(v=>`<option${(proj.target_tia_version||"V21")===v?" selected":""}>${v}</option>`).join("")}
      </select></div>
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">Output language (AI)</label>
      <select id="tia-lang" style="width:80px;flex:none">
        ${["EN","TR","DE"].map(v=>`<option${(proj.output_language||"EN")===v?" selected":""}>${v}</option>`).join("")}
      </select>
      <span class="sm-hint">RD drafts + sequence-FB comments; library blocks stay English</span></div>
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">Send to TIA view</label>
      <label style="display:flex;gap:5px;align-items:center;font-size:12px;cursor:pointer">
        <input id="tia-live-progress" type="checkbox" ${ (st.tia_settings||{}).live_progress===false ? "" : "checked" }/> Live step progress in the transfer modal
      </label></div>
    <div class="sm-field"><label style="width:170px;flex:0 0 170px">Compile error assistance</label>
      <select id="tia-fix-assist" style="width:230px;flex:none">
        ${[["off","Off — raw errors only"],
           ["hints","Hints — classify + tips (no AI)"],
           ["suggest","AI suggest — on demand button"],
           ["auto_propose","AI auto-propose — still needs approval"]]
          .map(([v,l])=>`<option value="${v}"${((st.tia_settings||{}).fix_assist_mode||"hints")===v?" selected":""}>${l}</option>`).join("")}
      </select>
      <span class="sm-hint">AI never applies a fix without engineer approval; fixes touch only the sequence FB</span></div>
    <div class="sm-hint" style="margin:4px 0 8px">Safety defaults (locked): downloads go to <b>PLCSIM only</b>; F/safety blocks are <b>never</b> auto-imported.</div>
    <button class="btn" id="tia-apply" style="font-size:12px">Apply TIA settings</button>
    <span class="sm-hint" id="tia-hint"></span>`;

  host.querySelector("#tia-proj-browse")?.addEventListener("click", async () => {
    const r = await Backend.browse_for_file("tia_project");
    if (r && r.ok && r.path) host.querySelector("#tia-proj-path").value = r.path;
  });

  host.querySelector("#tia-apply")?.addEventListener("click", async () => {
    const enabled = {};
    host.querySelectorAll(".tia-enable").forEach(c => { enabled[c.dataset.bid] = c.checked; });
    const r1 = await Backend.set_tia_settings({
      default_plc_name: host.querySelector("#tia-plc-name").value.trim(),
      live_progress: host.querySelector("#tia-live-progress").checked,
      fix_assist_mode: host.querySelector("#tia-fix-assist").value,
      enabled,
    });
    const r2 = await Backend.set_project_target({
      target_platform: host.querySelector("#tia-cpu").value,
      target_tia_version: host.querySelector("#tia-ver").value,
      output_language: host.querySelector("#tia-lang").value,
      plc_name: host.querySelector("#tia-plc-name").value.trim(),
      tia_project_path: host.querySelector("#tia-proj-path").value.trim(),
    });
    host.querySelector("#tia-hint").textContent =
      (r1.ok ? "✓ bridge settings" : "✗ " + (r1.msg||"")) + " · " +
      (r2.ok ? "✓ project target" : (r2.msg||"project fields skipped"));
  });
}

/* ─────────────────────────────────────────────────────────────────────
   FAT/SAT PROTOCOL MODAL (SAT v2 Faz 6) — type / language / PDF options.
   Mirrors the Send-to-TIA modal pattern; keeps the reveal_path behaviour
   of the old one-click FAT action.
───────────────────────────────────────────────────────────────────── */
function _openProtocolModal() {
  if ($("protocol-overlay")) return;
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "protocol-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:480px">
    <div class="sm-head">${svg("check",14)} Generate Test Protocol (FAT / SAT)</div>
    <div class="sm-body">
      <div class="sm-hint">SAT is a genuine site-acceptance protocol (loop check,
        real E-stop chain, IEC 62443 hardening, handover) — not a FAT copy.</div>
      <div class="sm-field" style="margin-top:8px"><label style="width:110px">Type</label>
        <select id="pr-type" style="flex:1">
          <option value="FAT" selected>FAT — Factory Acceptance (PLCSim)</option>
          <option value="SAT">SAT — Site Acceptance (real plant)</option>
          <option value="BOTH">BOTH — two separate documents</option>
        </select></div>
      <div class="sm-field"><label style="width:110px">Language</label>
        <select id="pr-lang" style="flex:1">
          <option value="de" selected>Deutsch (DE)</option>
          <option value="en">English (EN)</option>
          <option value="tr">Türkçe (TR)</option>
        </select></div>
      <label style="display:flex;gap:6px;font-size:12px;cursor:pointer;margin-top:6px">
        <input id="pr-pdf" type="checkbox"/> Also produce <b>PDF</b> (Markdown is always written)</label>
      <div id="pr-sistema" style="display:none;border:1px solid var(--warn,#c90);border-radius:6px;padding:8px 10px;margin:10px 0 0;font-size:12px"></div>
      <div id="pr-rag-banner" style="display:none;border:2px solid #dc2626;background:rgba(220,38,38,.08);border-radius:6px;padding:10px 12px;margin:10px 0 0;font-size:12px"></div>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="pr-go">Generate</button>
      <button class="btn ghost" id="pr-sistema-btn" title="Engineer SISTEMA declarations">SISTEMA records…</button>
      <button class="btn ghost" id="pr-cancel">Close</button>
      <span class="sm-hint" id="pr-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#pr-cancel").addEventListener("click", () => ov.remove());
  q("#pr-sistema-btn").addEventListener("click", () => { ov.remove(); _openSistemaModal(); });

  // Faz 2.3: show the pending SISTEMA functions up front so the engineer
  // knows the protocol will carry a PENDING box.
  Backend.get_sistema_status().then(st => {
    if (st && st.ok && (st.pending||[]).length) {
      const el = q("#pr-sistema");
      el.style.display = "";
      el.innerHTML = `<b>SISTEMA verification pending</b> for: ` +
        st.pending.map(escapeHtml).join(", ") +
        `<br>The protocol will be generated with a visible PENDING box.`;
    }
  }).catch((e)=>{ logLine(`[sistema] status check failed: ${e && e.message || e}`, "warn"); });

  q("#pr-go").addEventListener("click", async () => {
    q("#pr-go").disabled = true;
    q("#pr-hint").textContent = "Generating…";
    const r = await Backend.generate_fat(
      q("#pr-type").value, q("#pr-lang").value, q("#pr-pdf").checked);
    logLine(`[fat] ${r.msg||"Done"}`, r.ok ? "success" : "warn");
    if (r.ok) {
      q("#pr-hint").textContent = "✓ done";
      if (r.rag_warnings && r.rag_warnings.length > 0) {
        // Safety chain (Phase D): show red banner + confirm before closing
        const banner = q("#pr-rag-banner");
        if (banner) {
          const warnHtml = r.rag_warnings.map(w =>
            `<div style="margin:4px 0">⚠️ <b>[${escapeHtml(w.entry_id||"?")}]</b> ${escapeHtml((w.chunk_text||"").split("\n")[0].replace(/^#+\s*/,"").substring(0,100))}</div>`
          ).join("");
          banner.style.display = "block";
          banner.innerHTML = `<b style="color:#dc2626">⚠️ ${t("dlg.safety_kb_warn")}</b> — ${r.rag_warnings.length} ${t("dlg.safety_kb_body")}<br>${warnHtml}<br><button class="btn primary" id="pr-rag-ok" style="margin-top:6px">${t("dlg.acknowledge")}</button>`;
          q("#pr-rag-ok").addEventListener("click", () => {
            if (r.path) Backend.reveal_path(r.path);
            ov.remove(); switchBottomTab("terminal"); refreshProjectState();
          });
          toast("Protocol generated (safety warnings — see banner)");
          return; // hold modal open until user clicks "Gördüm"
        }
      }
      toast("Protocol generated");
      if (r.path) Backend.reveal_path(r.path);
      ov.remove();
      switchBottomTab("terminal");
      refreshProjectState();
    } else {
      q("#pr-hint").textContent = "✗ " + (r.msg || "failed").split("\n")[0];
      q("#pr-go").disabled = false;
      if (r.rd05_blocked) toast("Blocked: RD05 (Safety) not ready", "error");
    }
  });
}

/* ─────────────────────────────────────────────────────────────────────
   SISTEMA RECORDS MODAL (Faz 2/6) — engineer declarations
   {function, file, achieved_pl, engineer}; the software reminds and
   documents, the engineer calculates and signs.
───────────────────────────────────────────────────────────────────── */
function _openSistemaModal() {
  if ($("sistema-overlay")) return;
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "sistema-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:640px">
    <div class="sm-head">${svg("check",14)} SISTEMA Records (engineer declarations)</div>
    <div class="sm-body">
      <div class="sm-hint">The software reminds and documents — the calculation and
        the signature are the safety engineer's responsibility. No automatic PL
        calculation is performed.</div>
      <div id="sm-pending" style="display:none;border:1px solid var(--warn,#c90);border-radius:6px;padding:6px 10px;margin:8px 0;font-size:12px"></div>
      <div id="sm-list" style="margin:8px 0;max-height:200px;overflow:auto;font-size:12px"></div>
      <div style="border-top:1px solid var(--border,#333);padding-top:8px">
        <div class="sm-field"><label style="width:110px">Function</label>
          <input id="sm-fn" type="text" placeholder="e.g. EStop_Main (from RD05)" style="flex:1"/></div>
        <div class="sm-field"><label style="width:110px">SISTEMA file</label>
          <input id="sm-file" type="text" placeholder="e.g. estop_main.ssm" style="flex:1"/></div>
        <div class="sm-field"><label style="width:110px">Achieved PL</label>
          <input id="sm-pl" type="text" placeholder="a–e" style="width:80px;flex:none"/></div>
        <div class="sm-field"><label style="width:110px">Engineer</label>
          <input id="sm-eng" type="text" placeholder="Your name (mandatory)" style="flex:1"/></div>
      </div>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="sm-add">Add record</button>
      <select id="sm-lang" title="Prep list language" style="font-size:12px">
        <option value="de" selected>DE</option><option value="en">EN</option><option value="tr">TR</option>
      </select>
      <button class="btn ghost" id="sm-prep">SISTEMA prep list…</button>
      <button class="btn ghost" id="sm-close">Close</button>
      <span class="sm-hint" id="sm-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#sm-close").addEventListener("click", () => ov.remove());

  async function refresh() {
    const st = await Backend.get_sistema_status();
    const list = q("#sm-list");
    if (!st || !st.ok) {
      list.innerHTML = `<i>${escapeHtml((st&&st.msg)||"status failed")}</i>`;
      return;
    }
    const pend = q("#sm-pending");
    if ((st.pending||[]).length) {
      pend.style.display = "";
      pend.innerHTML = `<b>Pending (PLr in RD05, no record yet):</b> ` +
        st.pending.map(escapeHtml).join(", ");
    } else {
      pend.style.display = "none";
    }
    const recs = st.records || [];
    if (!recs.length) { list.innerHTML = "<i>No records yet.</i>"; return; }
    list.innerHTML = `<table style="width:100%;border-collapse:collapse">
      <tr><th align="left">Function</th><th align="left">PL</th><th align="left">File</th>
          <th align="left">Date</th><th align="left">Engineer</th><th></th></tr>` +
      recs.map((r, i) => `<tr>
        <td>${escapeHtml(r.function||"")}</td><td>${escapeHtml(r.achieved_pl||"—")}</td>
        <td>${escapeHtml(r.file||"—")}</td><td>${escapeHtml(r.date||"")}</td>
        <td>${escapeHtml(r.engineer||"")}</td>
        <td><button class="btn ghost sm-del" data-i="${i}" style="font-size:11px">✕</button></td>
      </tr>`).join("") + `</table>`;
    list.querySelectorAll(".sm-del").forEach(btn =>
      btn.addEventListener("click", async () => {
        const r = await Backend.delete_sistema_record(parseInt(btn.dataset.i, 10));
        if (!r.ok) q("#sm-hint").textContent = r.msg || "delete failed";
        await refresh();
      }));
  }

  q("#sm-add").addEventListener("click", async () => {
    const r = await Backend.add_sistema_record(
      q("#sm-fn").value.trim(), q("#sm-file").value.trim(),
      q("#sm-pl").value.trim(), q("#sm-eng").value.trim());
    if (!r.ok) { q("#sm-hint").textContent = r.msg || "add failed"; return; }
    q("#sm-hint").textContent = "✓ record added";
    q("#sm-fn").value = ""; q("#sm-file").value = ""; q("#sm-pl").value = "";
    await refresh();
  });
  q("#sm-prep").addEventListener("click", async () => {
    const r = await Backend.generate_sistema_prep(q("#sm-lang").value);
    logLine(`[sistema] ${r.msg||"Done"}`, r.ok ? "success" : "warn");
    q("#sm-hint").textContent = r.ok ? "✓ prep list written" : (r.msg||"failed").split("\n")[0];
    if (r.ok && r.path) Backend.reveal_path(r.path);
  });

  refresh();
}

/* ─────────────────────────────────────────────────────────────────────
   CE ASSESSMENT MODAL (Faz 6.3) — language + PDF, same pattern as the
   protocol modal. CE is a deliverable document, so the engineer must be
   able to pick the language (not a hardcoded DE) and optionally a PDF.
───────────────────────────────────────────────────────────────────── */
function _openCeModal() {
  if ($("ce-overlay")) return;
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "ce-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:480px">
    <div class="sm-head">${svg("file-text",14)} CE Assessment (wesentliche Veränderung)</div>
    <div class="sm-body">
      <div class="sm-hint">Essential-modification assessment for retrofit projects.
        The template does not replace a legal assessment — the engineer decides
        and signs. Greenfield projects produce a non-blocking "not a retrofit" note.</div>
      <div class="sm-field" style="margin-top:8px"><label style="width:110px">Language</label>
        <select id="ce-lang" style="flex:1">
          <option value="de" selected>Deutsch (DE)</option>
          <option value="en">English (EN)</option>
          <option value="tr">Türkçe (TR)</option>
        </select></div>
      <label style="display:flex;gap:6px;font-size:12px;cursor:pointer;margin-top:6px">
        <input id="ce-pdf" type="checkbox"/> Also produce <b>PDF</b> (Markdown is always written)</label>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="ce-go">Generate</button>
      <button class="btn ghost" id="ce-cancel">Close</button>
      <span class="sm-hint" id="ce-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#ce-cancel").addEventListener("click", () => ov.remove());
  q("#ce-go").addEventListener("click", async () => {
    q("#ce-go").disabled = true;
    q("#ce-hint").textContent = "Generating…";
    const r = await Backend.generate_ce_assessment(q("#ce-lang").value, q("#ce-pdf").checked);
    logLine(`[ce] ${r.msg||"Done"}`, r.ok ? "success" : "warn");
    if (r.ok) {
      q("#ce-hint").textContent = "✓ done";
      toast("CE assessment generated");
      if (r.path) Backend.reveal_path(r.path);
      ov.remove();
    } else {
      q("#ce-hint").textContent = "✗ " + (r.msg || "failed").split("\n")[0];
      q("#ce-go").disabled = false;
    }
  });
}

function _openSendToTiaModal() {
  if ($("tia-send-overlay")) return;
  const ov = document.createElement("div");
  ov.className = "overlay show"; ov.id = "tia-send-overlay";
  ov.innerHTML = `<div class="settings-modal" style="max-width:560px">
    <div class="sm-head">${svg("upload",14)} Send to TIA Portal (Openness)</div>
    <div class="sm-body">
      <div id="tia-send-info" class="sm-hint">Checking bridge status…</div>
      <div class="sm-field" style="margin-top:8px"><label style="width:120px">TIA project</label>
        <input id="ts-path" type="text" placeholder=".ap19 / .ap20 / .ap21 path" style="flex:1"/>
        <button class="btn ghost" id="ts-browse" style="font-size:12px;flex:none" title="Pick the TIA project file">Browse…</button></div>
      <div class="sm-field"><label style="width:120px">PLC name</label>
        <input id="ts-plc" type="text" value="PLC_1" style="width:140px;flex:none"/></div>
      <div id="ts-consent" style="display:none;border:1px solid var(--warn,#c90);border-radius:6px;padding:8px 10px;margin:8px 0">
        <div style="font-size:12px;margin-bottom:6px"><b>CONFIDENTIAL project.</b> This is a LOCAL transfer into TIA Portal
          (no cloud egress) but still needs sign-off; the consent is written to AI_DECISION_LOG.</div>
        <div class="sm-field"><label style="width:90px">Engineer</label>
          <input id="ts-engineer" type="text" placeholder="Your name" style="flex:1"/></div>
        <label style="display:flex;gap:6px;font-size:12px;cursor:pointer">
          <input id="ts-confirm" type="checkbox" style="margin-top:2px"/> I authorise this local transfer.</label>
      </div>
      <label style="display:flex;gap:6px;font-size:12px;cursor:pointer;margin-top:6px">
        <input id="ts-plcsim" type="checkbox"/> After a clean compile, also download to <b>PLCSIM Advanced</b> (never a real PLC).</label>
      <div id="ts-steps" style="display:none;margin-top:8px;font-size:12px"></div>
      <details id="ts-rawwrap" style="display:none;margin-top:6px">
        <summary style="cursor:pointer;font-size:11px;color:var(--fg-dim,#888)">Raw log</summary>
        <div class="raw-progress-log" id="ts-log" style="margin-top:4px;max-height:160px;overflow:auto;user-select:text;-webkit-user-select:text"></div>
      </details>
      <div id="ts-errors" style="display:none;margin-top:8px"></div>
    </div>
    <div class="sm-foot">
      <button class="btn primary" id="ts-go">Import + Compile</button>
      <button class="btn ghost" id="ts-copy">Copy log</button>
      <button class="btn ghost" id="ts-cancel">Close</button>
      <span class="sm-hint" id="ts-hint"></span>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const q = s => ov.querySelector(s);
  q("#ts-cancel").addEventListener("click", () => ov.remove());
  q("#ts-browse").addEventListener("click", async () => {
    const r = await Backend.browse_for_file("tia_project");
    if (r && r.ok && r.path) q("#ts-path").value = r.path;
  });
  q("#ts-copy").addEventListener("click", async () => {
    const txt = [q("#ts-steps").innerText, q("#ts-log").textContent,
                 q("#ts-errors").innerText, q("#ts-hint").textContent]
      .filter(Boolean).join("\n").trim();
    if (!txt) { q("#ts-hint").textContent = "nothing to copy yet"; return; }
    try {
      await navigator.clipboard.writeText(txt);
    } catch (e) {
      // pywebview/WebView2 may block the async clipboard API — fall back
      const ta = document.createElement("textarea");
      ta.value = txt; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); ta.remove();
    }
    q("#ts-hint").textContent = "✓ log copied to clipboard";
  });

  Backend.get_tia_bridge_status().then(st => {
    if (!st.ok) { q("#tia-send-info").textContent = st.msg||"status failed"; return; }
    ov._tiaLive = (st.tia_settings||{}).live_progress !== false;
    ov._tiaFixMode = (st.tia_settings||{}).fix_assist_mode || "hints";
    const ready = (st.bridges||[]).filter(b => b.status === "ready");
    const enabled = ready.filter(b => b.enabled);
    // B-09: when the bridge is not usable, the engineer needs the manual
    // escape hatch spelled out — the generated SCL is still fully usable.
    const bridgeErr = (st.bridges||[]).map(b => b.last_error).filter(Boolean)[0] || "";
    const manualSteps =
      `<details style="margin-top:6px"><summary style="cursor:pointer">Manual import — no Openness needed</summary>
       <ol style="margin:6px 0 2px 18px;font-size:12px;line-height:1.5">
         <li>Your generated files are in <code>_output/scl/</code> (.scl + .db).</li>
         <li>In TIA Portal: PLC → <b>External source files</b> → <i>Add new external file</i> → select the .scl files.</li>
         <li>Right-click the sources → <b>Generate blocks from source</b>.</li>
         <li>Import the tag table: PLC tags → <i>Import</i> → <code>_output/tia/PLC_Tags.xml</code> (if generated).</li>
         <li>Compile (Software, rebuild all) and fix any reported lines back in the editor.</li>
       </ol></details>`;
    q("#tia-send-info").innerHTML = ready.length
      ? (enabled.length
          ? `Bridge: <b>${escapeHtml(enabled[0].name)}</b> ready. Files from <code>_output/scl/</code> (.scl + .db).`
          : `TIA detected but bridge disabled — enable it in Settings → TIA Portal.`)
      : `No ready TIA bridge${bridgeErr ? ` — ${escapeHtml(bridgeErr)}` : " (install TIA V19/V20/V21 + pythonnet)"}.${manualSteps}`;
    const proj = st.project || {};
    if (proj.tia_project_path) q("#ts-path").value = proj.tia_project_path;
    if (proj.plc_name) q("#ts-plc").value = proj.plc_name;
    if (proj.classification && !["PUBLIC","INTERNAL"].includes(proj.classification))
      q("#ts-consent").style.display = "";
  });

  q("#ts-go").addEventListener("click", async () => {
    const consentVisible = q("#ts-consent").style.display !== "none";
    const opts = {
      project_path: q("#ts-path").value.trim(),
      plc_name: q("#ts-plc").value.trim(),
      download_plcsim: q("#ts-plcsim").checked,
      consent: consentVisible
        ? {engineer: q("#ts-engineer").value.trim(), confirmed: q("#ts-confirm").checked}
        : {engineer: "n/a", confirmed: true},
    };
    if (opts.download_plcsim &&
        !window.confirm("Download to PLCSIM Advanced after compile?\n(Real PLC downloads are hard-blocked by design.)")) {
      return;
    }
    q("#ts-go").disabled = true; q("#ts-hint").textContent = "";
    const r = await Backend.send_to_tia(opts);
    if (!r.ok) { q("#ts-hint").textContent = r.msg||"failed"; q("#ts-go").disabled = false; return; }
    q("#ts-errors").style.display = "none"; q("#ts-errors").innerHTML = "";
    q("#ts-rawwrap").style.display = ""; q("#ts-log").textContent = r.msg;
    if (ov._tiaLive !== false) { q("#ts-steps").style.display = ""; }
    else { q("#ts-rawwrap").open = true; }
    _pollTiaSend(ov);
  });
}

async function _pollTiaSend(ov) {
  const logEl = ov.querySelector("#ts-log");
  const st = await Backend.get_tia_send_status();
  if (st.exists && logEl) {
    logEl.textContent = (st.log_tail||"") + "\n" + (st.details||[]).join("\n");
    logEl.scrollTop = logEl.scrollHeight;
    if (ov._tiaLive !== false) _renderTiaSteps(ov, st.steps||[]);
  }
  if (!st.exists || st.running) { setTimeout(() => _pollTiaSend(ov), 2000); return; }
  const hint = ov.querySelector("#ts-hint");
  const go = ov.querySelector("#ts-go");
  if (go) go.disabled = false;
  if (logEl && st.msg) {
    logEl.textContent += "\n[result] " + st.msg;
    logEl.scrollTop = logEl.scrollHeight;
  }
  if (st.succeeded) {
    if (hint) hint.textContent = "✓ " + (st.msg||"done");
    toast("TIA: " + (st.msg||"transfer complete"));
    logLine("[tia] " + (st.msg||"transfer complete"), "success");
    logLine("[tia] Label upgraded: AUTO_VERIFIED_compile | PENDING_PLCSIM_VERIFY", "info");
    refreshProjectState();  // compile evidence changes the gate model (W-A5)
  } else {
    if (hint) hint.textContent = "✗ " + (st.msg||"failed");
    toast("TIA transfer failed: " + (st.msg||"error"), "error");
    (st.details||[]).slice(0,10).forEach(d => logLine("[tia] " + d, "warn"));
    _renderTiaAssist(ov, st);
  }
}

const _TIA_STEP_ICON = {pending:"○", running:"▶", ok:"✓", warn:"⚠", fail:"✗", skip:"–"};
const _TIA_STEP_COLOR = {ok:"var(--ok,#3a3)", warn:"var(--warn,#c90)",
                         fail:"var(--err,#c33)", running:"var(--accent,#48f)"};

function _renderTiaSteps(ov, steps) {
  const el = ov.querySelector("#ts-steps");
  if (!el || !steps.length) return;
  el.innerHTML = steps.map(s => `
    <div style="display:flex;gap:8px;align-items:baseline;padding:1px 0">
      <span style="width:14px;text-align:center;color:${_TIA_STEP_COLOR[s.status]||"var(--fg-dim,#888)"}">${_TIA_STEP_ICON[s.status]||"○"}</span>
      <span style="${s.status==="pending"?"color:var(--fg-dim,#888)":""}">${escapeHtml(s.label)}</span>
      ${s.info ? `<span class="sm-hint" style="margin-left:auto">${escapeHtml(s.info)}</span>` : ""}
    </div>`).join("");
}

// Compile-error assistance panel: grouped hints (hints+) and the FB_Seq
// AI fix proposal flow (suggest/auto_propose) — apply always needs an
// engineer name + checkbox, and the re-send stays manual by design.
function _renderTiaAssist(ov, st) {
  const el = ov.querySelector("#ts-errors");
  if (!el) return;
  const groups = st.error_analysis || [];
  const mode = st.fix_assist_mode || ov._tiaFixMode || "hints";
  if (!groups.length && !st.fix_proposal) return;
  const catLabel = {ai_generated:"AI-generated sequence FB", tags:"IO tags",
                    assembler:"Assembler output", library:"Library blocks",
                    unknown:"Other"};
  el.style.display = "";
  el.innerHTML = groups.map((g,gi) => `
    <div style="border:1px solid var(--border,#444);border-radius:6px;padding:6px 8px;margin-bottom:6px;font-size:12px">
      <div style="font-weight:600">${escapeHtml(catLabel[g.category]||g.category)}
        <span class="sm-hint">(${g.errors.length} error${g.errors.length>1?"s":""})</span></div>
      <div class="sm-hint" style="margin:2px 0 4px">${escapeHtml(g.hint||"")}</div>
      ${g.errors.slice(0,6).map(e => `<div style="color:var(--err,#c33)">✗ ${escapeHtml(e.block?e.block+": ":"")}${escapeHtml(e.text)}</div>`).join("")}
      ${g.errors.length>6 ? `<div class="sm-hint">… ${g.errors.length-6} more (see raw log)</div>` : ""}
      ${g.proposable && (mode==="suggest"||mode==="auto_propose")
        ? `<button class="btn" style="font-size:12px;margin-top:4px" data-fix-block="${escapeHtml(g.blocks[0]||"")}">Propose fix (AI)</button>`
        : ""}
    </div>`).join("") + `<div id="ts-fix"></div>`;
  el.querySelectorAll("[data-fix-block]").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true; btn.textContent = "Proposing…";
      const eng = (ov.querySelector("#ts-engineer")||{}).value || "";
      // Clicking the button IS the consent for this one AI call.
      const r = await Backend.tia_fix_propose({
        block: btn.dataset.fixBlock,
        consent: {confirmed: true, engineer: eng.trim() || "n/a"},
      });
      btn.disabled = false; btn.textContent = "Propose fix (AI)";
      if (!r.ok) { toast(r.msg||"proposal failed", "error"); return; }
      _renderTiaProposal(ov, r.proposal);
    });
  });
  if (st.fix_proposal) _renderTiaProposal(ov, st.fix_proposal);
}

function _renderTiaProposal(ov, p) {
  const el = ov.querySelector("#ts-fix");
  if (!el || !p) return;
  el.innerHTML = `
    <div style="border:1px solid var(--accent,#48f);border-radius:6px;padding:6px 8px;font-size:12px">
      <div style="font-weight:600">Proposed fix — ${escapeHtml(p.file||"")}</div>
      <div class="sm-hint" style="margin:2px 0 4px">Review the diff. Applying writes ONLY this file
        (backup kept in _output/scl/_history/); re-run Import + Compile yourself afterwards.</div>
      <pre style="max-height:200px;overflow:auto;font-size:11px;user-select:text;-webkit-user-select:text;margin:4px 0">${escapeHtml(p.diff||"")}</pre>
      <div class="sm-field"><label style="width:90px">Engineer</label>
        <input id="ts-fix-eng" type="text" placeholder="Your name" style="flex:1"/></div>
      <label style="display:flex;gap:6px;font-size:12px;cursor:pointer;margin:4px 0">
        <input id="ts-fix-ok" type="checkbox"/> I reviewed the diff and approve this fix.</label>
      <button class="btn primary" id="ts-fix-apply" style="font-size:12px">Apply fix</button>
      <button class="btn ghost" id="ts-fix-discard" style="font-size:12px">Discard</button>
      <span class="sm-hint" id="ts-fix-hint"></span>
    </div>`;
  el.querySelector("#ts-fix-apply").addEventListener("click", async () => {
    const r = await Backend.tia_fix_apply({
      engineer: el.querySelector("#ts-fix-eng").value.trim(),
      confirmed: el.querySelector("#ts-fix-ok").checked,
    });
    if (!r.ok) { el.querySelector("#ts-fix-hint").textContent = r.msg||"failed"; return; }
    el.innerHTML = "";
    toast(r.msg||"Fix applied — re-run Import + Compile");
    logLine("[tia] " + (r.msg||"fix applied"), "success");
    const hint = ov.querySelector("#ts-hint");
    if (hint) hint.textContent = "Fix applied — click Import + Compile to re-run.";
  });
  el.querySelector("#ts-fix-discard").addEventListener("click", async () => {
    await Backend.tia_fix_discard();
    el.innerHTML = "";
  });
}

async function openGateTimeline() {
  setActivePage("gate");
}

/* ─────────────────────────────────────────────────────────────────────
   PROMPT VIEW  (M4 — full Prompt Workspace)
───────────────────────────────────────────────────────────────────── */
const PROMPT_CATEGORIES = [
  {id:"analyze",    label:"Analyze"},
  {id:"extract",    label:"Extract"},
  {id:"motor",      label:"Motors"},
  {id:"valve",      label:"Valves"},
  {id:"io",         label:"IO"},
  {id:"code_gen",   label:"Code Gen"},
  {id:"review",     label:"Review"},
  {id:"test_gen",   label:"Test Gen"},
  {id:"doc_gen",    label:"Docs"},
  {id:"system",     label:"System FBs"},
];
let _pvCategory = "analyze";
let _pvPrompts   = [];
let _pvSelected  = null;   // {name, path, title, text}
let _pvMode      = "view"; // "view" | "new"

async function showPromptView() {
  const v = $("prompt-view");
  _pvPrompts = await Backend.list_prompts_by_category(_pvCategory);
  // No empty editor on open (2026-07-06 audit): preselect the first prompt.
  if (!_pvSelected && _pvMode === "view" && _pvPrompts.length) {
    const p = _pvPrompts[0];
    const r = await Backend.get_prompt_text(p.path);
    if (r && r.ok !== false) {
      _pvSelected = {name: p.name, path: p.path,
                     title: p.title || p.name, text: r.text || ""};
    }
  }
  _renderPromptView(v);
  hideViews(); v.classList.add("show"); injectIcons(v);
}

function _renderPromptView(v) {
  const catTabs = PROMPT_CATEGORIES.map((c)=>
    `<div class="pv-cat ${_pvCategory===c.id?"active":""}" data-cat="${c.id}">${c.label}</div>`
  ).join("");
  const promptList = _pvPrompts.length
    ? _pvPrompts.map((p)=>`<div class="pv-item ${_pvSelected&&_pvSelected.name===p.name?"active":""}" data-name="${p.name}" data-path="${escapeHtml(p.path)}">${escapeHtml(p.title||p.name)}</div>`).join("")
    : `<div style="color:var(--fg-dim);font-size:12px;padding:10px">No prompts in this category</div>`;
  const bodyHtml = _pvMode === "new"
    ? `<div class="pv-editor-wrap">
        <div class="pv-editor-head">
          <span style="font-weight:600;color:var(--fg)">New Prompt</span>
          <input id="pv-new-title" class="pv-input" placeholder="Title…" style="flex:1;margin:0 8px" />
          <select id="pv-new-gate" class="pv-select">
            ${[1,2,3,4,5,6,7].map((n)=>`<option value="${n}">Gate ${n}</option>`).join("")}
          </select>
        </div>
        <textarea id="pv-new-body" class="pv-textarea" placeholder="Write your prompt here…"></textarea>
        <div class="pv-action-row">
          <button class="btn primary" id="pv-save-new">Save Prompt</button>
          <button class="btn ghost" id="pv-cancel-new">Cancel</button>
        </div>
      </div>`
    : (_pvSelected
        ? `<div class="pv-editor-wrap">
            <div class="pv-editor-head">
              <span style="font-weight:600;color:var(--fg);flex:1">${escapeHtml(_pvSelected.title||_pvSelected.name)}</span>
            </div>
            <textarea class="pv-textarea" id="pv-textarea">${escapeHtml(_pvSelected.text||"")}</textarea>
            <div class="pv-action-row">
              <button class="btn primary" id="pv-save">Save</button>
              <button class="btn" id="pv-copy">Copy</button>
              <button class="btn" id="pv-normalize">Normalize (AI)</button>
              <button class="btn" id="pv-adapt">Adapt to project</button>
            </div>
            <div id="pv-result" class="pv-result" style="display:none"></div>
          </div>`
        : `<div style="display:grid;place-items:center;flex:1;color:var(--fg-dim);font-size:13px">Select a prompt from the list →</div>`);
  // Library-workspace indicator + actions for the library-build workflow
  const pvActionsHtml = `
    <span class="ws-badge ws-library" title="Library workspace — author and freeze reference FBs (project-independent)">LIBRARY WORKSPACE</span>
    <button class="btn" id="pv-datasheet-btn" title="Select a device datasheet PDF → AI extracts spec → saves to 09_HARDWARE_LIBRARY → updates RAG index">${svg("upload",12)} Datasheet</button>
    <button class="btn" id="pv-gen-ref-fb-btn" disabled title="Manual step — write a .contract.json in 06_KNOWLEDGE_BASE/contracts/, then run fb_acceptance_check.py (CLI); not automated yet">${svg("sparkles",12)} Generate Ref FB</button>
    <button class="btn" id="pv-new-btn">+ New Prompt</button>`;
  v.innerHTML=`<div class="pv-wrap">
    ${pageHeader({backId:"pv-back", icon:"sparkles", title:"Prompt Workspace", subtitle:"Reusable AI prompt templates for building library FBs and project documents", actionsHtml: pvActionsHtml})}
    <div class="pv-cats">${catTabs}</div>
    <div class="pv-body">
      <div class="pv-list" id="pv-list">${promptList}</div>
      <div class="pv-divider" id="pv-divider"></div>
      <div class="pv-panel">${bodyHtml}</div>
    </div>
  </div>`;
  injectIcons(v);
  // Drag-to-resize between prompt list and editor
  const pvDiv = v.querySelector("#pv-divider");
  const pvList = v.querySelector("#pv-list");
  if (pvDiv && pvList) {
    let _rx = 0, _lw = 0;
    pvDiv.addEventListener("mousedown", (e) => {
      _rx = e.clientX; _lw = pvList.offsetWidth;
      pvDiv.classList.add("dragging");
      const onMove = (ev) => {
        const w = Math.min(400, Math.max(120, _lw + (ev.clientX - _rx)));
        pvList.style.width = w + "px"; pvList.style.flex = `0 0 ${w}px`;
      };
      const onUp = () => {
        pvDiv.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
  }
  v.querySelector("#pv-back").addEventListener("click", ()=>{ _pvSelected=null; setActivePage("explorer"); });
  v.querySelector("#pv-new-btn").addEventListener("click", ()=>{ _pvMode="new"; _pvSelected=null; _renderPromptView(v); injectIcons(v); });
  // Datasheet button: browse → AI extract → save to 09_HARDWARE_LIBRARY → update RAG
  const dsBtn = v.querySelector("#pv-datasheet-btn");
  if (dsBtn) dsBtn.addEventListener("click", async () => {
    dsBtn.disabled = true; dsBtn.textContent = "Selecting…";
    try {
      const pick = await Backend.browse_for_file("pdf");
      if (!pick || !pick.ok || !pick.path) { dsBtn.disabled = false; dsBtn.innerHTML = `${svg("upload",12)} Datasheet`; return; }
      dsBtn.textContent = "Extracting…";
      const r = await Backend.ingest_device(pick.path);
      if (r && r.ok) {
        toast(`Device saved: ${r.device_id}${r.rag_warn ? " (RAG: " + r.rag_warn + ")" : ""}`);
      } else {
        toast(`Datasheet error: ${(r && r.msg) || "unknown error"}`);
      }
    } catch(e) { toast(`Datasheet error: ${e.message||e}`); }
    dsBtn.disabled = false; dsBtn.innerHTML = `${svg("upload",12)} Datasheet`;
  });
  // Generate Ref FB remains a manual step today.
  v.querySelectorAll(".pv-cat").forEach((el)=>el.addEventListener("click", async()=>{
    _pvCategory = el.getAttribute("data-cat");
    _pvPrompts = await Backend.list_prompts_by_category(_pvCategory);
    _pvSelected = null; _pvMode = "view";
    _renderPromptView(v); injectIcons(v);
  }));
  v.querySelectorAll(".pv-item").forEach((el)=>el.addEventListener("click", async()=>{
    const path = el.getAttribute("data-path");
    const name = el.getAttribute("data-name");
    const r = await Backend.get_prompt_text(path);
    _pvSelected = {name, path, title: el.textContent, text: r.text||""};
    _pvMode = "view";
    _renderPromptView(v); injectIcons(v);
  }));
  // New prompt actions
  const saveNew = v.querySelector("#pv-save-new");
  if (saveNew) saveNew.addEventListener("click", async()=>{
    const title = v.querySelector("#pv-new-title").value.trim();
    const body  = v.querySelector("#pv-new-body").value.trim();
    const gate  = parseInt(v.querySelector("#pv-new-gate").value);
    if (!title || !body) { toast("Title and body are required"); return; }
    const r = await Backend.save_user_prompt(_pvCategory, title, body, gate);
    if (r && r.ok) {
      toast(r.msg||"Saved"); _pvMode="view";
      _pvPrompts = await Backend.list_prompts_by_category(_pvCategory);
      _renderPromptView(v); injectIcons(v);
    } else toast((r&&r.msg)||"Save failed");
  });
  const cancelNew = v.querySelector("#pv-cancel-new");
  if (cancelNew) cancelNew.addEventListener("click", ()=>{ _pvMode="view"; _renderPromptView(v); injectIcons(v); });
  // Prompt actions
  const getTextareaVal = ()=>(v.querySelector("#pv-textarea")||{value:_pvSelected&&_pvSelected.text||""}).value;
  const saveBtn = v.querySelector("#pv-save");
  if (saveBtn) saveBtn.addEventListener("click", async()=>{
    const text = getTextareaVal();
    _pvSelected.text = text;
    if (_pvSelected.path) {
      const r = await Backend.save_file(_pvSelected.path, text);
      toast(r && r.ok ? "Saved" : (r&&r.msg)||"Save failed");
    } else toast("No path — use Save Prompt for new prompts");
  });
  const copyBtn = v.querySelector("#pv-copy");
  if (copyBtn) copyBtn.addEventListener("click", async()=>{
    const text = getTextareaVal();
    try { await navigator.clipboard.writeText(text); toast("Copied to clipboard"); }
    catch { const r = await Backend.copy_prompt(_pvSelected.name); toast(r.msg||"Copied"); }
  });
  const applyToEditor = (text) => {
    const ta = v.querySelector("#pv-textarea");
    if (ta) { ta.value = text; if (_pvSelected) _pvSelected.text = text; }
    v.querySelector("#pv-result").style.display = "none";
    toast("Applied to editor");
  };
  const normBtn = v.querySelector("#pv-normalize");
  if (normBtn) normBtn.addEventListener("click", async()=>{
    const res = v.querySelector("#pv-result");
    res.style.display="block"; res.className="pv-result loading"; res.textContent="Normalizing…";
    const r = await Backend.normalize_prompt(getTextareaVal(), _pvCategory);
    if (!r.ok) {
      res.className="pv-result warn";
      res.innerHTML=`<strong>No API key set</strong> — add one in Settings to normalize.`;
    } else if (r.ok) {
      res.className="pv-result ok";
      res.innerHTML=`<strong>Normalized:</strong><pre class="pv-pre" style="margin-top:8px">${escapeHtml(r.normalized)}</pre>
        <div style="margin-top:8px;display:flex;gap:6px">
          <button class="btn primary" id="pv-apply-norm">Apply to editor</button>
          <button class="btn ghost" id="pv-dismiss-norm">Dismiss</button>
        </div>`;
      res.querySelector("#pv-apply-norm").addEventListener("click",()=>applyToEditor(r.normalized));
      res.querySelector("#pv-dismiss-norm").addEventListener("click",()=>{ res.style.display="none"; });
    } else {
      res.className="pv-result warn"; res.textContent=`Error: ${r.msg||"unknown"}`;
    }
  });
  const adaptBtn = v.querySelector("#pv-adapt");
  if (adaptBtn) adaptBtn.addEventListener("click", async()=>{
    const res = v.querySelector("#pv-result");
    res.style.display="block"; res.className="pv-result loading"; res.textContent="Adapting…";
    const r = await Backend.adapt_prompt(getTextareaVal());
    if (r.ok) {
      const warns = (r.warnings||[]).map((w)=>`<div class="pv-warn-item">⚠ ${escapeHtml(w)}</div>`).join("");
      const suggs = (r.suggestions||[]).map((s)=>`<div class="pv-sugg-item">→ ${escapeHtml(s)}</div>`).join("");
      res.className="pv-result ok";
      res.innerHTML=`${warns}${suggs}<pre class="pv-pre" style="margin-top:8px">${escapeHtml(r.enhanced)}</pre>
        <div style="margin-top:8px;display:flex;gap:6px">
          <button class="btn primary" id="pv-apply-adapt">Apply to editor</button>
          <button class="btn ghost" id="pv-dismiss-adapt">Dismiss</button>
        </div>`;
      res.querySelector("#pv-apply-adapt").addEventListener("click",()=>applyToEditor(r.enhanced));
      res.querySelector("#pv-dismiss-adapt").addEventListener("click",()=>{ res.style.display="none"; });
    } else {
      res.className="pv-result warn"; res.textContent=`Adapt failed: ${r.msg||"unknown"}`;
    }
  });
}

/* ─────────────────────────────────────────────────────────────────────
   FLOWCHART VIEW  (RD03 — derived diagram + change-request chat)
   The Flow Steps TABLE is the source of truth: the diagram shown here and
   the impact findings are always derived deterministically by the backend.
   The chat asks the AI for a replacement TABLE; nothing touches the file
   until the engineer reviews the proposal and clicks Apply.
───────────────────────────────────────────────────────────────────── */
let _fcData      = null;  // last rd03_get() result
let _dossierList = null;  // last list_machine_dossier() result
let _dossierSel  = null;  // selected item in the dossier view ("rd03" | file)
// 2026-07-06 user decision: the AI chat-edit ("prompt ile düzeltme") was
// retired — this view is now the Machine Dossier workspace. RD03 stays
// visible below as the read-only contract; sequence edits go through the
// RD03 file + engineer review, device decisions through the decision grid.
let _fcMmId     = 0;      // unique ids for mermaid.render

async function _fcRenderMermaid(el, code) {
  if (!el) return;
  if (!window.mermaid) {
    el.innerHTML = `<pre class="pv-pre" style="margin:0">${escapeHtml(code)}</pre>
      <div style="color:var(--fg-dim);font-size:11px;margin-top:6px">mermaid.js not loaded — showing source</div>`;
    return;
  }
  try {
    _mmApply();
    const { svg } = await window.mermaid.render(`fc-mm-${++_fcMmId}`, code);
    el.innerHTML = svg;
    const s = el.querySelector("svg");
    if (s) { s.style.maxWidth = "100%"; s.style.height = "auto"; }
  } catch (e) {
    el.innerHTML = `<pre class="pv-pre" style="margin:0">${escapeHtml(code)}</pre>
      <div style="color:var(--error);font-size:11px;margin-top:6px">Diagram render failed: ${escapeHtml(String(e && e.message || e))}</div>`;
  }
}

function _fcFindingsHtml(findings) {
  if (!findings || !findings.length)
    return `<div style="color:var(--success);font-size:12px;padding:4px 0">✓ Impact check: no findings</div>`;
  const sevColor = { error: "var(--error)", warning: "var(--warning)", info: "var(--fg-dim)" };
  return findings.map((f) =>
    `<div style="display:flex;gap:6px;align-items:flex-start;font-size:11.5px;padding:3px 0;border-bottom:1px solid var(--border)">
      <span style="color:${sevColor[f.severity]||"var(--fg-dim)"};font-weight:700;white-space:nowrap">${escapeHtml((f.severity||"").toUpperCase())}</span>
      <span class="mono" style="color:var(--fg-dim);white-space:nowrap">${escapeHtml(f.code||"")}</span>
      <span style="color:var(--fg)">${escapeHtml(f.msg||"")}</span>
    </div>`).join("");
}

async function showFlowchartView() {
  _fcData = await Backend.rd03_get();
  _dossierList = await Backend.list_machine_dossier();
  const v = $("flowchart-view");
  _renderFlowchartView(v);
  hideViews(); v.classList.add("show"); injectIcons(v);
  // Pane content (incl. mermaid) renders after the container is visible.
  await _renderDossierPane(v);
  injectIcons(v);
}

function _dossierPages() {
  // ONE list entry per PAGE (user audit 2026-07-06): state_table.json is
  // infrastructure, the PDF is a handover artifact (born in _delivery/),
  // and the md/xlsx twins collapse — 04 opens the grid (Excel button
  // inside), 06 opens the md view (Excel button inside).
  const raw = (_dossierList && _dossierList.files) || [];
  return raw.filter((f)=>
    f.kind !== "json" && f.kind !== "pdf" &&
    f.name !== "04_decision_table.md" && f.name !== "06_ce_matrix.xlsx");
}

function _renderFlowchartView(v) {
  const files = _dossierPages();
  const iconFor = (k) => k === "svg" ? "flow" : (k === "xlsx" ? "table" :
    (k === "json" ? "layers" : "file"));

  // keep the selection across re-renders; default = first page, else RD03
  if (_dossierSel !== "rd03" && !files.some((f)=>f.name===_dossierSel)) {
    _dossierSel = files.length ? files[0].name : "rd03";
  }

  const row = (sel, icon, label, extra) => `
    <div class="tree-row fc-item ${_dossierSel===sel?"active":""}" data-sel="${escapeHtml(sel)}" style="padding-left:10px;cursor:pointer">
      <span class="ic" data-i="${icon}" data-s="13"></span>
      <span class="tree-label">${escapeHtml(label)}</span>
      ${extra||""}
    </div>`;

  const fileRows = files.map((f)=>row(f.name, iconFor(f.kind), f.name,
    `<span class="mono" style="margin-left:auto;font-size:10px;color:var(--fg-dim)">${escapeHtml(f.kind)}</span>`)).join("") ||
    `<div style="padding:8px 10px;font-size:11px;color:var(--fg-dim)">${t("side.dossier_empty")}</div>`;

  v.innerHTML = `<div class="page-inner" style="max-width:none">
    ${pageHeader({backId:"fc-back", icon:"flow", title:t("side.dossier"),
      subtitle:t("dossier.page_sub"),
      actionsHtml:`<button class="btn primary" id="fc-dossier-gen">${svg("refresh",12)} ${t("gen.generate")}</button>`})}
    <div style="display:flex;border:1px solid var(--border);border-radius:8px;overflow:hidden;height:calc(100vh - 205px);min-height:380px">
      <div style="width:252px;flex:0 0 252px;border-right:1px solid var(--border);overflow:auto;display:flex;flex-direction:column">
        <div class="caps" style="padding:8px 10px;border-bottom:1px solid var(--border)">${t("dossier.section_pack")}</div>
        <div>${fileRows}</div>
        <div class="caps" style="padding:8px 10px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-top:auto">${t("dossier.step_sequence")}</div>
        ${row("rd03", "history", "RD03 — " + t("dossier.step_sequence"))}
      </div>
      <div id="fc-pane" style="flex:1;min-width:0;overflow:hidden;display:flex;flex-direction:column"></div>
    </div>
  </div>`;

  v.querySelectorAll(".fc-item").forEach((r)=>{
    r.addEventListener("click", async ()=>{
      _dossierSel = r.getAttribute("data-sel");
      v.querySelectorAll(".fc-item").forEach((x)=>x.classList.toggle("active", x===r));
      await _renderDossierPane(v);
    });
  });
  const dgen = v.querySelector("#fc-dossier-gen");
  if (dgen) dgen.addEventListener("click", async ()=>{
    logLine("[dossier] Generating machine dossier…", "info");
    const res = await Backend.generate_machine_dossier();
    if (res && res.ok) {
      logLine(`[dossier] ${res.msg}`, "success");
      (res.warnings||[]).forEach((w)=>logLine(`[dossier] ! ${w}`, "warn"));
      toast(res.msg);
      showFlowchartView();
    } else {
      toast(res && res.msg ? res.msg : "Dossier generation failed");
    }
  });
  v.querySelector("#fc-back").addEventListener("click", ()=>setActivePage("explorer"));
}

async function _renderDossierPane(v) {
  const pane = v.querySelector("#fc-pane");
  if (!pane) return;
  const files = _dossierPages();
  const rawNames = ((_dossierList && _dossierList.files) || []).map((x)=>x.name);
  const sel = _dossierSel;

  if (sel === "rd03") { _renderRd03Pane(pane); return; }

  const f = files.find((x)=>x.name===sel);
  if (!f) {
    pane.innerHTML = `<div class="editor-empty" style="margin:auto">${t("dossier.select_hint")}</div>`;
    return;
  }
  if (f.kind === "svg") {
    const r = await Backend.get_dossier_svg(f.name);
    if (r && r.ok) renderDossierSvg(pane, {name: f.name, svgText: r.svg});
    else pane.innerHTML = `<div class="editor-empty" style="margin:auto">${escapeHtml((r&&r.msg)||t("gen.could_not_open"))}</div>`;
    return;
  }
  if (f.name.startsWith("04_decision_table")) {
    const r = await Backend.get_decision_table();
    if (r && r.ok) renderDecisionGrid(pane, {name: f.name, headers: r.headers, rows: r.rows});
    else pane.innerHTML = `<div class="editor-empty" style="margin:auto">${escapeHtml((r&&r.msg)||t("gen.could_not_open"))}</div>`;
    return;
  }
  if (f.kind === "md") {
    const r = await Backend.read_file(f.path);
    const twin = f.name.replace(/\.md$/, ".xlsx");
    const twinBtn = rawNames.includes(twin)
      ? `<div style="display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid var(--border)">
           <span class="sm-hint" style="flex:1">${escapeHtml(f.name)}</span>
           <button class="btn-sm" id="fc-md-excel">${t("dossier.open_excel")}</button>
         </div>` : "";
    pane.innerHTML = `<div style="display:flex;flex-direction:column;height:100%">${twinBtn}
      <div style="flex:1;overflow:auto;padding:16px 20px"><div class="md-view">${renderMarkdown((r&&r.text)||"")}</div></div></div>`;
    const xb = pane.querySelector("#fc-md-excel");
    if (xb) xb.addEventListener("click", async ()=>{
      const res = await Backend.open_dossier_file(twin);
      if (!(res && res.ok)) toast(res && res.msg ? res.msg : t("gen.could_not_open"));
    });
    return;
  }
  // xlsx (C&E) / json / pdf — system application
  pane.innerHTML = `
    <div style="margin:auto;text-align:center;color:var(--fg-dim);font-size:12.5px">
      <div style="margin-bottom:10px">${escapeHtml(f.name)} — ${t("dossier.external_only")}</div>
      <button class="btn primary" id="fc-ext-open">${t("dossier.open_external")}</button>
    </div>`;
  const btn = pane.querySelector("#fc-ext-open");
  if (btn) btn.addEventListener("click", async ()=>{
    const res = await Backend.open_dossier_file(f.name);
    if (!(res && res.ok)) toast(res && res.msg ? res.msg : t("gen.could_not_open"));
  });
}

function _renderRd03Pane(pane) {
  const d = _fcData || {};
  if (!d.ok) {
    pane.innerHTML = `<div style="color:var(--fg-dim);font-size:13px;padding:24px;line-height:1.6">
      ${escapeHtml(d.msg || "RD03 (Logic Flow) not found.")}<br>
      Run <b>Retrofit Pre-Analysis</b> (Gate 1) or create
      <span class="mono">metadata/RD03_Flowchart.md</span> from the template first.</div>`;
    return;
  }
  const stepsTableHtml = (d.steps && d.steps.length) ? `
    <div style="overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin-top:10px">
      <table class="fc-step-table">
        <thead><tr>
          <th>ID</th><th>Step Name</th><th>Entry Condition</th>
          <th>Actions</th><th>Exit Condition</th><th>Next</th><th>Status</th>
        </tr></thead>
        <tbody>${d.steps.map(s=>`<tr>
          <td class="fc-id">${escapeHtml(s.id||"")}</td>
          <td class="fc-name">${escapeHtml(s.name||"")}</td>
          <td class="fc-cond">${escapeHtml(s.entry||"")}</td>
          <td class="fc-act">${escapeHtml(s.actions||"")}</td>
          <td class="fc-cond">${escapeHtml(s.exit||"")}</td>
          <td class="fc-next">${escapeHtml(s.next||"")}</td>
          <td><span class="badge ${(s.status||"").includes("UNVERIFIED")?"warn":(s.status||"").toLowerCase().includes("approved")?"ok":""}">${escapeHtml(s.status||"")}</span></td>
        </tr>`).join("")}</tbody>
      </table>
    </div>` : "";

  pane.innerHTML = `<div style="overflow:auto;padding:14px 18px">
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
      <span class="sm-hint" style="flex:1">${t("dossier.rd03_note")}</span>
      <button class="btn" id="fc-regen">${svg("refresh",12)} ${t("dossier.regen_diagram")}</button>
      <button class="btn" id="fc-open">${svg("file-text",12)} ${t("dossier.open_rd03")}</button>
    </div>
    <div class="caps" style="margin:4px 0 6px;display:flex;align-items:center;gap:8px">
      ${t("dossier.section_rd03")}
      <span style="font-weight:400;font-size:10px;color:var(--fg-dim)">${escapeHtml(d.file||"")} · ${d.step_count} steps · ${t("flow.table_truth")}</span>
    </div>
    <div id="fc-diagram" style="border:1px solid var(--border);border-radius:8px;padding:10px;overflow:auto;max-height:46vh"></div>
    ${stepsTableHtml}
    <div class="caps" style="margin:12px 0 4px">${t("dossier.impact_check")}</div>
    <div>${_fcFindingsHtml(d.findings)}</div>
    <div class="caps" style="margin:14px 0 4px">Flow chat (AI) — propose · review · apply</div>
    <div id="fc-chat" style="border:1px solid var(--border);border-radius:8px;padding:10px">
      <div class="sm-hint" style="margin-bottom:6px">Describe a change to the flow steps in plain language. The AI answers with a PROPOSED table (DRAFT_UNVERIFIED) — nothing touches RD03 until you press Apply, and applying demotes the document to DRAFT for re-review.</div>
      <div id="fc-chat-log" style="max-height:26vh;overflow:auto;font-size:12px"></div>
      <div id="fc-chat-proposal" style="display:none;border:1px solid var(--warn,#c90);border-radius:6px;padding:8px;margin:6px 0">
        <div style="font-size:11px;margin-bottom:4px">⚠ <b>Proposal (DRAFT_UNVERIFIED)</b> — review, then apply or discard:</div>
        <pre id="fc-chat-table" style="max-height:20vh;overflow:auto;font-size:11px;margin:0"></pre>
        <div style="margin-top:6px;display:flex;gap:8px">
          <button class="btn primary" id="fc-chat-apply">✓ Apply to RD03 (demotes to DRAFT)</button>
          <button class="btn" id="fc-chat-discard">✗ Discard</button>
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-top:6px">
        <input id="fc-chat-input" type="text" placeholder="e.g. add a purge step between S3 and S4…" style="flex:1"/>
        <button class="btn" id="fc-chat-send">${svg("sparkles",12)} Propose (AI)</button>
      </div>
    </div>
  </div>`;

  const cur = pane.querySelector("#fc-diagram");
  if (cur && d.mermaid) _fcRenderMermaid(cur, d.mermaid);
  const regenBtn = pane.querySelector("#fc-regen");
  if (regenBtn) regenBtn.addEventListener("click", async ()=>{
    const r = await Backend.rd03_regen_mermaid();
    toast(r.msg || (r.ok ? "Diagram regenerated" : "Regen failed"));
    logLine(`[flowchart] regen: ${r.msg||""}`, r.ok ? "success" : "error");
    if (r.ok) showFlowchartView();
  });
  const openBtn = pane.querySelector("#fc-open");
  if (openBtn) openBtn.addEventListener("click", ()=>{
    const tree = STATE && STATE.tree || [];
    const match = tree.find((n) => n.name && n.name.startsWith("RD03"));
    if (match) { setActivePage("explorer"); openFile(match.path); }
    else toast("RD03 — file not found in project tree");
  });

  // G-03 (2026-07-10 audit): rd03_chat_propose/apply were fully functional
  // backend endpoints with no GUI reach. Compact chat: propose → engineer
  // reviews the DRAFT table → explicit Apply (RD03 demotes to DRAFT).
  const chatLog = pane.querySelector("#fc-chat-log");
  const chatIn = pane.querySelector("#fc-chat-input");
  const propBox = pane.querySelector("#fc-chat-proposal");
  const propPre = pane.querySelector("#fc-chat-table");
  const history = [];
  const addLine = (role, text) => {
    const div = document.createElement("div");
    div.style.cssText = "margin:3px 0";
    div.innerHTML = `<b>${role === "user" ? "You" : "AI"}:</b> ${escapeHtml(text)}`;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
  };
  const send = async () => {
    const q = (chatIn.value || "").trim();
    if (!q) return;
    chatIn.value = "";
    addLine("user", q);
    history.push({role: "user", content: q});
    addLine("ai", "…thinking");
    const r = await Backend.rd03_chat_propose(history);
    chatLog.lastChild.remove();
    if (!r.ok) { addLine("ai", r.msg || "Proposal failed"); return; }
    addLine("ai", r.reply || "(proposal below)");
    history.push({role: "assistant", content: r.reply || ""});
    if (r.has_proposal && r.proposed_table) {
      propPre.textContent = r.proposed_table;
      propBox.style.display = "";
    }
  };
  pane.querySelector("#fc-chat-send")?.addEventListener("click", send);
  chatIn?.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  pane.querySelector("#fc-chat-discard")?.addEventListener("click", () => {
    propBox.style.display = "none";
    propPre.textContent = "";
  });
  pane.querySelector("#fc-chat-apply")?.addEventListener("click", async () => {
    const r = await Backend.rd03_chat_apply(propPre.textContent || "");
    toast(r.msg || (r.ok ? "Applied" : "Apply failed"));
    logLine(`[flowchart] chat apply: ${r.msg || ""}`, r.ok ? "success" : "error");
    if (r.ok) showFlowchartView();
  });
}

/* ─────────────────────────────────────────────────────────────────────
   ABOUT MODAL  (M8)
───────────────────────────────────────────────────────────────────── */
function showAbout() {
  if ($("about-overlay")) return;
  const ov=document.createElement("div");
  ov.className="overlay show"; ov.id="about-overlay";
  ov.innerHTML=`<div class="settings-modal" style="width:420px;text-align:center">
    <div class="sm-head"><span class="ic" data-i="factory" data-s="16"></span>About<div class="fill"></div><span class="icon-btn" id="about-close" style="cursor:pointer">${svg("x",14)}</span></div>
    <div class="sm-body" style="padding:28px 32px">
      <div style="width:56px;height:56px;background:var(--accent);border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px">
        <span class="ic" data-i="factory" data-s="28" style="color:#fff"></span>
      </div>
      <div style="font-size:20px;font-weight:700;color:var(--fg);margin-bottom:4px">AUTOMATION FACTORY</div>
      <div style="font-size:12px;color:var(--accent);font-family:var(--mono);margin-bottom:20px">Workbench ${escapeHtml(STATE&&STATE.version||"v3.1.0")}</div>
      <div style="font-size:12px;color:var(--fg-dim);line-height:1.7;margin-bottom:20px">
        Gate-driven IEC 61131-3 automation project toolchain.<br>
        Siemens TIA Portal SCL generation, IO list management,<br>
        AI-assisted engineering, FAT protocol and BOM generation.
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;margin-bottom:24px">
        <div style="background:var(--bg3);border-radius:8px;padding:10px;border:1px solid var(--border)">
          <div style="color:var(--fg-dim);margin-bottom:2px">Runtime</div>
          <div style="color:var(--fg);font-family:var(--mono)">pywebview + Python</div>
        </div>
        <div style="background:var(--bg3);border-radius:8px;padding:10px;border:1px solid var(--border)">
          <div style="color:var(--fg-dim);margin-bottom:2px">Gates</div>
          <div style="color:var(--fg);font-family:var(--mono)">7 engineering phases</div>
        </div>
        <div style="background:var(--bg3);border-radius:8px;padding:10px;border:1px solid var(--border)">
          <div style="color:var(--fg-dim);margin-bottom:2px">AI Modes</div>
          <div style="color:var(--fg);font-family:var(--mono)">Direct API</div>
        </div>
        <div style="background:var(--bg3);border-radius:8px;padding:10px;border:1px solid var(--border)">
          <div style="color:var(--fg-dim);margin-bottom:2px">Standards</div>
          <div style="color:var(--fg);font-family:var(--mono)">IEC 61131-3 · TIA V19</div>
        </div>
      </div>
      <div style="font-size:10px;color:var(--fg-muted)">© 2026 Mehmet Haydar · MIT License</div>
    </div>
  </div>`;
  document.body.appendChild(ov); injectIcons(ov);
  ov.querySelector("#about-close").addEventListener("click",()=>ov.remove());
  ov.addEventListener("click",(e)=>{ if(e.target===ov) ov.remove(); });
}

/* ─────────────────────────────────────────────────────────────────────
   COMMAND PALETTE
───────────────────────────────────────────────────────────────────── */
function openPalette() {
  const ov=$("palette-overlay"); ov.classList.add("show");
  const input=$("palette-input"); input.value=""; input.focus();
  paletteFilter("");
}
function closePalette() { $("palette-overlay").classList.remove("show"); }
function paletteItems() {
  const items=[];
  items.push({icon:"layers",    title:"Workbench",          sub:"View",        run:()=>{ closePalette(); setActivePage("explorer"); }});
  items.push({icon:"chip",      title:"Gate Workspace",     sub:"View · Ctrl+G",run:()=>{ closePalette(); setActivePage("gate"); }});
  items.push({icon:"zap",       title:"Dashboard",          sub:"View",        run:()=>{ closePalette(); setActivePage("dashboard"); }});
  items.push({icon:"file-text", title:"Customer Report",    sub:"View",        run:()=>{ closePalette(); setActivePage("report"); }});
  items.push({icon:"cpu",       title:"Hardware / BOM",     sub:"View",        run:()=>{ closePalette(); setActivePage("hardware"); }});
  items.push({icon:"sparkles",  title:"Prompt Workspace",   sub:"View",        run:()=>{ closePalette(); setActivePage("prompt"); }});
  items.push({icon:"package",   title:"Block Library",      sub:"View",        run:()=>{ closePalette(); setActivePage("library"); }});
  items.push({icon:"sparkles",  title:"Welcome / Onboarding",sub:"View",       run:()=>{ closePalette(); showOnboarding(); }});
  items.push({icon:"git-branch",title:"Git Panel",          sub:"View",        run:()=>{ closePalette(); setActivePage("git"); }});
  items.push({icon:"panel-right",title:"Split Editor",      sub:"View · Ctrl+\\",run:()=>{ closePalette(); enterSplit(); }});
  items.push({icon:"check",     title:"Generate FAT / SAT Protocol",sub:"Action",run:()=>{ closePalette(); runAction("generate_fat"); }});
  items.push({icon:"check",     title:"SISTEMA Records / Prep List",sub:"Action", run:()=>{ closePalette(); runAction("sistema_records"); }});
  items.push({icon:"file-text", title:"CE Assessment (wesentliche Veränderung)",sub:"Action · retrofit",run:()=>{ closePalette(); runAction("generate_ce"); }});
  items.push({icon:"file-text", title:"Generate Customer Report",sub:"Action", run:()=>{ closePalette(); runAction("generate_report"); }});
  // Add gate shortcuts from model
  if (_gateModel) (_gateModel.gates||[]).forEach((g)=>
    items.push({icon:"chip",title:`Gate ${g.n}: ${g.name}`,sub:g.status,run:()=>{ closePalette(); showGateView(g.n); }}));
  _workflows.forEach((wf)=>items.push({icon:"zap",title:wf.name,sub:`Workflow · ${wf.steps} steps`,run:()=>{ closePalette(); runWorkflow(wf.name); }}));
  items.push({icon:"save",      title:"Save File",          sub:"Ctrl+S",      run:()=>{ closePalette(); saveCurrentFile(); }});
  items.push({icon:"search",    title:"Find in File",       sub:"Ctrl+F",      run:()=>{ closePalette(); openFindBar(); }});
  items.push({icon:"file-plus", title:"New File",           sub:"Ctrl+N",      run:()=>{ closePalette(); promptNewFile(""); }});
  items.push({icon:"arrow-right",title:"Next Tab",         sub:"Ctrl+Tab",    run:()=>{ closePalette(); if(OPEN_TABS.length>1){const i=OPEN_TABS.findIndex(t=>t.path===ACTIVE_TAB);if(i>=0){ACTIVE_TAB=OPEN_TABS[(i+1)%OPEN_TABS.length].path;renderTabBar();renderActiveTab();}} }});
  items.push({icon:"settings",  title:"Settings",           sub:"F1",          run:()=>{ closePalette(); openSettings(); }});
  items.push({icon:"factory",   title:"About Automation Factory", sub:"Help",  run:()=>{ closePalette(); showAbout(); }});
  // open tabs
  OPEN_TABS.forEach((t)=>items.push({icon:FILE_ICON[t.kind]||"file", title:t.name, sub:"Open tab", run:()=>{ closePalette(); ACTIVE_TAB=t.path; renderTabBar(); renderActiveTab(); }}));
  // tree files (top-level only)
  (STATE.tree||[]).filter((n)=>n.kind!=="folder").forEach((n)=>
    items.push({icon:FILE_ICON[n.kind]||"file", title:n.name, sub:"File", run:()=>{ closePalette(); openFile(n.path); }}));
  // actions
  (STATE.actions||[]).forEach((a)=>
    items.push({icon:a.icon, title:a.label, sub:"Action", run:()=>{ closePalette(); runAction(a.id); }}));
  return items;
}
async function paletteSearch(q) {
  // fast local filter first
  const items = paletteItems().filter((it)=>it.title.toLowerCase().includes(q));
  // if typing and it looks like a file search, also query backend
  if (q.length>=2) {
    const results = await Backend.search_project(q);
    results.forEach((r)=>{
      if (!items.find((i)=>i.title===r.name)) {
        items.push({icon:FILE_ICON[r.kind]||"file", title:r.name, sub:`${r.match==="content"?`line ${r.line}`:""} ${r.path}`.trim(), run:()=>{ closePalette(); openFile(r.path); }});
      }
    });
  }
  return items;
}
let _palTimer=null;
let _palSelIdx=0;
function _setPalSel(idx) {
  const els=$("palette-results").querySelectorAll(".pal-item");
  if (!els.length) return;
  _palSelIdx=Math.max(0,Math.min(idx,els.length-1));
  els.forEach((el,i)=>el.classList.toggle("sel",i===_palSelIdx));
  els[_palSelIdx]?.scrollIntoView({block:"nearest"});
}
function paletteFilter(q) {
  q=(q||"").toLowerCase();
  _palSelIdx=0;
  const items=paletteItems().filter((it)=>it.title.toLowerCase().includes(q));
  renderPaletteItems(items);
  window._palItems=items;
  if (q.length>=2) {
    clearTimeout(_palTimer);
    _palTimer=setTimeout(async()=>{
      const all=await paletteSearch(q);
      _palSelIdx=0;
      renderPaletteItems(all);
      window._palItems=all;
    },300);
  }
}
function renderPaletteItems(items) {
  $("palette-results").innerHTML=items.slice(0,20).map((it,i)=>
    `<div class="pal-item ${i===_palSelIdx?"sel":""}" data-idx="${i}"><span class="ic" data-i="${it.icon}" data-s="15"></span><span>${escapeHtml(it.title)}</span><span class="sub">${escapeHtml(it.sub)}</span></div>`).join("");
  injectIcons($("palette-results"));
  $("palette-results").querySelectorAll(".pal-item").forEach((el)=>
    el.addEventListener("click",()=>items[+el.getAttribute("data-idx")].run()));
}

/* ─────────────────────────────────────────────────────────────────────
   TOAST
───────────────────────────────────────────────────────────────────── */
let toastTimer=null;
function toast(msg) {
  const t=$("toast"); t.textContent=msg; t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>t.classList.remove("show"),2800);
}

/* ─────────────────────────────────────────────────────────────────────
   INIT
───────────────────────────────────────────────────────────────────── */
let started=false;
let _workflows=[];
async function init() {
  if (started) return;
  started=true;
  if (typeof mermaid !== "undefined") {
    _mmApply();
  }
  STATE = await Backend.get_state();
  render();
  applyTheme(STATE.theme||"dark");
  applyAccent(STATE.accent||"emerald");
  Backend.get_workflows().then((wfs)=>{ _workflows=wfs||[]; });

  // Top bar
  $("btn-theme").addEventListener("click", toggleTheme);
  $("btn-settings").addEventListener("click", openSettings);
  $("cmd-trigger").addEventListener("click", openPalette);
  $("btn-new-project").addEventListener("click", showOnboarding);
  $("btn-open-project").addEventListener("click", openProjectBrowse);
  $("status-gate").addEventListener("click", openGateTimeline);
  $("split-toggle").addEventListener("click", enterSplit);
  $("btn-refresh-tree").addEventListener("click",async()=>{ await refreshProjectState(); toast("Refreshed"); });
  document.addEventListener("click",(e)=>{ if (e.target.id==="ed-mode-btn") toggleEditMode(); });

  // Sidebar new file button
  const btnNewFile = document.querySelector(".sidebar-head .tools .icon-btn");
  if (btnNewFile) btnNewFile.addEventListener("click",()=>promptNewFile(""));

  // Bottom panel tabs
  document.querySelectorAll(".btab").forEach((el)=>el.addEventListener("click",()=>{
    const tab=el.getAttribute("data-tab"); if (!tab) return;
    switchBottomTab(tab);
  }));

  // Activity bar
  document.querySelectorAll(".activitybar .act-btn").forEach((el)=>el.addEventListener("click",()=>{
    const view = el.getAttribute("data-view");
    if (view) setActivePage(view);
  }));

  // Palette
  $("palette-input").addEventListener("input",(e)=>paletteFilter(e.target.value));
  $("palette-input").addEventListener("keydown",(e)=>{
    if (!$("palette-overlay").classList.contains("show")) return;
    if (e.key==="ArrowDown"){ e.preventDefault(); _setPalSel(_palSelIdx+1); }
    else if (e.key==="ArrowUp"){ e.preventDefault(); _setPalSel(_palSelIdx-1); }
    else if (e.key==="Enter"){ e.preventDefault(); if (window._palItems&&window._palItems[_palSelIdx]) window._palItems[_palSelIdx].run(); }
    else if (e.key==="Escape"){ e.preventDefault(); closePalette(); }
  });
  $("palette-overlay").addEventListener("click",(e)=>{ if(e.target===$("palette-overlay")) closePalette(); });

  // Keyboard shortcuts
  document.addEventListener("keydown",(e)=>{
    const mod = e.ctrlKey||e.metaKey;
    if (mod && e.key.toLowerCase()==="k") { e.preventDefault(); openPalette(); return; }
    if (mod && e.key==="\\")             { e.preventDefault(); enterSplit(); return; }
    if (mod && e.key.toLowerCase()==="s"){ e.preventDefault(); saveCurrentFile(); return; }
    if (mod && e.key.toLowerCase()==="w"){ e.preventDefault(); if (ACTIVE_TAB) closeTab(ACTIVE_TAB); return; }
    if (mod && e.key.toLowerCase()==="n"){ e.preventDefault(); promptNewFile(""); return; }
    if (mod && e.key.toLowerCase()==="f"){ e.preventDefault(); if (_find.open) { const fi=$("find-input"); if(fi)fi.focus(); } else openFindBar(); return; }
    if (mod && e.key==="Tab" && OPEN_TABS.length > 1) {
      e.preventDefault();
      const idx = OPEN_TABS.findIndex((t)=>t.path===ACTIVE_TAB);
      if (idx >= 0) {
        const next = e.shiftKey ? (idx - 1 + OPEN_TABS.length) % OPEN_TABS.length : (idx + 1) % OPEN_TABS.length;
        ACTIVE_TAB = OPEN_TABS[next].path; renderTabBar(); renderActiveTab();
      }
      return;
    }
    if (e.key==="Escape") {
      closePalette();
      if (_find.open) { closeFindBar(); return; }
      if (splitMode) exitSplit();
      hideGhostText();
      // Close any open overlay modal (settings, about, new-project)
      const overlay = document.querySelector(".overlay.show:not(#palette-overlay)");
      if (overlay) { overlay.remove(); return; }
      return;
    }
    if (e.key==="F1")                  { e.preventDefault(); openSettings(); return; }
    if (mod && e.key.toLowerCase()==="g"){ e.preventDefault(); setActivePage("gate"); return; }
    if (e.key==="Tab" && AI_GHOST_TEXT) { e.preventDefault(); acceptGhostText(); return; }
  });

  // Panel-bottom toggle (hide/show bottom panel)
  const panelBottomBtn = document.querySelector('.tab-tools .ic[data-i="panel-bottom"]');
  if (panelBottomBtn) {
    let bottomVisible = true;
    panelBottomBtn.style.cursor="pointer";
    panelBottomBtn.addEventListener("click",()=>{
      const bp = document.querySelector(".bottom");
      if (!bp) return;
      bottomVisible = !bottomVisible;
      bp.style.display = bottomVisible ? "" : "none";
      panelBottomBtn.style.opacity = bottomVisible ? "1" : "0.4";
      toast(bottomVisible ? "Bottom panel shown" : "Bottom panel hidden");
    });
  }

  // Right-rail gate section click → gate view
  const gateCapEl = $("gate-caps");
  const gateTitleEl = $("gate-title");
  const gateBarEl = $("gate-bar");
  [gateCapEl, gateTitleEl, gateBarEl].forEach((el)=>{
    if (el) { el.style.cursor="pointer"; el.title="Open Gate Workspace"; el.addEventListener("click",()=>setActivePage("gate")); }
  });

  // Sidebar resizer drag
  const resizer = $("sidebar-resizer");
  const sidebar  = $("sidebar");
  if (resizer && sidebar) {
    let _rx = 0, _sw = 0;
    resizer.addEventListener("mousedown",(e)=>{
      _rx = e.clientX; _sw = sidebar.offsetWidth;
      resizer.classList.add("dragging");
      const onMove=(ev)=>{
        const w = Math.min(480, Math.max(160, _sw + (ev.clientX - _rx)));
        sidebar.style.width = w+"px"; sidebar.style.flex = `0 0 ${w}px`;
      };
      const onUp=()=>{
        resizer.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  // Bottom panel resizer drag
  const bResizer = $("bottom-resizer");
  const bPanel   = $("bottom-panel");
  if (bResizer && bPanel) {
    const BKEY = "bottomPanelHeight";
    const saved = parseInt(localStorage.getItem(BKEY) || "180", 10);
    if (!isNaN(saved)) { bPanel.style.height = saved+"px"; bPanel.style.flex = `0 0 ${saved}px`; }
    let _by = 0, _bh = 0;
    bResizer.addEventListener("mousedown", (e) => {
      _by = e.clientY; _bh = bPanel.offsetHeight;
      bResizer.classList.add("dragging");
      document.body.style.cursor = "ns-resize";
      const onMove = (ev) => {
        const h = Math.min(window.innerHeight * 0.6, Math.max(80, _bh - (ev.clientY - _by)));
        bPanel.style.height = h+"px"; bPanel.style.flex = `0 0 ${h}px`;
      };
      const onUp = () => {
        bResizer.classList.remove("dragging");
        document.body.style.cursor = "";
        localStorage.setItem(BKEY, bPanel.offsetHeight);
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
  }

  // Auto-open a default file so the editor isn't empty on launch
  const defPath = STATE.default_file||((STATE.tree||[]).find((n)=>n.kind!=="folder")||{}).path;
  if (defPath) openFile(defPath);

  // Auto-show onboarding if no project loaded; else populate gate nav bar
  if (!STATE.project_path) {
    setActivePage("explorer");
    showOnboarding();
  } else {
    _refreshGateModel();
  }
}

injectIcons();
applyI18n();   // interface language (EN/TR/DE) — static chrome, before init
// Denetim G-01 fix (2026-07-10): the old code raced a blind `setTimeout(init,
// 900)` against the real `pywebviewready` event. On a slow machine (large
// project tree, AV scanning the exe, first-run JIT) the timeout could fire
// FIRST — init() then ran with Backend.ready()===false, silently rendering
// SAMPLE/demo data (fake "demo_project"), and the `started` guard inside
// init() made it a permanent no-op once the real pywebviewready event
// finally arrived: the engineer would be stuck looking at demo data with no
// visible error. Fix: actively poll for window.pywebview.api instead of
// guessing a fixed delay, and — if pywebview never shows up within a long
// grace period (true plain-browser preview) — remember that and force a
// full state refresh the moment pywebviewready does eventually fire.
let _bootFellBackToDemo = false;
function _pollForPywebviewThenInit(elapsedMs) {
  if (window.pywebview && window.pywebview.api) { init(); return; }
  const GRACE_MS = 15000; // generous: covers slow cold starts, not just 900ms
  if (elapsedMs >= GRACE_MS) {
    console.warn("[boot] window.pywebview.api not detected after " + GRACE_MS +
      "ms — starting in browser/demo mode (sample data) until it appears.");
    _bootFellBackToDemo = true;
    init();
    return;
  }
  setTimeout(() => _pollForPywebviewThenInit(elapsedMs + 150), 150);
}
window.addEventListener("pywebviewready", () => {
  if (_bootFellBackToDemo) {
    // The real backend showed up late, after we already rendered demo data —
    // replace it with the real project state instead of leaving the UI stuck.
    _bootFellBackToDemo = false;
    refreshProjectState();
    try { toast("Backend connected — refreshed with live project data"); } catch(_) {}
  } else {
    init();
  }
});
if (window.pywebview && window.pywebview.api) init();
else _pollForPywebviewThenInit(0);
