// src/lib/api.js
const BASE = import.meta.env.VITE_DEMO_MODE === 'true' ? '' : 'http://localhost:8000';
const isDemo = import.meta.env.VITE_DEMO_MODE === 'true';

import { runs, variants, registry, activity } from './mockData';

const delay = (ms) => new Promise(res => setTimeout(res, ms));
const randomDelay = () => delay(300 + Math.random() * 400);

const api = {
  async getRuns(filters = {}) {
    if (!isDemo) {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.mode) params.append('mode', filters.mode);
      if (filters.task_type) params.append('task_type', filters.task_type);
      const res = await fetch(`${BASE}/runs?${params}`);
      return await res.json();
    }
    await randomDelay();
    let data = [...runs];
    if (filters.status) data = data.filter(r => r.status === filters.status);
    if (filters.mode) data = data.filter(r => r.mode === filters.mode);
    if (filters.task_type) data = data.filter(r => r.task_type === filters.task_type);
    return data;
  },

  async getRun(id) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/${id}`);
      if (!res.ok) throw new Error('Run not found');
      return await res.json();
    }
    await randomDelay();
    return runs.find(r => r.id === id) || null;
  },

  async getVariants(runId) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/${runId}/variants`);
      return await res.json();
    }
    await randomDelay();
    return variants.filter(v => v.run_id === runId);
  },

  async createRun(config) {
    if (!isDemo) {
      const payload = { ...config, dataset: config.mode === 'dataset' ? config.dataset : undefined, criteria: config.mode === 'nodataset' ? config.criteria : undefined };
      const res = await fetch(`${BASE}/runs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      return await res.json();
    }
    await randomDelay();
    const newRun = { id: `run-${Date.now()}`, ...config, status: 'queued', best_score: null, baseline_score: null, best_prompt: null, iterations_run: 0, token_count: 0, latency_ms: 0, failure_reason: null, created_at: new Date().toISOString(), completed_at: null };
    runs.unshift(newRun);
    return newRun;
  },

  async cancelRun(id) {
    if (!isDemo) {
      await fetch(`${BASE}/runs/${id}`, { method: 'DELETE' });
      return { success: true };
    }
    await randomDelay();
    const run = runs.find(r => r.id === id);
    if (run && ['queued', 'running'].includes(run.status)) { run.status = 'failed'; run.failure_reason = 'Cancelled by user'; run.completed_at = new Date().toISOString(); }
    return { success: true };
  },

  async getRegistry(filters = {}) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/registry`);
      return await res.json();
    }
    await randomDelay();
    return [...registry];
  },

  async saveToRegistry(runId) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/registry`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_id: runId }) });
      return await res.json();
    }
    await randomDelay();
    return { success: true };
  },

  async exportRun(id, format) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/${id}/export?format=${format}`);
      const data = await res.json();
      return format === 'text' ? data.prompt : JSON.stringify(data, null, 2);
    }
    await randomDelay();
    const run = runs.find(r => r.id === id);
    if (!run) return null;
    if (format === 'text') return run.best_prompt || run.base_prompt;
    if (format === 'json') return JSON.stringify(run, null, 2);
    return null;
  },

  async getVersions(runId) {
    if (!isDemo) {
      const res = await fetch(`${BASE}/runs/${runId}/versions`);
      return await res.json();
    }
    await randomDelay();
    return variants.filter(v => v.run_id === runId).sort((a, b) => b.score - a.score).map((v, i) => ({ ...v, version: i + 1, label: `Iteration ${v.iteration}` }));
  },

  async getRecentActivity() {
    await randomDelay();
    return activity.slice(0, 5);
  }
};

export default api;