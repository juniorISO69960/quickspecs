"""Draws the eBay spec image (1600×1200 PNG) directly with Pillow — no browser needed.

Uses the Segoe UI / Consolas fonts that come with Windows, falling back to Arial
and then Pillow's built-in font. Text is sized as large as it can be while
everything still fits on the image.
"""

import datetime
import os

from PIL import Image, ImageDraw, ImageFont

import render

W, H = 1600, 1200
SS = 2  # draw at 2× and shrink, for smooth edges

C = {
    "ink": "#16191f", "muted": "#5f6672", "faint": "#8a919c", "line": "#e4e7ec", "tile": "#f6f7f9",
    "white": "#ffffff", "good": "#15803d", "good_bg": "#e7f6ec", "warn": "#b45309", "warn_bg": "#fdf3e3",
    "bad": "#c62828", "bad_bg": "#fdecec", "no_bg": "#eef0f2", "no": "#a3a9b2", "bar_bg": "#e3e6eb",
}
TONE = {"good": "good", "warn": "warn", "bad": "bad", "muted": "muted"}

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONT_FILES = {
    "regular": ["segoeui.ttf", "arial.ttf"],
    "semibold": ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"],
    "bold": ["segoeuib.ttf", "arialbd.ttf"],
    "mono": ["consolab.ttf", "consola.ttf", "courbd.ttf", "cour.ttf"],
}
_fonts = {}


def font(kind, size):
    key = (kind, max(6, round(size)))
    if key not in _fonts:
        f = None
        for name in FONT_FILES[kind]:
            path = os.path.join(FONT_DIR, name)
            if os.path.exists(path):
                f = ImageFont.truetype(path, key[1])
                break
        _fonts[key] = f or ImageFont.load_default(key[1])
    return _fonts[key]


_measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def tlen(text, fnt):
    return _measure.textlength(text, font=fnt)


def wrap(text, fnt, maxw):
    lines, cur = [], ""
    for word in (text or "").split(" "):
        trial = f"{cur} {word}" if cur else word
        if tlen(trial, fnt) <= maxw:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        while tlen(word, fnt) > maxw and len(word) > 1:  # break very long words
            i = len(word)
            while i > 1 and tlen(word[:i], fnt) > maxw:
                i -= 1
            lines.append(word[:i])
            word = word[i:]
        cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


class Canvas:
    """Draws when `paint` is True; otherwise only measures (used to find the best text size)."""

    def __init__(self, paint):
        self.paint = paint
        self.img = Image.new("RGB", (W * SS, H * SS), C["white"]) if paint else None
        self.d = ImageDraw.Draw(self.img) if paint else None

    def text(self, x, y, text, fnt, color, anchor="la"):
        if self.paint:
            self.d.text((x, y), text, font=fnt, fill=C.get(color, color), anchor=anchor)

    def para(self, x, y, text, fnt, color, maxw, lh=1.22):
        lines = wrap(text, fnt, maxw)
        for i, line in enumerate(lines):
            self.text(x, y + i * fnt.size * lh, line, fnt, color)
        return len(lines) * fnt.size * lh

    def tracked(self, x, y, text, fnt, color, tracking):
        """Letter-spaced text, for small uppercase labels."""
        for ch in text:
            self.text(x, y, ch, fnt, color)
            x += tlen(ch, fnt) + tracking
        return fnt.size * 1.3

    def rrect(self, box, r, fill, outline=None, width=0):
        if self.paint:
            self.d.rounded_rectangle(box, r, fill=C.get(fill, fill),
                                     outline=C.get(outline, outline) if outline else None, width=width)

    def check(self, cx, cy, s, color, width):
        if self.paint:
            pts = [(cx - 0.32 * s, cy + 0.02 * s), (cx - 0.08 * s, cy + 0.26 * s), (cx + 0.34 * s, cy - 0.24 * s)]
            self.d.line(pts, fill=C[color], width=round(width), joint="curve")

    def dash(self, cx, cy, s, color, width):
        if self.paint:
            self.d.line([(cx - 0.22 * s, cy), (cx + 0.22 * s, cy)], fill=C[color], width=round(width))

    def circle(self, cx, cy, r, fill):
        if self.paint:
            self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C[fill])


def cpu_subs(cpu):
    """Generation on its own line, then cores/clock."""
    sub, gen = cpu["sub"], cpu.get("gen")
    if gen and sub.startswith(gen):
        return [gen, sub[len(gen):].lstrip(" ·")]
    return [sub]


