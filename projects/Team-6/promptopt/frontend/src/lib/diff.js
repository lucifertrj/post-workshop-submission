export function computeDiff(baseText, optimizedText) {
  const tokenize = (text) => text.split(/(\s+|[.,!?;:])/).filter(t => t.length > 0);
  const a = tokenize(baseText), b = tokenize(optimizedText);
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) {
    if (a[i - 1] === b[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1;
    else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
  }
  const result = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) { result.unshift({ type: 'equal', text: a[i - 1] }); i--; j--; }
    else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) { result.unshift({ type: 'add', text: b[j - 1] }); j--; }
    else { result.unshift({ type: 'remove', text: a[i - 1] }); i--; }
  }
  const merged = [];
  for (const token of result) {
    const last = merged[merged.length - 1];
    if (last && last.type === token.type) last.text += token.text;
    else merged.push({ ...token });
  }
  return merged;
}