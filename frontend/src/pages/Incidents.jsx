import { useCallback, useEffect, useState } from "react";
import { Plus, XCircle } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext.jsx";
import { Badge, EmptyState, ErrorAlert, PageTitle } from "../components/ui.jsx";

export default function Incidents() {
  const { can } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", severity: "media", ticket_id: "", notes: "" });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/incidents", { params: { page_size: 50 } });
      setItems(data.items);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (event) => {
    event.preventDefault();
    try {
      await api.post("/incidents", {
        title: form.title,
        severity: form.severity,
        ticket_id: form.ticket_id || null,
        notes: form.notes || null,
      });
      setForm({ title: "", severity: "media", ticket_id: "", notes: "" });
      setShowForm(false);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const close = async (id) => {
    try {
      await api.patch(`/incidents/${id}`, { status: "closed" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div>
      <PageTitle
        title="Incidentes"
        subtitle={`${total} incidentes · ISO 27001 A.5.24 respuesta a incidentes`}
        actions={
          can("incidents.write") && (
            <button
              onClick={() => setShowForm((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-500"
            >
              <Plus className="h-4 w-4" /> Nuevo incidente
            </button>
          )
        }
      />
      <ErrorAlert message={error} />

      {showForm && (
        <form
          onSubmit={create}
          className="mb-5 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-4"
        >
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Título del incidente"
            required
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2"
          />
          <select
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value })}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="alta">Severidad alta</option>
            <option value="media">Severidad media</option>
            <option value="baja">Severidad baja</option>
          </select>
          <input
            value={form.ticket_id}
            onChange={(e) => setForm({ ...form, ticket_id: e.target.value })}
            placeholder="Ticket (OST-xxxx)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <textarea
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Notas / contexto"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-3"
            rows={2}
          />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500">
            Crear
          </button>
        </form>
      )}

      {items.length === 0 ? (
        <EmptyState message="No hay incidentes registrados." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Título</th>
                <th className="px-4 py-3">Severidad</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Apertura</th>
                <th className="px-4 py-3">Ticket</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((incident) => (
                <tr key={incident.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">#{incident.id}</td>
                  <td className="px-4 py-2.5 font-medium text-slate-800">{incident.title}</td>
                  <td className="px-4 py-2.5">
                    <Badge kind="severity" value={incident.severity} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge kind="status" value={incident.status} />
                  </td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">
                    {new Date(incident.opened_at + "Z").toLocaleString("es-PE")}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                    {incident.ticket_id || "-"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {incident.status !== "closed" && can("incidents.write") && (
                      <button
                        onClick={() => close(incident.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Cerrar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
