import React, { useEffect, useState } from 'react';
import { groupsApi, scoreApi } from '../lib/api';

interface Props { user: any; onSelectGroup: (g: any) => void; }

export default function Dashboard({ user, onSelectGroup }: Props) {
  const [groups, setGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', contribution_amount: '', meeting_frequency: 'monthly', meeting_day: 'Saturday', created_date: '' });

  useEffect(() => {
    groupsApi.list().then(r => setGroups(r.data)).finally(() => setLoading(false));
  }, []);

  const createGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await groupsApi.create({ ...form, contribution_amount: Number(form.contribution_amount), created_date: form.created_date });
      setGroups([...groups, res.data]);
      setShowCreate(false);
      setForm({ name: '', description: '', contribution_amount: '', meeting_frequency: 'monthly', meeting_day: 'Saturday', created_date: '' });
    } catch (err: any) { alert(err.response?.data?.detail || 'Failed to create group'); }
  };

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700 }}>Welcome, {user.full_name.split(' ')[0]} 👋</h1>
          <p style={{ color: '#6b7280', marginTop: 4 }}>Manage your chama groups and track credit scores</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          style={{ padding: '10px 20px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontSize: 14 }}>
          + New Group
        </button>
      </div>

      {showCreate && (
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24, marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>Create New Chama Group</h3>
          <form onSubmit={createGroup}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {[['Group Name', 'name', 'text', 'Umoja Welfare Association'],
                ['Description', 'description', 'text', 'Monthly savings group'],
                ['Contribution Amount (KES)', 'contribution_amount', 'number', '2000'],
                ['Formation Date', 'created_date', 'date', '']].map(([label, key, type, ph]) => (
                <div key={key}>
                  <label style={{ fontSize: 12, fontWeight: 500, color: '#6b7280', display: 'block', marginBottom: 4 }}>{label}</label>
                  <input type={type} value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}
                    placeholder={ph} required
                    style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, boxSizing: 'border-box' as any }} />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 12, fontWeight: 500, color: '#6b7280', display: 'block', marginBottom: 4 }}>Meeting Frequency</label>
                <select value={form.meeting_frequency} onChange={e => setForm({ ...form, meeting_frequency: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13 }}>
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Biweekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button type="submit" style={{ padding: '8px 20px', background: '#059669', color: '#fff', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' }}>Create Group</button>
              <button type="button" onClick={() => setShowCreate(false)} style={{ padding: '8px 20px', background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>Loading your groups...</div>
      ) : groups.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🏦</div>
          <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No groups yet</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>Create your first chama group to get started</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {groups.map(g => (
            <div key={g.id} onClick={() => onSelectGroup(g)}
              style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24, cursor: 'pointer', transition: 'all 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}
              onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)')}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.06)')}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>🏦</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{g.name}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>{g.meeting_frequency} · KES {Number(g.contribution_amount).toLocaleString()}/cycle</div>
                </div>
              </div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>Formed {g.created_date} · Click to manage →</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}