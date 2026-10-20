import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, Search, Zap } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext.jsx";
import { Badge, EmptyState, ErrorAlert, PageTitle } from "../components/ui.jsx";

const SEVERITIES = ["", "alta", "media", "baja"];
const STATUSES = ["", "pending", "triaged", "escalated", "closed"];

export default function Alerts() {
  const { can } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const page_size = pageSize;

  const load = useCallback(async () => {
    try {
      const params = { page, page_size };
      if (severity) params.severity = severity;
      if (status) params.status = status;
      if (search) params.q = search;
      const { data } = await api.get("/alerts", { params });
      setItems(data.items);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [page, severity, status, search, page_size]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, [load]);

  const triage = async (id) => {
    setBusyId(id);
    try {
      await api.post(`/triage/${id}`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <PageTitle
        title="Alertas"
        subtitle={`${total} alertas · ingesta desde Wazuh / OPNsense`}
        actions={
          <button
            onClick={load}
            className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <RefreshCw className="h-4 w-4" /> Actualizar
          </button>
        }
      />
      <ErrorAlert message={error} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Buscar título, IP, descripción..."
            className="w-72 rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-sky-500"
          />
        </div>
        <select
          value={severity}
          onChange={(e) => {
            setSeverity(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s ? `Severidad: ${s}` : "Todas las severidades"}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? `Estado: ${s}` : "Todos los estados"}
            </option>
          ))}
        </select>
      </div>

      {items.length === 0 ? (
        <EmptyState message="No hay alertas con los filtros seleccionados." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Fuente</th>
                <th className="px-4 py-3">Severidad</th>
                <th className="px-4 py-3">Título</th>
                <th className="px-4 py-3">Origen</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((alert) => (
                <tr key={alert.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">#{alert.id}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">
                    {new Date(alert.created_at + "Z").toLocaleString("es-PE")}
                  </td>
                  <td className="px-4 py-2.5 text-xs uppercase text-slate-500">{alert.source}</td>
                  <td className="px-4 py-2.5">
                    <Badge kind="severity" value={alert.severity} />
                  </td>
                  <td className="max-w-xs px-4 py-2.5">
                    <Link
                      to={`/alerts/${alert.id}`}
                      className="block truncate font-medium text-slate-800 hover:text-sky-600"
                      title={alert.title}
                    >
                      {alert.title}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{alert.src_ip}</td>
                  <td className="px-4 py-2.5">
                    <Badge kind="status" value={alert.status} />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {alert.status === "pending" && can("triage.execute") && (
                      <button
                        onClick={() => triage(alert.id)}
                        disabled={busyId === alert.id}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
                      >
                        <Zap className="h-3.5 w-3.5" />
                        {busyId === alert.id ? "Triando..." : "Triar"}
                      </button>
                    )}
                    <Link
                      to={`/alerts/${alert.id}`}
                      className="ml-2 inline-flex rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      Ver detalle
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
        <span>
          Página {page} de {pages} · {total} registros
        </span>
        <div className="flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-40"
          >
            Anterior
          </button>
          <button
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
}
