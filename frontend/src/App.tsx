import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import GroupDetail from './pages/GroupDetail';

type Page = 'login' | 'register' | 'dashboard' | 'group';

export default function App() {
  const [page, setPage] = useState<Page>('login');
  const [user, setUser] = useState<any>(null);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
      setPage('dashboard');
    }
  }, []);

  const handleLogin = (user: any, token: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    setUser(user);
    setPage('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setPage('login');
  };

  const handleSelectGroup = (group: any) => {
    setSelectedGroup(group);
    setPage('group');
  };

  if (page === 'login') return <Login onLogin={handleLogin} onGoRegister={() => setPage('register')} />;
  if (page === 'register') return <Register onRegistered={() => setPage('login')} onGoLogin={() => setPage('login')} />;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f8fafc' }}>
      {/* Sidebar */}
      <div style={{ width: 220, background: '#0f172a', display: 'flex', flexDirection: 'column', padding: '24px 12px', position: 'fixed', top: 0, left: 0, bottom: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px', marginBottom: 32 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🏦</div>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>ChamaScore</div>
            <div style={{ color: '#64748b', fontSize: 11 }}>Credit Platform</div>
          </div>
        </div>
        {[['🏠', 'Dashboard', 'dashboard'], ['🏦', 'My Groups', 'dashboard']].map(([icon, label, target]) => (
          <button key={label} onClick={() => setPage(target as Page)}
            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 8, marginBottom: 4, background: page === target ? 'rgba(59,130,246,0.15)' : 'transparent', color: page === target ? '#60a5fa' : '#94a3b8', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: page === target ? 600 : 400, textAlign: 'left' as any, width: '100%' }}>
            <span>{icon}</span>{label}
          </button>
        ))}
        <div style={{ marginTop: 'auto', borderTop: '1px solid #1e293b', paddingTop: 16 }}>
          <div style={{ color: '#94a3b8', fontSize: 12, padding: '0 12px', marginBottom: 8 }}>{user?.full_name}</div>
          <button onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 8, background: 'transparent', color: '#ef4444', border: 'none', cursor: 'pointer', fontSize: 14, width: '100%' }}>
            🚪 Sign Out
          </button>
        </div>
      </div>

      {/* Main content */}
      <main style={{ marginLeft: 220, flex: 1 }}>
        {page === 'dashboard' && <Dashboard user={user} onSelectGroup={handleSelectGroup} />}
        {page === 'group' && selectedGroup && <GroupDetail group={selectedGroup} user={user} onBack={() => setPage('dashboard')} />}
      </main>
    </div>
  );
}