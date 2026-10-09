#!/usr/bin/env python3
# cliss: Live dashboard of your CPU, memory, network, disks, temperatures and top processes
import glob
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from clissfx import run, mix, gradient, clamp

GREEN, YELLOW, RED = (80, 220, 120), (240, 200, 60), (240, 80, 70)
HEAT = gradient([GREEN, YELLOW, RED], 101)
COOL = gradient([(70, 140, 255), (150, 110, 255), (230, 100, 220)], 101)
RX_COLORS = gradient([(40, 120, 200), (90, 220, 255)], 101)
TX_COLORS = gradient([(150, 60, 200), (255, 120, 220)], 101)
BORDER = (70, 85, 115)
TITLE = (140, 200, 255)
TEXT = (210, 215, 225)
DIM = (115, 120, 140)
TRACK = (32, 35, 46)
H_EIGHTHS = " ▏▎▍▌▋▊▉█"
V_EIGHTHS = " ▁▂▃▄▅▆▇█"
REAL_FS = {"ext2", "ext3", "ext4", "btrfs", "xfs", "zfs", "f2fs", "vfat", "exfat", "ntfs", "ntfs3", "fuseblk"}


def heat(f):
    return HEAT[int(clamp(f) * 100)]


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def human(n, suffix="B"):
    for unit in ("", "K", "M", "G", "T"):
        if abs(n) < 1024 or unit == "T":
            return ("%.0f%s%s" if unit == "" else "%.1f%s%s") % (n, unit, suffix)
        n /= 1024.0


def duration(sec):
    d, sec = divmod(int(sec), 86400)
    h, sec = divmod(sec, 3600)
    m = sec // 60
    return ("%dd %dh" % (d, h)) if d else ("%dh %dm" % (h, m)) if h else "%dm" % m


# ----------------------------------------------------------------- data ----

