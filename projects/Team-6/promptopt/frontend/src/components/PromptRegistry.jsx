import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

function StatusPill({ status }) {
  const styles = { production: { bg: 'var(--grb)', color: 'var(--gr)', text: 'production' }, optimizing: { bg: 'var(--blb)', color: 'var(--bl)', text: 'optimizing', pulse: true }, draft: { bg: 'var(--bg4)', color: 'var(--t3)', text: 'draft' } }[status] || { bg: 'var(--bg4)', color: 'var(--t3)', text: status };
  return (<span className={`status-pill ${styles.pulse ? 'pulse' : ''}`} style={{ background: styles.bg, color: styles.color }}>{styles.text}</span>);
}
function TypeTag({ type }) {
  const styles = { classification: { bg: 'var(--blb)', color: 'var(--bl)' }, summarization: { bg: 'var(--pub)', color: 'var(--pu)' }, extraction: { bg: 'var(--amb)', color: 'var(--am)' }, judge: { bg: 'var(--grb)', color: 'var(--gr)' }, generation: { bg: 'var(--blb)', color: 'var(--bl)' } }[type] || { bg: 'var(--bg4)', color: 'var(--t3)' };
  return <span className="type-tag" style={{ background: styles.bg, color: styles.color, fontSize: 11, padding: '2px 8px', borderRadius: 99, fontWeight: 500 }}>{type}</span>;
}

function HistoryDrawer({ runId, onClose }) {
  const [versions, setVersions] = useState([]); const [selected, setSelected] = useState(null);
  useEffect(() => { if (runId) api.getVersions(runId).then(setVersions); }, [runId]);
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header"><h3 className="drawer-title">Version History</h3><button className="drawer-close" onClick={onClose}>×</button></div>
        {selected && (<div className="selected-preview"><div className="t3" style={{ fontSize: 11, marginBottom: 6 }}>Preview: Version {selected.version}</div><div className="mono preview-text">{selected.prompt_text}</div></div>)}
        <div className="versions-list">{versions.map((v, i) => (<button key={v.id} className={`version-row ${selected?.id === v.id ? 'selected' : ''}`} onClick={() => setSelected(v)}><span className="version-badge">v{v.version}</span><span className="version-label t">{v.label}</span><span className="version-score gr">{v.score?.toFixed(2) ?? '—'}</span><span className="version-time t3">{new Date(v.created_at).toLocaleDateString()}</span></button>))}</div>
      </div>
      <style>{`
        .drawer-overlay { position: fixed; inset: 0; background: rgba(13,20,36,0.4); z-index: 100; display: flex; justify-content: flex-end; }
        .drawer { width: 400px; background: var(--bg2); border-left: 1px solid var(--bd); display: flex; flex-direction: column; animation: slideIn 0.2s ease; }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
        .drawer-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--bd); } .drawer-title { font-family: var(--disp); font-weight: 600; font-size: 16px; }
        .drawer-close { background: none; border: none; font-size: 24px; color: var(--t3); cursor: pointer; line-height: 1; } .drawer-close:hover { color: var(--t); }
        .selected-preview { padding: 16px 20px; border-bottom: 1px solid var(--bd); background: var(--bg3); } .preview-text { font-size: 12px; line-height: 1.5; max-height: 100px; overflow-y: auto; white-space: pre-wrap; }
        .versions-list { flex: 1; overflow-y: auto; padding: 8px 0; }
        .version-row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 12px 20px; text-align: left; background: none; border: none; border-bottom: 1px solid var(--bd); cursor: pointer; transition: background 0.15s; } .version-row:hover { background: var(--bg3); } .version-row.selected { background: rgba(26,110,245,0.08); }
        .version-badge { background: var(--ac); color: white; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; } .version-label { flex: 1; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .version-score { font-family: var(--disp); font-weight: 600; font-size: 13px; } .version-time { font-size: 11px; }
        .gr { color: var(--gr); } .t { color: var(--t); } .t3 { color: var(--t3); } .mono { font-family: var(--mono); }
      `}</style>
    </div>
  );
}

