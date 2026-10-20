import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function ProtectedRoute({ children, permission }) {
  const { isAuthenticated, can } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  if (permission && !can(permission)) {
    return (
      <div className="p-8">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-800">
          <h2 className="font-semibold">Acceso restringido</h2>
          <p className="text-sm">
            Tu rol no tiene el permiso <code className="font-mono">{permission}</code> para ver
            este módulo.
          </p>
        </div>
      </div>
    );
  }
  return children;
}
