"""Turns raw collected data into clean, buyer-friendly spec values."""

import math
import re

JUNK = {"", "to be filled by o.e.m.", "system product name", "system manufacturer", "default string",
        "not applicable", "none", "o.e.m.", "oem", "invalid", "123456789", "0", "system serial number",
        "chassis serial number", "base board serial number", "not specified", "unknown"}

BRANDS = [
    (r"^lenovo", "Lenovo"), (r"^dell", "Dell"), (r"^hewlett|^hp\b", "HP"), (r"^asus", "ASUS"),
    (r"^acer", "Acer"), (r"^micro-star|^msi\b", "MSI"), (r"^microsoft", "Microsoft"),
    (r"^samsung", "Samsung"), (r"^apple", "Apple"), (r"^toshiba", "Toshiba"), (r"^dynabook", "Dynabook"),
    (r"^fujitsu", "Fujitsu"), (r"^lg ", "LG"), (r"^razer", "Razer"), (r"^gigabyte", "Gigabyte"),
    (r"^panasonic", "Panasonic"), (r"^huawei", "Huawei"), (r"^xiaomi", "Xiaomi"), (r"^framework", "Framework"),
    (r"^google", "Google"), (r"^sony", "Sony"), (r"^vaio", "VAIO"), (r"^getac", "Getac"),
]

LAPTOP_CHASSIS = {8: "Laptop", 9: "Laptop", 10: "Notebook", 14: "Notebook", 30: "Tablet",
                  31: "2-in-1 convertible", 32: "2-in-1 detachable"}
DESKTOP_CHASSIS = {3: "Desktop", 4: "Desktop", 5: "Desktop", 6: "Mini tower", 7: "Tower",
                   13: "All-in-one", 15: "Desktop", 16: "Desktop", 35: "Mini PC", 36: "Stick PC"}

RAM_TYPES = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 27: "LPDDR", 28: "LPDDR2", 29: "LPDDR3",
             30: "LPDDR4", 34: "DDR5", 35: "LPDDR5"}

RES_NAMES = {
    (1280, 720): "HD", (1366, 768): "HD", (1280, 800): "WXGA", (1440, 900): "WXGA+", (1600, 900): "HD+",
    (1920, 1080): "Full HD", (1920, 1200): "WUXGA (FHD+)", (2160, 1440): "2K", (2256, 1504): "2K",
    (2560, 1440): "QHD", (2560, 1600): "WQXGA (QHD+)", (2880, 1620): "3K", (2880, 1800): "3K",
    (2880, 1920): "3K", (3000, 2000): "3K", (3200, 1800): "QHD+", (3840, 2160): "4K UHD",
    (3840, 2400): "4K+ (WQUXGA)", (1280, 1024): "SXGA",
}

PANEL_SIZES = [10.1, 11.6, 12.0, 12.3, 12.4, 12.5, 13.0, 13.3, 13.4, 13.5, 13.6, 14.0, 14.5, 15.0, 15.6,
               16.0, 16.1, 17.0, 17.3, 18.0]

VIRTUAL_GPU = re.compile(r"parsec|virtual|remote display|basic display|basic render|citrix|vmware|"
                         r"hyper-v|idd|spacedesk|duet|displaylink|meta virtual|oculus|usb mobile monitor", re.I)


def clean(s):
    if s is None:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return None if s.lower() in JUNK else s


def gb(n_bytes, binary=False):
    if not n_bytes:
        return None
    return n_bytes / (1024 ** 3 if binary else 1000 ** 3)


def fmt_disk_size(n_bytes):
    """Label disks the way they're sold: 256 GB, 512 GB, 1 TB."""
    g = gb(n_bytes)
    if not g:
        return None
    sizes = [16, 32, 64, 120, 128, 240, 250, 256, 320, 480, 500, 512, 750, 960, 1000, 1500, 2000,
             3000, 4000, 6000, 8000, 10000, 12000, 16000]
    closest = min(sizes, key=lambda std: abs(g - std) / std)
    if abs(g - closest) / closest < 0.05:
        g = closest
    if g >= 1000:
        tb = g / 1000
        return f"{tb:g} TB" if tb == int(tb) else f"{tb:.1f} TB"
    return f"{round(g)} GB"


