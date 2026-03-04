import React, { useState } from 'react';
import { authApi } from '../lib/api';

interface Props { onLogin: (user: any, token: string) => void; onGoRegister: () => void; }

export default function Login({ onLogin, onGoRegister }: Props) {
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await authApi.login(form);
      onLogin(res.data.user, res.data.access_token);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: '40px', width: '100%', maxWidth: 420, boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ width: 56, height: 56, borderRadius: 12, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, margin: '0 auto 16px' }}>🏦</div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>ChamaScore</h1>
          <p style={{ color: '#6b7280', fontSize: 14, marginTop: 4 }}>Sign in to your account</p>
        </div>
        {error && <div style={{ background: '#fee2e2', color: '#dc2626', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
        <form onSubmit={handle}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>Email</label>
            <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
              style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
              placeholder="john@example.co.ke" required />
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>Password</label>
            <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
              style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
              placeholder="••••••••" required />
          </div>
          <button type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px', background: loading ? '#93c5fd' : '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer' }}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#6b7280' }}>
          No account?{' '}
          <button onClick={onGoRegister} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Register here</button>
        </p>
      </div>
    </div>
  );
}