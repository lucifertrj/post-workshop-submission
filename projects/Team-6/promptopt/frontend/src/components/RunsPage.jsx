import { useState, useEffect, useMemo } from 'react';
import api from '../lib/api';
import RunInspector from './RunInspector';

function StatusPill({ status }) {
  const styles = { queued: { bg: 'var(--bg4)', color: 'var(--t3)', text: 'queued' }, running: { bg: 'var(--blb)', color: 'var(--bl)', text: 'running', pulse: true }, complete: { bg: 'var(--grb)', color: 'var(--gr)', text: 'complete' }, failed: { bg: 'var(--reb)', color: 'var(--re)', text: 'failed' } }[status] || { bg: 'var(--bg4)', color: 'var(--t3)', text: status };
  return (<span className={`status-pill ${styles.pulse ? 'pulse' : ''}`} style={{ background: styles.bg, color: styles.color }}>{styles.text}</span>);
}

function TypeTag({ type }) {
  const styles = { classification: { bg: 'var(--blb)', color: 'var(--bl)' }, summarization: { bg: 'var(--pub)', color: 'var(--pu)' }, extraction: { bg: 'var(--amb)', color: 'var(--am)' }, judge: { bg: 'var(--grb)', color: 'var(--gr)' }, generation: { bg: 'var(--blb)', color: 'var(--bl)' } }[type] || { bg: 'var(--bg4)', color: 'var(--t3)' };
  return <span className="type-tag" style={{ background: styles.bg, color: styles.color, fontSize: 11, padding: '2px 8px', borderRadius: 99, fontWeight: 500 }}>{type}</span>;
}

function ScoreBar({ score, baseline }) {
  const width = score ? `${Math.round(score * 100)}%` : '0%'; const baselineWidth = baseline ? `${Math.round(baseline * 100)}%` : '0%';
  return (<div className="score-bar"><div className="score-baseline" style={{ width: baselineWidth }} /><div className="score-fill" style={{ width }} /><span className="score-text">{score ? score.toFixed(2) : '—'}</span></div>);
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime(); const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now'; if (mins < 60) return `${mins}m ago`; const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`; const days = Math.floor(hrs / 24); return `${days}d ago`;
}

export default function RunsPage() {
  const [runs, setRuns] = useState([]); const [selectedRunId, setSelectedRunId] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); const [datasetFilter, setDatasetFilter] = useState('all');
  const [search, setSearch] = useState(''); const [debouncedSearch, setDebouncedSearch] = useState('');
  
  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => { api.getRuns().then(setRuns); }, []);
  
  const filteredRuns = useMemo(() => runs.filter(r => {
    if (activeTab !== 'all' && r.status !== activeTab) return false;
    if (datasetFilter === 'dataset' && r.mode !== 'dataset') return false;
    if (datasetFilter === 'nodataset' && r.mode !== 'nodataset') return false;
    if (debouncedSearch && !r.task_name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }), [runs, activeTab, datasetFilter, debouncedSearch]);
  
  const tabs = [{ id: 'all', label: `All (${runs.length})` }, { id: 'complete', label: `Completed (${runs.filter(r=>r.status==='complete').length})` }, { id: 'running', label: `Running (${runs.filter(r=>r.status==='running').length})` }, { id: 'failed', label: `Failed (${runs.filter(r=>r.status==='failed').length})` }];
  
  return (
    <div className="runs-page">
      <div className="tabs">{tabs.map(tab => (<button key={tab.id} className={`tab ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>))}</div>
      <div className="filters">
        <input type="text" placeholder="Search runs..." className="search-input" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className="filter-chips">{['all', 'dataset', 'nodataset'].map(mode => (<button key={mode} className={`chip ${datasetFilter === mode ? 'active' : ''}`} onClick={() => setDatasetFilter(mode)}>{mode === 'all' ? 'All modes' : mode === 'dataset' ? 'With dataset' : 'No dataset'}</button>))}</div>
      </div>
      <div className="runs-layout">
        <div className="runs-table">
          <table>
            <thead><tr><th>Run ID</th><th>Task</th><th>Type</th><th>Mode</th><th>Score</th><th>Tokens</th><th>Iters</th><th>Status</th><th>Time</th></tr></thead>
            <tbody>{filteredRuns.map(run => (<tr key={run.id} className={selectedRunId === run.id ? 'selected' : ''} onClick={() => setSelectedRunId(run.id)}><td className="mono">{run.id}</td><td><div className="t" style={{ fontWeight: 500 }}>{run.task_name}</div></td><td><TypeTag type={run.task_type} /></td><td className="t3" style={{ fontSize: 12 }}>{run.mode}</td><td><ScoreBar score={run.best_score} baseline={run.baseline_score} /></td><td className="t2">{run.token_count}</td><td className="t2">{run.iterations_run}/{run.max_iterations}</td><td><StatusPill status={run.status} /></td><td className="t3">{timeAgo(run.created_at)}</td></tr>))}</tbody>
          </table>
          {filteredRuns.length === 0 && <div className="empty-state t3">No runs match your filters</div>}
        </div>
        <RunInspector runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
      </div>
      <style>{`
        .runs-page { display: flex; flex-direction: column; height: calc(100vh - 100px); }
        .tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--bd); padding-bottom: 8px; }
        .tab { padding: 8px 16px; border-radius: 6px 6px 0 0; font-weight: 500; color: var(--t2); background: none; border: none; cursor: pointer; } .tab:hover { background: var(--bg3); color: var(--t); } .tab.active { background: var(--bg2); color: var(--ac2); border-bottom: 2px solid var(--ac); font-weight: 600; }
        .filters { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
        .search-input { flex: 1; max-width: 300px; padding: 8px 12px; border: 1px solid var(--bd); border-radius: 6px; background: var(--bg2); font-size: 13px; } .search-input:focus { outline: none; border-color: var(--ac); }
        .filter-chips { display: flex; gap: 6px; } .chip { padding: 6px 12px; border-radius: 99px; font-size: 12px; font-weight: 500; background: var(--bg3); color: var(--t2); border: none; cursor: pointer; } .chip:hover { background: var(--bg4); } .chip.active { background: var(--ac); color: white; }
        .runs-layout { display: flex; gap: 20px; flex: 1; min-height: 0; }
        .runs-table { flex: 1; background: var(--bg2); border-radius: 8px; border: 1px solid var(--bd); overflow: hidden; display: flex; flex-direction: column; }
        .runs-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .runs-table th { text-align: left; padding: 12px 16px; background: var(--bg3); color: var(--t2); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--bd); }
        .runs-table td { padding: 12px 16px; border-bottom: 1px solid var(--bd); }
        .runs-table tr:hover { background: var(--bg3); cursor: pointer; } .runs-table tr.selected { background: rgba(26,110,245,0.08); }
        .status-pill { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 99px; display: inline-block; } .status-pill.pulse { position: relative; } .status-pill.pulse::after { content: ''; position: absolute; width: 6px; height: 6px; background: currentColor; border-radius: 50%; right: -4px; top: 50%; transform: translateY(-50%); animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        .score-bar { position: relative; width: 80px; height: 6px; background: var(--bg4); border-radius: 3px; overflow: hidden; } .score-baseline { position: absolute; height: 100%; background: var(--bd2); } .score-fill { position: absolute; height: 100%; background: var(--gr); } .score-text { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-size: 9px; font-weight: 600; color: var(--t); text-shadow: 0 0 2px var(--bg2); }
        .empty-state { padding: 40px; text-align: center; font-size: 13px; } .mono { font-family: var(--mono); font-size: 12px; }
      `}</style>
    </div>
  );
}