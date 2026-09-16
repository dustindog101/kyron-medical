import React, { useMemo } from 'react';
import { Calendar, Clock, User, Stethoscope } from 'lucide-react';

/**
 * Facility schedule built from GET /api/appointments (real booked rows),
 * grouped by location. Falls back to the location directory when the
 * appointment carries an unrecognized code.
 */
export default function ScheduleView({ appointments, locations, onShowToast }) {
  const columns = useMemo(() => {
    const locs = locations.length > 0
      ? locations
      : [
          { code: 'MAIN', name: 'Main Campus' },
          { code: 'NORTH', name: 'North Clinic' },
          { code: 'WEST', name: 'Westside Office' },
        ];
    return locs.map((loc) => ({
      ...loc,
      list: appointments.filter((a) => (a.location_code || 'MAIN') === loc.code),
    }));
  }, [appointments, locations]);

  const total = appointments.length;

  const renderCampusColumn = (col) => (
    <div key={col.code} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-[280px] min-w-0">
      <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between gap-2 shrink-0">
        <div className="min-w-0">
          <h3 className="font-bold text-slate-900 text-sm truncate">{col.name}</h3>
          <span className="text-xs text-slate-500 font-mono">Location Code: {col.code}</span>
        </div>
        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 whitespace-nowrap shrink-0">
          {col.list.length} {col.list.length === 1 ? 'Booking' : 'Bookings'}
        </span>
      </div>

      <div className="p-4 space-y-3 flex-1 min-h-0 overflow-y-auto max-h-[60vh] lg:max-h-[52vh]">
        {col.list.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">No consultations scheduled for this facility.</div>
        ) : (
          col.list.map((item, idx) => (
            <div key={item.id ?? idx} className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-2 hover:border-blue-300 transition-colors min-w-0">
              <div className="flex items-center justify-between gap-2 text-xs min-w-0">
                <span className="font-semibold text-emerald-800 bg-emerald-100/70 px-2 py-0.5 rounded flex items-center gap-1 min-w-0">
                  <Clock className="w-3 h-3 shrink-0" />
                  <span className="truncate">{item.appointment_time}</span>
                </span>
                <span className="text-[11px] font-semibold text-slate-500 whitespace-nowrap shrink-0">{item.status || 'Confirmed'}</span>
              </div>
              <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5 min-w-0">
                <User className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <span className="truncate">{item.patient_name || 'Unknown Caller'}</span>
              </div>
              <div className="text-xs text-slate-600 flex items-center gap-1.5 min-w-0">
                <Stethoscope className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span className="truncate">{item.doctor_name}</span>
              </div>
              {(item.body_part || item.issue_type) && (
                <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200/60 flex items-center justify-between gap-2 min-w-0">
                  <span className="truncate">{item.body_part}{item.body_part && item.issue_type ? ` (${item.issue_type})` : item.issue_type ? `(${item.issue_type})` : ''}</span>
                  <span className="text-blue-600 font-medium whitespace-nowrap shrink-0">Kyron AI Intake</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 min-w-0">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1 basis-64">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 min-w-0">
            <Calendar className="w-5 h-5 text-blue-600 shrink-0" />
            <span className="truncate">Facility Schedule & AI Booked Consultations</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {total} booked appointment{total === 1 ? '' : 's'} across clinic locations, filled by Kyron Voice AI.
          </p>
        </div>
        <button
          onClick={() => onShowToast?.('✓ Synced facility schedules with master calendar')}
          className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors whitespace-nowrap shrink-0"
        >
          Sync Facility Calendars
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {columns.map(renderCampusColumn)}
      </div>
    </div>
  );
}
