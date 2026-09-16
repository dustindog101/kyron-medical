import React, { useState } from 'react';
import { X, Play, Zap, AlertCircle } from 'lucide-react';

const BODY_PARTS = ['Knee', 'Hip', 'Shoulder', 'Hand/Wrist', 'Foot/Ankle', 'Spine'];
const ISSUE_TYPES = ['Sports Medicine', 'Fracture', 'Joint Replacement', 'General'];
const LOCATIONS = [
  { code: 'MAIN', label: 'Main Campus' },
  { code: 'NORTH', label: 'North Clinic' },
  { code: 'WEST', label: 'Westside Office' },
];

/**
 * Inbound-call simulator. Submits to POST /api/calls/simulate, where the
 * backend runs the real routing engine + booking — the dashboard then
 * refreshes from live rows. No client-side routing logic remains here.
 */
export default function SimulatorModal({ isOpen, onClose, onRunSimulation, physicians, running, error }) {
  const [formData, setFormData] = useState({
    name: 'Jonathan Rivera',
    phone: '+12025557341',
    isNew: true,
    bodyPart: 'Knee',
    issueType: 'Sports Medicine',
    doctor: '',
    location: 'MAIN',
  });

  if (!isOpen) return null;

  const set = (patch) => setFormData((prev) => ({ ...prev, ...patch }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (running) return;
    onRunSimulation(formData);
  };

  const applyPreset = (preset) => {
    if (preset === 'patel-trap') {
      set({ name: 'Eleanor Vance', phone: '+13015551944', isNew: true, bodyPart: 'Hip', issueType: 'Joint Replacement', doctor: 'Dr. Aisha Patel', location: 'MAIN' });
    } else if (preset === 'knee-fracture') {
      set({ name: 'Tyler Johnson', phone: '+14155556622', isNew: true, bodyPart: 'Knee', issueType: 'Fracture', doctor: '', location: 'NORTH' });
    } else if (preset === 'spine-followup') {
      set({ name: 'Arthur Pendelton', phone: '+12405553377', isNew: false, bodyPart: 'Spine', issueType: 'General', doctor: 'Dr. Aisha Patel', location: 'MAIN' });
    }
  };

  const inputCls = 'w-full text-sm px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-60';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-blue-600 shrink-0" />
              <span>Simulate Inbound Patient Call</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Runs the live backend routing engine and books a real slot. The new call appears in the dashboard.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors shrink-0"
            aria-label="Close simulator"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-3.5 bg-blue-50/60 border border-blue-200 rounded-xl space-y-2">
          <div className="text-xs font-bold text-blue-900">⚡ 1-Click Evaluation Scenarios:</div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => applyPreset('patel-trap')} className="text-xs font-medium px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 hover:bg-blue-100 transition-colors">
              🔒 Closed Panel Trap (Patel → Chen)
            </button>
            <button type="button" onClick={() => applyPreset('knee-fracture')} className="text-xs font-medium px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 hover:bg-blue-100 transition-colors">
              🦴 Knee Fracture Match
            </button>
            <button type="button" onClick={() => applyPreset('spine-followup')} className="text-xs font-medium px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 hover:bg-blue-100 transition-colors">
              🩺 Established Spine Follow-up
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span className="break-words min-w-0">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Patient Full Name</label>
            <input type="text" required disabled={running} value={formData.name} onChange={(e) => set({ name: e.target.value })} className={inputCls} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="min-w-0">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Caller Phone</label>
              <input type="text" required disabled={running} value={formData.phone} onChange={(e) => set({ phone: e.target.value })} className={inputCls} />
            </div>
            <div className="min-w-0">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Patient Status</label>
              <select value={formData.isNew ? 'new' : 'returning'} disabled={running} onChange={(e) => set({ isNew: e.target.value === 'new' })} className={inputCls}>
                <option value="new">New Patient (First Visit)</option>
                <option value="returning">Established Returning Patient</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="min-w-0">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Affected Anatomy</label>
              <select value={formData.bodyPart} disabled={running} onChange={(e) => set({ bodyPart: e.target.value })} className={inputCls}>
                {BODY_PARTS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="min-w-0">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Clinical Issue</label>
              <select value={formData.issueType} disabled={running} onChange={(e) => set({ issueType: e.target.value })} className={inputCls}>
                {ISSUE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Requested Doctor (Optional — Tests Redirections)</label>
            <select value={formData.doctor} disabled={running} onChange={(e) => set({ doctor: e.target.value })} className={inputCls}>
              <option value="">No preference (Auto-match best specialist)</option>
              {physicians.map((p) => (
                <option key={p.id} value={p.name}>{p.name}{!p.accepts_new_patients ? ' (CLOSED to new patients)' : ''}</option>
              ))}
            </select>
            <p className="text-[11px] text-blue-600 mt-1">Tip: request Dr. Aisha Patel as a new patient to test closed-panel handling.</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Preferred Location</label>
            <select value={formData.location} disabled={running} onChange={(e) => set({ location: e.target.value })} className={inputCls}>
              {LOCATIONS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </div>

          <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} disabled={running} className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-60">
              Cancel
            </button>
            <button type="submit" disabled={running} className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-60">
              <Play className="w-3.5 h-3.5" />
              <span>{running ? 'Running simulation…' : 'Run Call Simulation'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
