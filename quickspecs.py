"""QuickSpecs — make an easy-to-read spec sheet for selling a Windows laptop.

Run it on the laptop you're selling. It reads the hardware, saves an HTML
spec sheet in a "reports" folder next to the program, and opens it.

    python quickspecs.py               # scan this PC
    python quickspecs.py --save-raw    # also save the raw data (for debugging)
    python quickspecs.py --from-json raw.json   # build a sheet from saved data
"""

import argparse
import json
import os
import re
import sys
import webbrowser

import collect
import card_image
import render
import specs


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def output_dir():
    for base in (app_dir(), os.path.join(os.path.expanduser("~"), "Desktop"), os.path.expanduser("~")):
        path = os.path.join(base, "reports") if base == app_dir() else base
        try:
            os.makedirs(path, exist_ok=True)
            test = os.path.join(path, ".write_test")
            open(test, "w").close()
            os.remove(test)
            return path
        except OSError:
            continue
    return os.getcwd()


def safe_name(s):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "", s).strip(" .")[:80] or "PC"


def main():
    ap = argparse.ArgumentParser(description="Make a spec sheet for selling this laptop.")
    ap.add_argument("--from-json", help="build from a saved raw data file instead of scanning")
    ap.add_argument("--save-raw", action="store_true", help="also save the raw collected data as JSON")
    ap.add_argument("--no-open", action="store_true", help="don't ask to open the spec sheet")
    ap.add_argument("--no-image", action="store_true", help="skip making the eBay image")
    ap.add_argument("--out", help="output folder (default: reports folder next to the program)")
    args = ap.parse_args()

    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        print("QuickSpecs: reading this computer's specs (takes about 10 seconds)...")
        raw = collect.collect_all()

    sp = specs.build(raw)
    out_dir = args.out or output_dir()
    os.makedirs(out_dir, exist_ok=True)
    parts = [sp["brand"], sp["model"]]
    if sp["serial"]:
        parts.append(sp["serial"])
    base = safe_name(" ".join(p for p in parts if p))
    html_path = os.path.join(out_dir, f"{base} - specs.html")
    png_name = f"{base} - ebay.png"
    png_path = os.path.join(out_dir, png_name)
    if not args.no_image:
        print("Making the eBay image...")
        try:
            card_image.make_png(sp, png_path)
        except Exception as e:
            print(f"  (Couldn't make the image: {e})")
            png_path = None
    else:
        png_path = None
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render.page(sp, png_name if png_path else None))
    txt_path = os.path.join(out_dir, f"{base} - specs.txt")
    # utf-8-sig so Notepad shows the bullets and symbols correctly
    with open(txt_path, "w", encoding="utf-8-sig") as f:
        f.write(render.text_file(sp))
    if args.save_raw:
        with open(os.path.join(out_dir, f"{base} - raw.json"), "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=1)

    print(f"\n  {' '.join(p for p in [sp['brand'], sp['model']] if p)}")
    print("  " + render.listing_text(sp).split("\n", 2)[2].replace("\n", "\n  "))
    print(f"\nSpec sheet: {html_path}")
    if png_path:
        print(f"eBay image: {png_path}")
    print(f"Text file:  {txt_path}")
    if not args.no_open and sys.stdin and sys.stdin.isatty():
        try:
            answer = input("\nOpen the spec sheet (HTML) now? [Y/n] ").strip().lower()
        except EOFError:
            answer = "n"
        if answer in ("", "y", "yes"):
            webbrowser.open("file:///" + html_path.replace("\\", "/"))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep the window open if double-clicked
        print(f"\nSomething went wrong: {e}")
        if getattr(sys, "frozen", False):
            input("Press Enter to close...")
        raise SystemExit(1)
