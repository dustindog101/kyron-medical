// Shared call-status presentation. Backend enum: SCHEDULED | REDIRECTED |
// ABANDONED | FAILED. TRIAGE is a legacy mock-only value, still rendered.

export const STATUS_META = {
  SCHEDULED: {
    label: 'Scheduled',
    pill: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    solid: 'bg-emerald-100 text-emerald-800',
  },
  REDIRECTED: {
    label: 'Redirected',
    pill: 'bg-purple-50 text-purple-700 border-purple-200',
    solid: 'bg-purple-100 text-purple-800',
  },
  TRIAGE: {
    label: 'Triage Handoff',
    pill: 'bg-amber-50 text-amber-700 border-amber-200',
    solid: 'bg-amber-100 text-amber-800',
  },
  ABANDONED: {
    label: 'Abandoned',
    pill: 'bg-rose-50 text-rose-700 border-rose-200',
    solid: 'bg-rose-100 text-rose-800',
  },
  FAILED: {
    label: 'Failed',
    pill: 'bg-slate-100 text-slate-600 border-slate-300',
    solid: 'bg-slate-200 text-slate-700',
  },
};

export const statusMeta = (status) =>
  STATUS_META[status] ?? STATUS_META.FAILED;

/** Filter tabs shown in CallsView — derived from statuses actually present. */
export const CALL_FILTERS = [
  { value: 'ALL', label: 'All Calls' },
  { value: 'SCHEDULED', label: 'Scheduled' },
  { value: 'REDIRECTED', label: 'Redirected' },
  { value: 'ABANDONED', label: 'Dropped' },
  { value: 'FAILED', label: 'Failed' },
];

export function sourceBadgeClass(source = '') {
  if (source.includes('Sync')) return 'bg-violet-100 text-violet-800 border-violet-200';
  if (source.includes('Simulation') || source === 'Direct Simulation') return 'bg-blue-100 text-blue-800 border-blue-200';
  return 'bg-slate-200 text-slate-700 border-slate-300';
}

export function sourceHelp(source = '') {
  if (source.includes('Webhook')) return 'Outcome reported by the voice flow itself (authoritative)';
  if (source.includes('Sync')) return 'Transcript synced from Vogent dial history; outcome inferred when the flow never reported one';
  if (source.includes('Simulation')) return 'Simulated call run through the backend routing engine';
  return 'Call outcome provenance';
}
