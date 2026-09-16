import React from 'react';
import { Phone, Users, Stethoscope, Calendar, Plus, RefreshCw } from 'lucide-react';

export default function Navbar({
  activeTab, setActiveTab, onOpenSimulate, onRefresh, refreshing,
  callCount, patientCount, connected, usingDemo, lastUpdated,
}) {
  const tabs = [
    { id: 'calls', label: 'Calls & Triage', short: 'Calls', icon: Phone, count: callCount },
    { id: 'patients', label: 'Patients & Records', short: 'Patients', icon: Users, count: patientCount },
    { id: 'providers', label: 'Physicians & Protocols', short: 'Physicians', icon: Stethoscope, count: null },
    { id: 'schedule', label: 'Clinic Schedule', short: 'Schedule', icon: Calendar, count: null },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-3 h-16">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold tracking-wider shadow-sm shrink-0">
              KM
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-bold text-slate-900 text-base tracking-tight truncate">Kyron Medical</span>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 whitespace-nowrap">
                  Clinical Suite
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block truncate">AI Voice Scheduling & Clinical Operations</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center space-x-1 bg-slate-100 p-1 rounded-lg border border-slate-200 shrink-0">
            {tabs.map(({ id, label, icon: Icon, count }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === id
                    ? 'bg-white text-blue-700 shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{label}</span>
                {count != null && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-slate-200 text-slate-700 font-mono">
                    {count}
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <ConnectionDot connected={connected} usingDemo={usingDemo} lastUpdated={lastUpdated} />
            <button
              onClick={onOpenSimulate}
              className="inline-flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 rounded-md text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-colors shadow-sm whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Simulate Call</span>
              <span className="sm:hidden">Simulate</span>
            </button>
            <button
              onClick={onRefresh}
              disabled={refreshing}
              title={usingDemo ? 'Reconnect to the live backend to sync' : 'Sync latest calls from telephony'}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md border border-slate-200 transition-colors disabled:opacity-60"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="md:hidden flex items-center gap-1 py-2 border-t border-slate-100 text-xs overflow-x-auto">
          {tabs.map(({ id, short, icon: Icon, count }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1 py-1 px-2 rounded font-medium whitespace-nowrap ${
                activeTab === id ? 'text-blue-700 font-semibold bg-blue-50' : 'text-slate-600'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{short}{count != null ? ` (${count})` : ''}</span>
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}

function ConnectionDot({ connected, usingDemo, lastUpdated }) {
  if (usingDemo) {
    return (
      <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200 whitespace-nowrap" title="Static preview data — backend not connected">
        <span className="w-2 h-2 rounded-full bg-amber-500" />
        <span>Demo Data</span>
      </div>
    );
  }
  if (!connected) {
    return (
      <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-rose-700 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200 whitespace-nowrap">
        <span className="w-2 h-2 rounded-full bg-rose-500" />
        <span>Offline</span>
      </div>
    );
  }
  return (
    <div
      className="hidden lg:flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 whitespace-nowrap"
      title={lastUpdated ? `Last synced ${lastUpdated.toLocaleTimeString()}` : 'Connected to backend API'}
    >
      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
      <span>Live API</span>
    </div>
  );
}
