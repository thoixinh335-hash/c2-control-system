-- ============================================
-- C2 System Schema - PostgreSQL
-- Database: c2_db
-- ============================================

-- Bảng thiết bị (Agents)
CREATE TABLE IF NOT EXISTS devices (
    device_id       VARCHAR(64) PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    ip_address      VARCHAR(45),
    os_name         VARCHAR(100),
    os_version      VARCHAR(100),
    cpu_cores       INTEGER,
    total_ram_mb    BIGINT,
    agent_version   VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'offline',   -- online | offline | error
    first_seen      TIMESTAMP DEFAULT NOW(),
    last_seen       TIMESTAMP DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'
);

-- Bảng người dùng (Dashboard users)
CREATE TABLE IF NOT EXISTS users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(150),
    role            VARCHAR(20) DEFAULT 'operator',  -- admin | operator | viewer
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_login      TIMESTAMP
);

-- Bảng lệnh (Command queue & history)
CREATE TABLE IF NOT EXISTS commands (
    command_id      SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    command_text    TEXT NOT NULL,
    command_type    VARCHAR(50) DEFAULT 'shell',      -- shell | upload | download | script
    status          VARCHAR(20) DEFAULT 'pending',    -- pending | sent | running | completed | failed | timeout
    output          TEXT,
    exit_code       INTEGER,
    created_at      TIMESTAMP DEFAULT NOW(),
    sent_at         TIMESTAMP,
    completed_at    TIMESTAMP,
    timeout_sec     INTEGER DEFAULT 60
);

-- Bảng nhật ký (System logs)
CREATE TABLE IF NOT EXISTS logs (
    log_id          SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) REFERENCES devices(device_id) ON DELETE CASCADE,
    level           VARCHAR(20) DEFAULT 'INFO',       -- DEBUG | INFO | WARN | ERROR | CRITICAL
    source          VARCHAR(50) DEFAULT 'server',      -- server | agent | dashboard
    message         TEXT NOT NULL,
    details         JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Bảng cấu hình (Key-value config)
CREATE TABLE IF NOT EXISTS configs (
    config_key      VARCHAR(100) PRIMARY KEY,
    config_value    TEXT NOT NULL,
    description     VARCHAR(500),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Bảng cảnh báo (Alerts)
CREATE TABLE IF NOT EXISTS alerts (
    alert_id        SERIAL PRIMARY KEY,
    device_id       VARCHAR(64) REFERENCES devices(device_id) ON DELETE CASCADE,
    alert_type      VARCHAR(50) NOT NULL,              -- offline | high_cpu | high_ram | command_fail | custom
    severity        VARCHAR(20) DEFAULT 'info',        -- info | warning | critical
    title           VARCHAR(255) NOT NULL,
    message         TEXT,
    is_read         BOOLEAN DEFAULT FALSE,
    is_resolved     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    resolved_at     TIMESTAMP
);

-- Indexes cho hiệu năng
CREATE INDEX IF NOT EXISTS idx_commands_device   ON commands(device_id);
CREATE INDEX IF NOT EXISTS idx_commands_status   ON commands(status);
CREATE INDEX IF NOT EXISTS idx_logs_device       ON logs(device_id);
CREATE INDEX IF NOT EXISTS idx_logs_created      ON logs(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_device     ON alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unread     ON alerts(is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_devices_status    ON devices(status);

-- Insert dữ liệu cấu hình mặc định
INSERT INTO configs (config_key, config_value, description) VALUES
    ('heartbeat_interval', '30', 'Khoảng thời gian heartbeat (giây)'),
    ('command_timeout', '60', 'Timeout mặc định cho lệnh (giây)'),
    ('max_log_days', '30', 'Số ngày giữ log trước khi xóa'),
    ('alert_cpu_threshold', '90', 'Ngưỡng CPU để cảnh báo (%)'),
    ('alert_ram_threshold', '85', 'Ngưỡng RAM để cảnh báo (%)')
ON CONFLICT (config_key) DO NOTHING;

-- Insert user admin mặc định (password: admin123)
-- Mật khẩu được hash bằng passlib bcrypt
INSERT INTO users (username, password_hash, display_name, role) VALUES
    ('admin', '$2b$12$LJ3m4ys3Lk0TSwHCpNqrquEfHLAJMVzgUaEUhG5f5fHybFNFrKZq', 'Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;
