"""
Paku System Monitoring Feature
==============================
Lightweight cross-platform system resource inspector:
- CPU utilization and core metrics
- Physical memory usage and availability
- Disk partition usage and space analysis
- Active process inspection and resource consumers
- High resource warnings and diagnostic suggestions
Zero mandatory third-party dependencies with automatic psutil acceleration if present.
"""

from __future__ import annotations

import csv
import ctypes
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel

console = Console(legacy_windows=False)


@dataclass
class MemoryMetrics:
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class DiskPartition:
    mount: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class ProcessEntry:
    pid: int
    name: str
    mem_mb: float
    cpu_percent: float


def get_memory_metrics() -> MemoryMetrics:
    """Retrieve memory usage without requiring third-party libraries."""
    if psutil:
        try:
            vm = psutil.virtual_memory()
            return MemoryMetrics(
                total_gb=round(vm.total / (1024 ** 3), 2),
                used_gb=round(vm.used / (1024 ** 3), 2),
                free_gb=round(vm.available / (1024 ** 3), 2),
                percent=round(vm.percent, 1),
            )
        except Exception:
            pass

    system = platform.system()
    if system == "Windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total = stat.ullTotalPhys / (1024 ** 3)
                avail = stat.ullAvailPhys / (1024 ** 3)
                used = max(0.0, total - avail)
                percent = float(stat.dwMemoryLoad)
                return MemoryMetrics(
                    total_gb=round(total, 2),
                    used_gb=round(used, 2),
                    free_gb=round(avail, 2),
                    percent=round(percent, 1),
                )
        except Exception:
            pass
    elif system == "Linux":
        try:
            meminfo = Path("/proc/meminfo")
            if meminfo.exists():
                data: Dict[str, int] = {}
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        data[key] = int(parts[1])
                total_kb = data.get("MemTotal", 0)
                avail_kb = data.get("MemAvailable", data.get("MemFree", 0))
                used_kb = max(0, total_kb - avail_kb)
                total_gb = total_kb / (1024 ** 2)
                used_gb = used_kb / (1024 ** 2)
                free_gb = avail_kb / (1024 ** 2)
                percent = (used_kb / total_kb * 100.0) if total_kb > 0 else 0.0
                return MemoryMetrics(
                    total_gb=round(total_gb, 2),
                    used_gb=round(used_gb, 2),
                    free_gb=round(free_gb, 2),
                    percent=round(percent, 1),
                )
        except Exception:
            pass

    return MemoryMetrics(total_gb=0.0, used_gb=0.0, free_gb=0.0, percent=0.0)


def _get_cpu_times_windows() -> Tuple[int, int, int]:
    """Helper to read Windows system times."""
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_uint), ("dwHighDateTime", ctypes.c_uint)]
    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        i = (idle.dwHighDateTime << 32) + idle.dwLowDateTime
        k = (kernel.dwHighDateTime << 32) + kernel.dwLowDateTime
        u = (user.dwHighDateTime << 32) + user.dwLowDateTime
        return i, k, u
    return 0, 0, 0


def get_cpu_utilization(sample_interval: float = 0.15) -> float:
    """Measure current CPU utilization percentage."""
    if psutil:
        try:
            return float(psutil.cpu_percent(interval=sample_interval))
        except Exception:
            pass

    system = platform.system()
    if system == "Windows":
        try:
            i1, k1, u1 = _get_cpu_times_windows()
            time.sleep(sample_interval)
            i2, k2, u2 = _get_cpu_times_windows()
            idle_delta = i2 - i1
            total_delta = (k2 - k1) + (u2 - u1)
            if total_delta > 0:
                util = 100.0 * (1.0 - (idle_delta / total_delta))
                return round(max(0.0, min(100.0, util)), 1)
        except Exception:
            pass
    elif system == "Linux":
        try:
            def read_proc_stat():
                with open("/proc/stat", "r") as f:
                    for line in f:
                        if line.startswith("cpu "):
                            parts = [float(x) for x in line.split()[1:]]
                            idle = parts[3] + (parts[4] if len(parts) > 4 else 0.0)
                            total = sum(parts)
                            return idle, total
                return 0.0, 0.0

            idle1, total1 = read_proc_stat()
            time.sleep(sample_interval)
            idle2, total2 = read_proc_stat()
            total_d = total2 - total1
            idle_d = idle2 - idle1
            if total_d > 0:
                util = 100.0 * (1.0 - (idle_d / total_d))
                return round(max(0.0, min(100.0, util)), 1)
        except Exception:
            pass

    return 0.0


