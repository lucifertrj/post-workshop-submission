import { useState } from 'react';
import { computeDiff } from '../lib/diff';

export default function DiffViewer({ basePrompt, optimizedPrompt, maxHeight = 200 }) {
  const [expanded, setExpanded] = useState(false);
  if (!basePrompt || !optimizedPrompt) return <div className="t3" style={{ fontStyle: 'italic' }}>No diff available</div>;
  const diffTokens = computeDiff(basePrompt, optimizedPrompt);
  const previewText = diffTokens.slice(0, expanded ? diffTokens.length : 80).map((t, i) => {
    const style = { equal: { color: 'var(--t2)' }, add: { background: 'var(--grb)', color: '#065f46', padding: '0 3px', borderRadius: 3, fontWeight: 500 }, remove: { background: 'var(--reb)', color: '#991b1b', padding: '0 3px', borderRadius: 3, textDecoration: 'line-through' } }[t.type];
    return <span key={i} style={style}>{t.text}</span>;
  });
  const isTruncated = diffTokens.length > 80 && !expanded;
  return (
    <div className="diff-viewer">
      <div className="diff-content" style={{ maxHeight, overflow: 'auto', lineHeight: 1.6, fontSize: 13 }}>{previewText}</div>
      {isTruncated && <button className="show-more-btn" onClick={() => setExpanded(true)}>Show more ({diffTokens.length - 80} tokens)</button>}
      <style>{`
        .diff-viewer { position: relative; }
        .diff-content { font-family: var(--mono); white-space: pre-wrap; word-break: break-word; }
        .show-more-btn { margin-top: 8px; font-size: 12px; color: var(--ac); background: none; border: none; cursor: pointer; padding: 4px 0; font-weight: 500; }
        .show-more-btn:hover { text-decoration: underline; }
      `}</style>
    </div>
  );
}