class Stats:
    """Samples /proc and /sys about once a second. Nothing here needs root."""

    INTERVAL = 0.5

    def __init__(self):
        self.host = socket.gethostname()
        self.kernel = platform.release()
        model = ""
        for line in (read("/proc/cpuinfo") or "").splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
        self.cpu_model = " ".join(model.replace("(R)", "").replace("(TM)", "").split()) or platform.machine()
        self.tick = os.sysconf("SC_CLK_TCK")
        self.page = os.sysconf("SC_PAGE_SIZE")
        self.nvidia = shutil.which("nvidia-smi")

        self.cpu = 0.0
        self.cores = []
        self.freq = None
        self.mem = {}
        self.load = (0.0, 0.0, 0.0)
        self.tasks = 0
        self.uptime = 0.0
        self.rx = self.tx = 0.0
        self.rd = self.wr = 0.0
        self.disks = []
        self.temps = []
        self.cpu_temp = None
        self.battery = None
        self.gpus = []
        self.top = []

        self.cpu_hist = deque(maxlen=400)
        self.mem_hist = deque(maxlen=400)
        self.rx_hist = deque(maxlen=400)
        self.tx_hist = deque(maxlen=400)

        self._cpu = self.read_cpu()
        self._net = self.read_net()
        self._io = self.read_io()
        self._procs = self.read_procs()
        self._t = time.monotonic()
        self.next = self._t + 0.3  # first real sample comes quickly
        self.ok = bool(self._cpu)

    # raw readers ---------------------------------------------------------

    @staticmethod
    def read_cpu():
        out = []
        for line in (read("/proc/stat") or "").splitlines():
            if not line.startswith("cpu"):
                break
            v = [int(x) for x in line.split()[1:9]]
            out.append((v[3] + v[4], sum(v)))
        return out

    @staticmethod
    def read_net():
        rx = tx = 0
        for line in (read("/proc/net/dev") or "").splitlines()[2:]:
            name, _, data = line.partition(":")
            if name.strip() == "lo":
                continue
            f = data.split()
            if len(f) >= 9:
                rx += int(f[0])
                tx += int(f[8])
        return rx, tx

    @staticmethod
    def read_io():
        try:
            disks = {d for d in os.listdir("/sys/block") if not d.startswith(("loop", "ram", "zram", "dm-", "sr"))}
        except OSError:
            disks = set()
        rd = wr = 0
        for line in (read("/proc/diskstats") or "").splitlines():
            f = line.split()
            if len(f) > 9 and f[2] in disks:
                rd += int(f[5]) * 512
                wr += int(f[9]) * 512
        return rd, wr

    @staticmethod
    def read_procs():
        procs = {}
        try:
            pids = [p for p in os.listdir("/proc") if p.isdigit()]
        except OSError:
            return procs
        for pid in pids:
            s = read("/proc/%s/stat" % pid)
            if not s:
                continue
            r = s.rfind(")")
            f = s[r + 2:].split()
            if len(f) > 21:
                procs[int(pid)] = (s[s.find("(") + 1:r], int(f[11]) + int(f[12]), int(f[21]))
        return procs

    # sampling ------------------------------------------------------------

    def maybe_sample(self):
        now = time.monotonic()
        if now < self.next:
            return
        dt = max(1e-3, now - self._t)
        self._t = now
        self.next = now + self.INTERVAL

        cpu = self.read_cpu()
        usage = []
        for (pi, pt), (ci, ct) in zip(self._cpu, cpu):
            d = ct - pt
            usage.append(clamp(1 - (ci - pi) / d) if d > 0 else 0.0)
        self._cpu = cpu
        if usage:
            self.cpu, self.cores = usage[0], usage[1:]
        self.cpu_hist.append(self.cpu)

        freqs = []
        for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
            v = read(p)
            if v and v.strip().isdigit():
                freqs.append(int(v))
        self.freq = sum(freqs) / len(freqs) / 1e6 if freqs else None

        mem = {}
        for line in (read("/proc/meminfo") or "").splitlines():
            k, _, v = line.partition(":")
            parts = v.split()
            if parts:
                mem[k] = int(parts[0]) * 1024
        self.mem = mem
        total = mem.get("MemTotal", 0)
        self.mem_hist.append((total - mem.get("MemAvailable", 0)) / total if total else 0)

        la = (read("/proc/loadavg") or "0 0 0 0/0").split()
        self.load = tuple(float(x) for x in la[:3])
        self.tasks = int(la[3].split("/")[1]) if "/" in la[3] else 0
        self.uptime = float((read("/proc/uptime") or "0").split()[0])

        rx, tx = self.read_net()
        self.rx, self.tx = max(0, rx - self._net[0]) / dt, max(0, tx - self._net[1]) / dt
        self._net = (rx, tx)
        self.rx_hist.append(self.rx)
        self.tx_hist.append(self.tx)

        rd, wr = self.read_io()
        self.rd, self.wr = max(0, rd - self._io[0]) / dt, max(0, wr - self._io[1]) / dt
        self._io = (rd, wr)

        self.disks = self.read_disks()
        self.read_sensors()
        self.read_gpus()

        procs = self.read_procs()
        top = []
        for pid, (name, ticks, rss) in procs.items():
            prev = self._procs.get(pid)
            used = (ticks - prev[1]) if prev and prev[0] == name else 0
            top.append((used / self.tick / dt * 100, rss * self.page, pid, name))
        top.sort(reverse=True)
        self.top = top
        self._procs = procs

    def read_disks(self):
        seen, out = set(), []
        for line in (read("/proc/mounts") or "").splitlines():
            f = line.split()
            if len(f) < 3 or f[2] not in REAL_FS or f[0] in seen or f[1].startswith(("/snap", "/boot")):
                continue
            seen.add(f[0])
            try:
                st = os.statvfs(f[1])
            except OSError:
                continue
            total = st.f_blocks * st.f_frsize
            if total:
                out.append((f[1], total - st.f_bfree * st.f_frsize, total))
        return out

    def read_sensors(self):
        temps = []
        cpu_temp = None
        for h in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            name = (read(h + "/name") or "?").strip()
            for inp in sorted(glob.glob(h + "/temp*_input")):
                v = read(inp)
                try:
                    c = int(v) / 1000.0
                except (TypeError, ValueError):
                    continue
                if not 0 < c < 150:
                    continue
                label = (read(inp[:-6] + "_label") or "").strip()
                temps.append((("%s %s" % (name, label)).strip(), c))
                if cpu_temp is None and name in ("k10temp", "coretemp", "zenpower", "cpu_thermal"):
                    cpu_temp = c
        self.temps = temps
        self.cpu_temp = cpu_temp

        self.battery = None
        for b in sorted(glob.glob("/sys/class/power_supply/BAT*")):
            cap = read(b + "/capacity")
            if cap and cap.strip().isdigit():
                self.battery = (int(cap), (read(b + "/status") or "").strip())
                break

    def read_gpus(self):
        gpus = []
        for dev in sorted(glob.glob("/sys/class/drm/card[0-9]*/device")):
            busy = read(dev + "/gpu_busy_percent")
            if busy is None or not busy.strip().isdigit():
                continue
            used = read(dev + "/mem_info_vram_used")
            total = read(dev + "/mem_info_vram_total")
            gpus.append(("GPU%d" % len(gpus), int(busy) / 100,
                         int(used) if used else 0, int(total) if total else 0))
        if self.nvidia:
            try:
                out = subprocess.run(
                    [self.nvidia, "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=0.8).stdout
                for line in out.strip().splitlines():
                    name, util, used, total = [x.strip() for x in line.split(",")]
                    gpus.append((name.replace("NVIDIA ", "").replace("GeForce ", ""),
                                 int(util) / 100, int(used) << 20, int(total) << 20))
            except (OSError, ValueError, subprocess.SubprocessError):
                self.nvidia = None
        self.gpus = gpus


_stats = None


def stats():
    """One sampler for the whole run, so history survives terminal resizes."""
    global _stats
    if _stats is None:
        _stats = Stats()
    return _stats


# -------------------------------------------------------------- drawing ----

def box(s, x, y, w, h, title, note=""):
    if w < 4 or h < 2:
        return
    for i in range(x + 1, x + w - 1):
        s.put(i, y, "─", BORDER)
        s.put(i, y + h - 1, "─", BORDER)
    for j in range(y + 1, y + h - 1):
        s.put(x, j, "│", BORDER)
        s.put(x + w - 1, j, "│", BORDER)
    s.put(x, y, "╭", BORDER)
    s.put(x + w - 1, y, "╮", BORDER)
    s.put(x, y + h - 1, "╰", BORDER)
    s.put(x + w - 1, y + h - 1, "╯", BORDER)
    s.text(x + 2, y, " %s " % title, TITLE, None, True)
    if note and len(title) + len(note) + 8 < w:
        s.text(x + w - len(note) - 3, y, note, DIM)


def hbar(s, x, y, w, frac, palette):
    """A horizontal bar with eighth-cell precision, colored along its length."""
    if w <= 0:
        return
    fill = clamp(frac) * w
    n = int(fill)
    part = int((fill - n) * 8)
    for i in range(w):
        col = palette[min(100, int((i + 0.5) / w * 100))]
        if i < n:
            s.put(x + i, y, "█", col, TRACK)
        elif i == n and part:
            s.put(x + i, y, H_EIGHTHS[part], col, TRACK)
        else:
            s.put(x + i, y, " ", None, TRACK)


def graph(s, x, y, w, h, values, top, palette, flip=False):
    """A scrolling area chart, newest sample on the right."""
    if w <= 0 or h <= 0:
        return
    vals = list(values)[-w:]
    pad = w - len(vals)
    for c in range(w):
        v = vals[c - pad] if c >= pad else 0
        level = clamp(v / top if top else 0) * h * 8
        for r in range(h):
            fill = int(clamp(level - r * 8, 0, 8))
            if not fill:
                break
            col = palette[int(r / max(1, h - 1) * 100) if h > 1 else int(clamp(v / top) * 100)]
            if flip:   # grows downward: only full and half blocks exist upside down
                ch = "█" if fill >= 6 else "▀" if fill >= 3 else "▔"
                s.put(x + c, y + r, ch, col)
            else:
                s.put(x + c, y + h - 1 - r, V_EIGHTHS[fill], col)


class SystemMonitor:
    def __init__(self, scr):
        self.s = scr
        self.st = stats()
        self.cores = []
        self.cpu = 0.0

    def ease(self, cur, target, dt):
        return cur + (target - cur) * min(1.0, dt * 8)

    # panels --------------------------------------------------------------

    def cpu_panel(self, x, y, w, h, t):
        st, s = self.st, self.s
        note = []
        if st.freq:
            note.append("%.2f GHz" % st.freq)
        if st.cpu_temp is not None:
            note.append("%d°C" % st.cpu_temp)
        box(s, x, y, w, h, "CPU", " · ".join(note))
        iw = w - 4
        s.text(x + 2, y + 1, ("%3d%%" % round(self.cpu * 100)), heat(self.cpu), None, True)
        s.text(x + 7, y + 1, st.cpu_model[:max(0, iw - 5)], DIM)

        n = len(self.cores)
        cols = 1 if iw < 40 else 2 if iw < 90 else 3
        rows = -(-n // cols) if n else 0
        gh = h - 3 - rows - 1
        if gh >= 2:
            graph(s, x + 2, y + 2, iw, gh, st.cpu_hist, 1.0, HEAT)
        else:
            gh = -1
        cy = y + 3 + gh
        cw = (iw - (cols - 1) * 2) // cols
        for i, v in enumerate(self.cores):
            r, c = i % rows, i // rows
            cx = x + 2 + c * (cw + 2)
            if cy + r >= y + h - 1:
                continue
            s.text(cx, cy + r, "%2d" % i, DIM)
            hbar(s, cx + 3, cy + r, cw - 8, v, HEAT)
            s.text(cx + cw - 4, cy + r, "%3d%%" % round(v * 100), heat(v))

    def mem_panel(self, x, y, w, h, t):
        st, s = self.st, self.s
        m = st.mem
        total = m.get("MemTotal", 0)
        used = total - m.get("MemAvailable", 0)
        swap_t = m.get("SwapTotal", 0)
        swap_u = swap_t - m.get("SwapFree", 0)
        box(s, x, y, w, h, "Memory", "%s total" % human(total))
        iw = w - 4
        lines = [("RAM ", used, total)]
        if swap_t:
            lines.append(("Swap", swap_u, swap_t))
        for i, (label, u, tot) in enumerate(lines):
            if y + 1 + i >= y + h - 1:
                break
            info = "%s / %s" % (human(u), human(tot))
            s.text(x + 2, y + 1 + i, label, TEXT, None, True)
            bw = iw - 6 - len(info) - 1
            hbar(s, x + 7, y + 1 + i, bw, u / tot if tot else 0, COOL)
            s.text(x + w - 2 - len(info), y + 1 + i, info, TEXT)
        gy = y + 1 + len(lines)
        gh = y + h - 1 - gy
        if gh >= 1:
            graph(s, x + 2, gy, iw, gh, st.mem_hist, 1.0, COOL)

    def net_panel(self, x, y, w, h, t):
        st, s = self.st, self.s
        box(s, x, y, w, h, "Network")
        iw = w - 4
        s.text(x + 2, y + 1, "▼ %s/s" % human(st.rx), RX_COLORS[100], None, True)
        tx = "▲ %s/s" % human(st.tx)
        s.text(x + w - 2 - len(tx), y + 1, tx, TX_COLORS[100], None, True)
        gh = h - 3
        if gh >= 2:
            top = max(64 * 1024, max(list(st.rx_hist)[-iw:] or [0]), max(list(st.tx_hist)[-iw:] or [0]))
            up = gh - gh // 2
            graph(s, x + 2, y + 2, iw, up, st.rx_hist, top, RX_COLORS)
            graph(s, x + 2, y + 2 + up, iw, gh // 2, st.tx_hist, top, TX_COLORS, flip=True)
            peak = "peak %s/s" % human(top)
            s.text(x + w - 2 - len(peak), y + h - 1, peak, DIM)

    def disk_panel(self, x, y, w, h, t):
        st, s = self.st, self.s
        box(s, x, y, w, h, "Disks", "R %s/s  W %s/s" % (human(st.rd), human(st.wr)))
        iw = w - 4
        for i, (mount, used, total) in enumerate(st.disks[:h - 2]):
            info = "%s / %s" % (human(used), human(total))
            name = mount if len(mount) <= 10 else "…" + mount[-9:]
            s.text(x + 2, y + 1 + i, name, TEXT, None, True)
            bw = iw - 11 - len(info) - 1
            hbar(s, x + 13, y + 1 + i, bw, used / total, HEAT)
            s.text(x + w - 2 - len(info), y + 1 + i, info, TEXT)

    def sensor_lines(self):
        st = self.st
        lines = []
        for name, busy, used, total in st.gpus:
            lines.append(("gpu", name, busy, used, total))
        if st.battery:
            lines.append(("bat",) + st.battery)
        for label, c in st.temps:
            lines.append(("temp", label, c))
        return lines

    def sensor_panel(self, x, y, w, h, t):
        s = self.s
        box(s, x, y, w, h, "Sensors")
        iw = w - 4
        for i, line in enumerate(self.sensor_lines()[:h - 2]):
            yy = y + 1 + i
            kind = line[0]
            if kind == "gpu":
                _, name, busy, used, total = line
                info = "%3d%%" % round(busy * 100)
                if total:
                    info += "  %s / %s" % (human(used), human(total))
                s.text(x + 2, yy, name[:10], TEXT, None, True)
                hbar(s, x + 13, yy, iw - 12 - len(info), busy, HEAT)
                s.text(x + w - 2 - len(info), yy, info, TEXT)
            elif kind == "bat":
                _, cap, status = line
                info = "%d%% %s" % (cap, status.lower())
                s.text(x + 2, yy, "Battery", TEXT, None, True)
                hbar(s, x + 13, yy, iw - 12 - len(info), cap / 100, HEAT[::-1])
                s.text(x + w - 2 - len(info), yy, info, TEXT)
            else:
                _, label, c = line
                info = "%d°C" % round(c)
                s.text(x + 2, yy, label[:iw - 6], DIM)
                s.text(x + w - 2 - len(info), yy, info, heat((c - 35) / 60), None, True)

    def proc_panel(self, x, y, w, h, t):
        st, s = self.st, self.s
        box(s, x, y, w, h, "Processes", "%d tasks" % st.tasks)
        if h < 4:
            return
        iw = w - 4
        name_w = max(6, iw - 7 - 7 - 9 - 3)
        s.text(x + 2, y + 1, "%7s %-*s %6s %8s" % ("PID", name_w, "NAME", "CPU%", "MEM"), DIM, None, True)
        for i, (cpu, rss, pid, name) in enumerate(st.top[:h - 3]):
            yy = y + 2 + i
            frac = cpu / 100
            s.text(x + 2, yy, "%7d" % pid, DIM)
            s.text(x + 10, yy, name[:name_w], TEXT, None, i == 0)
            s.text(x + 11 + name_w, yy, "%6.1f" % cpu, heat(frac), None, cpu >= 50)
            s.text(x + 18 + name_w, yy, "%8s" % human(rss), TEXT)

    # layout --------------------------------------------------------------

    def frame(self, dt, t):
        s, st = self.s, self.st
        st.maybe_sample()
        s.clear()
        w, h = s.w, s.h
        if not st.ok:
            msg = "SystemMonitor needs Linux (/proc is not available here)"
            s.text(max(0, (w - len(msg)) // 2), h // 2, msg, TEXT)
            return

        if len(self.cores) != len(st.cores):
            self.cores = list(st.cores)
        self.cores = [self.ease(c, v, dt) for c, v in zip(self.cores, st.cores)]
        self.cpu = self.ease(self.cpu, st.cpu, dt)

        # header
        dot = "●" if int(t * 2) % 2 else "○"
        s.text(1, 0, dot, heat(self.cpu))
        s.text(3, 0, st.host, TITLE, None, True)
        info = "  %s · up %s · load %.2f %.2f %.2f" % (st.kernel, duration(st.uptime), *st.load)
        s.text(3 + len(st.host), 0, info[:max(0, w - len(st.host) - 14)], DIM)
        clock = time.strftime("%H:%M:%S")
        s.text(w - len(clock) - 1, 0, clock, TEXT, None, True)

        top, avail = 1, h - 1
        n = len(st.cores)
        sensors = len(self.sensor_lines())
        if w >= 100 and h >= 24:
            lw = int(w * 0.56)
            rw = w - lw
            cols = 2 if lw - 4 < 90 else 3
            cpu_h = min(avail - 6, 4 + -(-n // cols) + max(3, avail // 4))
            self.cpu_panel(0, top, lw, cpu_h, t)
            self.proc_panel(0, top + cpu_h, lw, avail - cpu_h, t)

            disk_h = min(len(st.disks), 4) + 2 if st.disks else 0
            sens_h = min(sensors, 7) + 2 if sensors else 0
            rest = avail - disk_h - sens_h
            if rest < 12:   # not enough room: drop sensors, then disks
                rest += sens_h
                sens_h = 0
            if rest < 12:
                rest += disk_h
                disk_h = 0
            mem_h = rest // 2
            y = top
            self.mem_panel(lw, y, rw, mem_h, t)
            y += mem_h
            self.net_panel(lw, y, rw, rest - mem_h, t)
            y += rest - mem_h
            if disk_h:
                self.disk_panel(lw, y, rw, disk_h, t)
                y += disk_h
            if sens_h:
                self.sensor_panel(lw, y, rw, sens_h, t)
        else:
            # narrow terminals: stack what fits, most useful first
            cols = 1 if w - 4 < 40 else 2
            panels = [(self.cpu_panel, 3 + -(-n // cols) + 3),
                      (self.mem_panel, 6),
                      (self.net_panel, 6),
                      (self.proc_panel, 8)]
            y = top
            for i, (draw, want) in enumerate(panels):
                left = top + avail - y
                if left < 4:
                    break
                ph = left if i == len(panels) - 1 or left - want < 4 else want
                draw(0, y, w, ph, t)
                y += ph


if __name__ == "__main__":
    run(SystemMonitor, fps=20)
