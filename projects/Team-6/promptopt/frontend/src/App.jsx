import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from './lib/api';
import Dashboard from './components/Dashboard';
import RunsPage from './components/RunsPage';
import OptimizationWizard from './components/OptimizationWizard';
import PromptRegistry from './components/PromptRegistry';

function Sidebar() {
  const [runningCount, setRunningCount] = useState(0);
  useEffect(() => { api.getRuns({ status: 'running' }).then(d => setRunningCount(d.length)); }, []);
  const navItems = [
    { label: '◈ Dashboard', path: '/' },
    { label: ' Runs', path: '/runs', badge: runningCount > 0 ? runningCount : null },
    { label: '✦ New Optimization', path: '/wizard' },
    { label: '≡ Prompt Registry', path: '/registry' }
  ];
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">PromptOpt</div>
      <nav>
        {navItems.map((item, i) => (
          <NavLink key={i} to={item.path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end={item.path === '/'}>
            {item.label}
            {item.badge && <span className="badge">{item.badge}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

function Topbar({ title, children }) {
  return (<header className="topbar"><h2>{title}</h2><div className="topbar-actions">{children}</div></header>);
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<><Topbar title="Dashboard" /><Dashboard /></>} />
            <Route path="/runs" element={<><Topbar title="Runs" /><RunsPage /></>} />
            <Route path="/wizard" element={<><Topbar title="New Optimization" /><OptimizationWizard /></>} />
            <Route path="/registry" element={<><Topbar title="Prompt Registry" /><PromptRegistry /></>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}