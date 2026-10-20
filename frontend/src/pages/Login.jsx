import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Activity, Lock, ShieldAlert, User } from "lucide-react";
import { useAuth } from "../auth/AuthContext.jsx";
import { errorMessage } from "../api/client";

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-600">
            <Activity className="h-7 w-7 text-white" />
          </div>
          <h1 className="mt-4 text-2xl font-bold text-white">SOC-Lite</h1>
          <p className="mt-1 text-sm text-slate-400">
            Triaje automático de alertas · NIST CSF DE.AE · ISO 27001
          </p>
        </div>

        <form
          onSubmit={submit}
          className="space-y-4 rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-xl"
        >
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">
              Usuario
            </span>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full rounded-lg border border-slate-600 bg-slate-900 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 outline-none focus:border-emerald-500"
                placeholder="analyst"
              />
            </div>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">
              Contraseña
            </span>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-lg border border-slate-600 bg-slate-900 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 outline-none focus:border-emerald-500"
                placeholder="••••••••"
              />
            </div>
          </label>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-60"
          >
            {loading ? "Validando..." : "Iniciar sesión"}
          </button>
          <p className="text-center text-xs text-slate-500">
            admin/Admin123! · analyst/Analyst123! · viewer/Viewer123!
          </p>
        </form>
      </div>
    </div>
  );
}
