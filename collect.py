"""Reads hardware and Windows info from this PC.

Everything comes from tools built into Windows (PowerShell/WMI, powercfg,
netsh, Win32 display APIs), so nothing extra has to be installed on the
laptop being sold. Works without admin; running as admin adds SSD wear data.
"""

import ctypes
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

CREATE_NO_WINDOW = 0x08000000

PS_SCRIPT = r'''
$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$r = [ordered]@{}

# ---------- System / model ----------
$cs   = Get-CimInstance Win32_ComputerSystem
$csp  = Get-CimInstance Win32_ComputerSystemProduct
$bios = Get-CimInstance Win32_BIOS
$enc  = Get-CimInstance Win32_SystemEnclosure
$r.system = [ordered]@{
  manufacturer    = $cs.Manufacturer
  model           = $cs.Model
  family          = $cs.SystemFamily
  product_version = $csp.Version
  sku             = $cs.SystemSKUNumber
  serial          = $bios.SerialNumber
  bios_version    = $bios.SMBIOSBIOSVersion
  bios_date       = $(if ($bios.ReleaseDate) { $bios.ReleaseDate.ToString('yyyy-MM-dd') })
  chassis_types   = @($enc.ChassisTypes)
  total_ram_bytes = $cs.TotalPhysicalMemory
}

# ---------- CPU ----------
$r.cpus = @(Get-CimInstance Win32_Processor | ForEach-Object {
  [ordered]@{ name = $_.Name; cores = $_.NumberOfCores; threads = $_.NumberOfLogicalProcessors; max_mhz = $_.MaxClockSpeed }
})

# ---------- RAM ----------
$r.ram_modules = @(Get-CimInstance Win32_PhysicalMemory | ForEach-Object {
  [ordered]@{ capacity = $_.Capacity; speed = $_.Speed; configured_speed = $_.ConfiguredClockSpeed
              smbios_type = $_.SMBIOSMemoryType; form_factor = $_.FormFactor
              maker = $_.Manufacturer; part = $_.PartNumber; slot = $_.DeviceLocator }
})

# ---------- GPU (real VRAM lives in the registry; AdapterRAM caps at 4 GB) ----------
$vram = @{}
Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}' | ForEach-Object {
  $p = Get-ItemProperty $_.PSPath
  $m = $p.'HardwareInformation.qwMemorySize'
  if (-not $m) { $m = $p.'HardwareInformation.MemorySize' }
  if ($m -is [byte[]]) {
    if ($m.Length -ge 8) { $m = [BitConverter]::ToUInt64($m, 0) } elseif ($m.Length -ge 4) { $m = [BitConverter]::ToUInt32($m, 0) } else { $m = $null }
  }
  if ($p.DriverDesc -and $m) { $vram[$p.DriverDesc] = [uint64]$m }
}
$r.gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object {
  $mem = $vram[$_.Name]
  if (-not $mem) { $mem = $_.AdapterRAM }
  [ordered]@{ name = $_.Name; vram_bytes = $mem; driver = $_.DriverVersion; pnp = $_.PNPDeviceID; status = $_.Status }
})

# ---------- Monitors (physical size) ----------
$basic = @(Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorBasicDisplayParams)
$conn  = @(Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorConnectionParams)
$ids   = @(Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID)
function Decode($arr) { if ($arr) { -join ($arr | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ }) } }
$r.monitors = @($basic | ForEach-Object {
  $inst = $_.InstanceName
  $c = $conn | Where-Object { $_.InstanceName -eq $inst } | Select-Object -First 1
  $i = $ids  | Where-Object { $_.InstanceName -eq $inst } | Select-Object -First 1
  [ordered]@{ width_cm = $_.MaxHorizontalImageSize; height_cm = $_.MaxVerticalImageSize
              output_tech = $c.VideoOutputTechnology; name = (Decode $i.UserFriendlyName); maker = (Decode $i.ManufacturerName) }
})

# ---------- Storage ----------
$r.disks = @(Get-PhysicalDisk | ForEach-Object {
  $rel = $null
  try { $rel = $_ | Get-StorageReliabilityCounter -ErrorAction Stop } catch {}
  [ordered]@{ name = $_.FriendlyName; media = [string]$_.MediaType; bus = [string]$_.BusType; size = $_.Size
              health = [string]$_.HealthStatus; wear = $rel.Wear; power_on_hours = $rel.PowerOnHours; temp = $rel.Temperature }
})
$r.diskdrives = @(Get-CimInstance Win32_DiskDrive | ForEach-Object {
  [ordered]@{ name = $_.Model; size = $_.Size; interface = $_.InterfaceType; media = $_.MediaType }
})

# ---------- Battery (WMI fallback; powercfg is read from Python) ----------
$r.battery_live = @(Get-CimInstance Win32_Battery | ForEach-Object {
  [ordered]@{ name = $_.Name; charge = $_.EstimatedChargeRemaining; status = $_.BatteryStatus }
})
$r.battery_wmi = [ordered]@{
  design = @(Get-CimInstance -Namespace root\wmi -ClassName BatteryStaticData | ForEach-Object { $_.DesignedCapacity })
  full   = @(Get-CimInstance -Namespace root\wmi -ClassName BatteryFullChargedCapacity | ForEach-Object { $_.FullChargedCapacity })
  cycles = @(Get-CimInstance -Namespace root\wmi -ClassName BatteryCycleCount | ForEach-Object { $_.CycleCount })
}

# ---------- Network ----------
$r.net = @(Get-NetAdapter -Physical | ForEach-Object {
  [ordered]@{ name = $_.Name; desc = $_.InterfaceDescription; media = [string]$_.PhysicalMediaType
              ndis = [string]$_.NdisPhysicalMedium; status = [string]$_.Status; speed = $_.LinkSpeed }
})
$r.wlan_drivers = ((netsh wlan show drivers) -join "`n")

# ---------- Devices (camera, fingerprint, bluetooth, TPM, touch) ----------
$r.devices = @(Get-PnpDevice -PresentOnly -Class Camera, Image, Biometric, Bluetooth, SecurityDevices, HIDClass | ForEach-Object {
  [ordered]@{ class = $_.Class; name = $_.FriendlyName; status = [string]$_.Status }
})

# ---------- Windows ----------
$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$r.os = [ordered]@{
  caption = $os.Caption; version = $os.Version; build = $os.BuildNumber; ubr = $cv.UBR
  display_version = $cv.DisplayVersion; edition_id = $cv.EditionID; arch = $os.OSArchitecture
  install_date = $(if ($os.InstallDate) { $os.InstallDate.ToString('yyyy-MM-dd') })
}
$lic = Get-CimInstance SoftwareLicensingProduct -Filter "ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' AND PartialProductKey IS NOT NULL" | Select-Object -First 1
$sls = Get-CimInstance SoftwareLicensingService
$r.activation = [ordered]@{
  status = $lic.LicenseStatus; description = $lic.Description; channel = $lic.ProductKeyChannel
  firmware_key_present = [bool]$sls.OA3xOriginalProductKey
}

# ---------- Security ----------
$sb = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State'
$r.security = [ordered]@{
  secure_boot   = $sb.UEFISecureBootEnabled
  firmware_type = $env:firmware_type
  is_admin      = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$r | ConvertTo-Json -Depth 6 -Compress
'''


