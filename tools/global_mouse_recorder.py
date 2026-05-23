import ctypes
import ctypes.wintypes
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8766

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205

SM_CXSCREEN = 0
SM_CYSCREEN = 1

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LRESULT = ctypes.wintypes.LPARAM
WPARAM = ctypes.wintypes.WPARAM
LPARAM = ctypes.wintypes.LPARAM
HHOOK = ctypes.wintypes.HANDLE

LowLevelMouseProc = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    WPARAM,
    LPARAM,
)

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelMouseProc,
    ctypes.wintypes.HINSTANCE,
    ctypes.wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = HHOOK

user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.GetMessageW.argtypes = [
    ctypes.POINTER(ctypes.wintypes.MSG),
    ctypes.wintypes.HWND,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = ctypes.wintypes.HMODULE


class Recorder:
    def __init__(self):
        self.lock = threading.Lock()
        self.recording = False
        self.started_at = 0.0
        self.last_move_at = 0.0
        self.last_move = None
        self.events = []
        self.screen_width = max(1, user32.GetSystemMetrics(SM_CXSCREEN))
        self.screen_height = max(1, user32.GetSystemMetrics(SM_CYSCREEN))

    def start(self):
        with self.lock:
            self.recording = True
            self.started_at = time.perf_counter()
            self.last_move_at = 0.0
            self.last_move = None
            self.events = []

    def stop(self):
        with self.lock:
            self.recording = False
            return self.snapshot()

    def snapshot(self):
        duration = 0
        if self.events:
            duration = int(self.events[-1]["t"])
        return {
            "version": 1,
            "source": "global_mouse_recorder",
            "durationMs": duration,
            "screen": {
                "width": self.screen_width,
                "height": self.screen_height,
            },
            "events": list(self.events),
        }

    def add_mouse_event(self, message, x, y):
        with self.lock:
            if not self.recording:
                return

            now = time.perf_counter()
            t = int((now - self.started_at) * 1000)
            nx = min(1.0, max(0.0, x / self.screen_width))
            ny = min(1.0, max(0.0, y / self.screen_height))

            if message == WM_MOUSEMOVE:
                if now - self.last_move_at < 0.06:
                    return
                if self.last_move is not None:
                    dx = nx - self.last_move[0]
                    dy = ny - self.last_move[1]
                    if (dx * dx + dy * dy) < 0.000025:
                        return
                self.last_move = (nx, ny)
                self.last_move_at = now
                self.events.append({"t": t, "type": "move", "x": nx, "y": ny})
                return

            if message == WM_LBUTTONDOWN:
                self.events.append({"t": t, "type": "click", "button": 0, "x": nx, "y": ny})
                return

            if message == WM_RBUTTONDOWN:
                self.events.append({"t": t, "type": "click", "button": 2, "x": nx, "y": ny})
                return


recorder = Recorder()
hook_handle = None


@LowLevelMouseProc
def mouse_proc(n_code, w_param, l_param):
    if n_code >= 0:
        info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
        recorder.add_mouse_event(w_param, info.pt.x, info.pt.y)
    return user32.CallNextHookEx(hook_handle, n_code, w_param, l_param)


def install_mouse_hook():
    global hook_handle
    module_handle = kernel32.GetModuleHandleW(None)
    ctypes.set_last_error(0)
    hook_handle = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc, module_handle, 0)
    first_error = ctypes.get_last_error()
    if not hook_handle:
        ctypes.set_last_error(0)
        hook_handle = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc, None, 0)
    if not hook_handle:
        raise ctypes.WinError(ctypes.get_last_error() or first_error)

    msg = ctypes.wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "recording": recorder.recording})
            return

        if self.path == "/start":
            recorder.start()
            self.send_json(200, {"ok": True, "recording": True})
            return

        if self.path == "/stop":
            self.send_json(200, {"ok": True, "recording": False, "lesson": recorder.stop()})
            return

        if self.path == "/events":
            self.send_json(200, {"ok": True, "lesson": recorder.snapshot()})
            return

        self.send_json(404, {"ok": False, "error": "not found"})

    def log_message(self, fmt, *args):
        return


def main():
    hook_thread = threading.Thread(target=install_mouse_hook, daemon=True)
    hook_thread.start()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Global mouse recorder running at http://{HOST}:{PORT}")
    print("Endpoints: /health, /start, /stop, /events")
    server.serve_forever()


if __name__ == "__main__":
    main()
