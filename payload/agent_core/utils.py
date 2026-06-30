"""C2 Agent - Utilities"""
import socket, uuid, platform, psutil

def get_device_id():
    hostname = socket.gethostname()
    return f"{hostname}-{uuid.getnode():012x}"

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
