import { NavLink } from 'react-router-dom';
import api from '../lib/api';
import { useEffect, useState } from 'react';

export default function Sidebar() {
  const [runningCount, setRunningCount] = useState(0);
  useEffect(() => { api.getRuns({ status: 'running' }).then(d => setRunningCount(d.length)); }, []);
  const navItems = [
    { label: ' Dashboard', path: '/' },
    { label: '↻ Runs', path: '/runs', badge: runningCount > 0 ? runningCount : null },
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