def ghz(mhz):
    return f"{mhz / 1000:.2f}".rstrip("0").rstrip(".") + " GHz"


def fmt_mem(n_bytes):
    g = gb(n_bytes, binary=True)
    if not g:
        return None
    if g >= 1:
        return f"{g:g} GB" if g == int(g) else f"{g:.1f} GB"
    return f"{round(g * 1024)} MB"


def brand_name(manufacturer):
    m = clean(manufacturer) or ""
    for pat, name in BRANDS:
        if re.search(pat, m, re.I):
            return name
    return re.sub(r",?\s*(inc\.?|corporation|corp\.?|co\.,? ?ltd\.?|ltd\.?|limited|computer)\b", "", m,
                  flags=re.I).strip(" ,") or None


def model_name(sysinfo, brand):
    model = clean(sysinfo.get("model"))
    version = clean(sysinfo.get("product_version"))
    family = clean(sysinfo.get("family"))
    machine_type = None
    # Lenovo puts the marketing name ("ThinkPad T480") in the product version and a
    # machine-type code ("20L5CTO1WW") in the model field.
    if brand == "Lenovo" and version and not re.fullmatch(r"lenovo|[\d.]+", version, re.I):
        machine_type = model
        model = version
    if model and re.fullmatch(r"[\w-]{4,12}", model) and family and not re.match(r"^\d|^type", family, re.I):
        # e.g. MSI "MS-16V1" with family "GF63 Thin" style
        if brand in ("MSI", "Gigabyte"):
            machine_type, model = model, family
    if model and brand and model.lower().startswith(brand.lower() + " "):
        model = model[len(brand) + 1:]
    return model, machine_type


