import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, FilePlus, BarChart, Settings, DollarSign, HelpCircle, Lightbulb } from 'lucide-react';

const items = [
  { to: '/dashboard', label: 'Dashboard', icon: Home },
  { to: '/create', label: 'Create', icon: FilePlus },
  { to: '/campaigns', label: 'My Campaigns', icon: BarChart },
  { to: '/analytics', label: 'Analytics', icon: BarChart },
  { to: '/idea-generator', label: 'Idea Generator', icon: Lightbulb },
  { to: '/pricing', label: 'Pricing', icon: DollarSign },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/help-support', label: 'Help & Support', icon: HelpCircle },
];

export default function AppSidebar() {
  return (
    <nav className="app-sidebar flex flex-col gap-4 bg-[var(--surface)] border-r border-[var(--border)] min-h-screen p-4">
      <div className="px-0 py-2">
        <div className="text-xl font-semibold text-[var(--text)]">Agent Anywhere</div>
        <div className="text-sm text-[var(--text-muted)] mt-1">Admin</div>
      </div>

      <div className="flex-1 px-2">
        <ul className="space-y-2">
          {items.map((it) => {
            const Icon = it.icon;
            return (
              <li key={it.to}>
                <NavLink
                  to={it.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition ${
                      isActive
                        ? 'bg-[var(--brand-50)] text-[var(--brand-700)] border border-[var(--brand-100)]'
                        : 'text-[var(--text)] bg-[var(--surface)] border border-[var(--border)] hover:bg-[var(--bg-muted)]'
                    }`
                  }
                  style={({ isActive }) => ({ color: isActive ? 'var(--brand-700)' : 'var(--text)' })}
                  end
                >
                  <Icon className="w-5 h-5" style={{ color: 'var(--text)' }} />
                  <span className="truncate" style={{ color: 'var(--text)' }}>{it.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="px-3 py-4 border-t border-[var(--border)] mt-4">
        <div className="text-xs text-[var(--text-muted)]">v1.0.0</div>
      </div>
    </nav>
  );
}
