import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api, { errorMessage } from "../api/client";
import { Badge, ErrorAlert, PageTitle, StatCard } from "../components/ui.jsx";

const SEV_COLORS = { alta: "#dc2626", media: "#d97706", baja: "#059669" };
const TREND_COLOR = { total: "#2563eb", alta: "#dc2626" };

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/metrics/overview");
      setMetrics(data);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000); // refresco cada 30 s
    return () => clearInterval(id);
  }, [load]);

  if (loading && !metrics) return <p className="text-sm text-slate-500">Cargando métricas...</p>;
  if (!metrics) return <ErrorAlert message={error} />;

  const severityData = ["alta", "media", "baja"].map((sev) => ({
    name: sev.charAt(0).toUpperCase() + sev.slice(1),
    alertas: metrics.by_severity[sev] || 0,
  }));
  const verdictData = [
    { name: "Verdaderos positivos", value: metrics.recent_triage.filter((t) => t.verdict === "verdadero_positivo").length },
    { name: "Falsos positivos", value: metrics.recent_triage.filter((t) => t.verdict === "falso_positivo").length },
    { name: "Sospechosos", value: metrics.recent_triage.filter((t) => t.verdict === "sospechoso").length },
  ].filter((d) => d.value > 0);
  const PIE_COLORS = ["#dc2626", "#059669", "#d97706"];

  return (
    <div>
      <PageTitle
        title="Dashboard operacional"
        subtitle="Métricas del SOC-Lite · NIST CSF DE.AE (análisis de anomalías)"
        actions={
          <button
            onClick={load}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Actualizar
          </button>
        }
      />
      <ErrorAlert message={error} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        <StatCard label="Alertas totales" value={metrics.total_alerts} tone="sky" />
        <StatCard label="Pendientes" value={metrics.pending_alerts} tone="amber" hint="requieren triaje" />
        <StatCard label="Triadas" value={metrics.triaged_alerts} tone="emerald" />
        <StatCard label="MTTT promedio" value={`${metrics.avg_mttt_seconds}s`} tone="sky" hint="ingesta → triaje" />
        <StatCard
          label="Tasa falsos positivos"
          value={`${metrics.false_positive_rate}%`}
          tone={metrics.false_positive_rate > 70 ? "red" : "emerald"}
          hint="objetivo: reducirla"
        />
        <StatCard label="Incidentes abiertos" value={metrics.open_incidents} tone={metrics.open_incidents ? "red" : "slate"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Tendencia de alertas (7 días)
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={metrics.trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="total" stroke={TREND_COLOR.total} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="alta" stroke={TREND_COLOR.alta} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Alertas por severidad</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={severityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="alertas" radius={[6, 6, 0, 0]}>
                {severityData.map((entry) => (
                  <Cell key={entry.name} fill={SEV_COLORS[entry.name.toLowerCase()]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Veredictos recientes ({metrics.recent_triage.length})
          </h2>
          {verdictData.length === 0 ? (
            <p className="text-sm text-slate-500">Sin triajes recientes.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={verdictData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} label>
                  {verdictData.map((_, index) => (
                    <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Top orígenes</h2>
          <ul className="space-y-2">
            {metrics.top_sources.map((source) => (
              <li key={source.ip} className="flex items-center justify-between text-sm">
                <span className="font-mono text-slate-700">{source.ip}</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-red-500"
                      style={{
                        width: `${Math.round((source.count / metrics.top_sources[0].count) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="w-6 text-right text-slate-500">{source.count}</span>
                </div>
              </li>
            ))}
            {metrics.top_sources.length === 0 && (
              <li className="text-sm text-slate-500">Sin datos.</li>
            )}
          </ul>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Últimos triajes</h2>
            <Link to="/alerts" className="text-xs font-medium text-sky-600 hover:underline">
              Ver alertas →
            </Link>
          </div>
          <ul className="space-y-2">
            {metrics.recent_triage.slice(0, 6).map((item) => (
              <li key={item.alert_id} className="rounded-lg border border-slate-100 p-2">
                <Link to={`/alerts/${item.alert_id}`} className="block">
                  <p className="truncate text-xs font-medium text-slate-800">{item.title}</p>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Badge kind="severity" value={item.severity} />
                    <Badge kind="verdict" value={item.verdict} />
                  </div>
                </Link>
              </li>
            ))}
            {metrics.recent_triage.length === 0 && (
              <li className="text-sm text-slate-500">Aún no hay triajes.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