def run_powershell():
    fd, path = tempfile.mkstemp(suffix=".ps1", prefix="quickspecs_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(PS_SCRIPT)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", path],
            capture_output=True, timeout=180, creationflags=CREATE_NO_WINDOW,
        )
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        # Take the JSON line (ignore any stray output before it).
        start = out.find("{")
        if start < 0:
            raise RuntimeError("PowerShell returned no data:\n" + proc.stderr.decode(errors="replace"))
        return json.loads(out[start:])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def battery_report():
    """Parse `powercfg /batteryreport` (works without admin, most reliable source)."""
    tmpdir = tempfile.mkdtemp(prefix="quickspecs_")
    out = os.path.join(tmpdir, "battery.xml")
    try:
        subprocess.run(["powercfg", "/batteryreport", "/xml", "/output", out],
                       capture_output=True, timeout=60, creationflags=CREATE_NO_WINDOW)
        if not os.path.exists(out):
            return []
        root = ET.parse(out).getroot()
        batteries = []
        for el in root.iter():
            if el.tag.split("}")[-1] != "Battery":
                continue
            fields = {child.tag.split("}")[-1]: (child.text or "").strip() for child in el}
            if "DesignCapacity" in fields:
                batteries.append(fields)
        return batteries
    except Exception:
        return []
    finally:
        try:
            if os.path.exists(out):
                os.remove(out)
            os.rmdir(tmpdir)
        except OSError:
            pass


