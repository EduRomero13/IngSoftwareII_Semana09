import {
  Activity,
  AlertTriangle,
  ClipboardList,
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Users,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, perm: "metrics.read", end: true },
  { to: "/alerts", label: "Alertas", icon: AlertTriangle, perm: "alerts.read" },
  { to: "/incidents", label: "Incidentes", icon: ShieldCheck, perm: "incidents.read" },
  { to: "/users", label: "Usuarios", icon: Users, perm: "users.read" },
  { to: "/audit", label: "Auditoría", icon: History, perm: "audit.read" },
  { to: "/reports", label: "Reportes", icon: FileText, perm: "reports.export" },
];

const ROLE_COLORS = {
  admin: "bg-purple-100 text-purple-700",
  analyst: "bg-sky-100 text-sky-700",
  viewer: "bg-slate-200 text-slate-600",
};

export default function Layout() {
  const { user, logout, can } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-60 flex-col bg-slate-900 text-slate-200">
        <div className="flex items-center gap-2 px-5 py-5">
          <Activity className="h-7 w-7 text-emerald-400" />
          <div>
            <p className="text-lg font-bold leading-tight text-white">SOC-Lite</p>
            <p className="text-[11px] uppercase tracking-wider text-slate-400">
              Triaje de alertas
            </p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.filter((item) => can(item.perm)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                  isActive
                    ? "bg-emerald-600 font-semibold text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">{user?.username}</p>
              <span
                className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  ROLE_COLORS[user?.role] || "bg-slate-700 text-slate-300"
                }`}
              >
                {user?.role}
              </span>
            </div>
            <button
              onClick={logout}
              title="Cerrar sesión"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="ml-60 flex-1 px-8 py-7">
        <Outlet />
      </main>
    </div>
  );
}