def get_disk_partitions() -> List[DiskPartition]:
    """Retrieve disk capacity and usage for all accessible storage mounts."""
    partitions: List[DiskPartition] = []
    if psutil:
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append(DiskPartition(
                        mount=part.mountpoint,
                        total_gb=round(usage.total / (1024 ** 3), 2),
                        used_gb=round(usage.used / (1024 ** 3), 2),
                        free_gb=round(usage.free / (1024 ** 3), 2),
                        percent=round(usage.percent, 1),
                    ))
                except (PermissionError, OSError):
                    continue
            if partitions:
                return partitions
        except Exception:
            pass

    system = platform.system()
    targets: List[str] = []
    if system == "Windows":
        try:
            # Query drive letters
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    targets.append(drive)
                bitmask >>= 1
        except Exception:
            targets = ["C:\\"]
    else:
        targets = ["/"]
        home = str(Path.home())
        if home != "/":
            targets.append(home)

    for target in targets:
        try:
            usage = shutil.disk_usage(target)
            total = usage.total / (1024 ** 3)
            used = usage.used / (1024 ** 3)
            free = usage.free / (1024 ** 3)
            pct = (usage.used / usage.total * 100.0) if usage.total > 0 else 0.0
            partitions.append(DiskPartition(
                mount=target,
                total_gb=round(total, 2),
                used_gb=round(used, 2),
                free_gb=round(free, 2),
                percent=round(pct, 1),
            ))
        except (OSError, PermissionError):
            pass

    return partitions


def get_top_processes(limit: int = 10, sort_by: str = "memory") -> List[ProcessEntry]:
    """Retrieve top resource-consuming processes safely."""
    processes: List[ProcessEntry] = []

    if psutil:
        try:
            entries = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    info = proc.info
                    mem = (info['memory_info'].rss / (1024 ** 2)) if info.get('memory_info') else 0.0
                    cpu = info.get('cpu_percent') or 0.0
                    name = info.get('name') or "unknown"
                    entries.append(ProcessEntry(pid=info['pid'], name=name, mem_mb=round(mem, 1), cpu_percent=round(cpu, 1)))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            entries.sort(key=lambda p: p.mem_mb if sort_by == "memory" else p.cpu_percent, reverse=True)
            return entries[:limit]
        except Exception:
            pass

    system = platform.system()
    if system == "Windows":
        try:
            # Use tasklist CSV format
            out = subprocess.check_output(
                ["tasklist", "/fo", "csv", "/nh"],
                text=True, stderr=subprocess.DEVNULL, timeout=8
            )
            reader = csv.reader(out.splitlines())
            raw_entries: List[ProcessEntry] = []
            for row in reader:
                if len(row) >= 5:
                    pname = row[0]
                    try:
                        pid = int(row[1])
                    except ValueError:
                        continue
                    mem_str = row[4].replace(",", "").replace(".", "").replace(" K", "").replace("K", "").strip()
                    try:
                        mem_kb = float(mem_str)
                        mem_mb = round(mem_kb / 1024.0, 1)
                    except ValueError:
                        mem_mb = 0.0
                    raw_entries.append(ProcessEntry(pid=pid, name=pname, mem_mb=mem_mb, cpu_percent=0.0))
            raw_entries.sort(key=lambda p: p.mem_mb, reverse=True)
            return raw_entries[:limit]
        except Exception:
            pass
    elif system == "Linux":
        try:
            cmd = ["ps", "-eo", "pid,comm,%mem,%cpu", "--sort=-%mem"]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
            lines = out.splitlines()[1:]  # skip header
            raw_entries = []
            for line in lines:
                parts = line.strip().split(None, 3)
                if len(parts) >= 4:
                    try:
                        pid = int(parts[0])
                        pname = parts[1]
                        mem_pct = float(parts[2])
                        cpu_pct = float(parts[3])
                        # Estimate MB from total memory
                        mem_sys = get_memory_metrics()
                        mem_mb = round((mem_pct / 100.0) * mem_sys.total_gb * 1024, 1)
                        raw_entries.append(ProcessEntry(pid=pid, name=pname, mem_mb=mem_mb, cpu_percent=cpu_pct))
                    except ValueError:
                        continue
            raw_entries.sort(key=lambda p: p.mem_mb if sort_by == "memory" else p.cpu_percent, reverse=True)
            return raw_entries[:limit]
        except Exception:
            pass

    return processes


