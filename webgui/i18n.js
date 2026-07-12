/* i18n.js — Workbench interface language (EN/TR/DE).
   Scope: UI chrome (menus, panels, dialogs, settings). Terminal/log lines
   and technical identifiers stay English by design — they are support
   material and grep targets. Fallback is always English.
   Loaded BEFORE app.js; exposes t(), applyI18n(), setUiLang(), UI_LANG. */
"use strict";

const I18N_LANGS = [
  ["en", "English"], ["tr", "Türkçe"], ["de", "Deutsch"],
];

const I18N = {
  /* ---- topbar ---- */
  "top.new_project":   {en: "New Project", tr: "Yeni Proje", de: "Neues Projekt"},
  "top.open_project":  {en: "Open Project", tr: "Proje Aç", de: "Projekt öffnen"},
  "top.toggle_theme":  {en: "Toggle theme", tr: "Tema değiştir", de: "Design umschalten"},
  "top.settings":      {en: "Settings", tr: "Ayarlar", de: "Einstellungen"},
  "top.search":        {en: "Search files, prompts, gates…", tr: "Dosya, prompt, gate ara…", de: "Dateien, Prompts, Gates suchen…"},

  /* ---- activity bar ---- */
  "act.group_project": {en: "PROJECT", tr: "PROJE", de: "PROJEKT"},
  "act.group_library": {en: "LIBRARY", tr: "KÜTÜPHANE", de: "BIBLIOTHEK"},
  "act.explorer":      {en: "Explorer — project files", tr: "Gezgin — proje dosyaları", de: "Explorer — Projektdateien"},
  "act.dashboard":     {en: "Dashboard — project status", tr: "Pano — proje durumu", de: "Dashboard — Projektstatus"},
  "act.gates":         {en: "Gates — gate workflow", tr: "Gate'ler — kapı akışı", de: "Gates — Gate-Workflow"},
  "act.flowchart":     {en: "Machine Dossier — visual pack + decision table + RD03 sequence",
                        tr: "Makine Dosyası — görsel paket + karar tablosu + RD03 dizisi",
                        de: "Maschinenakte — Visualpaket + Entscheidungstabelle + RD03-Folge"},
  "act.report":        {en: "Report — customer output", tr: "Rapor — müşteri çıktısı", de: "Bericht — Kundenausgabe"},
  "act.git":           {en: "Git — version control", tr: "Git — sürüm kontrolü", de: "Git — Versionsverwaltung"},
  "act.vcompare":      {en: "Version Compare — diff legacy project version folders", tr: "Sürüm Karşılaştır — eski sürüm klasörlerini kıyasla", de: "Versionsvergleich — Altprojekt-Stände vergleichen"},
  "act.prompts":       {en: "Prompts — AI prompt workspace", tr: "Prompt'lar — AI prompt çalışma alanı", de: "Prompts — KI-Prompt-Arbeitsbereich"},
  "act.library":       {en: "Library — reference FB library", tr: "Kütüphane — referans FB kütüphanesi", de: "Bibliothek — Referenz-FB-Bibliothek"},
  "act.hardware":      {en: "Hardware — BOM and device specs", tr: "Donanım — BOM ve cihaz verileri", de: "Hardware — Stückliste und Gerätedaten"},

  /* ---- sidebar ---- */
  "side.explorer":     {en: "Explorer", tr: "Gezgin", de: "Explorer"},
  "side.reports":      {en: "Reports", tr: "Raporlar", de: "Berichte"},
  "side.workdesk":     {en: "Workdesk", tr: "Çalışma Masası", de: "Arbeitsplatz"},
  "side.reading":      {en: "Review (read-only)", tr: "İnceleme (salt okuma)", de: "Prüfung (nur lesen)"},
  "side.dossier":      {en: "Machine Dossier", tr: "Makine Dosyası", de: "Maschinenakte"},
  "side.dossier_gen":  {en: "Generate Machine Dossier (deterministic — operator flow, block structure, GRAFCET, decision table, summary, C&E)",
                        tr: "Makine Dosyası üret (deterministik — kullanım akışı, blok yapısı, GRAFCET, karar tablosu, özet, C&E)",
                        de: "Maschinenakte erzeugen (deterministisch — Bedienablauf, Bausteinstruktur, GRAFCET, Entscheidungstabelle, Übersicht, C&E)"},
  "side.dossier_empty":{en: "Not generated yet — press ↻ above. Deterministic; no AI.",
                        tr: "Henüz üretilmedi — üstteki ↻ düğmesine bas. Deterministik; AI yok.",
                        de: "Noch nicht erzeugt — oben ↻ drücken. Deterministisch, ohne KI."},
  "side.handover":     {en: "Export handover package (ZIP)", tr: "Teslim paketi dışa aktar (ZIP)", de: "Übergabemappe exportieren (ZIP)"},
  "side.qa_ph":        {en: "Ask the project… (tag, operand, device)", tr: "Projeye sor… (etiket, operand, cihaz)", de: "Projekt fragen… (Tag, Operand, Gerät)"},
  "side.qa_btn":       {en: "Ask", tr: "Sor", de: "Fragen"},

  /* ---- gate nav / right rail ---- */
  "gnb.timeline":      {en: "Timeline", tr: "Zaman çizgisi", de: "Zeitleiste"},
  "rr.next_step":      {en: "Next step", tr: "Sıradaki adım", de: "Nächster Schritt"},
  "rr.actions":        {en: "Actions", tr: "Eylemler", de: "Aktionen"},
  "rr.actions_project": {en: "Project actions", tr: "Proje eylemleri", de: "Projekt-Aktionen"},
  "rr.actions_file":   {en: "File actions", tr: "Dosya eylemleri", de: "Datei-Aktionen"},
  "rr.gate_hint":      {en: "Gates = the 7-step quality workflow — each gate must be completed (and approved where required) before the next",
                        tr: "Gate'ler = 7 adımlı kalite akışı — her kapı, sıradakinden önce tamamlanmalı (gerekli yerlerde onaylanmalı)",
                        de: "Gates = der 7-stufige Qualitätsworkflow — jedes Gate muss vor dem nächsten abgeschlossen (und ggf. freigegeben) sein"},

  /* ---- editor / bottom panel ---- */
  "ed.empty":          {en: "Select a file from the Explorer — or press ⌘K", tr: "Gezgin'den bir dosya seç — veya ⌘K'ya bas", de: "Datei im Explorer wählen — oder ⌘K drücken"},
  "ed.saved":          {en: "● Saved", tr: "● Kaydedildi", de: "● Gespeichert"},
  "ed.mode":           {en: "Edit", tr: "Düzenle", de: "Bearbeiten"},
  "ed.mode_hint":      {en: "Toggle edit / preview mode", tr: "Düzenleme / önizleme değiştir", de: "Bearbeiten / Vorschau umschalten"},
  "bt.inspector":      {en: "Inspector", tr: "Denetçi", de: "Inspektor"},
  "bt.diagnostics":    {en: "Diagnostics", tr: "Tanılar", de: "Diagnose"},
  "bt.ai_preview":     {en: "AI Preview", tr: "AI Önizleme", de: "KI-Vorschau"},
  "bt.terminal":       {en: "Terminal", tr: "Terminal", de: "Terminal"},

  /* ---- palette ---- */
  "pal.ph":            {en: "Go to file, prompt, gate or action…", tr: "Dosyaya, prompt'a, gate'e veya eyleme git…", de: "Zu Datei, Prompt, Gate oder Aktion springen…"},

  /* ---- settings ---- */
  "set.title":         {en: "Settings", tr: "Ayarlar", de: "Einstellungen"},
  "set.appearance":    {en: "Appearance", tr: "Görünüm", de: "Darstellung"},
  "set.language":      {en: "Interface language", tr: "Arayüz dili", de: "Oberflächensprache"},
  "set.language_hint": {en: "Menus and panels. Terminal/log lines stay English (support material).",
                        tr: "Menüler ve paneller. Terminal/log satırları İngilizce kalır (destek materyali).",
                        de: "Menüs und Panels. Terminal-/Log-Zeilen bleiben Englisch (Support-Material)."},
  "set.dark":          {en: "Dark", tr: "Koyu", de: "Dunkel"},
  "set.light":         {en: "Light", tr: "Açık", de: "Hell"},
  "set.accent":        {en: "Accent colour", tr: "Vurgu rengi", de: "Akzentfarbe"},
  "set.profile":       {en: "Profile", tr: "Profil", de: "Profil"},
  "set.your_name":     {en: "Your name", tr: "Adın", de: "Ihr Name"},
  "set.name_ph":       {en: "shown on reports and sign-offs", tr: "raporlarda ve imzalarda görünür", de: "erscheint auf Berichten und Freigaben"},

  /* ---- dialogs the user must understand (were hardcoded Turkish) ---- */
  "dlg.push_conf_head": {
    en: "This project is classified CONFIDENTIAL/RESTRICTED.",
    tr: "Bu proje gizli/kısıtlı olarak sınıflandırılmış.",
    de: "Dieses Projekt ist als VERTRAULICH/EINGESCHRÄNKT eingestuft."},
  "dlg.push_conf_tail": {
    en: "If the remote is a private/company server you may continue.\nIf it is a public host (GitHub public, GitLab.com) cancel now.\n\nConfirm push to the private/company server?",
    tr: "Hedef uzak depo özel/kurumsal bir sunucuysa devam edebilirsiniz.\nGenel bir sunucuysa (GitHub public, GitLab.com) iptal edin.\n\nÖzel/kurumsal sunucuya push'u onaylıyor musunuz?",
    de: "Ist das Remote ein privater/Firmen-Server, können Sie fortfahren.\nBei einem öffentlichen Host (GitHub public, GitLab.com) jetzt abbrechen.\n\nPush auf den privaten/Firmen-Server bestätigen?"},
  "dlg.push_cancelled": {en: "Push cancelled (privacy guard)", tr: "Push iptal edildi (gizlilik koruması)", de: "Push abgebrochen (Datenschutz)"},
  "dlg.rd_no_metadata": {en: "— metadata file not created yet", tr: "— metadata dosyası henüz oluşturulmadı", de: "— Metadatendatei noch nicht erstellt"},
  "dlg.safety_kb_warn": {en: "SAFETY KB Warning", tr: "SAFETY KB Uyarısı", de: "SAFETY-KB-Warnung"},
  "dlg.safety_kb_body": {
    en: "critical safety record(s) found. A note was added to the document.",
    tr: "kritik güvenlik kaydı bulundu. Dokümana not eklendi.",
    de: "kritische Sicherheitseinträge gefunden. Ein Hinweis wurde ins Dokument eingefügt."},
  "dlg.acknowledge":    {en: "Seen — continue", tr: "Gördüm, devam et", de: "Gesehen — weiter"},

  /* ---- machine dossier in-app views ---- */
  "dossier.page_sub":  {en: "Approval-side visual pack — device decisions edit in the table; the RD03 step sequence below stays the contract",
                        tr: "Onay tarafı görsel paket — cihaz kararları tabloda düzenlenir; alttaki RD03 adım dizisi sözleşme olarak kalır",
                        de: "Visualpaket der Freigabeseite — Geräteentscheidungen werden in der Tabelle bearbeitet; die RD03-Schrittfolge unten bleibt der Vertrag"},
  "dossier.section_pack": {en: "Visual pack", tr: "Görsel paket", de: "Visualpaket"},
  "dossier.section_rd03": {en: "RD03 — step sequence (contract, read-only here)",
                        tr: "RD03 — adım dizisi (sözleşme, burada salt-okunur)",
                        de: "RD03 — Schrittfolge (Vertrag, hier schreibgeschützt)"},
  "dossier.step_sequence": {en: "Step sequence", tr: "Adım dizisi", de: "Schrittfolge"},
  "dossier.select_hint": {en: "Select a page from the left", tr: "Soldan bir sayfa seç", de: "Links eine Seite wählen"},
  "dossier.impact_check": {en: "Impact check (deterministic)", tr: "Etki kontrolü (deterministik)", de: "Auswirkungsprüfung (deterministisch)"},
  "dossier.regen_diagram": {en: "Regen RD03 diagram", tr: "RD03 diyagramını yeniden üret", de: "RD03-Diagramm neu erzeugen"},
  "dossier.open_rd03":  {en: "Open RD03", tr: "RD03'ü aç", de: "RD03 öffnen"},
  "dossier.external_only": {en: "opens in its system application", tr: "sistem uygulamasında açılır", de: "öffnet in der System-Anwendung"},
  "dossier.rd03_note":  {en: "Legacy view — this mermaid diagram is the OLD RD03 story (AI-drafted, cross-checked against the proven chain). The NEW deterministic pages are the GRAFCET SVGs in the list above.",
                        tr: "Eski görünüm — bu mermaid diyagramı ESKİ RD03 hikâyesi (AI taslağı, kanıtlı zincire karşı çapraz-kontrollü). YENİ deterministik sayfalar üstteki listedeki GRAFCET SVG'leri.",
                        de: "Alte Ansicht — dieses Mermaid-Diagramm ist die ALTE RD03-Darstellung (KI-Entwurf, gegen die bewiesene Kette geprüft). Die NEUEN deterministischen Seiten sind die GRAFCET-SVGs in der Liste oben."},
  "dossier.view_hint": {en: "delivery view — edits happen in the decision table, the diagram regenerates",
                        tr: "teslim görünümü — düzenleme karar tablosunda yapılır, diyagram yeniden üretilir",
                        de: "Lieferansicht — Änderungen erfolgen in der Entscheidungstabelle, das Diagramm wird neu erzeugt"},
  "dossier.open_external": {en: "Open externally", tr: "Dışarıda aç", de: "Extern öffnen"},
  "dossier.open_excel": {en: "Open in Excel", tr: "Excel'de aç", de: "In Excel öffnen"},
  "dossier.save_decisions": {en: "Save decisions", tr: "Kararları kaydet", de: "Entscheidungen speichern"},
  "dossier.saved":     {en: "Decisions saved", tr: "Kararlar kaydedildi", de: "Entscheidungen gespeichert"},
  "dossier.grid_hint": {en: "Only the two DECISION columns are editable — deterministic cells are locked. Your entries persist in decisions.json across regenerations.",
                        tr: "Yalnız iki KARAR sütunu yazılabilir — deterministik hücreler kilitli. Girdilerin decisions.json'da saklanır, yeniden üretimde silinmez.",
                        de: "Nur die zwei ENTSCHEIDUNGS-Spalten sind editierbar — deterministische Zellen sind gesperrt. Ihre Einträge bleiben in decisions.json über Neuerzeugungen erhalten."},

  /* ---- flowchart view ---- */
  "flow.table_truth":  {en: "table is the source of truth — the diagram derives from it",
                        tr: "tablo kaynak gerçek — diyagram buradan türetilir",
                        de: "die Tabelle ist die Quelle — das Diagramm wird daraus abgeleitet"},

  /* ---- generic ---- */
  "gen.generate":      {en: "Generate", tr: "Üret", de: "Erzeugen"},
  "gen.open":          {en: "Open", tr: "Aç", de: "Öffnen"},
  "gen.close":         {en: "Close", tr: "Kapat", de: "Schließen"},
  "gen.cancel":        {en: "Cancel", tr: "İptal", de: "Abbrechen"},
  "gen.save":          {en: "Save", tr: "Kaydet", de: "Speichern"},
  "gen.could_not_open":{en: "Could not open file", tr: "Dosya açılamadı", de: "Datei konnte nicht geöffnet werden"},
};

let UI_LANG = "en";
try {
  const stored = localStorage.getItem("ui_lang");
  if (stored && I18N_LANGS.some(([c]) => c === stored)) UI_LANG = stored;
} catch (e) { /* localStorage unavailable — stay English */ }

function t(key) {
  const e = I18N[key];
  if (!e) return key;
  return e[UI_LANG] || e.en || key;
}

function applyI18n(rootEl) {
  const root = rootEl || document;
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  root.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.getAttribute("data-i18n-title"));
  });
  root.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = t(el.getAttribute("data-i18n-ph"));
  });
}

function setUiLang(lang) {
  if (!I18N_LANGS.some(([c]) => c === lang)) return;
  UI_LANG = lang;
  try { localStorage.setItem("ui_lang", lang); } catch (e) { /* ok */ }
  applyI18n();
}