def card_data(sp):
    w, b = sp["windows"], sp["battery"]
    chips = [(sp["device_type"], None, False)]
    if w["name"]:
        chips.append((w["name"], None, False))
    if w["activated"] is True:
        chips.append(("Windows activated", "good", True))
    elif w["activated"] is False:
        chips.append((f"Windows {w['status'].lower()}", "bad", False))
    if b and b["health_pct"] is not None:
        chips.append((f"Battery health {b['health_pct']}%", b["tone"], False))

    disk_val, disk_subs = render.storage_summary(sp["disks"])
    gpu_val, gpu_subs = render.gpu_summary(sp["gpus"])
    tiles = [
        {"label": "Processor", "value": sp["cpu"]["value"], "subs": cpu_subs(sp["cpu"])},
        {"label": "Memory (RAM)", "value": sp["ram"]["value"], "subs": [sp["ram"]["sub"]]},
        {"label": "Storage", "value": disk_val, "subs": disk_subs},
        {"label": "Graphics", "value": gpu_val, "subs": gpu_subs},
    ]
    d = sp["display"]
    if d:
        subs = [d["sub"]] + (["Unplug external monitors for exact screen info"] if d.get("external") else [])
        tiles.append({"label": "Display", "value": d["value"], "subs": subs})
    else:
        tiles.append({"label": "Display", "value": "Not detected", "subs": []})
    if b and b["health_pct"] is not None:
        tiles.append({"label": "Battery health", "value": f"{b['health_pct']}% · {b['label']}", "tone": b["tone"],
                      "bar": b["health_pct"],
                      "subs": [f"{b['full_wh']:.1f} of {b['design_wh']:.1f} Wh original" if b["full_wh"] and b["design_wh"] else None,
                               f"{b['cycles']:,} charge cycles" if b["cycles"] else None]})
    elif b:
        tiles.append({"label": "Battery health", "value": "Present", "subs": ["Health data not reported"]})
    elif sp["is_laptop"]:
        tiles.append({"label": "Battery", "value": "Not detected", "subs": ["Battery may be missing or disconnected"]})
    else:
        tiles.append({"label": "Network", "value": sp["network"]["value"], "subs": [sp["network"]["sub"]]})
    for t in tiles:
        t["subs"] = [s for s in t["subs"] if s]
    return chips, tiles


