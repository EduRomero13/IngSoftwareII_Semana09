const SEVERITY = {
  alta: "bg-red-100 text-red-700 ring-red-200",
  media: "bg-amber-100 text-amber-700 ring-amber-200",
  baja: "bg-emerald-100 text-emerald-700 ring-emerald-200",
};

const STATUS = {
  pending: "bg-slate-100 text-slate-700 ring-slate-200",
  triaged: "bg-sky-100 text-sky-700 ring-sky-200",
  escalated: "bg-red-100 text-red-700 ring-red-200",
  closed: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  discarded: "bg-slate-100 text-slate-500 ring-slate-200",
  open: "bg-red-100 text-red-700 ring-red-200",
};

const VERDICT = {
  verdadero_positivo: "bg-red-100 text-red-700 ring-red-200",
  falso_positivo: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  sospechoso: "bg-amber-100 text-amber-700 ring-amber-200",
};

const STATUS_LABEL = {
  pending: "Pendiente",
  triaged: "Triada",
  escalated: "Escalada",
  closed: "Cerrada",
  discarded: "Descartada",
  open: "Abierto",
};

const VERDICT_LABEL = {
  verdadero_positivo: "Verdadero positivo",
  falso_positivo: "Falso positivo",
  sospechoso: "Sospechoso",
};

export function Badge({ kind = "severity", value }) {
  const palette =
    kind === "severity"
      ? SEVERITY
      : kind === "status"
        ? STATUS
        : VERDICT;
  const label =
    kind === "status"
      ? STATUS_LABEL[value] || value
      : kind === "verdict"
        ? VERDICT_LABEL[value] || value
        : value;
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${
        palette[value] || "bg-slate-100 text-slate-600 ring-slate-200"
      }`}
    >
      {label}
    </span>
  );
}

export function StatCard({ label, value, hint, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    red: "border-red-200 bg-red-50 text-red-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    sky: "border-sky-200 bg-sky-50 text-sky-700",
  };
  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs opacity-70">{hint}</p>}
    </div>
  );
}

export function PageTitle({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function EmptyState({ message }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

export function ErrorAlert({ message }) {
  if (!message) return null;
  return (
    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}
