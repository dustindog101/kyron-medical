import React, { useMemo, useState } from 'react';
import {
  MapPin,
  CheckCircle2,
  Lock,
  Clock,
  ChevronRight,
  X,
} from 'lucide-react';
import { initialsOf } from '../api/normalize';

export default function ProvidersView({ physicians, locations, loading }) {
  const [selectedLocation, setSelectedLocation] = useState('ALL');
  const [selectedAnatomy, setSelectedAnatomy] = useState('ALL');
  const [selectedPanelStatus, setSelectedPanelStatus] = useState('ALL');
  const [activeDoctorModal, setActiveDoctorModal] = useState(null);

  const anatomies = useMemo(() => {
    const set = new Set();
    for (const doc of physicians) for (const p of doc.protocols) if (p.body_part) set.add(p.body_part);
    return [...set].sort();
  }, [physicians]);

  const filteredPhysicians = useMemo(() => physicians.filter((doc) => {
    if (selectedLocation !== 'ALL' && !doc.locations.some((loc) => loc.code === selectedLocation)) return false;
    if (selectedAnatomy !== 'ALL' && !doc.protocols.some((proto) => proto.body_part === selectedAnatomy)) return false;
    if (selectedPanelStatus === 'NEW' && !doc.accepts_new_patients) return false;
    if (selectedPanelStatus === 'CLOSED' && doc.accepts_new_patients) return false;
    return true;
  }), [physicians, selectedLocation, selectedAnatomy, selectedPanelStatus]);

  const locationOptions = locations.length > 0
    ? locations
    : [{ code: 'MAIN', name: 'Main Campus' }, { code: 'NORTH', name: 'North Clinic' }, { code: 'WEST', name: 'Westside Office' }];

  return (
    <div className="space-y-6 min-w-0">
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 min-w-0">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">Filter Providers:</span>
          <select value={selectedLocation} onChange={(e) => setSelectedLocation(e.target.value)} className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-full">
            <option value="ALL">All Campuses</option>
            {locationOptions.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
          <select value={selectedAnatomy} onChange={(e) => setSelectedAnatomy(e.target.value)} className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-full">
            <option value="ALL">All Anatomical Areas</option>
            {anatomies.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={selectedPanelStatus} onChange={(e) => setSelectedPanelStatus(e.target.value)} className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-full">
            <option value="ALL">All Panel Statuses</option>
            <option value="NEW">Accepting New Patients</option>
            <option value="CLOSED">Closed Panel (Follow-ups Only)</option>
          </select>
        </div>
        <div className="text-xs text-slate-500 whitespace-nowrap">
          Showing <strong className="text-slate-900">{filteredPhysicians.length}</strong> of {physicians.length} clinical providers
        </div>
      </div>

      {loading && physicians.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 h-56 animate-pulse" />
          ))}
        </div>
      ) : filteredPhysicians.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-sm text-slate-500">
          No providers match the selected filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredPhysicians.map((doc) => (
            <div
              key={doc.id}
              onClick={() => setActiveDoctorModal(doc)}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-blue-400 transition-all cursor-pointer flex flex-col justify-between min-w-0"
            >
              <div className="min-w-0">
                <div className="flex items-start justify-between gap-3 mb-3 min-w-0">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-11 h-11 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
                      {initialsOf(doc.name)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold text-slate-900 text-base truncate">{doc.name}</h3>
                      <p className="text-xs text-slate-500 truncate">{doc.specialty}</p>
                    </div>
                  </div>
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0 border whitespace-nowrap ${
                    doc.accepts_new_patients ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {doc.accepts_new_patients ? 'Open to New' : 'Closed Panel'}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 mb-3">
                  {doc.locations.map((loc) => (
                    <span key={loc.code} className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 whitespace-nowrap">
                      <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                      <span className="truncate">{loc.name}</span>
                    </span>
                  ))}
                  {doc.open_slots_count > 0 && (
                    <span className="inline-flex items-center text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 whitespace-nowrap">
                      {doc.open_slots_count} open slots
                    </span>
                  )}
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 mb-3 space-y-1.5 min-w-0">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Accepted Protocols:</div>
                  <div className="flex flex-wrap gap-1">
                    {doc.protocols.map((proto, pIdx) => (
                      <span key={pIdx} className="text-xs font-semibold px-2 py-0.5 rounded bg-white text-slate-800 border border-slate-200 break-words">
                        {proto.body_part}: <span className="text-blue-600 font-normal">{proto.type}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 text-xs text-slate-600 min-w-0">
                <span className="flex items-center gap-1.5 text-emerald-700 font-medium min-w-0">
                  <Clock className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{doc.next_slot}</span>
                </span>
                <span className="text-blue-600 font-semibold flex items-center gap-0.5 whitespace-nowrap shrink-0">
                  View Criteria <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeDoctorModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4" onClick={() => setActiveDoctorModal(null)}>
          <div
            className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={`${activeDoctorModal.name} profile`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-base shadow-sm shrink-0">
                  {initialsOf(activeDoctorModal.name)}
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-bold text-slate-900 break-words">{activeDoctorModal.name}</h2>
                  <p className="text-xs text-slate-500 break-words">{activeDoctorModal.specialty}</p>
                </div>
              </div>
              <button onClick={() => setActiveDoctorModal(null)} className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors shrink-0" aria-label="Close profile">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className={`p-3 rounded-lg border text-xs font-semibold flex items-start gap-2 ${
              activeDoctorModal.accepts_new_patients ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}>
              {activeDoctorModal.accepts_new_patients ? (
                <><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /><span>Accepting both new patient consultations and returning follow-ups.</span></>
              ) : (
                <><Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" /><span>Closed Panel: restricted to established follow-ups only. New patients are redirected per practice protocol.</span></>
              )}
            </div>

            <div className="space-y-1.5 min-w-0">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Practice Guidelines & Pre-Visit Criteria:</h4>
              <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200 leading-relaxed break-words">
                {activeDoctorModal.intake_criteria}
              </p>
            </div>

            <div className="space-y-1.5 min-w-0">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Anatomical Specialties Handled:</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {activeDoctorModal.protocols.map((p, idx) => (
                  <div key={idx} className="p-2 bg-slate-50 border border-slate-200 rounded-lg min-w-0">
                    <strong className="text-slate-900 break-words">{p.body_part}</strong>
                    <div className="text-blue-600 break-words">{p.type}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button onClick={() => setActiveDoctorModal(null)} className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors">
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