def layout(sp, f, cv):
    """Lay out (and, if cv.paint, draw) the card at text scale f. Returns True if it all fits."""
    k = f * SS
    chips, tiles = card_data(sp)
    w = sp["windows"]
    M = 56 * SS
    inner = W * SS - 2 * M
    y = 50 * SS

    # --- Header: brand, model, serial
    y += cv.tracked(M, y, (sp["brand"] or "").upper(), font("bold", 22 * k), "muted", 3.5 * k)
    y += cv.para(M, y, sp["model"], font("bold", 64 * k), "ink", inner, lh=1.12) + 16 * k

    serial_html, _ = render.serial_bits(sp)
    if sp["serial"]:
        reg, mono = font("regular", 28 * k), font("mono", 30 * k)
        parts = [[(f"{sp['serial_label']}: ", reg, "muted"), (sp["serial"], mono, "ink")]]
        if sp["express_code"]:
            parts.append([("Express Service Code: ", reg, "muted"), (sp["express_code"], mono, "ink")])
        x = M
        sep = "   ·   "
        base = y + reg.size  # all pieces share one baseline so the mono text lines up
        for i, seg in enumerate(parts):
            seg_w = sum(tlen(t, fn) for t, fn, _ in seg)
            if i and x + tlen(sep, reg) + seg_w > M + inner:  # wrap Express code onto its own line
                y += 28 * k * 1.35
                base += 28 * k * 1.35
                x = M
            elif i:
                cv.text(x, base, sep, reg, "faint", anchor="ls")
                x += tlen(sep, reg)
            for t, fn, col in seg:
                cv.text(x, base, t, fn, col, anchor="ls")
                x += tlen(t, fn)
        y += 28 * k * 1.35 + 12 * k

    cf = font("semibold", 23 * k)
    ch_h, pad, gap = 23 * k * 1.75, 18 * k, 10 * k
    x = M
    for text, tone, tick in chips:
        cw = tlen(text, cf) + 2 * pad + (cf.size * 0.95 if tick else 0)
        if x > M and x + cw > M + inner:
            x, y = M, y + ch_h + gap
        bg = {"good": "good_bg", "warn": "warn_bg", "bad": "bad_bg"}.get(tone, "tile")
        fg = {"good": "good", "warn": "warn", "bad": "bad"}.get(tone, "ink")
        cv.rrect((x, y, x + cw, y + ch_h), ch_h / 2, bg, None if tone else "line", 2 * SS)
        tx = x + pad
        if tick:
            cv.check(tx + cf.size * 0.35, y + ch_h / 2, cf.size * 0.75, fg, 3 * k)
            tx += cf.size * 0.95
        cv.text(tx, y + (ch_h - cf.size * 1.32) / 2, text, cf, fg)
        x += cw + gap
    y += ch_h + 18 * k
    if cv.paint:
        cv.d.rectangle((M, y, M + inner, y + 4 * SS), fill=C["ink"])
    y += 4 * SS + 24 * k

    # --- Spec tiles (3 × 2)
    g = 16 * k
    tw = (inner - 2 * g) / 3
    p = 22 * k
    lf, vf, sf = font("bold", 18 * k), font("bold", 34 * k), font("regular", 22 * k)

    def tile_body(x, y0, t, cw):
        yy = y0 + p
        tw_ = cw - 2 * p

        yy += cv.tracked(x + p, yy, t["label"].upper(), lf, "muted", 2 * k) + 6 * k
        yy += cv.para(x + p, yy, t["value"], vf, TONE.get(t.get("tone"), "ink"), tw_, lh=1.18)
        if t.get("bar") is not None:
            yy += 8 * k
            bw = cw - 2 * p
            cv.rrect((x + p, yy, x + p + bw, yy + 10 * k), 5 * k, "bar_bg")
            cv.rrect((x + p, yy, x + p + bw * t["bar"] / 100, yy + 10 * k), 5 * k, TONE.get(t["tone"], "muted"))
            yy += 14 * k
        for s in t["subs"]:
            yy += 3 * k + cv.para(x + p, yy + 3 * k, s, sf, "muted", tw_, lh=1.25)
        return yy + p - y0

    for row in (tiles[:3], tiles[3:6]):
        measure = Canvas(False)
        saved, cv_ = cv, measure
        heights = []
        for t in row:  # measure first so every tile in a row is the same height
            cv = measure
            heights.append(tile_body(0, 0, t, tw))
        cv = saved
        rh = max(heights)
        for i, t in enumerate(row):
            x = M + i * (tw + g)
            cv.rrect((x, y, x + tw, y + rh), 18 * k, "tile", "line", 2 * SS)
            tile_body(x, y, t, tw)
        y += rh + g

    # --- Windows card + features card
    lw = (inner - g) / 3
    rw = inner - g - lw
    feats = sp["features"]
    ff = font("semibold", 24 * k)
    ffn = font("regular", 24 * k)
    col_w = (rw - 2 * p) / 3
    row_h = 24 * k * 1.75
    n_rows = -(-len(feats) // 3)

    def win_body(x, y0):
        yy = y0 + p
        yy += cv.tracked(x + p, yy, "WINDOWS", lf, "muted", 2 * k) + 6 * k
        yy += cv.para(x + p, yy, w["name"], font("bold", 31 * k), "ink", lw - 2 * p, lh=1.18)
        if w["version"]:
            yy += 3 * k + cv.para(x + p, yy + 3 * k, w["version"], sf, "muted", lw - 2 * p, lh=1.25)
        yy += 10 * k
        af = font("bold", 23 * k)
        tone = "good" if w["activated"] else ("bad" if w["activated"] is False else "muted")
        tx = x + p
        if w["activated"]:
            cv.check(tx + af.size * 0.35, yy + af.size * 0.68, af.size * 0.75, "good", 3 * k)
            tx += af.size * 0.95
        yy += cv.para(tx, yy, w["status"], af, tone, lw - 2 * p, lh=1.3)
        if w["channel"]:
            yy += 3 * k + cv.para(x + p, yy + 3 * k, f"License: {w['channel']}", sf, "muted", lw - 2 * p, lh=1.25)
        return yy + p - y0

    measure = Canvas(False)
    saved = cv
    cv = measure
    wh = win_body(0, 0)
    cv = saved
    fh = p + lf.size * 1.3 + 14 * k + n_rows * row_h + p - 8 * k
    bh = max(wh, fh)

    cv.rrect((M, y, M + lw, y + bh), 18 * k, "tile", "line", 2 * SS)
    win_body(M, y)
    fx = M + lw + g
    cv.rrect((fx, y, fx + rw, y + bh), 18 * k, "tile", "line", 2 * SS)
    cv.tracked(fx + p, y + p, "FEATURES", lf, "muted", 2 * k)
    fy = y + p + lf.size * 1.3 + 14 * k
    r = 13 * k
    fits_width = True
    for i, (name, ok) in enumerate(feats):
        cx = fx + p + (i % 3) * col_w
        cy = fy + (i // 3) * row_h
        cv.circle(cx + r, cy + ff.size * 0.68, r, "good_bg" if ok else "no_bg")
        if ok:
            cv.check(cx + r, cy + ff.size * 0.68, r * 1.45, "good", 3.4 * k)
        else:
            cv.dash(cx + r, cy + ff.size * 0.68, r * 1.45, "no", 3.4 * k)
        fnt = ff if ok else ffn
        cv.text(cx + 2 * r + 12 * k, cy, name, fnt, "ink" if ok else "faint")
        if 2 * r + 12 * k + tlen(name, fnt) > col_w - 6 * k:
            fits_width = False
    y += bh

    # --- Footer
    foot = font("regular", 20 * SS)
    fy = H * SS - 40 * SS - foot.size
    cv.text(M, fy, "Specs read directly from this computer's hardware", foot, "faint")
    date = datetime.datetime.now().strftime("%B %d, %Y").replace(" 0", " ")
    cv.text(M + inner - tlen(date, foot), fy, date, foot, "faint")
    return fits_width and y + 20 * SS <= fy


def make_png(sp, path):
    """Find the biggest text size that fits, draw it, and save the PNG."""
    f = 1.5
    while f > 0.55 and not layout(sp, f, Canvas(False)):
        f -= 0.02
    cv = Canvas(True)
    layout(sp, f, cv)
    cv.img.resize((W, H), Image.LANCZOS).save(path, optimize=True)
    return True
