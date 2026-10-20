import { useCallback, useEffect, useState } from "react";
import { Trash2, UserPlus } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext.jsx";
import { EmptyState, ErrorAlert, PageTitle } from "../components/ui.jsx";

const EMPTY = { username: "", email: "", full_name: "", password: "", role_name: "analyst" };

export default function Users() {
  const { user: me, can } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/users", { params: { page_size: 50 } });
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
      await api.post("/users", form);
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const update = async (id, patch) => {
    try {
      await api.put(`/users/${id}`, patch);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (id) => {
    if (!window.confirm("¿Eliminar este usuario? Su bitácora se conservará.")) return;
    try {
      await api.delete(`/users/${id}`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div>
      <PageTitle
        title="Usuarios y roles"
        subtitle={`${total} usuarios · control de acceso RBAC (ISO 27001 A.5.15)`}
        actions={
          can("users.manage") && (
            <button
              onClick={() => setShowForm((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-500"
            >
              <UserPlus className="h-4 w-4" /> Nuevo usuario
            </button>
          )
        }
      />
      <ErrorAlert message={error} />

      {showForm && (
        <form
          onSubmit={create}
          className="mb-5 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 md:grid-cols-5"
        >
          <input
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            placeholder="username"
            required
            minLength={3}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="correo@ejemplo.com"
            required
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            placeholder="Nombre completo"
            required
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="Contraseña"
            required
            minLength={6}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={form.role_name}
            onChange={(e) => setForm({ ...form, role_name: e.target.value })}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="admin">admin</option>
            <option value="analyst">analyst</option>
            <option value="viewer">viewer</option>
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500 md:col-span-5 md:justify-self-start">
            Crear usuario
          </button>
        </form>
      )}

      {items.length === 0 ? (
        <EmptyState message="No hay usuarios." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Usuario</th>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3">Activo</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">#{row.id}</td>
                  <td className="px-4 py-2.5 font-medium text-slate-800">
                    {row.username}
                    {row.username === me?.username && (
                      <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                        tú
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{row.full_name}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{row.email}</td>
                  <td className="px-4 py-2.5">
                    {can("users.manage") ? (
                      <select
                        value={row.role_name}
                        onChange={(e) => update(row.id, { role_name: e.target.value })}
                        className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="admin">admin</option>
                        <option value="analyst">analyst</option>
                        <option value="viewer">viewer</option>
                      </select>
                    ) : (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                        {row.role_name}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <input
                      type="checkbox"
                      checked={row.is_active}
                      disabled={!can("users.manage") || row.username === me?.username}
                      onChange={(e) => update(row.id, { is_active: e.target.checked })}
                    />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {can("users.manage") && row.username !== me?.username && (
                      <button
                        onClick={() => remove(row.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Eliminar
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