function RegistryCard({ entry, onExport, onHistory, onReoptimize }) {
  return (
    <div className="registry-card">
      <div className="card-header"><div><div className="card-task t" style={{ fontWeight: 500, fontSize: '13.5px' }}>{entry.task_name}</div><div className="card-mode t3" style={{ fontSize: '11.5px' }}>{entry.mode}</div></div><StatusPill status={entry.status} /></div>
      <div className="card-body"><div className="card-prompt mono">{entry.prompt_text}</div><div className="card-meta"><span className="meta-item"><strong className="gr">{entry.best_score?.toFixed(2)}</strong> score</span><span className="meta-item">v{entry.version}</span><span className="meta-item">{entry.token_count} tokens</span><TypeTag type={entry.task_type} /></div></div>
      <div className="card-footer"><button className="card-btn" onClick={() => onExport(entry)}>↓ Export</button><button className="card-btn" onClick={() => onHistory(entry)}>⊞ History</button><button className="card-btn" onClick={() => onReoptimize(entry)}>↻ Re-optimize</button></div>
      <style>{`
        .registry-card { background: var(--bg2); border: 1px solid var(--bd); border-radius: var(--radius); display: flex; flex-direction: column; overflow: hidden; transition: box-shadow 0.15s; } .registry-card:hover { box-shadow: var(--shadow); }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 14px 16px; border-bottom: 1px solid var(--bd); } .card-task { margin-bottom: 2px; }
        .card-body { padding: 14px 16px; flex: 1; } .card-prompt { font-size: 12px; line-height: 1.5; color: var(--t2); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 12px; white-space: pre-wrap; }
        .card-meta { display: flex; flex-wrap: wrap; gap: 8px 12px; font-size: 11px; color: var(--t3); } .meta-item { display: flex; align-items: center; gap: 4px; } .meta-item strong { font-family: var(--disp); }
        .card-footer { display: flex; gap: 1px; background: var(--bg3); padding: 1px; } .card-btn { flex: 1; padding: 10px; background: none; border: none; font-size: 12px; font-weight: 500; color: var(--t2); cursor: pointer; transition: background 0.15s; } .card-btn:hover { background: var(--bg4); color: var(--t); }
        .status-pill { font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 99px; } .status-pill.pulse { position: relative; } .status-pill.pulse::after { content: ''; position: absolute; width: 5px; height: 5px; background: currentColor; border-radius: 50%; right: -3px; top: 50%; transform: translateY(-50%); animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        .mono { font-family: var(--mono); } .t { color: var(--t); } .t2 { color: var(--t2); } .t3 { color: var(--t3); } .gr { color: var(--gr); }
      `}</style>
    </div>
  );
}