def get_system_snapshot() -> Dict[str, Any]:
    """Compile comprehensive system health snapshot."""
    mem = get_memory_metrics()
    cpu_pct = get_cpu_utilization(sample_interval=0.1)
    disks = get_disk_partitions()
    procs = get_top_processes(limit=8, sort_by="memory")

    # Diagnostic warnings
    warnings: List[str] = []
    if cpu_pct >= 85.0:
        warnings.append(f"High CPU utilization detected ({cpu_pct}%). Check active compute tasks.")
    if mem.percent >= 85.0:
        warnings.append(f"High memory consumption ({mem.percent}%). Reclaim RAM by closing unused programs.")
    for d in disks:
        if d.percent >= 90.0:
            warnings.append(f"Disk volume '{d.mount}' is near capacity ({d.percent}% used).")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {
            "utilization_percent": cpu_pct,
            "cores": os.cpu_count() or 1,
        },
        "memory": asdict(mem),
        "disks": [asdict(d) for d in disks],
        "top_processes": [asdict(p) for p in procs],
        "warnings": warnings,
        "is_psutil_accelerated": bool(psutil),
    }


def _render_bar(percent: float, width: int = 24, filled_char: str = "█", empty_char: str = "░") -> str:
    """Generate visual text progress bar."""
    filled_len = int(round(width * (max(0.0, min(100.0, percent)) / 100.0)))
    return (filled_char * filled_len) + (empty_char * (width - filled_len))