def clean_cpu(name):
    if not name:
        return None
    n = re.sub(r"\((r|tm|c)\)", "", name, flags=re.I)
    n = re.sub(r"\b(cpu|processor)\b", "", n, flags=re.I)
    n = re.sub(r"@\s*[\d.]+\s*ghz", "", n, flags=re.I)
    n = re.sub(r"\b\d+-core\b", "", n, flags=re.I)
    n = re.sub(r"\b(with|w/) radeon.*$", "", n, flags=re.I)
    n = re.sub(r"\s+-\s+qualcomm.*$", "", n, flags=re.I)
    n = re.sub(r"\s+-\s+", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    m = re.match(r"(\d+)(st|nd|rd|th) gen (.*)", n, re.I)
    if m:
        n = m.group(3)  # generation is shown separately (see cpu_family)
    return n


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def intel_generation(num):
    """Intel Core i-series model number → generation, e.g. 8650 → 8, 1165 → 11, 10510 → 10, 13980 → 13."""
    if len(num) == 3:
        return 1
    if len(num) == 4:
        return int(num[:2]) if num[0] == "1" and num[1] in "0123" else int(num[0])
    if len(num) == 5:
        return int(num[:2])
    return None


def cpu_family(raw_name):
    """Returns (family key, generation label) for a CPU name, e.g. ("intel-2006", "8th Gen")."""
    n = re.sub(r"\((r|tm|c)\)", "", raw_name or "", flags=re.I)
    low = re.sub(r"\s+", " ", n.lower())
    explicit = re.search(r"(\d+)(st|nd|rd|th) gen", low)
    if "ryzen" in low:
        m = re.search(r"ryzen ai (?:max\+? )?\d+ (?:hx |pro )*(\d)\d\d", low)
        if m:
            return "amd-ryzen", f"AI {m.group(1)}00 series"
        m = re.search(r"ryzen \d (?:pro )?(\d)\d\d\d", low)
        return "amd-ryzen", (f"{m.group(1)}000 series" if m else None)
    if "snapdragon" in low or "qualcomm" in low:
        return ("snapdragon-x-elite" if "x elite" in low else "snapdragon"), None
    if "amd" in low or "athlon" in low:
        return "amd", None
    if "intel" in low or re.search(r"\bcore\b|celeron|pentium|xeon|atom", low):
        m = re.search(r"ultra (\d) (\d)\d\d", low)
        if m:
            return f"intel-core-ultra-{m.group(1)}", f"Series {m.group(2)}"
        m = re.search(r"\bcore (\d) (\d)\d\d", low)  # 2023+ "Core 5 120U" naming
        if m:
            tier = m.group(1)
            return (f"intel-core-{tier}-2023" if tier in "357" else "intel-2020"), f"Series {m.group(2)}"
        m = re.search(r"\bi([3579])-? ?(\d{3,5})", low)
        if m:
            gen = int(explicit.group(1)) if explicit else intel_generation(m.group(2))
            if gen and gen >= 11:
                return f"intel-core-i{m.group(1)}-2020", f"{ordinal(gen)} Gen"
            return "intel-2006", (f"{ordinal(gen)} Gen" if gen else None)
        if "celeron" in low:
            return "intel-celeron", None
        if "pentium" in low:
            return "intel-pentium", None
        return "intel-2020", None
    return None, None


def is_integrated_gpu(name):
    n = name.lower()
    if "nvidia" in n:
        return False
    if "intel" in n:
        return not re.search(r"arc\W*\s*a\d{3}|arc\W*\s*b\d{3}", n)
    if "amd" in n or "radeon" in n or "ati " in n:
        return not re.search(r"\brx\b|\bpro w|\bfirepro|\bvega (56|64)\b|\bradeon (hd|r\d) \d{4}m?\b|\bradeon vii\b", n)
    return "adreno" in n or "qualcomm" in n or "microsoft" in n


def snap_panel(diag):
    if not diag:
        return None
    best = min(PANEL_SIZES, key=lambda s: abs(s - diag))
    return best if abs(best - diag) <= 0.5 else round(diag, 1)


def wifi_generation(netsh_text):
    m = re.search(r"Radio types supported\s*:\s*(.+)", netsh_text or "", re.I)
    if not m:
        return None, None
    radios = m.group(1).lower()
    for code, gen in (("802.11be", "Wi-Fi 7"), ("802.11ax", "Wi-Fi 6"), ("802.11ac", "Wi-Fi 5"),
                      ("802.11n", "Wi-Fi 4"), ("802.11g", "802.11g")):
        if code in radios:
            return gen, m.group(1).strip()
    return None, m.group(1).strip()


def bluetooth_radio(devices):
    bt = [d for d in devices if d.get("class") == "Bluetooth" and d.get("status") == "OK" and d.get("name")]
    if not bt:
        return None
    for d in bt:
        if re.search(r"bluetooth.*(adapter|radio)|wireless bluetooth|bluetooth\W*\(r\)|bluetooth \d\.\d", d["name"], re.I) \
                and not re.search(r"generic bluetooth radio", d["name"], re.I):
            return re.sub(r"\((r|tm)\)", "", d["name"], flags=re.I).replace("  ", " ").strip()
    if any("enumerator" in d["name"].lower() for d in bt):
        return "Yes"
    return None


def battery_info(raw):
    rep = raw.get("battery_report") or []
    live = raw.get("battery_live") or []
    batteries = []
    for b in rep:
        try:
            design = int(b.get("DesignCapacity") or 0)
            full = int(b.get("FullChargeCapacity") or 0)
        except ValueError:
            continue
        if design <= 0:
            continue
        cycles = b.get("CycleCount")
        batteries.append({
            "design": design, "full": full,
            "cycles": int(cycles) if cycles and cycles.isdigit() and int(cycles) > 0 else None,
            "maker": clean(b.get("Manufacturer")), "chemistry": clean(b.get("Chemistry")),
            "name": clean(b.get("Id")),
        })
    if not batteries:
        w = raw.get("battery_wmi") or {}
        designs, fulls, cycles = w.get("design") or [], w.get("full") or [], w.get("cycles") or []
        for i, d in enumerate(designs):
            if d and i < len(fulls):
                c = cycles[i] if i < len(cycles) else None
                batteries.append({"design": d, "full": fulls[i], "cycles": c or None,
                                  "maker": None, "chemistry": None, "name": None})
    if not batteries and not live:
        return None
    design = sum(b["design"] for b in batteries)
    full = sum(b["full"] for b in batteries)
    pct = min(100, round(full / design * 100)) if design else None
    if pct is None:
        label, tone = "Unknown", "muted"
    elif pct >= 80:
        label, tone = "Good", "good"
    elif pct >= 60:
        label, tone = "Fair", "warn"
    else:
        label, tone = "Worn — consider replacing", "bad"
    cycles = [b["cycles"] for b in batteries if b["cycles"]]
    charge = next((b.get("charge") for b in live if b.get("charge") is not None), None)
    return {
        "health_pct": pct, "label": label, "tone": tone,
        "design_wh": design / 1000 if design else None, "full_wh": full / 1000 if full else None,
        "cycles": sum(cycles) if cycles else None, "count": max(len(batteries), len(live)),
        "charge": charge, "plugged_in": any(b.get("status") == 2 for b in live),
        "maker": next((b["maker"] for b in batteries if b["maker"]), None),
        "chemistry": next((b["chemistry"] for b in batteries if b["chemistry"]), None),
    }


ACTIVATION = {0: "Not activated", 1: "Activated", 2: "Grace period", 3: "Grace period", 4: "Not genuine",
              5: "Not activated", 6: "Grace period"}


def build(raw):
    s = raw.get("system") or {}
    brand = brand_name(s.get("manufacturer"))
    model, machine_type = model_name(s, brand)
    chassis = (s.get("chassis_types") or [None])[0]
    has_battery = bool(raw.get("battery_report") or raw.get("battery_live"))
    device_type = LAPTOP_CHASSIS.get(chassis) or DESKTOP_CHASSIS.get(chassis) or ("Laptop" if has_battery else "PC")
    is_laptop = chassis in LAPTOP_CHASSIS or has_battery

    # CPU
    cpus = raw.get("cpus") or []
    cpu = cpus[0] if cpus else {}
    cpu_name = clean_cpu(cpu.get("name")) or "Unknown"
    cores, threads = cpu.get("cores"), cpu.get("threads")
    _, cpu_gen = cpu_family(cpu.get("name"))
    cpu_sub = [cpu_gen] if cpu_gen else []
    if cores:
        cpu_sub.append(f"{cores} cores / {threads} threads" if threads and threads != cores else f"{cores} cores")
    if cpu.get("max_mhz"):
        cpu_sub.append(ghz(cpu["max_mhz"]) + " base")
    if len(cpus) > 1:
        cpu_sub.append(f"{len(cpus)} sockets")

    # RAM
    mods = [m for m in (raw.get("ram_modules") or []) if m.get("capacity")]
    total_ram = sum(m["capacity"] for m in mods) or s.get("total_ram_bytes")
    if not mods and total_ram:  # VM / odd firmware: round reported usable RAM up
        total_ram = math.ceil(total_ram / 1024 ** 3) * 1024 ** 3
    ram_type = next((RAM_TYPES[m["smbios_type"]] for m in mods if m.get("smbios_type") in RAM_TYPES), None)
    ram_speed = max([m.get("configured_speed") or m.get("speed") or 0 for m in mods] or [0]) or None
    ram_sub = [x for x in [ram_type, f"{ram_speed} MT/s" if ram_speed else None] if x]
    if len(mods) > 1:
        sizes = {fmt_mem(m["capacity"]) for m in mods}
        ram_sub.append(f"{len(mods)} × {sizes.pop()}" if len(sizes) == 1 else " + ".join(fmt_mem(m["capacity"]) for m in mods))
    elif len(mods) == 1:
        ram_sub.append("1 module")

    # Storage (internal only)
    disks = []
    for d in raw.get("disks") or []:
        if (d.get("bus") or "").upper() in ("USB", "SD", "MMC", "VIRTUAL", "FILE BACKED VIRTUAL", "ISCSI"):
            continue
        media = d.get("media") if d.get("media") in ("SSD", "HDD", "SCM") else None
        bus = d.get("bus") if d.get("bus") not in (None, "", "Unknown", "RAID", "SAS") else None
        kind = "NVMe SSD" if bus == "NVMe" else " ".join(x for x in [bus, media] if x) or "Drive"
        if bus == "NVMe" or media == "SSD":
            kind = "NVMe SSD" if bus == "NVMe" else ("SATA SSD" if bus == "SATA" else "SSD")
        life = None
        if d.get("wear") is not None:
            life = max(0, 100 - int(d["wear"]))
        disks.append({"size": fmt_disk_size(d.get("size")), "bytes": d.get("size") or 0, "kind": kind,
                      "name": clean(d.get("name")), "health": d.get("health") or None, "life": life,
                      "hours": d.get("power_on_hours")})
    if not disks:
        for d in raw.get("diskdrives") or []:
            if (d.get("interface") or "").upper() == "USB":
                continue
            disks.append({"size": fmt_disk_size(d.get("size")), "bytes": d.get("size") or 0, "kind": "Drive",
                          "name": clean(d.get("name")), "health": None, "life": None, "hours": None})
    disks.sort(key=lambda d: -d["bytes"])

    # GPU
    gpus = []
    for g in raw.get("gpus") or []:
        name = clean(g.get("name"))
        if not name or VIRTUAL_GPU.search(name):
            continue
        name = re.sub(r"\((r|tm)\)", "", name, flags=re.I).replace("  ", " ").strip()
        integ = is_integrated_gpu(name)
        mem = fmt_mem(g.get("vram_bytes"))
        gpus.append({"name": name, "integrated": integ,
                     "memory": None if integ else mem,
                     "kind": "Integrated graphics" if integ else "Dedicated graphics",
                     "driver": g.get("driver")})
    gpus.sort(key=lambda g: g["integrated"])

    # Display
    displays = raw.get("displays") or []
    disp = next((d for d in displays if d.get("primary")), displays[0] if displays else None)
    monitors = raw.get("monitors") or []
    internal = [m for m in monitors if m.get("output_tech") in (6, 11, 13, 2147483648, -2147483648)]
    mon = internal[0] if internal else (monitors[0] if len(monitors) == 1 else None)
    diag = None
    if mon and mon.get("width_cm") and mon.get("height_cm"):
        diag = snap_panel(math.hypot(mon["width_cm"], mon["height_cm"]) / 2.54)
    res = disp.get("native") if disp else None
    display = None
    if res or diag:
        value = " ".join(x for x in [f'{diag:g}"' if diag else None, f"{res[0]} × {res[1]}" if res else None] if x)
        sub = [x for x in [RES_NAMES.get(tuple(res)) if res else None,
                           f"{disp['max_hz']} Hz" if disp and disp.get("max_hz") and disp["max_hz"] > 1 else None] if x]
        display = {"value": value, "sub": " · ".join(sub), "external": bool(monitors and not internal and is_laptop),
                   "count": len(displays)}

    # Network
    net = raw.get("net") or []
    wifi_ad = next((n for n in net if "802.11" in (n.get("media") or "") or n.get("ndis") == "9"
                    or re.search(r"wi-?fi|wireless|wlan|802\.11", n.get("desc") or "", re.I)), None)
    wifi_gen, wifi_radios = wifi_generation(raw.get("wlan_drivers"))
    eth = next((n for n in net if (n.get("media") == "802.3" or n.get("ndis") == "14")
                and not re.search(r"usb|virtual|bluetooth", n.get("desc") or "", re.I)), None)
    bt = bluetooth_radio(raw.get("devices") or [])
    tidy = lambda x: re.sub(r"\((r|tm)\)", "", x or "", flags=re.I).replace("  ", " ").strip() or None

    # Devices
    devices = [d for d in (raw.get("devices") or []) if d.get("status") == "OK"]
    cams = [d["name"] for d in devices if d.get("class") in ("Camera", "Image") and d.get("name")]
    # Windows Hello face needs an IR camera. Look for one by name; also trust Windows' face software device, but
    # only when a camera is actually present (Windows can leave that device installed on PCs with no camera).
    ir_cams = [c for c in cams if re.search(r"\bir\b|infrared|realsense|depth|hello|tobii", c, re.I)]
    face_dev = [d["name"] for d in devices if d.get("class") == "Biometric" and d.get("name")
                and re.search(r"face|facial", d["name"], re.I)]
    hello_face = [re.sub(r"\s*\((r|tm)\)", "", n, flags=re.I) for n in ir_cams + (face_dev if cams else [])]
    webcam = [c for c in cams if not re.search(r"\bir\b|infrared|depth|scanner|printer", c, re.I)]
    fingerprint = [re.sub(r"\s*\((r|tm)\)", "", d["name"], flags=re.I) for d in devices if d.get("class") == "Biometric" and d.get("name")
                   and not re.search(r"software device|facial|face", d["name"], re.I)]
    touch = any(re.search(r"touch ?screen", d.get("name") or "", re.I) for d in devices)
    pen = any(re.search(r"\bpen\b|stylus|wacom", d.get("name") or "", re.I) for d in devices)
    tpm_dev = next((d["name"] for d in devices if "trusted platform module" in (d.get("name") or "").lower()), None)
    tpm_ver = (re.search(r"(\d\.\d)", tpm_dev).group(1) if tpm_dev and re.search(r"(\d\.\d)", tpm_dev) else None)

    # Windows
    o = raw.get("os") or {}
    win_name = re.sub(r"^Microsoft\s+", "", o.get("caption") or "Windows").strip()
    build = o.get("build")
    build_full = f"{build}.{o['ubr']}" if build and o.get("ubr") else build
    version_line = " · ".join(x for x in [o.get("display_version"), f"build {build_full}" if build_full else None,
                                          o.get("arch")] if x)
    a = raw.get("activation") or {}
    status = a.get("status")
    activated = status == 1 if status is not None else None
    act_text = ACTIVATION.get(status, "Unknown") if status is not None else "Unknown"
    channel_raw = (a.get("channel") or a.get("description") or "").upper()
    channel = ("OEM" if "OEM" in channel_raw else "Retail" if "RETAIL" in channel_raw
               else "Volume (KMS/MAK)" if ("VOLUME" in channel_raw or "KMS" in channel_raw or "MAK" in channel_raw)
               else None)
    if a.get("firmware_key_present"):
        channel = (channel + " · " if channel else "") + "key built into firmware"

    sec = raw.get("security") or {}
    secure_boot = {1: True, 0: False}.get(sec.get("secure_boot"))

    battery = battery_info(raw) if is_laptop else None

    features = []
    if wifi_ad or wifi_gen:
        features.append((wifi_gen or "Wi-Fi", True))
    else:
        features.append(("Wi-Fi", False))
    features.append(("Bluetooth", bool(bt)))
    features.append(("Webcam", bool(webcam)))
    if is_laptop or hello_face:
        features.append(("Windows Hello face", bool(hello_face)))
    features.append(("Fingerprint reader", bool(fingerprint)))
    if is_laptop:
        features.append(("Touchscreen", touch))
    if pen:
        features.append(("Pen support", True))
    if eth:
        features.append(("Ethernet port", True))
    features.append((f"TPM {tpm_ver}" if tpm_ver else "TPM", bool(tpm_dev)))
    if secure_boot is not None:
        features.append(("Secure Boot", secure_boot))

    serial = clean(s.get("serial"))
    serial_label = "Service Tag" if brand == "Dell" else "Serial number"
    express_code = None
    # Dell's Express Service Code is the Service Tag read as a base-36 number.
    if brand == "Dell" and serial and re.fullmatch(r"[0-9A-Za-z]{5,7}", serial):
        express_code = str(int(serial, 36))

    details = [
        ("Device", [
            ("Brand", brand), ("Model", model), ("Machine type / SKU", machine_type or clean(s.get("sku"))),
            ("Product line", clean(s.get("family")) if clean(s.get("family")) != model else None),
            ("Form factor", device_type),
            (serial_label, ("SERIAL", serial) if serial else None),
            ("Express Service Code", ("SERIAL", express_code) if express_code else None),
            ("BIOS", " · ".join(x for x in [clean(s.get("bios_version")), s.get("bios_date")] if x) or None),
        ]),
        ("Processor & memory", [
            ("Processor", cpu_name), ("Generation", cpu_gen), ("Cores / threads", f"{cores} / {threads}" if cores else None),
            ("Base clock", ghz(cpu["max_mhz"]) if cpu.get("max_mhz") else None),
            ("Memory", " · ".join([fmt_mem(total_ram) or "?"] + ram_sub)),
        ] + [(f"Memory slot {clean(m.get('slot')) or i + 1}",
              " · ".join(x for x in [fmt_mem(m["capacity"]), clean(m.get("maker")), clean(m.get("part"))] if x))
             for i, m in enumerate(mods)]),
        ("Graphics & display", [(f"Graphics {i + 1}" if len(gpus) > 1 else "Graphics",
                                 " · ".join(x for x in [g["name"], g["memory"], g["kind"]] if x)) for i, g in enumerate(gpus)]
         + [("Screen", display and " · ".join(x for x in [display["value"], display["sub"]] if x))]),
        ("Storage", [(f"Drive {i + 1}" if len(disks) > 1 else "Drive",
                      " · ".join(x for x in [d["size"], d["kind"], d["name"],
                                             f"health: {d['health']}" if d["health"] else None,
                                             f"{d['life']}% life left" if d["life"] is not None else None,
                                             f"{d['hours']:,} hours powered on" if d["hours"] else None] if x))
                     for i, d in enumerate(disks)]),
        ("Connectivity", [
            ("Wi-Fi", " · ".join(x for x in [tidy(wifi_ad and wifi_ad.get("desc")), wifi_gen] if x) or None),
            ("Wi-Fi standards", wifi_radios),
            ("Ethernet", tidy(eth and eth.get("desc"))),
            ("Bluetooth", bt),
            ("Webcam", ", ".join(dict.fromkeys(webcam)) or None),
            ("Windows Hello face", ", ".join(dict.fromkeys(hello_face)) if hello_face
             else ("No (no IR camera found)" if is_laptop else None)),
            ("Fingerprint reader", ", ".join(dict.fromkeys(fingerprint)) or None),
        ]),
        ("Windows & security", [
            ("Windows", win_name), ("Version", version_line), ("Activation", act_text),
            ("License type", channel), ("Installed on", o.get("install_date")),
            ("TPM", tpm_dev), ("Secure Boot", {True: "On", False: "Off"}.get(secure_boot)),
            ("Firmware", sec.get("firmware_type")),
        ]),
    ]
    if battery:
        details.insert(4, ("Battery", [
            ("Health", f"{battery['health_pct']}% of original capacity" if battery["health_pct"] is not None else "Unknown"),
            ("Capacity now", f"{battery['full_wh']:.1f} Wh" if battery["full_wh"] else None),
            ("Original capacity", f"{battery['design_wh']:.1f} Wh" if battery["design_wh"] else None),
            ("Charge cycles", f"{battery['cycles']:,}" if battery["cycles"] else None),
            ("Batteries", str(battery["count"]) if battery["count"] > 1 else None),
            ("Maker / chemistry", " · ".join(x for x in [battery["maker"], battery["chemistry"]] if x) or None),
        ]))
    details = [(title, [(k, v) for k, v in rows if v]) for title, rows in details]
    details = [(t, rows) for t, rows in details if rows]

    return {
        "brand": brand, "model": model or "Unknown model", "machine_type": machine_type,
        "device_type": device_type, "is_laptop": is_laptop, "serial": serial,
        "serial_label": serial_label, "express_code": express_code,
        "cpu": {"value": cpu_name, "sub": " · ".join(cpu_sub), "gen": cpu_gen},
        "ram": {"value": fmt_mem(total_ram) or "Unknown", "sub": " · ".join(ram_sub)},
        "disks": disks, "gpus": gpus, "display": display, "battery": battery,
        "windows": {"name": win_name, "version": version_line, "activated": activated,
                    "status": act_text, "channel": channel},
        "network": {
            "value": " + ".join(x for x in [wifi_gen or ("Wi-Fi" if wifi_ad else None),
                                            "Ethernet" if eth else None, "Bluetooth" if bt else None] if x) or "None detected",
            "sub": " · ".join(x for x in [tidy(wifi_ad and wifi_ad.get("desc")), tidy(eth and eth.get("desc"))] if x),
        },
        "features": features, "details": details,
        "is_admin": bool(sec.get("is_admin")),
    }
