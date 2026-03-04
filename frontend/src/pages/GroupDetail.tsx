import React, { useEffect, useState } from 'react';
import { contributionsApi, loansApi, meetingsApi, scoreApi } from '../lib/api';

interface Props { group: any; user: any; onBack: () => void; }

const TABS = ['Overview', 'Contributions', 'Loans', 'Meetings', 'Credit Score'];

export default function GroupDetail({ group, user, onBack }: Props) {
  const [tab, setTab] = useState('Overview');
  const [contributions, setContributions] = useState<any[]>([]);
  const [loans, setLoans] = useState<any[]>([]);
  const [meetings, setMeetings] = useState<any[]>([]);
  const [score, setScore] = useState<any>(null);
  const [scoreLoading, setScoreLoading] = useState(false);

  useEffect(() => {
    contributionsApi.list(group.id).then(r => setContributions(r.data)).catch(() => {});
    loansApi.list(group.id).then(r => setLoans(r.data)).catch(() => {});
    meetingsApi.list(group.id).then(r => setMeetings(r.data)).catch(() => {});
  }, [group.id]);

  const loadScore = async () => {
    setScoreLoading(true);
    try { const r = await scoreApi.get(group.id); setScore(r.data); }
    catch (e) {} finally { setScoreLoading(false); }
  };

  useEffect(() => { if (tab === 'Credit Score') loadScore(); }, [tab]);

  const fmtKES = (n: number) => `KES ${Number(n).toLocaleString()}`;
  const bandColor: any = { Excellent: '#059669', 'Very Good': '#3b82f6', Good: '#8b5cf6', Fair: '#f59e0b', Poor: '#ef4444' };

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1000, margin: '0 auto' }}>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', fontSize: 14, fontWeight: 600, marginBottom: 16 }}>← Back to Dashboard</button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>🏦</div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>{group.name}</h1>
          <p style={{ color: '#6b7280', fontSize: 13 }}>{group.description} · {group.meeting_frequency} · KES {Number(group.contribution_amount).toLocaleString()}/cycle</p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '2px solid #e5e7eb', paddingBottom: 0 }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: tab === t ? 600 : 400, color: tab === t ? '#3b82f6' : '#6b7280', borderBottom: tab === t ? '2px solid #3b82f6' : '2px solid transparent', marginBottom: -2 }}>
            {t}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'Overview' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
            {[['Total Contributions', contributions.reduce((s, c) => s + Number(c.amount), 0), '#059669'],
              ['Active Loans', loans.filter(l => l.status === 'active').length + ' loans', '#dc2626'],
              ['Meetings Held', meetings.length + ' meetings', '#7c3aed']].map(([label, val, color]) => (
              <div key={label as string} style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: color as string }}>{typeof val === 'number' ? fmtKES(val) : val}</div>
              </div>
            ))}
          </div>
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20 }}>
            <h3 style={{ fontWeight: 600, marginBottom: 12 }}>Recent Contributions</h3>
            {contributions.slice(0, 5).map(c => (
              <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
                <span style={{ color: '#374151' }}>{c.contribution_date}</span>
                <span style={{ color: '#059669', fontWeight: 600 }}>{fmtKES(c.amount)}</span>
                <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 4 }}>{c.payment_method}</span>
              </div>
            ))}
            {contributions.length === 0 && <p style={{ color: '#9ca3af', fontSize: 13 }}>No contributions yet</p>}
          </div>
        </div>
      )}

      {/* Contributions */}
      {tab === 'Contributions' && (
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24 }}>
          <h3 style={{ fontWeight: 600, marginBottom: 16 }}>All Contributions</h3>
          {contributions.length === 0 ? <p style={{ color: '#9ca3af' }}>No contributions recorded yet</p> : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={{ borderBottom: '2px solid #f3f4f6' }}>
                {['Date', 'Amount', 'Method'].map(h => <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 12, color: '#6b7280', fontWeight: 600 }}>{h}</th>)}
              </tr></thead>
              <tbody>{contributions.map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid #f9fafb' }}>
                  <td style={{ padding: '10px 12px', fontSize: 13 }}>{c.contribution_date}</td>
                  <td style={{ padding: '10px 12px', fontSize: 13, color: '#059669', fontWeight: 600 }}>{fmtKES(c.amount)}</td>
                  <td style={{ padding: '10px 12px', fontSize: 13 }}>{c.payment_method}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}

      {/* Loans */}
      {tab === 'Loans' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {loans.length === 0 ? (
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 40, textAlign: 'center', color: '#9ca3af' }}>No loans yet</div>
          ) : loans.map(l => (
            <div key={l.id} style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{l.purpose}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>Applied: {l.application_date} · Rate: {l.interest_rate}%</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{fmtKES(l.amount)}</div>
                  <span style={{ fontSize: 11, padding: '2px 10px', borderRadius: 99, fontWeight: 600, background: l.status === 'active' ? '#ede9fe' : l.status === 'repaid' ? '#d1fae5' : '#fef3c7', color: l.status === 'active' ? '#5b21b6' : l.status === 'repaid' ? '#065f46' : '#92400e' }}>{l.status}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Meetings */}
      {tab === 'Meetings' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {meetings.length === 0 ? (
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 40, textAlign: 'center', color: '#9ca3af' }}>No meetings scheduled</div>
          ) : meetings.map(m => (
            <div key={m.id} style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20 }}>
              <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>📅 {m.title}</div>
              <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6 }}>{new Date(m.date).toLocaleDateString()}</div>
              {m.agenda && <div style={{ fontSize: 13, color: '#374151', background: '#f8fafc', padding: '8px 12px', borderRadius: 6 }}>{m.agenda}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Credit Score */}
      {tab === 'Credit Score' && (
        <div>
          {scoreLoading ? (
            <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>Calculating score...</div>
          ) : score ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, marginBottom: 16 }}>
                <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 28, textAlign: 'center' }}>
                  <div style={{ fontSize: 64, fontWeight: 800, color: bandColor[score.score_band] || '#111827', lineHeight: 1 }}>{score.score_value}</div>
                  <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>out of 850</div>
                  <div style={{ marginTop: 12, display: 'inline-block', padding: '6px 18px', borderRadius: 99, fontWeight: 700, fontSize: 14, background: bandColor[score.score_band] + '20', color: bandColor[score.score_band] }}>{score.score_band}</div>
                  <div style={{ marginTop: 16, fontSize: 12, color: '#9ca3af' }}>Calculated {score.score_date}</div>
                </div>
                <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24 }}>
                  <h3 style={{ fontWeight: 600, marginBottom: 16, fontSize: 15 }}>Feature Breakdown</h3>
                  {Object.entries(score.features).map(([key, f]: [string, any]) => (
                    <div key={key} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                        <span style={{ color: '#374151', fontWeight: 500 }}>{key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</span>
                        <span style={{ color: f.rating === 'excellent' ? '#059669' : f.rating === 'very_good' ? '#3b82f6' : f.rating === 'good' ? '#8b5cf6' : f.rating === 'fair' ? '#f59e0b' : '#ef4444', fontWeight: 600, textTransform: 'capitalize' }}>{f.rating.replace('_', ' ')}</span>
                      </div>
                      <div style={{ background: '#f3f4f6', borderRadius: 99, height: 6 }}>
                        <div style={{ width: `${f.normalized_score * 100}%`, background: f.rating === 'excellent' ? '#059669' : f.rating === 'very_good' ? '#3b82f6' : f.rating === 'good' ? '#8b5cf6' : f.rating === 'fair' ? '#f59e0b' : '#ef4444', height: '100%', borderRadius: 99 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20 }}>
                <h3 style={{ fontWeight: 600, marginBottom: 12, fontSize: 15 }}>💡 Recommendations</h3>
                {score.recommendations.map((r: string, i: number) => (
                  <div key={i} style={{ padding: '10px 16px', background: '#f0f9ff', borderLeft: '3px solid #3b82f6', borderRadius: 4, marginBottom: 8, fontSize: 13, color: '#374151' }}>{r}</div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>Could not load score</div>
          )}
        </div>
      )}
    </div>
  );
}