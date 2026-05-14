import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

function StepItem({ step, current, done, onClick, summary }) {
  const state = done ? 'done' : current ? 'current' : 'todo';
  const colors = { done: { circle: 'var(--gr)', text: 'var(--gr)', bg: 'var(--grb)' }, current: { circle: 'var(--ac)', text: 'var(--ac2)', bg: 'rgba(26,110,245,0.09)' }, todo: { circle: 'var(--bd2)', text: 'var(--t3)', bg: 'var(--bg3)' } }[state];
  return (<button className={`step-item ${state}`} onClick={onClick} style={{ background: colors.bg }}><div className="step-circle" style={{ background: colors.circle, color: '#fff' }}>{done ? '✓' : step}</div><div className="step-content"><div className="step-label" style={{ color: colors.text }}>Step {step}</div>{summary && <div className="step-summary t3">{summary}</div>}</div></button>);
}

function countTokens(text) { return Math.round((text || '').length / 4); }
function validateDataset(jsonStr) {
  try { const data = JSON.parse(jsonStr); if (!Array.isArray(data)) return { valid: false, error: 'Must be a JSON array' }; if (data.length === 0) return { valid: false, error: 'At least 1 example required' }; const invalid = data.some(item => !item.input || !item.label); if (invalid) return { valid: false, error: 'Each item needs "input" and "label"' }; return { valid: true, count: data.length }; } catch (e) { return { valid: false, error: 'Invalid JSON syntax' }; }
}
function getSuggestedRules(taskType) {
  const suggestions = { classification: ['Be concise and direct', 'Return only the category name'], summarization: ['Keep under 3 sentences', 'Preserve key facts and numbers'], extraction: ['Output valid JSON only', 'Use consistent field names'], judge: ['Explain your reasoning briefly', 'Be strict about evidence'], generation: ['Match the requested tone', 'Stay on topic and avoid tangents'] };
  return suggestions[taskType] || ['Be clear and specific', 'Follow instructions exactly'];
}

