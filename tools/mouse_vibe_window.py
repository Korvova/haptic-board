import time
import tkinter as tk
from tkinter import messagebox

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


BAUD_RATE = 115200
WAVE_STEP_MS = 28


class HapticWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Haptic Mouse Test")
        self.root.geometry("760x520")
        self.root.minsize(620, 420)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.ser = None
        self.last_x = None
        self.last_motion_at = 0.0
        self.last_wave_at = 0.0
        self.wave_jobs = []
        self.current_levels = (0, 0, 0)

        self.port_var = tk.StringVar(value=self.find_default_port())
        self.status_var = tk.StringVar(value="Disconnected")
        self.direction_var = tk.StringVar(value="Move inside the test area")
        self.level_var = tk.StringVar(value="L 0   C 0   R 0")
        self.intensity_var = tk.IntVar(value=190)
        self.threshold_var = tk.IntVar(value=3)
        self.gap_var = tk.IntVar(value=72)

        self.build_ui()
        self.root.after(40, self.idle_watchdog)

    def find_default_port(self):
        if list_ports is None:
            return "COM4"

        ports = list(list_ports.comports())
        if not ports:
            return "COM4"

        for port in ports:
            text = f"{port.device} {port.description}".lower()
            if "usb" in text or "uart" in text or "cp210" in text or "ch340" in text:
                return port.device
        return ports[0].device

    def build_ui(self):
        outer = tk.Frame(self.root, padx=16, pady=14)
        outer.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(outer)
        top.pack(fill=tk.X)

        tk.Label(top, text="Port").pack(side=tk.LEFT)
        tk.Entry(top, textvariable=self.port_var, width=12).pack(side=tk.LEFT, padx=(6, 8))
        tk.Button(top, text="Connect", command=self.connect).pack(side=tk.LEFT)
        tk.Button(top, text="Stop", command=self.stop).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(top, textvariable=self.status_var, anchor="e").pack(side=tk.RIGHT)

        controls = tk.Frame(outer, pady=10)
        controls.pack(fill=tk.X)

        self.add_slider(controls, "Power", self.intensity_var, 60, 255, 0)
        self.add_slider(controls, "Sensitivity", self.threshold_var, 1, 20, 1)
        self.add_slider(controls, "Wave gap ms", self.gap_var, 35, 180, 2)

        self.canvas = tk.Canvas(outer, bg="#111827", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 10))
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Configure>", self.draw_canvas)

        bottom = tk.Frame(outer)
        bottom.pack(fill=tk.X)
        tk.Label(bottom, textvariable=self.direction_var).pack(side=tk.LEFT)
        tk.Label(bottom, textvariable=self.level_var).pack(side=tk.RIGHT)

    def add_slider(self, parent, label, variable, from_, to, column):
        frame = tk.Frame(parent)
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 12))
        parent.columnconfigure(column, weight=1)
        tk.Label(frame, text=label).pack(anchor="w")
        tk.Scale(
            frame,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            variable=variable,
            showvalue=True,
        ).pack(fill=tk.X)

    def draw_canvas(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        third = width / 3

        colors = ["#2563eb", "#14b8a6", "#ef4444"]
        labels = ["LEFT D21", "CENTER D22", "RIGHT D23"]
        levels = self.current_levels

        for index in range(3):
            x0 = index * third
            x1 = (index + 1) * third
            self.canvas.create_rectangle(x0, 0, x1, height, fill=colors[index], outline="")
            overlay = 180 - int(levels[index] * 0.55)
            overlay = max(35, min(180, overlay))
            self.canvas.create_rectangle(x0, 0, x1, height, fill=f"#{overlay:02x}{overlay:02x}{overlay:02x}", outline="", stipple="gray50")
            self.canvas.create_text(
                (x0 + x1) / 2,
                height / 2,
                text=labels[index],
                fill="white",
                font=("Segoe UI", 18, "bold"),
            )

        self.canvas.create_text(
            width / 2,
            28,
            text="Move the mouse left or right here",
            fill="#e5e7eb",
            font=("Segoe UI", 12),
        )

    def connect(self):
        if serial is None:
            messagebox.showerror(
                "pyserial missing",
                "Install pyserial first: python -m pip install pyserial",
            )
            return

        self.disconnect()
        try:
            self.ser = serial.Serial(self.port_var.get().strip(), BAUD_RATE, timeout=0)
            time.sleep(1.8)
            self.status_var.set(f"Connected: {self.ser.port}")
            self.stop()
        except serial.SerialException as exc:
            self.ser = None
            self.status_var.set("Disconnected")
            messagebox.showerror("Serial error", str(exc))

    def disconnect(self):
        if self.ser is not None:
            try:
                self.send_stop()
                self.ser.close()
            except serial.SerialException:
                pass
        self.ser = None

    def send_levels(self, left, center, right):
        levels = tuple(max(0, min(255, int(v))) for v in (left, center, right))
        self.current_levels = levels
        self.level_var.set(f"L {levels[0]}   C {levels[1]}   R {levels[2]}")
        self.draw_canvas()

        if self.ser is None or not self.ser.is_open:
            return

        try:
            self.ser.write(f"V {levels[0]} {levels[1]} {levels[2]}\n".encode("ascii"))
        except serial.SerialException as exc:
            self.status_var.set(f"Serial error: {exc}")
            self.disconnect()

    def send_stop(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.write(b"S\n")

    def stop(self):
        for job in self.wave_jobs:
            self.root.after_cancel(job)
        self.wave_jobs.clear()
        self.send_levels(0, 0, 0)
        self.direction_var.set("Stopped")

    def on_enter(self, event):
        self.last_x = event.x
        self.last_motion_at = time.monotonic()

    def on_leave(self, event):
        self.last_x = None
        self.stop()

    def on_motion(self, event):
        now = time.monotonic()
        if self.last_x is None:
            self.last_x = event.x
            self.last_motion_at = now
            return

        dx = event.x - self.last_x
        self.last_x = event.x
        self.last_motion_at = now

        threshold = self.threshold_var.get()
        if abs(dx) < threshold:
            return

        min_gap = self.gap_var.get() / 1000.0
        if now - self.last_wave_at < min_gap:
            return

        direction = 1 if dx > 0 else -1
        speed_boost = min(65, abs(dx) * 4)
        power = min(255, self.intensity_var.get() + speed_boost)
        self.start_wave(direction, power)
        self.last_wave_at = now

    def start_wave(self, direction, power):
        for job in self.wave_jobs:
            self.root.after_cancel(job)
        self.wave_jobs.clear()

        soft = int(power * 0.28)
        mid = int(power * 0.62)

        if direction > 0:
            self.direction_var.set("Right: D21 -> D22 -> D23")
            frames = [
                (power, soft, 0),
                (mid, power, mid),
                (0, soft, power),
                (0, 0, 0),
            ]
        else:
            self.direction_var.set("Left: D23 -> D22 -> D21")
            frames = [
                (0, soft, power),
                (mid, power, mid),
                (power, soft, 0),
                (0, 0, 0),
            ]

        for index, frame in enumerate(frames):
            job = self.root.after(index * WAVE_STEP_MS, lambda f=frame: self.send_levels(*f))
            self.wave_jobs.append(job)

    def idle_watchdog(self):
        if time.monotonic() - self.last_motion_at > 0.18 and self.current_levels != (0, 0, 0):
            self.send_levels(0, 0, 0)
            self.direction_var.set("Idle")
        self.root.after(40, self.idle_watchdog)

    def close(self):
        self.stop()
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    HapticWindow(root)
    root.mainloop()
