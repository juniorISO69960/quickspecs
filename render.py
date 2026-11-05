"""Builds the spec sheet HTML page and the plain-text listing."""

import datetime
import json
from html import escape


CSS = """
:root{--ink:#16191f;--muted:#5f6672;--faint:#8a919c;--line:#e4e7ec;--bg:#eef0f3;--card:#fff;--tile:#f8f9fb;
--accent:#2563eb;--good:#15803d;--good-bg:#e7f6ec;--warn:#b45309;--warn-bg:#fdf3e3;--bad:#c62828;--bad-bg:#fdecec;}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 "Segoe UI",system-ui,-apple-system,sans-serif}
.toolbar{position:sticky;top:0;z-index:5;display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  padding:10px 16px;background:#16191f;color:#fff;font-size:14px}
.toolbar .name{font-weight:600;margin-right:auto}
.toolbar button{font:inherit;font-weight:600;border:0;border-radius:8px;padding:8px 14px;cursor:pointer;background:#fff;color:#16191f}
.toolbar a.btn{font-weight:600;border-radius:8px;padding:8px 14px;background:#fff;color:#16191f;text-decoration:none}
.toolbar button.primary{background:var(--accent);color:#fff}
.toolbar label{display:flex;gap:6px;align-items:center;cursor:pointer;user-select:none}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#16191f;color:#fff;padding:10px 18px;
  border-radius:10px;font-size:14px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.show{opacity:1}
.sheet{max-width:980px;margin:24px auto;background:var(--card);border-radius:18px;padding:40px 44px 28px;
  box-shadow:0 1px 2px rgba(0,0,0,.05),0 8px 30px rgba(0,0,0,.06)}
header{display:flex;gap:24px;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--ink);padding-bottom:22px}
.brand{font-size:15px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
h1{font-size:40px;line-height:1.1;margin:4px 0 10px;font-weight:750;letter-spacing:-.01em}
.tagline{font-size:16px;color:var(--muted);margin:-2px 0 12px}
.tagline b{color:var(--ink);font-family:Consolas,"Cascadia Mono",monospace;font-size:17px;letter-spacing:.04em}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-size:13.5px;font-weight:600;padding:4px 11px;border-radius:999px;background:var(--tile);border:1px solid var(--line)}
.chip.good{background:var(--good-bg);border-color:transparent;color:var(--good)}
.chip.bad{background:var(--bad-bg);border-color:transparent;color:var(--bad)}
.chip.warn{background:var(--warn-bg);border-color:transparent;color:var(--warn)}
.price{min-width:200px;text-align:right}
.price .lbl{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.price .amt{font-size:34px;font-weight:750;line-height:1.15;outline:none;min-width:120px;display:inline-block}
.editable{border-radius:6px;transition:background .15s}
.editable:hover,.editable:focus{background:#f1f5ff}
.editable:empty::before{content:attr(data-placeholder);color:#b6bcc6;font-weight:500}
h2{font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin:28px 0 12px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.tile{background:var(--tile);border:1px solid var(--line);border-radius:14px;padding:16px 18px;min-height:112px}
.tile .lbl{font-size:12.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;gap:7px;align-items:center}
.tile .lbl svg{width:16px;height:16px;flex:none}
.tile .val{font-size:22px;font-weight:700;line-height:1.25;margin-top:6px}
.tile .sub{font-size:14px;color:var(--muted);margin-top:3px}
.tile .sub + .sub{margin-top:1px}
.bar{height:8px;border-radius:99px;background:#e3e6eb;margin-top:10px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:99px}
.good-t{color:var(--good)}.warn-t{color:var(--warn)}.bad-t{color:var(--bad)}.muted-t{color:var(--muted)}
.bg-good{background:var(--good)}.bg-warn{background:var(--warn)}.bg-bad{background:var(--bad)}.bg-muted{background:var(--faint)}
.two{display:grid;grid-template-columns:1.1fr 1fr;gap:12px}
.features{display:grid;grid-template-columns:repeat(2,1fr);gap:8px 18px;list-style:none;padding:0;margin:10px 0 0}
.features li{display:flex;gap:9px;align-items:center;font-size:15.5px;font-weight:600}
.features li.no{color:var(--faint);font-weight:500}
.mark{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;flex:none;font-size:13px;font-weight:800}
.yes .mark{background:var(--good-bg);color:var(--good)}
.no .mark{background:#f0f1f3;color:#a3a9b2}
.win .val{font-size:20px}
.notes{min-height:48px;padding:10px 12px;border:1px dashed var(--line);border-radius:12px;font-size:15px;white-space:pre-wrap;outline:none}
.details{columns:2;column-gap:28px}
.dsec{break-inside:avoid;margin-bottom:18px}
.dsec h3{font-size:15px;margin:0 0 6px;padding-bottom:5px;border-bottom:1px solid var(--line)}
.dsec table{width:100%;border-collapse:collapse;font-size:13.5px}
.dsec td{padding:4px 0;vertical-align:top}
.dsec td:first-child{color:var(--muted);width:40%;padding-right:12px}
.dsec td:last-child{word-break:break-word}
.serial-real{display:none}
body.show-serial .serial-real{display:inline}
body.show-serial .serial-mask{display:none}
.serial-mask{color:var(--faint);font-style:italic}
.note{font-size:13px;color:var(--warn);background:var(--warn-bg);border-radius:10px;padding:8px 12px;margin-top:12px}
footer{margin-top:22px;padding-top:12px;border-top:1px solid var(--line);font-size:12.5px;color:var(--faint);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:760px){
  .sheet{margin:0;border-radius:0;padding:24px 16px}
  header{flex-direction:column}.price{text-align:left}
  h1{font-size:30px}.grid{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}.details{columns:1}
}
@media (max-width:460px){.grid{grid-template-columns:1fr}.features{grid-template-columns:1fr}}
@media print{
  @page{margin:12mm}
  body{background:#fff;font-size:14px}
  .toolbar,.toast,.no-print{display:none!important}
  .sheet{box-shadow:none;margin:0;padding:0;max-width:none;border-radius:0}
  .price:has(.amt:empty),.notes-wrap:has(.notes:empty){display:none}
  .editable:empty::before{content:""}
  .tile,.dsec{break-inside:avoid}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

JS = """
const KEY = 'quickspecs:' + location.pathname;
function load(){ try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch(e){ return {}; } }
function save(){ try { localStorage.setItem(KEY, JSON.stringify({
  price: document.getElementById('price').innerText.trim(),
  notes: document.getElementById('notes').innerText.trim(),
  serial: document.body.classList.contains('show-serial') })); } catch(e){} }