export default function OptimizationWizard() {
  const navigate = useNavigate(); const [step, setStep] = useState(1);
  const [config, setConfig] = useState({ task_name: '', task_type: 'classification', base_prompt: '', mode: 'nodataset', dataset_json: '', criteria: [], max_iterations: 8, early_stop_threshold: 0.92, variants_per_iter: 5, scorer: 'accuracy' });
  const [errors, setErrors] = useState({}); const [datasetValidation, setDatasetValidation] = useState(null);
  const [newRule, setNewRule] = useState(''); const [launching, setLaunching] = useState(false);
  
  useEffect(() => { setConfig(prev => ({ ...prev, scorer: prev.mode === 'dataset' ? 'accuracy' : 'llm_judge' })); }, [config.mode]);
  useEffect(() => { if (config.mode === 'dataset' && config.dataset_json) setDatasetValidation(validateDataset(config.dataset_json)); else setDatasetValidation(null); }, [config.dataset_json, config.mode]);
  
  const validateStep = (stepNum) => {
    const newErrors = {};
    if (stepNum === 1) { if (!config.task_name.trim()) newErrors.task_name = 'Task name is required'; }
    if (stepNum === 2) { if (!config.base_prompt.trim()) newErrors.base_prompt = 'Base prompt is required'; if (countTokens(config.base_prompt) > 4000) newErrors.base_prompt = 'Prompt exceeds 4000 tokens'; }
    if (stepNum === 3) { if (config.mode === 'dataset') { if (!config.dataset_json) newErrors.dataset = 'Paste your dataset JSON'; else if (datasetValidation?.error) newErrors.dataset = datasetValidation.error; } else { if (config.criteria.length === 0) newErrors.criteria = 'Add at least 1 evaluation rule'; } }
    setErrors(newErrors); return Object.keys(newErrors).length === 0;
  };
  const nextStep = () => { if (validateStep(step)) setStep(s => Math.min(4, s + 1)); };
  const prevStep = () => setStep(s => Math.max(1, s - 1));
  const addRule = () => { if (newRule.trim() && config.criteria.length < 10) { setConfig(prev => ({ ...prev, criteria: [...prev.criteria, newRule.trim()] })); setNewRule(''); } };
  const removeRule = (idx) => { setConfig(prev => ({ ...prev, criteria: prev.criteria.filter((_, i) => i !== idx) })); };
  
  const handleLaunch = async () => {
    if (!validateStep(4)) return; setLaunching(true);
    try { const payload = { ...config, dataset: config.mode === 'dataset' ? JSON.parse(config.dataset_json) : undefined, criteria: config.mode === 'nodataset' ? config.criteria : undefined }; const newRun = await api.createRun(payload); navigate(`/runs?highlight=${newRun.id}`); } catch (err) { alert('Failed to launch: ' + err.message); } finally { setLaunching(false); }
  };
  
  const summaries = { 1: config.task_name || 'Not set', 2: config.base_prompt ? `${countTokens(config.base_prompt)} tokens` : 'Not set', 3: config.mode === 'dataset' ? (datasetValidation?.valid ? `${datasetValidation.count} examples` : 'Invalid JSON') : `${config.criteria.length} rules`, 4: `Max ${config.max_iterations} iters • Threshold ${config.early_stop_threshold}` };
  
  return (
    <div className="wizard">
      <aside className="wizard-sidebar">
        <div className="wizard-title">New Optimization</div>
        {[1, 2, 3, 4].map(s => (<StepItem key={s} step={s} current={step === s} done={step > s} onClick={() => step > s && setStep(s)} summary={summaries[s]} />))}
      </aside>
      <main className="wizard-content">
        {step === 1 && (<div className="step-panel"><h2>Task Configuration</h2><p className="t2">Define what you're optimizing</p><div className="form-group"><label>Task name *</label><input type="text" value={config.task_name} onChange={(e) => setConfig(prev => ({ ...prev, task_name: e.target.value }))} placeholder="e.g., Support Ticket Classifier" className={errors.task_name ? 'error' : ''} />{errors.task_name && <span className="error-msg">{errors.task_name}</span>}</div><div className="form-group"><label>Task type</label><select value={config.task_type} onChange={(e) => setConfig(prev => ({ ...prev, task_type: e.target.value }))}><option value="classification">Classification</option><option value="summarization">Summarization</option><option value="extraction">Extraction</option><option value="judge">Judge / Evaluation</option><option value="generation">Text Generation</option></select></div></div>)}
        {step === 2 && (<div className="step-panel"><h2>Base Prompt</h2><p className="t2">Your starting prompt — we'll improve it</p><div className="form-group"><label>Prompt text *</label><textarea value={config.base_prompt} onChange={(e) => setConfig(prev => ({ ...prev, base_prompt: e.target.value }))} placeholder="Enter your base prompt here..." className={`mono ${errors.base_prompt ? 'error' : ''}`} rows={8} /><div className="token-counter"><span className={countTokens(config.base_prompt) > 4000 ? 'warn' : 't3'}>{countTokens(config.base_prompt)} / 4000 tokens</span></div>{errors.base_prompt && <span className="error-msg">{errors.base_prompt}</span>}</div></div>)}
        {step === 3 && (<div className="step-panel"><h2>Evaluation Setup</h2><p className="t2">Choose how to score prompt variants</p><div className="mode-toggle"><button className={`mode-card ${config.mode === 'dataset' ? 'active' : ''}`} onClick={() => setConfig(prev => ({ ...prev, mode: 'dataset' }))}><div className="mode-icon">📊</div><div className="mode-title">With dataset</div><div className="mode-desc t3">Labeled examples for objective scoring</div></button><button className={`mode-card ${config.mode === 'nodataset' ? 'active' : ''}`} onClick={() => setConfig(prev => ({ ...prev, mode: 'nodataset' }))}><div className="mode-icon">✏️</div><div className="mode-title">No dataset</div><div className="mode-desc t3">Define criteria rules, no examples needed</div></button></div>{config.mode === 'dataset' && (<div className="form-group"><label>Dataset JSON *</label><textarea value={config.dataset_json} onChange={(e) => setConfig(prev => ({ ...prev, dataset_json: e.target.value }))} placeholder='[{"input": "What is your order number?", "label": "billing"}, ...]' className={`mono ${errors.dataset || datasetValidation?.error ? 'error' : ''}`} rows={10} />{datasetValidation && (<div className={`validation-msg ${datasetValidation.valid ? 'ok' : 'err'}`}>{datasetValidation.valid ? `✓ ${datasetValidation.count} examples loaded • JSON valid` : `✗ ${datasetValidation.error}`}</div>)}{errors.dataset && <span className="error-msg">{errors.dataset}</span>}</div>)}{config.mode === 'nodataset' && (<div className="form-group"><label>Evaluation rules *</label><div className="criteria-list">{config.criteria.map((rule, idx) => (<div key={idx} className="criteria-item"><span className="t">{rule}</span><button className="remove-btn" onClick={() => removeRule(idx)}>×</button></div>))}</div><div className="criteria-add"><input type="text" value={newRule} onChange={(e) => setNewRule(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addRule()} placeholder="Add a rule…" className="mono" /><button className="add-btn" onClick={addRule}>+ Add</button></div>{config.criteria.length === 0 && (<div className="suggestions t3">Suggested: {getSuggestedRules(config.task_type).map((s, i) => (<button key={i} className="suggestion-chip" onClick={() => { setConfig(prev => ({ ...prev, criteria: [...prev.criteria, s] })); }}>{s}</button>))}</div>)}{errors.criteria && <span className="error-msg">{errors.criteria}</span>}</div>)}</div>)}
        {step === 4 && (<div className="step-panel"><h2>Run Configuration</h2><p className="t2">Fine-tune the optimization loop</p><div className="slider-group"><label>Max iterations: <strong>{config.max_iterations}</strong></label><input type="range" min="2" max="20" value={config.max_iterations} onChange={(e) => setConfig(prev => ({ ...prev, max_iterations: Number(e.target.value) }))} /></div><div className="slider-group"><label>Early stop threshold: <strong>{config.early_stop_threshold.toFixed(2)}</strong></label><input type="range" min="0.5" max="1" step="0.01" value={config.early_stop_threshold} onChange={(e) => setConfig(prev => ({ ...prev, early_stop_threshold: Number(e.target.value) }))} /></div><div className="slider-group"><label>Variants per iteration: <strong>{config.variants_per_iter}</strong></label><input type="range" min="2" max="10" value={config.variants_per_iter} onChange={(e) => setConfig(prev => ({ ...prev, variants_per_iter: Number(e.target.value) }))} /></div><div className="scorer-info"><span className="t3">Scorer:</span> <strong>{config.scorer === 'accuracy' ? 'Accuracy (dataset mode)' : 'LLM Judge (criteria mode)'}</strong></div><button className="launch-btn" onClick={handleLaunch} disabled={launching}>{launching ? 'Launching...' : '✦ Launch optimization run →'}</button></div>)}
        <div className="wizard-nav"><button className="nav-btn secondary" onClick={prevStep} disabled={step === 1}>← Back</button>{step < 4 ? (<button className="nav-btn primary" onClick={nextStep}>Next →</button>) : (<button className="nav-btn primary" onClick={handleLaunch} disabled={launching}>{launching ? 'Launching...' : '✦ Launch run'}</button>)}</div>
      </main>
      <style>{`
        .wizard { display: flex; min-height: calc(100vh - 100px); gap: 24px; }
        .wizard-sidebar { width: 240px; background: var(--bg2); border-radius: var(--radius); padding: 20px; border: 1px solid var(--bd); display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
        .wizard-title { font-family: var(--disp); font-weight: 600; font-size: 16px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--bd); }
        .step-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px; border-radius: 8px; text-align: left; cursor: pointer; border: none; width: 100%; transition: all 0.15s; } .step-item:hover { filter: brightness(0.98); } .step-item.done { cursor: default; }
        .step-circle { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
        .step-content { flex: 1; min-width: 0; } .step-label { font-size: 12px; font-weight: 600; } .step-summary { font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .wizard-content { flex: 1; background: var(--bg2); border-radius: var(--radius); padding: 24px; border: 1px solid var(--bd); display: flex; flex-direction: column; }
        .step-panel h2 { font-family: var(--disp); font-weight: 600; font-size: 20px; margin-bottom: 4px; } .step-panel > .t2 { margin-bottom: 24px; }
        .form-group { margin-bottom: 20px; } .form-group label { display: block; font-weight: 500; margin-bottom: 8px; color: var(--t); }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--bd); border-radius: 6px; background: var(--bg); font-size: 13px; transition: border-color 0.15s; } .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: var(--ac); }
        .form-group input.error, .form-group textarea.error { border-color: var(--re); } .form-group .error-msg { color: var(--re); font-size: 11px; margin-top: 4px; display: block; }
        .mono { font-family: var(--mono); font-size: 12px; } .token-counter { text-align: right; font-size: 11px; margin-top: 4px; } .token-counter .warn { color: var(--am); font-weight: 600; }
        .mode-toggle { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .mode-card { padding: 16px; border: 2px solid var(--bd); border-radius: 8px; background: var(--bg); text-align: left; cursor: pointer; transition: all 0.15s; } .mode-card:hover { border-color: var(--ac); } .mode-card.active { border-color: var(--ac); background: rgba(26,110,245,0.06); }
        .mode-icon { font-size: 20px; margin-bottom: 8px; } .mode-title { font-weight: 600; margin-bottom: 4px; } .mode-desc { font-size: 12px; }
        .criteria-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; } .criteria-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg3); border-radius: 6px; font-size: 12px; } .remove-btn { background: none; border: none; color: var(--t3); font-size: 18px; cursor: pointer; padding: 0 4px; } .remove-btn:hover { color: var(--re); }
        .criteria-add { display: flex; gap: 8px; } .criteria-add input { flex: 1; } .add-btn { padding: 10px 16px; background: var(--ac); color: white; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; } .add-btn:hover { background: var(--ac2); }
        .suggestions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; } .suggestion-chip { padding: 4px 10px; background: var(--bg3); border: 1px solid var(--bd); border-radius: 99px; font-size: 11px; cursor: pointer; } .suggestion-chip:hover { background: var(--bg4); }
        .validation-msg { font-size: 11px; margin-top: 4px; font-weight: 500; } .validation-msg.ok { color: var(--gr); } .validation-msg.err { color: var(--re); }
        .slider-group { margin-bottom: 20px; } .slider-group label { display: flex; justify-content: space-between; font-weight: 500; margin-bottom: 8px; } .slider-group input[type="range"] { width: 100%; accent-color: var(--ac); }
        .scorer-info { background: var(--bg3); padding: 12px; border-radius: 6px; margin-bottom: 24px; font-size: 13px; display: flex; justify-content: space-between; }
        .launch-btn { width: 100%; padding: 14px; background: var(--ac); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; margin-top: auto; } .launch-btn:hover { background: var(--ac2); } .launch-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .wizard-nav { display: flex; justify-content: space-between; padding-top: 20px; border-top: 1px solid var(--bd); margin-top: auto; }
        .nav-btn { padding: 10px 24px; border-radius: 6px; font-weight: 500; cursor: pointer; border: none; font-size: 13px; } .nav-btn.secondary { background: var(--bg3); color: var(--t); } .nav-btn.secondary:hover { background: var(--bg4); } .nav-btn.secondary:disabled { opacity: 0.5; cursor: not-allowed; } .nav-btn.primary { background: var(--ac); color: white; } .nav-btn.primary:hover { background: var(--ac2); } .nav-btn.primary:disabled { opacity: 0.6; cursor: not-allowed; }
        @media(max-width: 900px) { .wizard { flex-direction: column; } .wizard-sidebar { width: 100%; flex-direction: row; overflow-x: auto; padding: 12px; } .step-item { flex-shrink: 0; } }
      `}</style>
    </div>
  );
}