import React, { useState } from 'react';
import { authApi } from '../lib/api';

interface Props { onRegistered: () => void; onGoLogin: () => void; }

export default function Register({ onRegistered, onGoLogin }: Props) {
  const [form, setForm] = useState({ email: '', phone: '', national_id: '', full_name: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await authApi.register(form);
      onRegistered();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally { setLoading(false); }
  };

  const field = (label: string, key: string, type = 'text', placeholder = '') => (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 13, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>{label}</label>
      <input type={type} value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}
        style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' as any }}
        placeholder={placeholder} required />
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: '40px', width: '100%', maxWidth: 440, boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ width: 56, height: 56, borderRadius: 12, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, margin: '0 auto 16px' }}>🏦</div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Create Account</h1>
          <p style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>Join ChamaScore today</p>
        </div>
        {error && <div style={{ background: '#fee2e2', color: '#dc2626', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>{error}</div>}
        <form onSubmit={handle}>
          {field('Full Name', 'full_name', 'text', 'John Kamau')}
          {field('Email', 'email', 'email', 'john@example.co.ke')}
          {field('Phone', 'phone', 'text', '0712345678')}
          {field('National ID', 'national_id', 'text', '12345678')}
          {field('Password', 'password', 'password', 'Min 8 chars, 1 uppercase, 1 number')}
          <button type="submit" disabled={loading}
            style={{ width: '100%', padding: '12px', background: loading ? '#93c5fd' : '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', marginTop: 8 }}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#6b7280' }}>
          Already have an account?{' '}
          <button onClick={onGoLogin} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Sign in</button>
        </p>
      </div>
    </div>
  );
}