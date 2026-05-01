import { useState, useEffect } from 'react';
import api from '../lib/api';
import DiffViewer from './DiffViewer';

export default function RunInspector({ runId, onClose }) {
  const [run, setRun] = useState(null);
  const [variants, setVariants] = useState([]);
  const [log, setLog] = useState([]);
  
  useEffect(() => {
    if (!runId) return;
    Promise.all([api.getRun(runId), api.getVariants(runId)]).then(([r, vars]) => {
      setRun(r); setVariants(vars.sort((a,b) => a.iteration - b.iteration));
      const entries = [
        { ts: r?.created_at, level: 'INFO', msg: `Run ${r?.id} initialized` },
        { ts: r?.created_at, level: 'INFO', msg: `Scoring baseline prompt...` },
        { ts: r?.created_at, level: 'SCORE', msg: `Baseline score: ${r?.baseline_score ?? '—'}` },
        ...vars.slice(0,3).map((v,i) => [
          { ts: v.created_at, level: 'INFO', msg: `Iteration ${v.iteration}: generated ${r?.variants_per_iter} variants` },
          { ts: v.created_at, level: 'SCORE', msg: `Variant ${i+1} score: ${v.score}` }
        ]).flat(),
        r?.status === 'complete' ? { ts: r.completed_at, level: 'DONE', msg: `Optimization complete. Best: ${r.best_score}` } :
        r?.status === 'failed' ? { ts: r.completed_at, level: 'ERROR', msg: `Failed: ${r.failure_reason}` } :
        { ts: new Date().toISOString(), level: 'INFO', msg: 'Optimization in progress...' }
      ];
      setLog(entries);
    });
  }, [runId]);
  
  if (!run) return <div className="inspector-empty t3">Select a run to inspect</div>;
  const sparkData = variants.map(v => ({ iter: v.iteration, score: v.score }));
  const maxScore = Math.max(...sparkData.map(d => d.score), 1);
  
  const handleExport = async () => {
    const text = await api.exportRun(runId, 'text');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${run.task_name.replace(/\s+/g,'_')}_prompt.txt`; a.click(); URL.revokeObjectURL(url);
  };
  const handleSave = async () => { await api.saveToRegistry(runId); alert('✓ Saved to Prompt Registry'); };
  
  return (
    <div className="inspector">
      <div className="inspector-header">
        <div><div className="inspector-id t3 mono">{run.id}</div><div className="inspector-title t">{run.task_name}</div></div>
        <button className="icon-btn" onClick={onClose}>↗</button>
      </div>
      <div className="metrics-grid">
        <div className="metric-box"><div className="metric-label t3">Best</div><div className="metric-value gr">{run.best_score ?? '—'}</div></div>
        <div className="metric-box"><div className="metric-label t3">Baseline</div><div className="metric-value t2">{run.baseline_score ?? '—'}</div></div>
        <div className="metric-box"><div className="metric-label t3">Tokens</div><div className="metric-value t2">{run.token_count}</div></div>
        <div className="metric-box"><div className="metric-label t3">Latency</div><div className="metric-value t2">{run.latency_ms}ms</div></div>
      </div>
      <div className="sparkline-container">
        <div className="t3" style={{ fontSize: 11, marginBottom: 8 }}>Score progression</div>
        <svg viewBox="0 0 300 60" className="sparkline">
          {sparkData.map((d, i) => {
            const x = 20 + (i * 50); const y = 50 - (d.score / maxScore * 40); const isLast = i === sparkData.length - 1;
            return (<g key={i}>{i > 0 && (<line x1={20 + ((i-1) * 50)} y1={50 - (sparkData[i-1].score / maxScore * 40)} x2={x} y2={y} stroke="var(--bd2)" strokeWidth="1" />)}<circle cx={x} cy={y} r={isLast ? 5 : 3} fill={isLast ? 'var(--gr)' : 'var(--ac)'} stroke="var(--bg2)" strokeWidth="2" /></g>);
          })}
        </svg>
      </div>
      <div className="diff-section">
        <div className="t3" style={{ fontSize: 11, marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}><span>Prompt evolution</span><span className="mono" style={{ fontSize: 10 }}>{variants.length} variants</span></div>
        <DiffViewer basePrompt={run.base_prompt} optimizedPrompt={run.best_prompt || variants[variants.length-1]?.prompt_text} />
      </div>
      <div className="log-section">
        <div className="t3" style={{ fontSize: 11, marginBottom: 8 }}>Run log</div>
        <div className="log-content mono">{log.map((entry, i) => (<div key={i} className={`log-line ${entry.level.toLowerCase()}`}><span className="log-time">{new Date(entry.ts).toLocaleTimeString()}</span><span className={`log-level ${entry.level}`}>[{entry.level}]</span><span className="log-msg">{entry.msg}</span></div>))}</div>
      </div>
      <div className="inspector-actions">
        <button className="btn secondary" onClick={handleExport}>↓ Export</button>
        <button className="btn primary" onClick={handleSave}>⊞ Save to registry</button>
      </div>
      <style>{`
        .inspector { width: 370px; background: var(--bg2); border-left: 1px solid var(--bd); padding: 20px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }
        .inspector-header { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 12px; border-bottom: 1px solid var(--bd); }
        .inspector-id { font-size: 11px; } .inspector-title { font-weight: 600; font-size: 15px; margin-top: 2px; }
        .icon-btn { background: var(--bg3); border-radius: 6px; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 14px; } .icon-btn:hover { background: var(--bg4); }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .metric-box { background: var(--bg3); border-radius: 6px; padding: 10px 8px; text-align: center; }
        .metric-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; } .metric-value { font-family: var(--disp); font-weight: 600; font-size: 18px; margin-top: 4px; }
        .gr { color: var(--gr); } .sparkline-container { background: var(--bg3); border-radius: 8px; padding: 12px; } .sparkline { width: 100%; height: 60px; }
        .diff-section { background: var(--bg3); border-radius: 8px; padding: 12px; } .log-section { flex: 1; min-height: 120px; }
        .log-content { background: var(--bg3); border-radius: 6px; padding: 10px; font-size: 11px; max-height: 150px; overflow-y: auto; line-height: 1.5; }
        .log-line { display: flex; gap: 8px; } .log-time { color: var(--t3); min-width: 45px; } .log-level { font-weight: 600; }
        .log-level.INFO { color: var(--bl); } .log-level.SCORE, .log-level.DONE { color: var(--gr); } .log-level.ERROR { color: var(--re); } .log-msg { color: var(--t2); }
        .inspector-actions { display: flex; gap: 10px; padding-top: 12px; border-top: 1px solid var(--bd); }
        .btn { flex: 1; padding: 10px; border-radius: 6px; font-weight: 500; font-size: 13px; cursor: pointer; border: none; }
        .btn.primary { background: var(--ac); color: white; } .btn.primary:hover { background: var(--ac2); }
        .btn.secondary { background: var(--bg3); color: var(--t); border: 1px solid var(--bd); } .btn.secondary:hover { background: var(--bg4); }
        .mono { font-family: var(--mono); }
      `}</style>
    </div>
  );
}