const st = load();
if (st.price) document.getElementById('price').innerText = st.price;
if (st.notes) document.getElementById('notes').innerText = st.notes;
const serialBox = document.getElementById('serialToggle');
if (serialBox){ const on = st.serial !== false; serialBox.checked = on; document.body.classList.toggle('show-serial', on);
  serialBox.addEventListener('change', () => { document.body.classList.toggle('show-serial', serialBox.checked); save(); }); }
for (const id of ['price','notes']) {
  const el = document.getElementById(id);
  el.addEventListener('input', save);
  el.addEventListener('paste', e => { e.preventDefault(); document.execCommand('insertText', false, e.clipboardData.getData('text/plain')); });
}
document.getElementById('price').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); } });

function toast(msg){ const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 1800); }
function listingText(){
  let text = LISTING;
  const price = document.getElementById('price').innerText.trim();
  const notes = document.getElementById('notes').innerText.trim();
  if (document.body.classList.contains('show-serial') && SERIAL) text = text.replace(/\\n/, '\\n' + SERIAL + '\\n');
  if (notes) text += '\\n\\nNotes:\\n' + notes;
  if (price) text = text.replace(/\\n/, '\\nPrice: ' + price + '\\n');
  return text;
}
async function copyListing(){
  const text = listingText();
  try { await navigator.clipboard.writeText(text); }
  catch(e){ const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  toast('Listing text copied — paste it into your ad');
}
document.getElementById('copyBtn').addEventListener('click', copyListing);
document.getElementById('printBtn').addEventListener('click', () => window.print());
"""

ICONS = {
    "cpu": '<path d="M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2"/><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    "ram": '<rect x="2" y="7" width="20" height="10" rx="1.5"/><path d="M6 11v2M10 11v2M14 11v2M18 11v2M5 17v2M19 17v2"/>',
    "disk": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="12" cy="11" r="3.5"/><path d="M7 17h2"/>',
    "gpu": '<rect x="2" y="6" width="20" height="11" rx="2"/><circle cx="9" cy="11.5" r="3"/><path d="M15 9.5h4M15 13.5h4M5 17v3"/>',
    "display": '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M1 19h22"/>',
    "battery": '<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 11v2M5 10v4M8 10v4"/>',
    "network": '<path d="M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r="1"/>',
    "windows": '<path d="M3 5.5 10 4.5v7H3zM12 4.2 21 3v8.5h-9zM3 12.5h7v7l-7-1zM12 12.5h9V21l-9-1.3z"/>',
}


def icon(name):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def tile(kind, label, value, subs=(), extra=""):
    sub_html = "".join(f'<div class="sub">{escape(s)}</div>' for s in subs if s)
    return (f'<div class="tile"><div class="lbl">{icon(kind)}{escape(label)}</div>'
            f'<div class="val">{escape(value)}</div>{sub_html}{extra}</div>')


def storage_summary(disks):
    if not disks:
        return "Unknown", []
    main = disks[0]
    value = " ".join(x for x in [main["size"], main["kind"]] if x)
    subs = []
    if len(disks) > 1:
        subs.append("+ " + ", ".join(" ".join(x for x in [d["size"], d["kind"]] if x) for d in disks[1:]))
    if main["life"] is not None:
        subs.append(f"{main['life']}% life left · {main['health'] or ''}".strip(" ·"))
    elif main["health"]:
        subs.append(f"Drive health: {main['health']}")
    return value, subs


def gpu_summary(gpus):
    if not gpus:
        return "Unknown", []
    main = gpus[0]
    subs = [" · ".join(x for x in [main["memory"], main["kind"]] if x)]
    if len(gpus) > 1:
        subs.append("+ " + ", ".join(g["name"] for g in gpus[1:]))
    return main["name"], subs


def listing_text(sp):
    title = " ".join(x for x in [sp["brand"], sp["model"]] if x)
    lines = [title, ""]
    lines.append(f"• Processor: {sp['cpu']['value']}" + (f" ({sp['cpu']['sub']})" if sp['cpu']['sub'] else ""))
    lines.append(f"• Memory: {sp['ram']['value']}" + (f" {sp['ram']['sub'].split(' · ')[0]}" if sp['ram']['sub'] else ""))
    if sp["disks"]:
        lines.append("• Storage: " + " + ".join(" ".join(x for x in [d["size"], d["kind"]] if x) for d in sp["disks"]))
    if sp["gpus"]:
        lines.append("• Graphics: " + " + ".join(g["name"] + (f" {g['memory']}" if g["memory"] else "") for g in sp["gpus"]))
    if sp["display"]:
        lines.append(f"• Display: {sp['display']['value']}" + (f" ({sp['display']['sub']})" if sp['display']['sub'] else ""))
    b = sp["battery"]
    if b and b["health_pct"] is not None:
        extra = f", {b['cycles']} cycles" if b["cycles"] else ""
        lines.append(f"• Battery health: {b['health_pct']}% ({b['label'].split(' —')[0]}{extra})")
    w = sp["windows"]
    act = " — activated" if w["activated"] else (" — NOT activated" if w["activated"] is False else "")
    lines.append(f"• {w['name']}" + (f" {w['version'].split(' · ')[0]}" if w["version"] else "") + act)
    have = [name for name, ok in sp["features"] if ok]
    if have:
        lines.append("• Features: " + ", ".join(have))
    return "\n".join(lines)


def text_file(sp):
    """Plain-text file: the short eBay section to paste, then every detail."""
    _, serial_text = serial_bits(sp)
    simple = listing_text(sp).split("\n")
    if serial_text:
        simple.insert(1, serial_text)
    rule = "=" * 60
    out = [rule, "FOR EBAY (copy and paste this part)", rule, "", *simple, "", "", rule, "FULL DETAILS", rule]
    for title, rows in sp["details"]:
        out += ["", title.upper(), "-" * len(title)]
        width = max(len(k) for k, _ in rows)
        for k, v in rows:
            if isinstance(v, tuple):
                v = v[1]
            out.append(f"{k.ljust(width)}  {v}")
    now = datetime.datetime.now()
    out += ["", "", f"Specs read directly from this computer's hardware by QuickSpecs · {now:%Y-%m-%d}"]
    return "\n".join(out) + "\n"


def blocks(sp):
    """Header chips, key-spec tiles, Windows card and features card — shared by the page and the eBay image."""
    # Header chips
    w = sp["windows"]
    chips = [f'<span class="chip">{escape(sp["device_type"])}</span>']
    if w["name"]:
        chips.append(f'<span class="chip">{escape(w["name"])}</span>')
    if w["activated"] is True:
        chips.append('<span class="chip good">✓ Windows activated</span>')
    elif w["activated"] is False:
        chips.append(f'<span class="chip bad">✗ Windows {escape(w["status"].lower())}</span>')
    b = sp["battery"]
    if b and b["health_pct"] is not None:
        chips.append(f'<span class="chip {b["tone"]}">Battery health {b["health_pct"]}%</span>')

    # Main tiles
    disk_val, disk_subs = storage_summary(sp["disks"])
    gpu_val, gpu_subs = gpu_summary(sp["gpus"])
    tiles = [
        tile("cpu", "Processor", sp["cpu"]["value"], [sp["cpu"]["sub"]]),
        tile("ram", "Memory (RAM)", sp["ram"]["value"], [sp["ram"]["sub"]]),
        tile("disk", "Storage", disk_val, disk_subs),
        tile("gpu", "Graphics", gpu_val, gpu_subs),
    ]
    d = sp["display"]
    if d:
        subs = [d["sub"]]
        if d.get("external"):
            subs.append("Unplug external monitors for exact screen info")
        tiles.append(tile("display", "Display", d["value"], subs))
    else:
        tiles.append(tile("display", "Display", "Not detected"))
    if b:
        if b["health_pct"] is not None:
            bar = (f'<div class="bar"><i class="bg-{b["tone"]}" style="width:{b["health_pct"]}%"></i></div>')
            subs = [f"{b['full_wh']:.1f} of {b['design_wh']:.1f} Wh original" if b["full_wh"] and b["design_wh"] else None,
                    f"{b['cycles']:,} charge cycles" if b["cycles"] else None]
            sub_html = "".join(f'<div class="sub">{escape(s)}</div>' for s in subs if s)
            tiles.append(f'<div class="tile"><div class="lbl">{icon("battery")}Battery health</div>'
                         f'<div class="val {b["tone"]}-t">{b["health_pct"]}% · {escape(b["label"])}</div>{bar}{sub_html}</div>')
        else:
            tiles.append(tile("battery", "Battery health", "Present", ["Health data not reported"]))
    elif sp["is_laptop"]:
        tiles.append(tile("battery", "Battery", "Not detected", ["Battery may be missing or disconnected"]))
    else:
        tiles.append(tile("network", "Network", sp["network"]["value"], [sp["network"]["sub"]]))

    # Windows + features
    act_cls = "good-t" if w["activated"] else ("bad-t" if w["activated"] is False else "muted-t")
    act_mark = "✓ " if w["activated"] else ("✗ " if w["activated"] is False else "")
    win_card = (f'<div class="tile win"><div class="lbl">{icon("windows")}Windows</div>'
                f'<div class="val">{escape(w["name"])}</div>'
                f'<div class="sub">{escape(w["version"])}</div>'
                f'<div class="sub {act_cls}" style="font-weight:700;margin-top:8px">{act_mark}{escape(w["status"])}</div>'
                + (f'<div class="sub">License: {escape(w["channel"])}</div>' if w["channel"] else "")
                + '</div>')
    feats = "".join(
        f'<li class="{"yes" if ok else "no"}"><span class="mark">{"✓" if ok else "–"}</span>{escape(name)}</li>'
        for name, ok in sp["features"])
    feat_card = f'<div class="tile feat"><div class="lbl">Features</div><ul class="features">{feats}</ul></div>'
    return chips, tiles, win_card, feat_card


def serial_bits(sp):
    """Returns (header line HTML, plain text) for the serial / Dell Service Tag."""
    if not sp["serial"]:
        return "", ""
    label = sp["serial_label"]
    html = f'{escape(label)}: <b>{escape(sp["serial"])}</b>'
    text = f"{label}: {sp['serial']}"
    if sp["express_code"]:
        html += f' &nbsp;·&nbsp; Express Service Code: <b>{escape(sp["express_code"])}</b>'
        text += f" (Express Service Code {sp['express_code']})"
    return html, text


def page(sp, photo_name=None):
    title = " ".join(x for x in [sp["brand"], sp["model"]] if x)
    now = datetime.datetime.now()
    chips, tiles, win_card, feat_card = blocks(sp)

    # Details
    def cell(v):
        if isinstance(v, tuple) and v[0] == "SERIAL":
            return (f'<span class="serial-real">{escape(v[1])}</span>'
                    f'<span class="serial-mask">Hidden</span>')
        return escape(str(v))

    details = "".join(
        f'<div class="dsec"><h3>{escape(t)}</h3><table>'
        + "".join(f"<tr><td>{escape(k)}</td><td>{cell(v)}</td></tr>" for k, v in rows)
        + "</table></div>" for t, rows in sp["details"])

    note = ""
    if not sp["is_admin"]:
        note = ('<div class="note no-print">Tip: right-click QuickSpecs and choose <b>Run as administrator</b> '
                'to also show SSD wear (life left) and power-on hours.</div>')

    brand_html = f'<div class="brand">{escape(sp["brand"] or "")}</div>'
    label = sp["serial_label"]
    toolbar_serial = (f'<label><input type="checkbox" id="serialToggle" checked> Show {escape(label.lower())}</label>'
                      if sp["serial"] else "")
    tagline, serial_text = serial_bits(sp)
    if tagline:
        tagline = f'<div class="tagline serial-real">{tagline}</div>'
    photo_link = (f'<a class="btn" href="{escape(photo_name)}" target="_blank">Open eBay image</a>'
                  if photo_name else "")

    js_data = (f"const LISTING = {json.dumps(listing_text(sp))};\n"
               f"const SERIAL = {json.dumps(serial_text)};\n")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} — Specs</title>
<style>{CSS}</style></head>
<body class="show-serial">
<div class="toolbar">
  <span class="name">QuickSpecs</span>
  {toolbar_serial}
  {photo_link}
  <button id="copyBtn">Copy listing text</button>
  <button id="printBtn" class="primary">Print / Save as PDF</button>
</div>
<main class="sheet">
  <header>
    <div>
      {brand_html}
      <h1>{escape(sp["model"])}</h1>
      {tagline}
      <div class="chips">{"".join(chips)}</div>
    </div>
    <div class="price">
      <div class="lbl">Price</div>
      <div id="price" class="amt editable" contenteditable="true" spellcheck="false" data-placeholder="Click to add"></div>
    </div>
  </header>

  <h2>Key specs</h2>
  <div class="grid">{"".join(tiles)}</div>

  <h2>Windows &amp; features</h2>
  <div class="two">{win_card}{feat_card}</div>

  <div class="notes-wrap">
    <h2>Condition &amp; notes</h2>
    <div id="notes" class="notes editable" contenteditable="true" data-placeholder="Click to add notes for buyers — condition, scratches, what's included (charger, box)…"></div>
  </div>

  <h2>Full details</h2>
  <div class="details">{details}</div>
  {note}

  <footer>
    <span>Specs read directly from this computer's hardware by QuickSpecs</span>
    <span>{now.strftime("%B %d, %Y").replace(" 0", " ")}</span>
  </footer>
</main>
<div id="toast" class="toast"></div>
<script>{js_data}{JS}</script>
</body></html>
"""