export default function PromptRegistry() {
  const navigate = useNavigate(); const [entries, setEntries] = useState([]); const [activeTab, setActiveTab] = useState('all');
  const [modeFilter, setModeFilter] = useState('all'); const [search, setSearch] = useState(''); const [debouncedSearch, setDebouncedSearch] = useState('');
  const [historyEntry, setHistoryEntry] = useState(null);
  
  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 300); return () => clearTimeout(t); }, [search]);
  useEffect(() => { api.getRegistry().then(setEntries); }, []);
  
  const filteredEntries = entries.filter(e => {
    if (activeTab !== 'all' && e.status !== activeTab) return false;
    if (modeFilter === 'dataset' && e.mode !== 'dataset') return false;
    if (modeFilter === 'nodataset' && e.mode !== 'nodataset') return false;
    if (debouncedSearch && !e.task_name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });
  
  const tabs = [{ id: 'all', label: `All (${entries.length})` }, { id: 'production', label: `Production (${entries.filter(e=>e.status==='production').length})` }, { id: 'optimizing', label: `Optimizing (${entries.filter(e=>e.status==='optimizing').length})` }, { id: 'draft', label: `Draft (${entries.filter(e=>e.status==='draft').length})` }];
  
  const handleExport = async (entry) => { const text = await api.exportRun(entry.run_id, 'text'); const blob = new Blob([text], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${entry.task_name.replace(/\s+/g,'_')}_v${entry.version}.txt`; a.click(); URL.revokeObjectURL(url); };
  const handleHistory = (entry) => setHistoryEntry(entry);
  const handleReoptimize = (entry) => navigate('/wizard', { state: { base_prompt: entry.prompt_text, task_name: entry.task_name, task_type: entry.task_type } });
  
  return (
    <div className="registry-page">
      <div className="registry-actions"><button className="new-prompt-btn" onClick={() => navigate('/wizard')}>✦ New prompt</button></div>
      <div className="tabs">{tabs.map(tab => (<button key={tab.id} className={`tab ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>))}</div>
      <div className="filters">
        <input type="text" placeholder="Search prompts…" className="search-input" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className="filter-chips">{['all', 'dataset', 'nodataset'].map(mode => (<button key={mode} className={`chip ${modeFilter === mode ? 'active' : ''}`} onClick={() => setModeFilter(mode)}>{mode === 'all' ? 'All modes' : mode === 'dataset' ? 'With dataset' : 'No dataset'}</button>))}</div>
      </div>
      <div className="card-grid">{filteredEntries.map(entry => (<RegistryCard key={entry.id} entry={entry} onExport={handleExport} onHistory={handleHistory} onReoptimize={handleReoptimize} />))}</div>
      {filteredEntries.length === 0 && (<div className="empty-state t3">No prompts match your filters. <button className="link-btn" onClick={() => { setSearch(''); setModeFilter('all'); setActiveTab('all'); }}>Clear filters</button></div>)}
      {historyEntry && <HistoryDrawer runId={historyEntry.run_id} onClose={() => setHistoryEntry(null)} />}
      <style>{`
        .registry-page { display: flex; flex-direction: column; min-height: calc(100vh - 100px); } .registry-actions { display: flex; justify-content: flex-end; margin-bottom: 16px; }
        .new-prompt-btn { padding: 10px 20px; background: var(--ac); color: white; border: none; border-radius: 6px; font-weight: 500; font-size: 13px; cursor: pointer; } .new-prompt-btn:hover { background: var(--ac2); }
        .tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--bd); padding-bottom: 8px; } .tab { padding: 8px 16px; border-radius: 6px 6px 0 0; font-weight: 500; color: var(--t2); background: none; border: none; cursor: pointer; } .tab:hover { background: var(--bg3); color: var(--t); } .tab.active { background: var(--bg2); color: var(--ac2); border-bottom: 2px solid var(--ac); font-weight: 600; }
        .filters { display: flex; gap: 12px; align-items: center; margin-bottom: 24px; } .search-input { flex: 1; max-width: 300px; padding: 8px 12px; border: 1px solid var(--bd); border-radius: 6px; background: var(--bg2); font-size: 13px; } .search-input:focus { outline: none; border-color: var(--ac); }
        .filter-chips { display: flex; gap: 6px; } .chip { padding: 6px 12px; border-radius: 99px; font-size: 12px; font-weight: 500; background: var(--bg3); color: var(--t2); border: none; cursor: pointer; } .chip:hover { background: var(--bg4); } .chip.active { background: var(--ac); color: white; }
        .card-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; } .empty-state { text-align: center; padding: 40px; font-size: 13px; } .link-btn { background: none; border: none; color: var(--ac); cursor: pointer; font-weight: 500; padding: 0; text-decoration: underline; } .link-btn:hover { color: var(--ac2); } .t3 { color: var(--t3); }
        @media(max-width: 1100px) { .card-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}