def render_system_overview(
    theme: Theme,
    mascot_loader: MascotLoader,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render main system dashboard."""
    snapshot = get_system_snapshot()

    if as_json:
        print(json.dumps(snapshot, indent=2))
        return 0

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   S Y S T E M", "システム監視  •  Resource Monitor", theme)))
    console.print()

    has_warnings = bool(snapshot["warnings"])
    mascot_state = "thinking" if has_warnings else "happy"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(mascot_state), theme)))
    console.print()

    # CPU & RAM Card
    cpu = snapshot["cpu"]
    mem = snapshot["memory"]
    cpu_bar = _render_bar(cpu["utilization_percent"])
    mem_bar = _render_bar(mem["percent"])

    perf_text = Text()
    perf_text.append(f"  CPU ({cpu['cores']} Cores)   ", style=theme.accent)
    perf_text.append(f"[{cpu_bar}] ", style=theme.warning if cpu["utilization_percent"] >= 80 else theme.primary)
    perf_text.append(f"{cpu['utilization_percent']:>5.1f}%\n", style=f"bold {theme.highlight}")

    perf_text.append("  RAM Usage      ", style=theme.accent)
    perf_text.append(f"[{mem_bar}] ", style=theme.warning if mem["percent"] >= 80 else theme.primary)
    perf_text.append(f"{mem['percent']:>5.1f}%  ", style=f"bold {theme.highlight}")
    perf_text.append(f"({mem['used_gb']:.1f} GB / {mem['total_gb']:.1f} GB)\n", style=theme.muted)

    console.print(Align.center(framed_section(perf_text, "Processor & Memory Utilization", theme)))
    console.print()

    # Disks Table
    disk_table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    disk_table.add_column("Mount", width=12, style=theme.text)
    disk_table.add_column("Used / Total", width=22, style=theme.muted)
    disk_table.add_column("Free", width=14, justify="right", style=theme.highlight)
    disk_table.add_column("Usage", width=18)

    for d in snapshot["disks"]:
        bar = _render_bar(d["percent"], width=10)
        status_style = theme.error if d["percent"] >= 90 else theme.warning if d["percent"] >= 80 else theme.success
        disk_table.add_row(
            d["mount"],
            f"{d['used_gb']:.1f} GB / {d['total_gb']:.1f} GB",
            f"{d['free_gb']:.1f} GB free",
            Text(f"[{bar}] {d['percent']:.0f}%", style=status_style),
        )

    console.print(Align.center(framed_section(disk_table, "Disk Storage Mounts", theme)))
    console.print()

    # Top Processes Table
    proc_table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    proc_table.add_column("PID", width=10, justify="right", style=theme.dim)
    proc_table.add_column("Process Name", width=34, style=theme.text)
    proc_table.add_column("Memory (RSS)", width=16, justify="right", style=theme.highlight)
    proc_table.add_column("CPU %", width=10, justify="right", style=theme.secondary)

    for p in snapshot["top_processes"]:
        proc_table.add_row(
            str(p["pid"]),
            p["name"],
            f"{p['mem_mb']:.1f} MB",
            f"{p['cpu_percent']:.1f}%",
        )

    console.print(Align.center(framed_section(proc_table, "Top Memory Consumers", theme)))
    console.print()

    # Diagnostic Warnings / Suggestions
    if snapshot["warnings"]:
        warn_text = Text()
        for w in snapshot["warnings"]:
            warn_text.append(f"  ! {w}\n", style=f"bold {theme.warning}")
        console.print(Align.center(framed_section(warn_text, "Resource Alerts", theme)))
        console.print()
    else:
        console.print(Align.center(
            styled_line(("✓  All resource metrics operating within nominal parameters.", theme.success))
        ))
        console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_system_disk(
    theme: Theme,
    mascot_loader: MascotLoader,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render detailed disk storage breakdown."""
    disks = get_disk_partitions()
    if as_json:
        print(json.dumps([asdict(d) for d in disks], indent=2))
        return 0

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   D I S K", "ディスク使用状況  •  Storage Analysis", theme)))
    console.print()

    table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    table.add_column("Drive / Mount", width=16, style=theme.text)
    table.add_column("Total Size", width=14, justify="right", style=theme.text)
    table.add_column("Used Space", width=14, justify="right", style=theme.muted)
    table.add_column("Free Space", width=14, justify="right", style=theme.highlight)
    table.add_column("Utilization", width=22)

    for d in disks:
        bar = _render_bar(d.percent, width=12)
        st = theme.error if d.percent >= 90 else theme.warning if d.percent >= 80 else theme.success
        table.add_row(
            d.mount,
            f"{d.total_gb:.2f} GB",
            f"{d.used_gb:.2f} GB",
            f"{d.free_gb:.2f} GB",
            Text(f"[{bar}] {d.percent:.1f}%", style=st),
        )

    console.print(Align.center(framed_section(table, "Disk Volumes & Partitions", theme)))
    console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_system_processes(
    theme: Theme,
    mascot_loader: MascotLoader,
    limit: int = 15,
    sort_by: str = "memory",
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render top active processes list."""
    procs = get_top_processes(limit=limit, sort_by=sort_by)
    if as_json:
        print(json.dumps([asdict(p) for p in procs], indent=2))
        return 0

    console.clear()
    console.print()
    subtitle = f"プロセス一覧  •  Top Processes by {sort_by.capitalize()}"
    console.print(Align.center(build_header("P A K U   P R O C E S S E S", subtitle, theme)))
    console.print()

    table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
    table.add_column("PID", width=10, justify="right", style=theme.dim)
    table.add_column("Process Name", style=theme.text)
    table.add_column("Memory (RSS)", width=16, justify="right", style=theme.highlight)
    table.add_column("CPU %", width=12, justify="right", style=theme.secondary)

    for p in procs:
        table.add_row(
            str(p.pid),
            p.name,
            f"{p.mem_mb:.1f} MB",
            f"{p.cpu_percent:.1f}%",
        )

    card_title = f"Top {len(procs)} Active Processes"
    console.print(Align.center(framed_section(table, card_title, theme)))
    console.print()

    console.print(Align.center(
        styled_line(("ℹ Read-only: Paku inspects process usage safely without terminating processes.", theme.muted))
    ))
    console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return 0


def render_system_monitor(
    theme: Theme,
    mascot_loader: MascotLoader,
    interval: float = 2.0,
    max_cycles: Optional[int] = None,
) -> int:
    """Live interactive periodic system monitor (clean exit on Ctrl+C or 'q')."""
    console.clear()
    cycle = 0
    try:
        while True:
            cycle += 1
            render_system_overview(theme, mascot_loader, as_json=False, wait_for_enter=False)
            console.print(Align.center(
                styled_line((f"Refreshing every {interval:.1f}s · Press Ctrl+C to exit monitor.", theme.dim))
            ))
            if max_cycles and cycle >= max_cycles:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print()
        console.print(Align.center(
            styled_line(("Monitor stopped cleanly.", theme.muted))
        ))
        console.print()

    return 0
