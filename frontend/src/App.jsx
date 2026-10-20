import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AlertDetail from "./pages/AlertDetail.jsx";
import Alerts from "./pages/Alerts.jsx";
import Audit from "./pages/Audit.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Incidents from "./pages/Incidents.jsx";
import Login from "./pages/Login.jsx";
import Reports from "./pages/Reports.jsx";
import Users from "./pages/Users.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="alerts" element={<Alerts />} />
        <Route
          path="alerts/:id"
          element={
            <ProtectedRoute permission="alerts.read">
              <AlertDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="incidents"
          element={
            <ProtectedRoute permission="incidents.read">
              <Incidents />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute permission="users.read">
              <Users />
            </ProtectedRoute>
          }
        />
        <Route
          path="audit"
          element={
            <ProtectedRoute permission="audit.read">
              <Audit />
            </ProtectedRoute>
          }
        />
        <Route
          path="reports"
          element={
            <ProtectedRoute permission="reports.export">
              <Reports />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
