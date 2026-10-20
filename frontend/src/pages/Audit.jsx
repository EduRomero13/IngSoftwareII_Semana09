import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext.jsx";
import { EmptyState, ErrorAlert, PageTitle, StatCard } from "../components/ui.jsx";

const MODULES = ["", "login", "alerts", "triage", "incidents", "users", "reports", "metrics", "audit"];
const ACTIONS = ["", "IN", "OUT", "CREATE", "UPDATE", "DELETE", "READ", "EXPORT", "EXECUTE"];

const ACTION_COLORS = {
  IN: "text-emerald-700 bg-emerald-50",
  OUT: "text-slate-600 bg-slate-100",
  CREATE: "text-sky-700 bg-sky-50",
  UPDATE: "text-amber-700 bg-amber-50",
  DELETE: "text-red-700 bg-red-50",
  READ: "text-slate-600 bg-slate-50",
  EXPORT: "text-purple-700 bg-purple-50",
  EXECUTE: "text-emerald-700 bg-emerald-50",
};

export default function Audit() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState(null);
  const [module, setModule] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const pageSize = 25;

  const load = useCallback(async () => {
    try {
      const params = { page, page_size: pageSize };
      if (module) params.module = module;
      if (action) params.action = action;
      const { data } = await api.get("/audit", { params });
      setRows(data.items);
      setTotal(data.total);
      const { data: sum } = await api.get("/audit/summary");
      setSummary(sum);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [page, module, action]);

  useEffect(() => {
    load();
  }, [load]);

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <PageTitle
        title="Bitácora de auditoría"
        subtitle="Entradas y salidas por módulo: usuario, fecha, hora y acción (ISO 27001 A.8.15)"
        actions={
          <button
            onClick={load}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            <RefreshCw className="h-4 w-4" /> Actualizar
          </button>
        }
      />
      <ErrorAlert message={error} />

      {summary && (
        <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Eventos totales" value={summary.total} tone="sky" />
          <StatCard
            label="Módulos con actividad"
            value={summary.by_module.length}
            hint="trazabilidad por módulo"
          />
          <StatCard
            label="Usuario más activo"
            value={summary.top_users[0]?.username || "-"}
            hint={`${summary.top_users[0]?.count || 0} eventos`}
            tone="emerald"
          />
          <StatCard
            label="Visibilidad"
            value={isAdmin ? "Global (admin)" : "Propia"}
            hint={isAdmin ? "todos los usuarios" : `solo ${user?.username}`}
            tone="amber"
          />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={module}
          onChange={(e) => {
            setModule(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {MODULES.map((m) => (
            <option key={m} value={m}>
              {m ? `Módulo: ${m}` : "Todos los módulos"}
            </option>
          ))}
        </select>
        <select
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a ? `Acción: ${a}` : "Todas las acciones"}
            </option>
          ))}
        </select>
        <span className="self-center text-xs text-slate-500">
          IN = entrada · OUT = salida del sistema
        </span>
      </div>

      {rows.length === 0 ? (
        <EmptyState message="Sin eventos para los filtros seleccionados." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Hora</th>
                <th className="px-4 py-3">Usuario</th>
                <th className="px-4 py-3">Módulo</th>
                <th className="px-4 py-3">Acción</th>
                <th className="px-4 py-3">Ruta</th>
                <th className="px-4 py-3">IP</th>
                <th className="px-4 py-3">Cód.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const created = new Date(row.created_at + "Z");
                return (
                  <tr key={row.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-xs text-slate-600">
                      {created.toLocaleDateString("es-PE")}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-600">
                      {created.toLocaleTimeString("es-PE")}
                    </td>
                    <td className="px-4 py-2.5 font-medium text-slate-800">{row.username || "-"}</td>
                    <td className="px-4 py-2.5 text-xs uppercase text-slate-600">{row.module}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-bold ${
                          ACTION_COLORS[row.action] || "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {row.action}
                      </span>
                    </td>
                    <td className="max-w-[260px] truncate px-4 py-2.5 font-mono text-xs text-slate-500">
                      {row.method} {row.path}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{row.ip || "-"}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{row.status_code || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
        <span>
          Página {page} de {pages} · {total} eventos
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
