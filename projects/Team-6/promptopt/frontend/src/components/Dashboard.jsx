import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../lib/api';

function StatCard({ title, value, sub, color, border }) {
  return (
    <div className="stat-card" style={{ borderTop: `3px solid ${border}` }}>
      <div className="stat-title t2">{title}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      {sub && <div className="stat-sub t3">{sub}</div>}
    </div>
  );
}

function ActivityItem({ event }) {
  const dotColor = { run_complete: 'var(--gr)', prompt_saved: 'var(--gr)', run_started: 'var(--bl)', iter_complete: 'var(--bl)', early_stop: 'var(--am)', run_failed: 'var(--re)' }[event.type] || 'var(--t3)';
  return (
    <div className="activity-item">
      <span className="activity-dot" style={{ background: dotColor }} />
      <div>
        <div className="t">{event.message}</div>
        <div className="t3" style={{ fontSize: '11px' }}>{new Date(event.timestamp).toLocaleTimeString()}</div>
      </div>
    </div>
  );
}

function ActiveRunCard({ run }) {
  const progress = Math.min(100, Math.round((run.iterations_run / run.max_iterations) * 100));
  return (
    <div className="active-run-card">
      <div className="active-run-header">
        <span className="run-id t3">{run.id}</span>
        <span className={`status-pill ${run.status}`}>{run.status}</span>
      </div>
      <div className="t" style={{ fontWeight: 500 }}>{run.task_name}</div>
      <div className="t3" style={{ fontSize: '12px' }}>{run.scorer} • {run.mode}</div>
      <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%`, background: 'var(--ac)' }} /></div>
      <div className="t2" style={{ fontSize: '12px' }}>Best: {run.best_score ?? '—'}</div>
    </div>
  );
}

export default function Dashboard() {
  const [runs, setRuns] = useState([]);
  const [activity, setActivity] = useState([]);
  const [stats, setStats] = useState({ best: 0, active: 0, improvement: 0, variants: 0 });

  useEffect(() => {
    Promise.all([api.getRuns(), api.getRecentActivity()]).then(([allRuns, recent]) => {
      setRuns(allRuns); setActivity(recent);
      const completed = allRuns.filter(r => r.status === 'complete');
      const best = completed.length ? Math.max(...completed.map(r => r.best_score)).toFixed(2) : '—';
      const active = allRuns.filter(r => r.status === 'running').length;
      const improvements = completed.filter(r => r.baseline_score).map(r => r.best_score - r.baseline_score);
      const avgImp = improvements.length ? (improvements.reduce((a,b)=>a+b,0)/improvements.length*100).toFixed(0) : '—';
      const totalVars = allRuns.reduce((sum, r) => sum + (r.iterations_run * r.variants_per_iter), 0);
      setStats({ best, active, improvement: avgImp + '%', variants: totalVars });
    });
  }, []);

  const chartData = runs.filter(r => r.status === 'complete' && r.best_score != null).sort((a,b) => new Date(a.created_at) - new Date(b.created_at)).map((r, i) => ({ name: `R${i+1}`, score: r.best_score }));
  const activeRuns = runs.filter(r => r.status === 'running');

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <StatCard title="Best Score" value={stats.best} sub="Across completed runs" color="var(--gr)" border="var(--gr)" />
        <StatCard title="Active Runs" value={stats.active} sub="Currently optimizing" color="var(--bl)" border="var(--bl)" />
        <StatCard title="Avg Improvement" value={stats.improvement} sub="vs baseline" color="var(--am)" border="var(--am)" />
        <StatCard title="Total Variants" value={stats.variants} sub="Generated this session" color="var(--pu)" border="var(--pu)" />
      </div>
      <div className="dashboard-grid">
        <div className="card chart-card">
          <h3 className="card-title">Score Trend</h3>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="name" stroke="var(--t3)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--t3)" fontSize={11} tickLine={false} axisLine={false} domain={[0.5, 1]} />
                <Tooltip contentStyle={{ background: 'var(--bg2)', border: `1px solid var(--bd)`, borderRadius: 6, fontSize: 12 }} />
                <Line type="monotone" dataKey="score" stroke="var(--gr)" strokeWidth={2} dot={{ r: 3, fill: 'var(--gr)' }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card activity-card">
          <h3 className="card-title">Recent Activity</h3>
          <div className="activity-list">{activity.map(ev => <ActivityItem key={ev.id} event={ev} />)}</div>
        </div>
      </div>
      {activeRuns.length > 0 && (
        <div className="card">
          <h3 className="card-title">Active Optimizations</h3>
          <div className="active-runs-grid">{activeRuns.map(run => <ActiveRunCard key={run.id} run={run} />)}</div>
        </div>
      )}
      <style>{`
        .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
        .stat-card{background:var(--bg2);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)}
        .stat-title{font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
        .stat-value{font-family:var(--disp);font-size:28px;font-weight:600;margin:8px 0}
        .stat-sub{font-size:11px}
        .dashboard-grid{display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:24px}
        .card{background:var(--bg2);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}
        .card-title{font-family:var(--disp);font-weight:600;font-size:16px;margin-bottom:16px;color:var(--t)}
        .activity-list{display:flex;flex-direction:column;gap:12px}
        .activity-item{display:flex;gap:10px;align-items:flex-start}
        .activity-dot{width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0}
        .active-runs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
        .active-run-card{background:var(--bg3);border-radius:var(--radius);padding:16px;border:1px solid var(--bd)}
        .active-run-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
        .run-id{font-family:var(--mono);font-size:11px}
        .status-pill{font-size:10px;font-weight:600;padding:2px 8px;border-radius:99px;background:var(--blb);color:var(--bl)}
        .status-pill.running{background:var(--blb);color:var(--bl)}
        .progress-bar{height:4px;background:var(--bd2);border-radius:2px;margin:12px 0;overflow:hidden}
        .progress-fill{height:100%;border-radius:2px;transition:width .3s}
        .chart-card .recharts-tooltip-wrapper{font-family:var(--sans)}
        @media(max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr)}.dashboard-grid{grid-template-columns:1fr}}
      `}</style>
    </div>
  );
}