# ---------- Display modes via Win32 (true pixel resolution + max refresh) ----------

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort), ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort), ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_ulong),
        ("dmPositionX", ctypes.c_long), ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", ctypes.c_ulong), ("dmDisplayFixedOutput", ctypes.c_ulong),
        ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort), ("dmBitsPerPel", ctypes.c_ulong),
        ("dmPelsWidth", ctypes.c_ulong), ("dmPelsHeight", ctypes.c_ulong),
        ("dmDisplayFlags", ctypes.c_ulong), ("dmDisplayFrequency", ctypes.c_ulong),
        ("dmICMMethod", ctypes.c_ulong), ("dmICMIntent", ctypes.c_ulong),
        ("dmMediaType", ctypes.c_ulong), ("dmDitherType", ctypes.c_ulong),
        ("dmReserved1", ctypes.c_ulong), ("dmReserved2", ctypes.c_ulong),
        ("dmPanningWidth", ctypes.c_ulong), ("dmPanningHeight", ctypes.c_ulong),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong), ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128), ("StateFlags", ctypes.c_ulong),
        ("DeviceID", ctypes.c_wchar * 128), ("DeviceKey", ctypes.c_wchar * 128),
    ]


def display_modes():
    displays = []
    try:
        user32 = ctypes.windll.user32
        i = 0
        while True:
            dd = DISPLAY_DEVICEW()
            dd.cb = ctypes.sizeof(dd)
            if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                break
            i += 1
            if not dd.StateFlags & 0x1:  # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
                continue
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(dm)
            cur = None
            if user32.EnumDisplaySettingsW(dd.DeviceName, 0xFFFFFFFF, ctypes.byref(dm)):  # ENUM_CURRENT_SETTINGS
                cur = (dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency)
            modes = []
            m = 0
            while True:
                dm = DEVMODEW()
                dm.dmSize = ctypes.sizeof(dm)
                if not user32.EnumDisplaySettingsW(dd.DeviceName, m, ctypes.byref(dm)):
                    break
                modes.append((dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency))
                m += 1
            if modes:
                max_w, max_h, _ = max(modes, key=lambda x: (x[0] * x[1], x[2]))
                max_hz = max(hz for w, h, hz in modes if (w, h) == (max_w, max_h))
            else:
                max_w = max_h = max_hz = None
            displays.append({
                "primary": bool(dd.StateFlags & 0x4),
                "adapter": dd.DeviceString,
                "current": cur,
                "native": (max_w, max_h) if max_w else None,
                "max_hz": max_hz,
            })
    except Exception:
        pass
    return displays


def nvidia_vram():
    """Some NVIDIA drivers don't publish VRAM in the registry; nvidia-smi does."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        result = {}
        for line in proc.stdout.decode(errors="replace").splitlines():
            name, _, mib = line.rpartition(",")
            if name and mib.strip().isdigit():
                result[name.strip()] = int(mib.strip()) * 1024 * 1024
        return result
    except Exception:
        return {}


def collect_all():
    data = run_powershell()
    gpus = data.get("gpus") or []
    if any("nvidia" in (g.get("name") or "").lower() and not g.get("vram_bytes") for g in gpus):
        smi = nvidia_vram()
        for g in gpus:
            if not g.get("vram_bytes"):
                for name, size in smi.items():
                    if name.lower() in (g.get("name") or "").lower() or (g.get("name") or "").lower() in name.lower():
                        g["vram_bytes"] = size
        # Names can differ between Windows and nvidia-smi; with a single NVIDIA card, just pair them.
        nv = [g for g in gpus if "nvidia" in (g.get("name") or "").lower()]
        if len(nv) == 1 and len(smi) == 1 and not nv[0].get("vram_bytes"):
            nv[0]["vram_bytes"] = next(iter(smi.values()))
    data["battery_report"] = battery_report()
    data["displays"] = display_modes()
    return data
